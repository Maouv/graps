"""Core AST traversal — Layer 1 static analysis (BLUEPRINT Section 4)."""

from __future__ import annotations

import ast
import signal
import threading
import tokenize
from pathlib import Path

from graps.scanner import (
    ParseResult,
    ParsedBranch,
    ParsedCall,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)

_MAX_BYTES = 1_000_000  # 1MB (Section 14)
_TIMEOUT_S = 5          # Section 14

# ponytail: re-export data carriers + legacy ParseResult alias so resolver/
# risk_analyzer keep importing from this module untouched. BLUEPRINT §4 only
# forbids graph_builder+above from importing the concrete *parser*; data
# carriers may be re-exported.
__all__ = [
    "safe_parse",
    "ParsedFile", "ParsedFunction", "ParsedImport",
    "ParsedCall", "ParsedBranch", "ParsedRoute", "ParseResult",
]


# Data carriers now live in graps.scanner (BLUEPRINT §4 BaseParser interface).
# --- Pre-parse guards (Section 14 edge cases) --------------------------------

def safe_parse(path: Path) -> ParsedFile:
    """Guarded entry point: size/timeout/encoding checks, then run visitor.

    Section 14 guards before ast.parse():
      - file > 1MB        → skip + warning
      - parse timeout >5s → skip + warning
      - non-UTF-8         → tokenize.detect_encoding()
    Returns ParsedFile with warnings populated; never raises on bad input.
    """
    result = ParsedFile(path=path)

    try:
        if path.stat().st_size > _MAX_BYTES:
            result.warnings.append(f"{path}: file too large (>1MB), skipped")
            return result
    except OSError as e:
        result.warnings.append(f"{path}: stat failed: {e}")
        return result

    # Detect encoding from the file's coding cookie before reading (Section 14).
    try:
        with open(path, "rb") as fb:
            encoding, _ = tokenize.detect_encoding(fb.readline)
        source = path.read_text(encoding=encoding)
    except (OSError, SyntaxError, UnicodeDecodeError, LookupError) as e:
        result.warnings.append(f"{path}: encoding/read error: {e}")
        return result

    # ponytail: signal.alarm is Unix-only; non-Unix runs without a timeout guard.
    has_alarm = hasattr(signal, "SIGALRM") and threading.current_thread() is threading.main_thread()

    def _timeout(signum: int, frame: object) -> None:
        raise TimeoutError

    if has_alarm:
        old = signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(_TIMEOUT_S)
    try:
        tree = ast.parse(source, filename=str(path))
    except (TimeoutError, SyntaxError, MemoryError, ValueError, RecursionError) as e:
        result.warnings.append(f"{path}: parse failed: {type(e).__name__}: {e}")
        return result
    finally:
        if has_alarm:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

    visitor = _ScannerVisitor(path.stem)
    visitor.visit(tree)
    parsed = visitor.result()
    parsed.path = path
    parsed.warnings = result.warnings + parsed.warnings
    return parsed


# --- Visitor (stdlib ast.NodeVisitor dispatch) -------------------------------

