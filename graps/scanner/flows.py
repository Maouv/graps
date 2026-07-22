"""Deterministic call_sequence flow resolution (DEC-0005, architecture §Flow taxonomy).

Structural truth only — no AI. For each function we emit, in source order, the
direct static call sites it makes. Resolve the clear, deterministic cases; every
other call stays explicitly ``unresolved`` with a reason and candidate function
IDs (FEAT-0017: "unknown dynamic relations remain unresolved with
reason/confidence"). This is the MVP direct-call sequence — never marketed as
complete runtime control flow (DEC-0005).

Resolution rules (MVP):
  ``self.x`` / ``cls.x`` -> method ``x`` in the same enclosing class.
  bare ``name``           -> same-file function or class named ``name``; else a
                             function/class named ``name`` reachable via
                             ``from <pkg> import name``.
  ``X.attr``              -> ``from <pkg> import X``-style import resolving to a
                             file that defines ``attr`` as a function or class.
  everything else         -> unresolved (external/dynamic/attribute dispatch).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from graps.scanner import ParsedFile, ParsedFunction
from graps.scanner.ids import class_id, flow_id, function_id, to_posix_rel
from graps.scanner.resolver import resolve_import

# --- Flow-worthiness taxonomy (spike-flow-classification.md, 10 rows) ---------

@dataclass
class Classification:
    """Flow-worthiness classification result.

    ``category``     : taxonomy row short name (e.g. "1or2_trivial", "3_delegator").
    ``flow_worthy``  : should the Flow tab render for this function?
    ``label``        : Source-tab label when flow_worthy=False.
    ``reason``       : one-line structural justification.
    """
    category: str
    flow_worthy: bool
    label: str
    reason: str


_CONTROL_KINDS = {"if", "for", "while", "try", "except"}


def _is_stub(func: ParsedFunction, body: str, has_control: bool) -> str | None:
    """Return stub label if the function is a stub/empty, else None.

    ponytail: body-text stub detection — parser doesn't expose body AST here.
    Regex + substring checks with n_calls==0 guard to limit false positives.
    Upgrade path: extend ParsedFunction with is_stub flag (parser-level).
    """
    if has_control:
        return None
    # raise NotImplementedError() — call-name check, no body text needed.
    if any("NotImplementedError" in c.name for c in func.calls):
        return "not implemented"
    if not body or func.calls:
        return None
    # Body-text markers — only for 0-call functions (else real code with a
    # TODO comment or a string containing "pass" would false-positive).
    if "NotImplementedError" in body or "TODO" in body:
        return "not implemented"
    if re.search(r"^\s*pass\s*$", body, re.MULTILINE):
        return "stub"
    if re.search(r"^\s*\.\.\.\s*$", body, re.MULTILINE):
        return "stub"
    return None


def classify_flow_worthiness(func: ParsedFunction, body: str) -> Classification:
    """Classify a function per the flow-worthiness taxonomy (10 rows).

    Pure, deterministic, no I/O. See spike-flow-classification.md for the
    taxonomy table and the two v2 refinements applied here:
      - Cat 4: collapse chained method calls on one line to 1 logical call.
      - Cat 7: require calls in a return/control context, not bare expressions.
      - Cat 10: route NotImplementedError stubs here, not cat 7.
    """
    calls = func.calls
    branch_kinds = {b.kind for b in func.branches}
    has_control = bool(branch_kinds & _CONTROL_KINDS)
    has_return = "return" in branch_kinds
    has_route = bool(func.routes)
    return_lines = {b.line for b in func.branches if b.kind == "return"}

    # v2 refinement 1: chained method calls on one line count as 1 logical call.
    n_logical = len({c.line for c in calls})
    # v2 refinement 2: is any call inside a return statement?
    calls_in_return = any(c.line in return_lines for c in calls)

    # Cat 10: stub / not implemented.
    stub = _is_stub(func, body, has_control)
    if stub is not None:
        return Classification("10_stub", False, stub, "empty body / NotImplementedError")

    # Cats 1+2: pure/trivial or data definition (no calls, no control, no routes).
    if not calls and not has_control and not has_route:
        return Classification("1or2_trivial", False, "pure function",
                              "no calls, no branches, no routes")

    # Cat 3: delegator — 1 logical call, immediately returned, no control.
    if n_logical == 1 and has_return and not has_control and not has_route:
        return Classification("3_delegator", False, "delegator", "single call returned")

    # v2 refinement 2: bare-expression call (not in return, no control) → trivial.
    if calls and not has_control and not has_route and not calls_in_return:
        return Classification("1or2_trivial", False, "pure function",
                              "bare expression call, not returned")

    # Cat 4: linear sequence — ≥2 logical calls, no control.
    if n_logical >= 2 and not has_control and not has_route:
        return Classification("4_linear", True, "linear sequence", "≥2 sequential calls")

    # Cats 5/6/8: control flow present.
    if has_control:
        if "if" in branch_kinds:
            return Classification("5_branch", True, "branching logic", "if/elif/else")
        if "for" in branch_kinds or "while" in branch_kinds:
            return Classification("6_loop", True, "loop/iteration", "for/while")
        return Classification("8_error", True, "error handling", "try/except")

    # Cat 7: unresolved call in context — partial, flow-worthy.
    # ponytail: after v2 refinements this is a catch-all; most paths hit cats
    # 1-6/8/10 above. Kept so any uncategorised call-bearing function still
    # gets a Flow tab (show-what's-known) rather than an empty Source fallback.
    if calls:
        return Classification("7_unresolved", True, "unresolved call",
                              "partial — show what's known")

    # Fallback: routes or mixed markers — flow-worthy.
    return Classification("misc_flow", True, "mixed markers", "routes or mixed markers")


# --- Indexes + resolution (unchanged) ----------------------------------------


def _build_indexes(
    results: list[ParsedFile], root: Path
) -> tuple[dict[str, list], dict[str, list[dict]], dict[str, list[str]]]:
    """file_id -> [ParsedFunction]; file_id -> [class dict]; short name -> [ids].

    Classes are indexed alongside functions (FEAT-0017 follow-up) so a
    constructor call (``Foo()``) can resolve to the class definition the same
    way a function call resolves to a function definition.
    """
    file_funcs: dict[str, list] = {}
    file_classes: dict[str, list[dict]] = {}
    name_to_ids: dict[str, list[str]] = {}
    for r in results:
        rel = r.id or to_posix_rel(r.path, root)
        file_funcs[rel] = r.functions
        file_classes[rel] = r.classes
        for f in r.functions:
            fid = function_id(rel, f.qualified_name)
            name_to_ids.setdefault(f.name, []).append(fid)
        for cls in r.classes:
            qn = cls.get("qualified_name") or cls.get("name", "")
            if not qn:
                continue
            cid = class_id(rel, qn)
            name_to_ids.setdefault(cls["name"], []).append(cid)
    return file_funcs, file_classes, name_to_ids


def _resolved_import_files(result: ParsedFile, root: Path) -> list[tuple[str, str, str]]:
    """Imports that resolve to an in-root file: (last_segment, resolved_rel, target)."""
    out: list[tuple[str, str, str]] = []
    for imp in result.imports:
        if imp.is_dynamic or imp.is_star or not imp.target:
            continue
        resolved = resolve_import(imp, result.path, root)
        if resolved is None:
            continue
        rrel = to_posix_rel(resolved, root)
        last = imp.target.split(".")[-1]
        out.append((last, rrel, imp.target))
    return out


def _resolve_call(
    name: str, calling: Any, rel: str,
    file_funcs: dict[str, list],
    file_classes: dict[str, list[dict]],
    name_to_ids: dict[str, list[str]],
    imported_files: list[tuple[str, str, str]],
) -> tuple[str | None, list[str], str | None]:
    """Return (target_id, candidates, unresolved_reason). target_id set if resolved."""
    # self.x / cls.x -> same enclosing class method.
    if name.startswith("self.") or name.startswith("cls."):
        method = name.split(".", 1)[1]
        same = [f for f in file_funcs.get(rel, []) if f.name == method]
        for f in same:
            if f.parent == calling.parent:
                return function_id(rel, f.qualified_name), [], None
        return None, [function_id(rel, f.qualified_name) for f in same], "method_not_in_class"

    # X.attr -> from-import whose local name == X resolving to a file defining
    # attr as a function or a class (constructor call, e.g. ``mod.Foo()``).
    if "." in name:
        base, attr = name.rsplit(".", 1)
        for last, rrel, _target in imported_files:
            if last == base:
                target_f = next((f for f in file_funcs.get(rrel, []) if f.name == attr), None)
                if target_f is not None:
                    return function_id(rrel, target_f.qualified_name), [], None
                target_c = next((c for c in file_classes.get(rrel, []) if c["name"] == attr), None)
                if target_c is not None:
                    return class_id(rrel, target_c.get("qualified_name") or target_c.get("name", "")), [], None
        return None, name_to_ids.get(attr, []), "attribute_call_unresolved"

    # bare name -> same-file function/class, else from-import named `name`.
    same = [f for f in file_funcs.get(rel, []) if f.name == name]
    if same:
        return function_id(rel, same[0].qualified_name), [], None
    same_cls = [c for c in file_classes.get(rel, []) if c["name"] == name]
    if same_cls:
        return class_id(rel, same_cls[0].get("qualified_name") or same_cls[0].get("name", "")), [], None
    for last, rrel, _target in imported_files:
        if last == name:
            target_f = next((f for f in file_funcs.get(rrel, []) if f.name == name), None)
            if target_f is not None:
                return function_id(rrel, target_f.qualified_name), [], None
            target_c = next((c for c in file_classes.get(rrel, []) if c["name"] == name), None)
            if target_c is not None:
                return class_id(rrel, target_c.get("qualified_name") or target_c.get("name", "")), [], None
    return None, name_to_ids.get(name, []), "unqualified_name_not_in_scope"


def build_call_edges_and_flows(
    results: list[ParsedFile], root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (call_edges, flows) for the whole project.

    call_edges: ordered, deterministic, with kind/confidence/target/candidates/
    unresolved_reason. flows: one ``call_sequence`` per flow-worthy function
    that makes >=1 call (steps mirroring its call edges in source order); one
    ``source_only`` marker per not-flow-worthy function so the frontend renders
    a Source tab with a category-specific label instead of "no flow step found"
    (spike-flow-classification.md).
    """
    file_funcs, file_classes, name_to_ids = _build_indexes(results, root)
    call_edges: list[dict[str, Any]] = []
    flows: list[dict[str, Any]] = []

    for result in sorted(results, key=lambda r: r.id or to_posix_rel(r.path, root)):
        rel = result.id or to_posix_rel(result.path, root)
        imported_files = _resolved_import_files(result, root)
        # Read source once per file for body-text stub detection. The taxonomy
        # classifier is pure (no I/O); the caller provides the body.
        try:
            src_lines = result.path.read_text(errors="replace").splitlines()
        except OSError:
            src_lines = []
        for func in result.functions:
            src = function_id(rel, func.qualified_name)
            ls = func.line_start or func.lineno
            le = func.line_end or ls
            body = "\n".join(src_lines[ls - 1:le]) if src_lines and ls > 0 else ""
            cls = classify_flow_worthiness(func, body)

            if not cls.flow_worthy:
                # Skip call_sequence emission; emit a source_only marker so the
                # frontend renders Source tab with a category-specific label.
                flows.append({
                    "id": flow_id(src, "source_only"),
                    "kind": "source_only",
                    "root_id": src,
                    "label": cls.label,
                    "category": cls.category,
                })

            if not func.calls:
                continue

            # Call edges are emitted for the graph view regardless of
            # flow_worthy — a delegator's single call still belongs in the
            # call graph even though its Flow tab is suppressed.
            steps: list[dict[str, Any]] = []
            resolved_any = False
            for order, call in enumerate(func.calls):
                target, candidates, reason = _resolve_call(
                    call.name, func, rel, file_funcs, file_classes, name_to_ids, imported_files
                )
                if target:
                    resolved_any = True
                edge = {
                    "source": src,
                    "target": target,
                    "name": call.name,
                    "kind": "call",
                    "order": order,
                    "line": call.line,
                    "confidence": "resolved" if target else "unresolved",
                    "candidates": sorted(set(candidates)),
                    "unresolved_reason": reason,
                }
                call_edges.append(edge)
                if cls.flow_worthy:
                    steps.append(edge)
            if cls.flow_worthy:
                all_resolved = all(s["confidence"] == "resolved" for s in steps)
                flow_confidence = "resolved" if (resolved_any and all_resolved) else (
                    "partial" if resolved_any else "unresolved"
                )
                flows.append({
                    "id": flow_id(src, "call_sequence"),
                    "kind": "call_sequence",
                    "root_id": src,
                    "confidence": flow_confidence,
                    "steps": steps,
                })

    return call_edges, flows


