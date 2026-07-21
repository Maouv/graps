"""Deterministic call_sequence flow resolution (DEC-0005, architecture §Flow taxonomy).

Structural truth only — no AI. For each function we emit, in source order, the
direct static call sites it makes. Resolve the clear, deterministic cases; every
other call stays explicitly ``unresolved`` with a reason and candidate function
IDs (FEAT-0017: "unknown dynamic relations remain unresolved with
reason/confidence"). This is the MVP direct-call sequence — never marketed as
complete runtime control flow (DEC-0005).

Resolution rules (MVP):
  ``self.x`` / ``cls.x`` -> method ``x`` in the same enclosing class.
  bare ``name``           -> same-file function named ``name``; else a function
                             named ``name`` reachable via ``from <pkg> import name``.
  ``X.attr``              -> ``from <pkg> import X``-style import resolving to a
                             file that defines ``attr``.
  everything else         -> unresolved (external/dynamic/attribute dispatch).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from graps.scanner import ParsedFile
from graps.scanner.ids import flow_id, function_id, to_posix_rel
from graps.scanner.resolver import resolve_import


def _build_indexes(
    results: list[ParsedFile], root: Path
) -> tuple[dict[str, list], dict[str, list[str]]]:
    """file_id -> [ParsedFunction]; short name -> [function_ids]."""
    file_funcs: dict[str, list] = {}
    name_to_ids: dict[str, list[str]] = {}
    for r in results:
        rel = r.id or to_posix_rel(r.path, root)
        file_funcs[rel] = r.functions
        for f in r.functions:
            fid = function_id(rel, f.qualified_name)
            name_to_ids.setdefault(f.name, []).append(fid)
    return file_funcs, name_to_ids


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

    # X.attr -> from-import whose local name == X resolving to a file defining attr.
    if "." in name:
        base, attr = name.rsplit(".", 1)
        for last, rrel, _target in imported_files:
            if last == base:
                target_f = next((f for f in file_funcs.get(rrel, []) if f.name == attr), None)
                if target_f is not None:
                    return function_id(rrel, target_f.qualified_name), [], None
        return None, name_to_ids.get(attr, []), "attribute_call_unresolved"

    # bare name -> same-file function, else from-import named `name`.
    same = [f for f in file_funcs.get(rel, []) if f.name == name]
    if same:
        return function_id(rel, same[0].qualified_name), [], None
    for last, rrel, _target in imported_files:
        if last == name:
            target_f = next((f for f in file_funcs.get(rrel, []) if f.name == name), None)
            if target_f is not None:
                return function_id(rrel, target_f.qualified_name), [], None
    return None, name_to_ids.get(name, []), "unqualified_name_not_in_scope"


def build_call_edges_and_flows(
    results: list[ParsedFile], root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (call_edges, call_sequence flows) for the whole project.

    call_edges: ordered, deterministic, with kind/confidence/target/candidates/
    unresolved_reason. flows: one ``call_sequence`` per function that makes >=1
    call, steps mirroring its call edges in source order.
    """
    file_funcs, name_to_ids = _build_indexes(results, root)
    call_edges: list[dict[str, Any]] = []
    flows: list[dict[str, Any]] = []

    for result in sorted(results, key=lambda r: r.id or to_posix_rel(r.path, root)):
        rel = result.id or to_posix_rel(result.path, root)
        imported_files = _resolved_import_files(result, root)
        for func in result.functions:
            if not func.calls:
                continue
            src = function_id(rel, func.qualified_name)
            steps: list[dict[str, Any]] = []
            resolved_any = False
            for order, call in enumerate(func.calls):
                target, candidates, reason = _resolve_call(
                    call.name, func, rel, file_funcs, name_to_ids, imported_files
                )
                if target:
                    resolved_any = True
                edge = {
                    "source": src,
                    "target": target,
                    "kind": "call",
                    "order": order,
                    "line": call.line,
                    "confidence": "resolved" if target else "unresolved",
                    "candidates": sorted(set(candidates)),
                    "unresolved_reason": reason,
                }
                call_edges.append(edge)
                steps.append(edge)
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
        # only C.m makes calls -> one flow, two resolved steps -> confidence resolved
        assert len(flows) == 1, [f["root_id"] for f in flows]
        assert flows[0]["root_id"].endswith("::main.C.m"), flows[0]["root_id"]
        assert flows[0]["confidence"] == "resolved", flows[0]["confidence"]

        # unresolvable call stays unresolved with a reason.
        (pkg / "dyn.py").write_text("def f():\n    return external_thing()\n")
        r2 = [safe_parse(p) for p in sorted(root.rglob("*.py"))]
        for r in r2:
            r.id = to_posix_rel(r.path, root)
        e2, _ = build_call_edges_and_flows(r2, root)
        ext = [e for e in e2 if e["source"].endswith("pkg/dyn.py::dyn.f")]
        assert ext and ext[0]["confidence"] == "unresolved" and ext[0]["unresolved_reason"]

    print("flows self-check ok")

