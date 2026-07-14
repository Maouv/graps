"""Convergence point — assemble scanner outputs into the versioned structural
graph (data-contracts §graph.json, FEAT-0017).

Structural truth only — no AI. Produces a schema-versioned graph with typed node
collections (files/functions/classes/modules), typed edge collections
(imports/calls/contains/module_depends), call_sequence flows, scan
diagnostics, and a deterministic ``content_hash``. Output ordering is
deterministic so identical input yields an identical hash (FEAT-0020 join key).

Architecture boundary: graph_builder never reads files or calls AI. It only
shapes facts produced by the scanner layer.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from graps.scanner import ParsedFile, ParsedImport
from graps.scanner.flows import build_call_edges_and_flows
from graps.scanner.ids import (
    class_id,
    content_hash,
    function_id,
    python_module_id,
    to_posix_rel,
)
from graps.scanner.modules import resolve_modules
from graps.scanner.resolver import resolve_import
from graps.scanner.risk_analyzer import analyze_risks
from graps.scanner.sanitize import sanitize_constant_value

SCHEMA_VERSION = "1.0.0"

# ponytail: memoize resolve_import per build_graph call; O(k) → 2× O(k) fs I/O.
_resolve_cache: dict[tuple[str, bool, bool, Path, Path], Path | None] = {}


def _resolved(imp: ParsedImport, current_file: Path, root: Path) -> Path | None:
    key = (imp.target, imp.is_dynamic, imp.is_star, current_file, root)
    if key not in _resolve_cache:
        _resolve_cache[key] = resolve_import(imp, current_file, root)
    return _resolve_cache[key]


def _rel(path: Path, root: Path) -> str:
    """Path relative to root as POSIX str (M-03: never leak absolute paths)."""
    return to_posix_rel(path, root)


def _sanitized_constants(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run every constant value through sanitize_constant_value (C-01)."""
    return [
        {"name": c["name"],
         "value": sanitize_constant_value(c["name"], c["value"]),
         "line": c.get("line")}
        for c in raw
    ]


def _warning_type(msg: str) -> str:
    m = msg.lower()
    if "star import" in m:
        return "star_import"
    if "importlib" in m or "dynamic import" in m:
        return "dynamic_import"
    if "dynamic_code" in m:
        return "dynamic_code"
    if "parse failed" in m or "too large" in m or "encoding" in m:
        return "parse_error"
    return "scan_warning"


def _parse_warning_line(msg: str) -> int | None:
    """Extract a leading ``line N:`` number from a parser warning, else None."""
    if msg.startswith("line "):
        tail = msg[5:]
        n = ""
        for ch in tail:
            if ch.isdigit():
                n += ch
            else:
                break
        return int(n) if n else None
    return None


def _clean_warning(msg: str) -> str:
    """Strip a leading absolute host path from a parser warning (M-03).

    safe_parse prefixes size/stat/encoding/parse-fail warnings with the file's
    absolute path; that must never be serialized into the graph/API.
    """
    if msg.startswith("/"):
        idx = msg.find(": ")
        if idx != -1:
            return msg[idx + 2:]
    return msg


def _file_rel(result: ParsedFile, root: Path) -> str:
    return result.id or to_posix_rel(result.path, root)