def build_control_flows(results: list[ParsedFile], root: Path) -> list[dict[str, Any]]:
    """Build control_flow flows from per-function branch markers (FEAT-0019).

    For each function that has branch markers (if/for/while/try/except/return),
    emit a ``control_flow`` flow with steps in source order. Confidence is always
    ``resolved`` — these are structural facts from the parser, not AI.
    """
    flows: list[dict[str, Any]] = []
    for r in results:
        rel = r.id or to_posix_rel(r.path, root)
        for f in r.functions:
            if not f.branches:
                continue
            src = function_id(rel, f.qualified_name)
            steps = [
                {"kind": b.kind, "line": b.line, "order": i}
                for i, b in enumerate(f.branches)
            ]
            flows.append({
                "id": flow_id(src, "control_flow"),
                "kind": "control_flow",
                "root_id": src,
                "confidence": "resolved",
                "steps": steps,
            })
    return flows


def build_request_flows(results: list[ParsedFile], root: Path) -> list[dict[str, Any]]:
    """Build request_flow flows from per-function route decorators (FEAT-0019).

    For each function that has HTTP route decorators, emit a ``request_flow``
    flow linking route identity → handler. Confidence is always ``resolved`` —
    these are structural facts from the parser, not AI.

    ponytail: handler → service/dependency linkage is NOT duplicated here; the
    call_sequence flow already captures that. This flow captures the route →
    handler edge only. Upgrade path: cross-reference call_sequence root_id.
    """
    flows: list[dict[str, Any]] = []
    for r in results:
        rel = r.id or to_posix_rel(r.path, root)
        for f in r.functions:
            if not f.routes:
                continue
            src = function_id(rel, f.qualified_name)
            steps = [
                {"method": rt.method, "path": rt.path, "line": rt.line, "order": i}
                for i, rt in enumerate(f.routes)
            ]
            flows.append({
                "id": flow_id(src, "request_flow"),
                "kind": "request_flow",
                "root_id": src,
                "confidence": "resolved",
                "steps": steps,
            })
    return flows