class _ScannerVisitor(ast.NodeVisitor):
    """Single-pass visitor. Tracks scope stack for nesting/qualified names."""

    def __init__(self, module_name: str) -> None:
        self.module = module_name
        self._scope: list[str] = [module_name]      # qualified-name components
        self._kind: list[str] = ["module"]           # parallel: module/class/func
        self._in_try = 0                             # try-body depth (Section 14)
        # FEAT-0017: per-function direct static call sites (source order).
        # Top of stack = current enclosing function's call list; empty at module scope.
        self._call_stacks: list[list[ParsedCall]] = []
        # FEAT-0019: per-function control-flow branch markers (source order).
        self._branch_stacks: list[list[ParsedBranch]] = []
        self.functions: list[ParsedFunction] = []
        self.imports: list[ParsedImport] = []
        self.classes: list[dict[str, object]] = []
        self.exported_names: list[str] = []
        self.warnings: list[str] = []

    def _qual(self, name: str) -> str:
        return ".".join(self._scope + [name])

    def _handle_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        is_nested = "func" in self._kind  # an enclosing function exists
        end_line = getattr(node, "end_lineno", None) or node.lineno
        pf = ParsedFunction(
            name=node.name,
            qualified_name=self._qual(node.name),
            lineno=node.lineno,
            line_start=node.lineno,
            line_end=end_line,
            is_nested=is_nested,
            is_property=any(_decorator_name(d) == "property" for d in node.decorator_list),
            is_private=node.name.startswith("_"),
            decorators=[_decorator_name(d) for d in node.decorator_list],
            parent=".".join(self._scope) if self._kind[-1] != "module" else None,
            calls=[],
            branches=[],
            routes=_extract_routes(node.decorator_list),
        )
        self.functions.append(pf)
        self._scope.append(node.name)
        self._kind.append("func")
        # FEAT-0017: record direct call sites in source order. Decorators are
        # evaluated at def-time (not call-time), so visit them WITHOUT a call
        # stack to keep them out of call_sequence. Body statements get the stack.
        self._call_stacks.append(pf.calls)
        self._branch_stacks.append(pf.branches)
        for stmt in node.body:
            self.visit(stmt)
        self._call_stacks.pop()
        self._branch_stacks.pop()
        self._scope.pop()
        self._kind.pop()

    # Section 14: nested funcs → is_nested via scope stack
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_func(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # FEAT-0017: retain classes with source ranges + direct method names.
        self.classes.append({
            "name": node.name,
            "qualified_name": self._qual(node.name),
            "line_start": node.lineno,
            "line_end": getattr(node, "end_lineno", None) or node.lineno,
            "decorators": [_decorator_name(d) for d in node.decorator_list],
            "methods": [
                n.name for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ],
            "parent": ".".join(self._scope) if self._kind[-1] != "module" else None,
        })
        self._scope.append(node.name)
        self._kind.append("class")
        self.generic_visit(node)
        self._scope.pop()
        self._kind.pop()

    # Section 14: plain + star imports
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(ParsedImport(
                target=alias.name, lineno=node.lineno,
                is_conditional=bool(self._in_try),
            ))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        base = "." * (node.level or 0) + (node.module or "")
        sep = "" if base.endswith(".") else "."  # keep leading dots for relative imports
        for alias in node.names:
            star = alias.name == "*"
            self.imports.append(ParsedImport(
                target=base if star else f"{base}{sep}{alias.name}",
                lineno=node.lineno,
                is_conditional=bool(self._in_try),
                is_star=star,
            ))
            if star:
                self.warnings.append(f"line {node.lineno}: star import from {base!r}")

    # Section 14: __all__ → exported_names; importlib/exec/eval → warnings
    def visit_Assign(self, node: ast.Assign) -> None:
        if any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            if isinstance(node.value, (ast.List, ast.Tuple)):
                self.exported_names = [
                    e.value for e in node.value.elts
                    if isinstance(e, ast.Constant) and isinstance(e.value, str)
                ]
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        fn = _decorator_name(node.func)
        if fn in ("exec", "eval"):
            self.warnings.append(f"line {node.lineno}: dynamic_code ({fn})")
        elif fn in ("importlib.import_module", "import_module"):
            self.warnings.append(f"line {node.lineno}: dynamic import (importlib)")
            self.imports.append(ParsedImport(
                target="<dynamic>", lineno=node.lineno,
                is_conditional=bool(self._in_try), is_dynamic=True,
            ))
        # FEAT-0017: record direct call sites in source order (call_sequence).
        # Only when inside a function body (a call stack is active). Dynamic
        # dispatch (exec/eval/importlib) is excluded — it has no static target.
        elif self._call_stacks and fn and not fn.startswith("("):
            self._call_stacks[-1].append(ParsedCall(name=fn, line=node.lineno))
        self.generic_visit(node)

    # FEAT-0019: control-flow branch markers (if/for/while/try/return).
    def visit_If(self, node: ast.If) -> None:
        if self._branch_stacks:
            self._branch_stacks[-1].append(ParsedBranch(kind="if", line=node.lineno))
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        if self._branch_stacks:
            self._branch_stacks[-1].append(ParsedBranch(kind="for", line=node.lineno))
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        if self._branch_stacks:
            self._branch_stacks[-1].append(ParsedBranch(kind="for", line=node.lineno))
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        if self._branch_stacks:
            self._branch_stacks[-1].append(ParsedBranch(kind="while", line=node.lineno))
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if self._branch_stacks:
            self._branch_stacks[-1].append(ParsedBranch(kind="return", line=node.lineno))
        self.generic_visit(node)

    # Section 14: try/except import → is_conditional on both branches
    def visit_Try(self, node: ast.Try) -> None:
        if self._branch_stacks:
            self._branch_stacks[-1].append(ParsedBranch(kind="try", line=node.lineno))
        self._in_try += 1
        for child in node.body:
            self.visit(child)
        self._in_try -= 1
        for h in node.handlers:
            if self._branch_stacks:
                self._branch_stacks[-1].append(ParsedBranch(kind="except", line=h.lineno))
            self._in_try += 1
            for child in h.body:
                self.visit(child)
            self._in_try -= 1
        for child in node.orelse + node.finalbody:
            self.visit(child)

    def result(self) -> ParsedFile:
        return ParsedFile(
            path=Path(self.module),
            functions=self.functions,
            imports=self.imports,
            classes=self.classes,
            exported_names=self.exported_names,
            warnings=self.warnings,
        )


def _decorator_name(node: ast.expr) -> str:
    """Flatten a decorator expr to dotted string (detect @property)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_decorator_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):           # @app.route("/") → app.route
        return _decorator_name(node.func)
    return ""


# FEAT-0019: HTTP route decorator extraction (request_flow).
_HTTP_METHODS = {"get", "post", "put", "delete", "patch"}


def _first_str_arg(call: ast.Call) -> str | None:
    """Extract first string positional arg from a Call node, else None."""
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    return None


def _method_from_kwargs(call: ast.Call) -> str:
    """Extract HTTP method from Flask ``methods=["GET"]`` kwarg, default GET."""
    for kw in call.keywords:
        if kw.arg == "methods" and isinstance(kw.value, ast.List) and kw.value.elts:
            first = kw.value.elts[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                return first.value.upper()
    return "GET"


def _extract_routes(decorators: list[ast.expr]) -> list[ParsedRoute]:
    """Extract HTTP routes from decorator list (FastAPI/Flask style).

    Detects ``@app.get("/x")``, ``@router.post("/y")``, ``@app.route("/z")``.
    Returns [] if no route decorators found.
    """
    out: list[ParsedRoute] = []
    for d in decorators:
        if not isinstance(d, ast.Call):
            continue
        name = _decorator_name(d.func)
        parts = name.split(".")
        last = parts[-1].lower() if parts else ""
        if last == "route":
            path = _first_str_arg(d)
            method = _method_from_kwargs(d)
        elif last in _HTTP_METHODS:
            path = _first_str_arg(d)
            method = last.upper()
        else:
            continue
        if path is not None:
            out.append(ParsedRoute(method=method, path=path, line=d.lineno))
    return out


if __name__ == "__main__":
    import tempfile

    src = '''
import os
from a import *
__all__ = ["foo", "Bar"]

class Bar:
    @property
    def p(self): ...
    def m(self):
        def inner(): ...

def foo():
    exec("x=1")

try:
    import fast_json as j
except ImportError:
    import json as j

import importlib
importlib.import_module("dynamic.mod")
'''
    p = Path(tempfile.mkdtemp()) / "sample.py"
    p.write_text(src)
    r = safe_parse(p)

    quals = {f.qualified_name: f for f in r.functions}
    assert "sample.Bar.m.inner" in quals and quals["sample.Bar.m.inner"].is_nested
    assert not quals["sample.foo"].is_nested
    assert quals["sample.Bar.p"].is_property
    assert quals["sample.Bar.m"].parent == "sample.Bar"
    assert quals["sample.foo"].parent is None

    assert r.exported_names == ["foo", "Bar"]
    assert any(i.is_star for i in r.imports)
    assert any(i.is_conditional and i.target == "fast_json" for i in r.imports)
    assert any(i.is_dynamic for i in r.imports)
    assert any("dynamic_code" in w for w in r.warnings)
    assert any("importlib" in w for w in r.warnings)

    # guards: oversized + syntax error never raise
    big = Path(tempfile.mkdtemp()) / "big.py"
    big.write_text("x = 1\n" * 200_000)
    assert "too large" in " ".join(safe_parse(big).warnings)
    bad = Path(tempfile.mkdtemp()) / "bad.py"
    bad.write_text("def (:\n")
    assert "parse failed" in " ".join(safe_parse(bad).warnings)

    # FEAT-0017: source ranges, direct call sites, and classes are retained.
    src2 = "class C:\n    def m(self):\n        self.helper()\n        return 1\n    def helper(self):\n        return 2\n"
    p2 = Path(tempfile.mkdtemp()) / "ranges.py"
    p2.write_text(src2)
    r2 = safe_parse(p2)
    quals2 = {f.qualified_name: f for f in r2.functions}
    m = quals2["ranges.C.m"]
    assert m.line_start == 2 and m.line_end == 4, (m.line_start, m.line_end)
    assert [c.name for c in m.calls] == ["self.helper"], m.calls
    assert [c.line for c in m.calls] == [3], m.calls
    assert r2.classes[0]["name"] == "C"
    assert r2.classes[0]["line_start"] == 1 and r2.classes[0]["line_end"] == 6
    assert r2.classes[0]["methods"] == ["m", "helper"]

    print("self-check ok")