def _build_files(results: list[ParsedFile], root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in results:
        rel = _file_rel(r, root)
        out.append({
            "id": rel,
            "type": "file",
            "path": rel,
            "language": r.language,
            "module_id": python_module_id(rel),
            "modified_at": r.file_modified_at or "",
            "constants": _sanitized_constants(r.constants),
            "exported_names": sorted(r.exported_names),
        })
    return out


def _build_functions(results: list[ParsedFile], root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in results:
        rel = _file_rel(r, root)
        mid = python_module_id(rel)
        for f in r.functions:
            ls = f.line_start or f.lineno
            out.append({
                "id": function_id(rel, f.qualified_name),
                "type": "function",
                "file_id": rel,
                "module_id": mid,
                "name": f.name,
                "qualified_name": f.qualified_name,
                "line_start": ls,
                "line_end": f.line_end or ls,
                "decorators": list(f.decorators),
                "is_private": f.name.startswith("_"),
                "is_nested": f.is_nested,
                "is_property": f.is_property,
                "parent": f.parent,
            })
    return out


def _build_classes(results: list[ParsedFile], root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in results:
        rel = _file_rel(r, root)
        mid = python_module_id(rel)
        for c in r.classes:
            qn = c.get("qualified_name") or c.get("name", "")
            out.append({
                "id": class_id(rel, qn),
                "type": "class",
                "file_id": rel,
                "module_id": mid,
                "name": c.get("name", ""),
                "qualified_name": qn,
                "line_start": c.get("line_start"),
                "line_end": c.get("line_end"),
                "decorators": list(c.get("decorators") or []),
                "methods": list(c.get("methods") or []),
                "parent": c.get("parent"),
            })
    return out


def _build_imports(results: list[ParsedFile], root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in results:
        rel = _file_rel(r, root)
        for order, imp in enumerate(r.imports):
            target: str | None = None
            reason: str | None = None
            if imp.is_dynamic:
                reason = "dynamic_import"
            elif imp.is_star:
                reason = "star_import"
            else:
                resolved = _resolved(imp, r.path, root)
                if resolved is not None:
                    target = to_posix_rel(resolved, root)
                else:
                    reason = "external_or_stdlib"
            out.append({
                "source": rel,
                "target": target,
                "kind": "imports",
                "order": order,
                "line": imp.lineno,
                "imported_name": imp.target,
                "is_dynamic": imp.is_dynamic,
                "is_star": imp.is_star,
                "is_conditional": imp.is_conditional,
                "confidence": "resolved" if target else "unresolved",
                "unresolved_reason": reason,
            })
    return out


def _build_contains(results: list[ParsedFile], root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in results:
        rel = _file_rel(r, root)
        order = 0
        for f in r.functions:
            out.append({
                "source": rel,
                "target": function_id(rel, f.qualified_name),
                "kind": "contains",
                "order": order,
            })
            order += 1
        for c in r.classes:
            qn = c.get("qualified_name") or c.get("name", "")
            out.append({
                "source": rel,
                "target": class_id(rel, qn),
                "kind": "contains",
                "order": order,
            })
            order += 1
    return out


def _build_module_depends(
    modules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """module -> module dependency edges, filtered to modules that exist."""
    existing = {m["id"] for m in modules}
    out: list[dict[str, Any]] = []
    for m in modules:
        for dep in m["dependency_ids"]:
            if dep in existing:
                out.append({"source": m["id"], "target": dep, "kind": "depends"})
    return out


def _build_diagnostics(
    results: list[ParsedFile], root: Path
) -> list[dict[str, Any]]:
    """Per-file parser warnings + structural risks → diagnostics (relative paths only)."""
    diags: list[dict[str, Any]] = []
    for r in results:
        rel = _file_rel(r, root)
        for w in r.warnings:
            diags.append({
                "file": rel,
                "level": "warning",
                "code": _warning_type(w),
                "message": _clean_warning(w),
                "line": _parse_warning_line(w),
            })
        for risk in analyze_risks(r, results):
            sev = str(risk.get("severity") or "").lower()
            diags.append({
                "file": rel,
                "level": "error" if sev == "high" else "warning",
                "code": str(risk.get("type") or "risk"),
                "message": str(risk.get("detail") or ""),
                "line": None,
            })
    diags.sort(key=lambda d: (d["file"], d["line"] or 0, d["code"]))
    return diags


def build_graph(results: list[ParsedFile], root: Path) -> dict[str, Any]:
    """Assemble the versioned structural graph (data-contracts §graph.json).

    Deterministic: results are sorted by relative id before any collection is
    built, so identical input yields identical output and ``content_hash``.
    """
    results_sorted = sorted(results, key=lambda r: r.id or to_posix_rel(r.path, root))

    files = _build_files(results_sorted, root)
    functions = _build_functions(results_sorted, root)
    classes = _build_classes(results_sorted, root)
    modules = resolve_modules(results_sorted, root)

    imports = _build_imports(results_sorted, root)
    call_edges, flows = build_call_edges_and_flows(results_sorted, root)
    contains = _build_contains(results_sorted, root)
    module_depends = _build_module_depends(modules)
    diagnostics = _build_diagnostics(results_sorted, root)

    nodes = {"files": files, "functions": functions, "classes": classes, "modules": modules}
    edges = {
        "imports": imports,
        "calls": call_edges,
        "contains": contains,
        "module_depends": module_depends,
    }
    edge_count = sum(len(v) for v in edges.values())

    graph: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "scan": {
            "root_id": ".",
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "root": ".",
            "file_count": len(files),
            "function_count": len(functions),
            "class_count": len(classes),
            "module_count": len(modules),
            "edge_count": edge_count,
            "diagnostics": diagnostics,
        },
        "content_hash": "",
        "nodes": nodes,
        "edges": edges,
        "flows": flows,
    }
    graph["content_hash"] = content_hash(graph)
    return graph


if __name__ == "__main__":
    import json
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
            "        return helper()\n"
        )
        (root / "bad.py").write_text("def (:\n")  # malformed
        (root / "cfg.py").write_text("DB_PASSWORD = 'hunter2'\nMAX = 3\n")

        results = [safe_parse(p) for p in sorted(root.rglob("*.py"))]
        for r in results:
            r.id = to_posix_rel(r.path, root)
        # Direct constant wiring proof through the real build_graph path (C-01).
        for r in results:
            if r.id == "cfg.py":
                r.constants = [{"name": "DB_PASSWORD", "value": "hunter2", "line": 1},
                               {"name": "MAX", "value": "3", "line": 2}]

        g = build_graph(results, root)
        assert g["schema_version"] == SCHEMA_VERSION
        assert set(g["nodes"]) == {"files", "functions", "classes", "modules"}
        assert set(g["edges"]) == {"imports", "calls", "contains", "module_depends"}
        assert g["scan"]["file_count"] == 5
        assert g["scan"]["function_count"] >= 2
        # Determinism: same input -> identical content_hash (scanned_at excluded).
        g2 = build_graph(list(results), root)
        assert g["content_hash"] == g2["content_hash"], "hash must be stable"
        assert g["scan"]["scanned_at"] != g2["scan"]["scanned_at"]  # timestamp differs
        # No absolute host path leaks anywhere in the serialized graph (M-03).
        blob = json.dumps(g, sort_keys=True)
        assert root.resolve().as_posix() not in blob, "absolute path leaked"
        # Malformed file -> diagnostic, but graph still produced (FEAT-0016).
        assert any(d["file"] == "bad.py" and d["code"] == "parse_error" for d in g["scan"]["diagnostics"])
        # C-01 redaction wired through build_graph.
        cfg = next(n for n in g["nodes"]["files"] if n["id"] == "cfg.py")
        assert cfg["constants"][0]["value"] == "[REDACTED]"
        assert cfg["constants"][1]["value"] == "3"
        # call_sequence flow present for C.m, helper() resolved cross-file.
        assert any(f["kind"] == "call_sequence" for f in g["flows"]), g["flows"]
        assert any(e["kind"] == "call" and e["target"] and e["target"].endswith("sub.helper")
                   for e in g["edges"]["calls"]), g["edges"]["calls"]

    print("graph_builder self-check ok")


