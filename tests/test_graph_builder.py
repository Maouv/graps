"""Unit tests for graph_builder.build_graph — schema v1.0.0 (FEAT-0017).

Tests the typed collections (files/functions/classes/modules), typed edges
(imports/calls/contains/module_depends), flows, scan diagnostics, content_hash
determinism, and C-01 constant redaction.
"""

from datetime import datetime

import pytest

from graps.scanner import ParsedFile
from graps.scanner.ast_parser import safe_parse
from graps.scanner.graph_builder import _sanitized_constants, build_graph
from graps.scanner.tree_sitter_parser import TreeSitterParser


def _make_project(tmp_path):
    """Create minimal project tree, return (root, results)."""
    (tmp_path / "main.py").write_text("from services import helper\n")
    svc = tmp_path / "services"
    svc.mkdir()
    (svc / "__init__.py").write_text("")
    (svc / "helper.py").write_text("def hello(name: str) -> str:\n    return f'hi {name}'\n")
    (tmp_path / "star.py").write_text("from os import *\n")
    results = [safe_parse(p) for p in sorted(tmp_path.rglob("*.py"))]
    return tmp_path, results


def test_build_graph__returns_schema_keys(tmp_path):
    root, results = _make_project(tmp_path)
    g = build_graph(results, root)
    assert set(g.keys()) == {"schema_version", "scan", "content_hash", "nodes", "edges", "flows"}


def test_build_graph__scan_counts_correct(tmp_path):
    root, results = _make_project(tmp_path)
    s = build_graph(results, root)["scan"]
    assert s["file_count"] == 4
    assert s["function_count"] == 1
    assert s["edge_count"] >= 1


def test_build_graph__scan_has_scanned_at(tmp_path):
    root, results = _make_project(tmp_path)
    s = build_graph(results, root)["scan"]
    datetime.fromisoformat(s["scanned_at"])  # raises if not ISO-8601


def test_build_graph__file_node_id_relative_to_root(tmp_path):
    root, results = _make_project(tmp_path)
    files = {f["id"]: f for f in build_graph(results, root)["nodes"]["files"]}
    assert "services/helper.py" in files
    assert not any(f["id"].startswith("/") for f in files.values()), "M-03: absolute path leak"


def test_build_graph__function_shape(tmp_path):
    root, results = _make_project(tmp_path)
    fns = build_graph(results, root)["nodes"]["functions"]
    hello = next(f for f in fns if f["name"] == "hello")
    assert hello["type"] == "function"
    assert hello["file_id"] == "services/helper.py"
    assert hello["qualified_name"] == "helper.hello"
    assert hello["decorators"] == []
    assert hello["is_private"] is False
    assert isinstance(hello["line_start"], int)
    assert isinstance(hello["line_end"], int)
    assert hello["is_nested"] is False
    assert hello["is_property"] is False
    assert hello["parent"] is None


def test_build_graph__private_function_detected(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "priv.py").write_text("def _hidden(): pass\n")
    results = [safe_parse(p) for p in root.rglob("*.py")]
    fns = build_graph(results, root)["nodes"]["functions"]
    assert fns[0]["is_private"] is True


def test_build_graph__import_edge_shape(tmp_path):
    root, results = _make_project(tmp_path)
    imports = build_graph(results, root)["edges"]["imports"]
    assert len(imports) >= 1
    e = imports[0]
    assert "source" in e and "target" in e
    assert e["kind"] == "imports"
    assert isinstance(e["order"], int)
    assert isinstance(e["imported_name"], str)
    assert not e["source"].startswith("/")


