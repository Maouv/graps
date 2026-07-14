"""Stable structural IDs and deterministic content hashing (data-contracts.md).

IDs are scan-root-relative and POSIX-normalized so the same project layout always
produces the same IDs regardless of the host machine. Absolute filesystem paths
never appear in any ID (M-03 / api-security).

Stable ID rules (data-contracts §Stable IDs):
  File     -> scan-root-relative POSIX path ("pkg/mod.py")
  Function -> "<file_id>::<qualified_name>" ("pkg/mod.py::C.m")
  Class    -> "<file_id>::<qualified_name>" ("pkg/mod.py::C")
  Module   -> canonical language boundary relative to scan root ("pkg.mod")
  Flow     -> "<root_id>#<flow_kind>" ("pkg/mod.py::C.m#call_sequence")

content_hash: sha256 over a canonical, sorted serialization of the structural
graph, excluding only the volatile scan timestamp — so identical structure
yields an identical hash. This is the join key between graph.json and
architecture.json (FEAT-0020).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def to_posix_rel(path: Path, root: Path) -> str:
    """Return ``path`` relative to ``root`` as a POSIX string (never absolute).

    Falls back to the input name only if the path cannot be expressed under
    root; it never leaks an absolute host path.
    """
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        # Already relative or outside root — strip to its POSIX name, no host dir.
        return Path(path).as_posix().lstrip("/")


def function_id(file_id: str, qualified_name: str) -> str:
    return f"{file_id}::{qualified_name}"


def class_id(file_id: str, qualified_name: str) -> str:
    return f"{file_id}::{qualified_name}"


def flow_id(root_id: str, flow_kind: str) -> str:
    return f"{root_id}#{flow_kind}"


def python_module_id(rel_posix: str) -> str:
    """Canonical Python module identity from a scan-root-relative POSIX path.

    "pkg/sub.py"            -> "pkg.sub"
    "pkg/__init__.py"       -> "pkg"
    "pkg/sub/__init__.py"   -> "pkg.sub"
    "top.py"                -> "top"
    The dotted form is the deterministic Python module name; package vs
    namespace confidence is resolved by ``modules.resolve_modules``.
    """
    p = rel_posix
    if p.endswith(".py"):
        p = p[:-3]
    parts = [seg for seg in p.split("/") if seg]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _canonical_payload(graph: dict) -> dict:
    """Structural fingerprint: drop only the volatile scan timestamp."""
    scan = dict(graph.get("scan") or {})
    scan.pop("scanned_at", None)
    return {
        "schema_version": graph.get("schema_version"),
        "scan": scan,
        "nodes": graph.get("nodes") or {},
        "edges": graph.get("edges") or {},
        "flows": graph.get("flows") or [],
    }


def content_hash(graph: dict) -> str:
    """sha256 over deterministic, sorted-key JSON of the structural content.

    Identical structure (same nodes/edges/flows/diagnostics/counts) always
    hashes identically; the scan timestamp is excluded so re-scans of an
    unchanged project are idempotent (FEAT-0020 hash-join key).
    """
    payload = _canonical_payload(graph)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pkg = root / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "sub.py").write_text("")

        assert to_posix_rel(pkg / "sub.py", root) == "pkg/sub.py"
        assert python_module_id("pkg/sub.py") == "pkg.sub"
        assert python_module_id("pkg/__init__.py") == "pkg"
        assert python_module_id("pkg/sub/__init__.py") == "pkg.sub"
        assert python_module_id("top.py") == "top"

        assert function_id("pkg/sub.py", "C.m") == "pkg/sub.py::C.m"
        assert class_id("pkg/sub.py", "C") == "pkg/sub.py::C"
        assert flow_id("pkg/sub.py::C.m", "call_sequence") == "pkg/sub.py::C.m#call_sequence"

        g = {"schema_version": "1.0.0", "scan": {"scanned_at": "T1", "file_count": 1},
             "nodes": {}, "edges": {}, "flows": []}
        g2 = {"schema_version": "1.0.0", "scan": {"scanned_at": "T2", "file_count": 1},
              "nodes": {}, "edges": {}, "flows": []}
        assert content_hash(g) == content_hash(g2), "timestamp must not affect hash"
        g3 = {"schema_version": "1.0.0", "scan": {"scanned_at": "T1", "file_count": 2},
              "nodes": {}, "edges": {}, "flows": []}
        assert content_hash(g) != content_hash(g3), "structure change must change hash"

    print("ids self-check ok")