if __name__ == "__main__":
    import tempfile

    from graps.scanner.ast_parser import safe_parse

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pkg = root / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "sub.py").write_text("def helper():\n    return 1\n")
        (pkg / "main.py").write_text(
            "from .sub import helper\n\n"
            "class C:\n"
            "    def m(self):\n"
            "        self.helper_method()\n"
            "        return helper()\n"
            "    def helper_method(self):\n"
            "        return 2\n"
        )
        results = [safe_parse(p) for p in sorted(root.rglob("*.py"))]
        for r in results:
            r.id = to_posix_rel(r.path, root)

        edges, flows = build_call_edges_and_flows(results, root)
        resolved = {e["target"] for e in edges if e["target"]}
        # self.helper_method -> C.helper_method (same class); helper() -> sub.helper (from-import)
        assert any(t and t.endswith("::main.C.helper_method") for t in resolved), resolved
        assert any(t and t.endswith("pkg/sub.py::sub.helper") for t in resolved), resolved
        # C.m: 2 calls on 2 lines, no control -> cat 4 (linear, flow-worthy).
        call_seq = [f for f in flows if f["kind"] == "call_sequence"]
        assert len(call_seq) == 1, [f["root_id"] for f in call_seq]
        assert call_seq[0]["root_id"].endswith("::main.C.m"), call_seq[0]["root_id"]
        assert call_seq[0]["confidence"] == "resolved", call_seq[0]["confidence"]
        # helper: 0 calls, return 1 -> cat 1/2 (trivial) -> source_only.
        # helper_method: 0 calls, return 2 -> cat 1/2 (trivial) -> source_only.
        source_only = [f for f in flows if f["kind"] == "source_only"]
        assert len(source_only) == 2, [(f["root_id"], f["label"]) for f in source_only]
        assert all(f["label"] == "pure function" for f in source_only), source_only

        # Stub detection: pass body -> "stub"; raise NotImplementedError -> "not implemented".
        (pkg / "stub.py").write_text(
            "def empty():\n    pass\n"
            "def todo():\n    raise NotImplementedError\n"
            "def impl():\n    return NotImplementedError()\n"
        )
        r2 = [safe_parse(p) for p in sorted(root.rglob("*.py"))]
        for r in r2:
            r.id = to_posix_rel(r.path, root)
        _, f2 = build_call_edges_and_flows(r2, root)
        so2 = {f["root_id"].rsplit("::", 1)[-1]: f for f in f2 if f["kind"] == "source_only"}
        assert "stub.empty" in so2 and so2["stub.empty"]["label"] == "stub", so2
        assert "stub.todo" in so2 and so2["stub.todo"]["label"] == "not implemented", so2
        assert "stub.impl" in so2 and so2["stub.impl"]["label"] == "not implemented", so2

        # Delegator: return external_thing() -> source_only, edge still unresolved.
        (pkg / "dyn.py").write_text("def f():\n    return external_thing()\n")
        r3 = [safe_parse(p) for p in sorted(root.rglob("*.py"))]
        for r in r3:
            r.id = to_posix_rel(r.path, root)
        e3, f3 = build_call_edges_and_flows(r3, root)
        ext = [e for e in e3 if e["source"].endswith("pkg/dyn.py::dyn.f")]
        assert ext and ext[0]["confidence"] == "unresolved" and ext[0]["unresolved_reason"]
        f_flows = [f for f in f3 if f["root_id"].endswith("::dyn.f")]
        assert len(f_flows) == 1 and f_flows[0]["kind"] == "source_only", f_flows
        assert f_flows[0]["label"] == "delegator", f_flows[0]["label"]

        # Chained-method collapse: "-".join(x.split()).lower() on one line -> 1 logical call.
        (pkg / "chain.py").write_text(
            "def slug(name):\n"
            '    return "-".join(name.split()).lower()\n'
        )
        r4 = [safe_parse(p) for p in sorted(root.rglob("*.py"))]
        for r in r4:
            r.id = to_posix_rel(r.path, root)
        _, f4 = build_call_edges_and_flows(r4, root)
        slug_flows = [f for f in f4 if f["root_id"].endswith("::chain.slug")]
        assert len(slug_flows) == 1 and slug_flows[0]["kind"] == "source_only", slug_flows
        assert slug_flows[0]["label"] == "delegator", slug_flows[0]["label"]

        # Bare-expression call (not in return) -> trivial, source_only.
        (pkg / "bare.py").write_text(
            "def touch(self, x):\n"
            "    self.x = x\n"
            "def attach(self, ext):\n"
            "    self.handler = ext.make()\n"
        )
        r5 = [safe_parse(p) for p in sorted(root.rglob("*.py"))]
        for r in r5:
            r.id = to_posix_rel(r.path, root)
        _, f5 = build_call_edges_and_flows(r5, root)
        touch_flows = [f for f in f5 if f["root_id"].endswith("::bare.touch")]
        assert len(touch_flows) == 1 and touch_flows[0]["kind"] == "source_only", touch_flows
        assert touch_flows[0]["label"] == "pure function", touch_flows[0]["label"]
        # attach has 1 call (ext.make()) not in return -> bare expression -> trivial.
        attach_flows = [f for f in f5 if f["root_id"].endswith("::bare.attach")]
        assert len(attach_flows) == 1 and attach_flows[0]["kind"] == "source_only", attach_flows
        assert attach_flows[0]["label"] == "pure function", attach_flows[0]["label"]

    print("flows self-check ok")