def test_build_graph__edge_via_tree_sitter(tmp_path):
    """edge-resolution-bug end-to-end guard: parse fixture via TreeSitterParser,
    build_graph, assert import edge ter-buat."""
    pytest.importorskip("tree_sitter_language_pack", reason="tslp not installed")
    pkg = tmp_path / "relpkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "sub.py").write_text("def helper():\n    return 1\n")
    (pkg / "main.py").write_text("from .sub import helper\n\ndef run():\n    return helper()\n")

    ts = TreeSitterParser()
    files = sorted(tmp_path.rglob("*.py"))
    results = [ts.parse_file(p, tmp_path) for p in files]
    results = [r for r in results if r is not None]

    g = build_graph(results, tmp_path)
    imports = g["edges"]["imports"]
    assert len(imports) >= 1, (
        f"expected >= 1 import edge via tree-sitter, got 0; "
        f"imports={[i.target for r in results for i in r.imports]}"
    )
    pairs = {(e["source"], e["target"]) for e in imports if e["target"]}
    assert ("relpkg/main.py", "relpkg/sub.py") in pairs, \
        f"edge relpkg/main.py → relpkg/sub.py missing; got {pairs}"


def test_build_graph__star_import_no_resolved_edge(tmp_path):
    root, results = _make_project(tmp_path)
    imports = build_graph(results, root)["edges"]["imports"]
    star_edges = [e for e in imports if e["source"] == "star.py"]
    # Star import → unresolved (target None), but edge still emitted.
    assert all(e["target"] is None for e in star_edges)
    assert all(e["unresolved_reason"] == "star_import" for e in star_edges)
    # Diagnostic for star import.
    diags = build_graph(results, root)["scan"]["diagnostics"]
    assert any(d["file"] == "star.py" and d["code"] == "star_import" for d in diags)


def test_build_graph__constants_default_empty(tmp_path):
    root, results = _make_project(tmp_path)
    files = build_graph(results, root)["nodes"]["files"]
    assert all(f["constants"] == [] for f in files)


def test_build_graph__constants_flow_through_and_redact(tmp_path):
    pf = ParsedFile(
        id="cfg.py", path=tmp_path / "cfg.py",
        constants=[{"name": "MAX_RETRY", "value": "3", "line": 1},
                   {"name": "DB_PASSWORD", "value": "hunter2", "line": 2}],
    )
    files = build_graph([pf], tmp_path)["nodes"]["files"]
    assert files[0]["constants"] == [
        {"name": "MAX_RETRY", "value": "3", "line": 1},
        {"name": "DB_PASSWORD", "value": "[REDACTED]", "line": 2},
    ], files[0]["constants"]


def test_sanitized_constants__redacts_db_password():
    out = _sanitized_constants([{"name": "DB_PASSWORD", "value": "hunter2", "line": 1}])
    assert out[0]["value"] == "[REDACTED]"


def test_sanitized_constants__preserves_safe_constant():
    out = _sanitized_constants([{"name": "MAX_RETRY", "value": "3", "line": 1}])
    assert out[0]["value"] == "3"


def test_sanitized_constants__redacts_api_key_pattern():
    # Value must match sk-ant-[a-zA-Z0-9\-_]{20,} (20+ alnum chars after sk-ant-).
    out = _sanitized_constants([{"name": "FOO", "value": "sk-ant-" + "a" * 25, "line": 1}])
    assert out[0]["value"] == "[REDACTED]"


def test_build_graph__content_hash_deterministic(tmp_path):
    root, results = _make_project(tmp_path)
    g1 = build_graph(results, root)
    g2 = build_graph(list(results), root)
    assert g1["content_hash"] == g2["content_hash"], "hash must be stable"
    assert g1["scan"]["scanned_at"] != g2["scan"]["scanned_at"]


def test_build_graph__no_absolute_path_leak(tmp_path):
    import json
    root, results = _make_project(tmp_path)
    g = build_graph(results, root)
    blob = json.dumps(g, sort_keys=True)
    assert root.resolve().as_posix() not in blob, "absolute path leaked"


def test_build_graph__graps_excluded_by_default():
    """FEAT-0020: .graps/ in _DEFAULT_EXCLUDES (scanner filter, bukan graph_builder)."""
    from graps.cli import _DEFAULT_EXCLUDES
    assert ".graps" in _DEFAULT_EXCLUDES
