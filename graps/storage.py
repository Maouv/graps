"""Project-local storage under ``{scan_root}/.graps/`` (FEAT-0020, architecture §Storage).

Owns versioned, atomic, hash-joined persistence of the structural graph and
overlays. Invariants:
  - Writes are atomic (complete temp data + ``os.replace``) and 0o600.
  - architecture.json only renders when its ``graph_content_hash`` matches the
    current graph ``content_hash`` (truth hierarchy: graph wins).
  - settings.json carries safe defaults; unknown keys are dropped (whitelist).
  - The file index tracks per-file mtime/size/hash so changed files can be mapped
    to affected structural modules (incremental invalidation infrastructure).
  - No provider secret or absolute host path is ever persisted — graph/storage
    content is scan-root-relative by construction.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
_GRAPH_SCHEMA = "1.0.0"
_SETTINGS_SCHEMA = "1.0.0"

_dot_lock = threading.Lock()

_SETTINGS_WHITELIST = {"ai_enrichment", "overrides", "panel_widths", "tabs"}


def graps_dir(scan_root: Path) -> Path:
    return scan_root / ".graps"


def cache_dir(scan_root: Path) -> Path:
    return graps_dir(scan_root) / "cache"


def _atomic_write_json(path: Path, data: Any) -> None:
    """Write complete JSON to a unique temp file, chmod 0o600, then atomically replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, sort_keys=True)
    tmp = path.with_name(
        f"{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    tmp.write_text(payload)
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    os.chmod(path, 0o600)


def _read_json(path: Path) -> Any | None:
    """Read JSON, returning None if missing/corrupt (never raises)."""
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


# --- graph.json ---------------------------------------------------------------

def write_graph(scan_root: Path, graph: dict[str, Any]) -> Path:
    """Atomically persist the structural graph to ``.graps/graph.json``."""
    path = graps_dir(scan_root) / "graph.json"
    with _dot_lock:
        _atomic_write_json(path, graph)
    return path


def read_graph(scan_root: Path) -> dict[str, Any] | None:
    """Load graph.json; return None if missing/corrupt or schema-incompatible."""
    data = _read_json(graps_dir(scan_root) / "graph.json")
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != _GRAPH_SCHEMA:
        return None
    return data


# --- settings.json ------------------------------------------------------------
# ponytail: default-ON ai_enrichment (requirement: AI Enrichment defaults ON but
# optional). Invalid/missing preferences always fall back to safe defaults and
# never mutate graph truth.

def default_settings() -> dict[str, Any]:
    return {
        "schema_version": _SETTINGS_SCHEMA,
        "ai_enrichment": True,
        "overrides": {},
        "panel_widths": {"dir": 280, "ai": 320},
        "tabs": [],
    }


def _coerce_settings(raw: Any) -> dict[str, Any]:
    base = default_settings()
    if not isinstance(raw, dict):
        return base
    if raw.get("schema_version") != _SETTINGS_SCHEMA:
        # Stale schema -> ignore stored values, keep safe defaults.
        return base
    out = dict(base)
    if isinstance(raw.get("ai_enrichment"), bool):
        out["ai_enrichment"] = raw["ai_enrichment"]
    if isinstance(raw.get("overrides"), dict):
        out["overrides"] = dict(raw["overrides"])
    if isinstance(raw.get("panel_widths"), dict):
        pw = {k: v for k, v in raw["panel_widths"].items() if isinstance(v, int)}
        out["panel_widths"] = {**base["panel_widths"], **pw}
    if isinstance(raw.get("tabs"), list):
        out["tabs"] = list(raw["tabs"])
    return out


def read_settings(scan_root: Path) -> dict[str, Any]:
    return _coerce_settings(_read_json(graps_dir(scan_root) / "settings.json"))


def write_settings(scan_root: Path, settings: dict[str, Any]) -> dict[str, Any]:
    """Persist whitelisted settings only; unknown keys are dropped. Returns the
    coerced settings actually written (callers return this to clients)."""
    coerced = _coerce_settings({**default_settings(), **{
        k: v for k, v in settings.items() if k in _SETTINGS_WHITELIST
    }})
    coerced["schema_version"] = _SETTINGS_SCHEMA
    path = graps_dir(scan_root) / "settings.json"
    with _dot_lock:
        _atomic_write_json(path, coerced)
    return coerced


# --- architecture.json (semantic overlay, hash-joined to graph truth) -----------

def write_architecture(
    scan_root: Path,
    graph_hash: str,
    modules: list[dict[str, Any]] | None = None,
    flow_labels: list[dict[str, Any]] | None = None,
    groups: list[dict[str, Any]] | None = None,
) -> Path:
    """Persist the semantic overlay. ``graph_content_hash`` ties it to graph truth.

    Phase 1 has no AI enrichment, so modules/flow_labels/groups default to empty;
    the hash-join mechanism is in place for Phase 2.
    """
    arch = {
        "schema_version": SCHEMA_VERSION,
        "graph_content_hash": graph_hash,
        "timestamp": _now_iso(),
        "modules": modules or [],
        "flow_labels": flow_labels or [],
        "groups": groups or [],
    }
    path = graps_dir(scan_root) / "architecture.json"
    with _dot_lock:
        _atomic_write_json(path, arch)
    return path


def read_architecture(scan_root: Path, graph_hash: str) -> dict[str, Any] | None:
    """Load architecture.json; return None if missing/corrupt or hash-mismatched.

    A mismatch means the overlay is stale relative to graph truth — callers must
    fall back to the structural graph (truth hierarchy).
    """
    data = _read_json(graps_dir(scan_root) / "architecture.json")
    if not isinstance(data, dict):
        return None
    if data.get("graph_content_hash") != graph_hash:
        return None
    return data


# --- incremental file index (FEAT-0020: changed files -> affected modules) ----

def _file_record(scan_root: Path, rel: str) -> dict[str, Any]:
    p = scan_root / rel
    try:
        st = p.stat()
        content = p.read_bytes()
    except OSError:
        return {"mtime": "", "size": 0, "hash": "", "error": "unreadable"}
    return {
        "mtime": str(st.st_mtime),
        "size": st.st_size,
        "hash": hashlib.sha256(content).hexdigest(),
    }


def compute_file_index(scan_root: Path, file_rels: list[str]) -> dict[str, dict[str, Any]]:
    return {rel: _file_record(scan_root, rel) for rel in sorted(set(file_rels))}


def read_file_index(scan_root: Path) -> dict[str, dict[str, Any]]:
    data = _read_json(cache_dir(scan_root) / "file_index.json")
    return data if isinstance(data, dict) else {}


def write_file_index(scan_root: Path, index: dict[str, dict[str, Any]]) -> Path:
    path = cache_dir(scan_root) / "file_index.json"
    with _dot_lock:
        _atomic_write_json(path, index)
    return path


def changed_files(old: dict[str, dict[str, Any]], new: dict[str, dict[str, Any]]) -> list[str]:
    """Return rels whose hash differs, or that were added/removed."""
    out: list[str] = []
    for rel in sorted(set(old) | set(new)):
        o, n = old.get(rel), new.get(rel)
        if o is None or n is None or o.get("hash") != n.get("hash"):
            out.append(rel)
    return out


def affected_modules(changed_rels: list[str], graph: dict[str, Any]) -> list[str]:
    """Module IDs whose source file changed — the invalidation unit for overlays."""
    modules = (graph.get("nodes") or {}).get("modules") or []
    changed = set(changed_rels)
    return sorted({m["id"] for m in modules if m.get("file_id") in changed})


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    import tempfile

    from graps.scanner.ast_parser import safe_parse
    from graps.scanner.graph_builder import build_graph
    from graps.scanner.ids import to_posix_rel

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pkg = root / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "sub.py").write_text("def helper():\n    return 1\n")
        results = [safe_parse(p) for p in sorted(root.rglob("*.py"))]
        for r in results:
            r.id = to_posix_rel(r.path, root)
        graph = build_graph(results, root)
        gh = graph["content_hash"]

        # 1. atomic graph write + reusable read (Phase 1 gate).
        write_graph(root, graph)
        assert read_graph(root) is not None
        reloaded = read_graph(root)
        assert reloaded["content_hash"] == gh, "graph.json must be reusable"
        assert ".graps" not in {f["id"] for f in reloaded["nodes"]["files"]}

        # 2. hash-join: architecture only renders when hash matches.
        write_architecture(root, gh)
        assert read_architecture(root, gh) is not None
        assert read_architecture(root, "wrong-hash") is None, "stale overlay must not join"

        # 3. settings: safe defaults, whitelist, invalid -> defaults.
        assert read_settings(root)["ai_enrichment"] is True  # default-ON
        written = write_settings(root, {"ai_enrichment": False, "evil": "drop", "panel_widths": {"dir": 400}})
        assert written["ai_enrichment"] is False
        assert "evil" not in written, "unknown keys must be dropped"
        assert read_settings(root)["panel_widths"]["dir"] == 400
        (graps_dir(root) / "settings.json").write_text("{ corrupt")
        assert read_settings(root) == default_settings(), "corrupt settings -> safe defaults"

        # 4. incremental: changed files map to affected modules.
        rels = [r.id for r in results]
        idx = compute_file_index(root, rels)
        write_file_index(root, idx)
        assert changed_files(idx, idx) == []
        (pkg / "sub.py").write_text("def helper():\n    return 2\n")
        new_idx = compute_file_index(root, rels)
        ch = changed_files(idx, new_idx)
        assert ch == ["pkg/sub.py"], ch
        aff = affected_modules(ch, graph)
        assert "pkg.sub" in aff, aff

        # 5. no absolute path or secret in persisted graph.
        blob = (graps_dir(root) / "graph.json").read_text()
        assert root.resolve().as_posix() not in blob, "abs path leaked into .graps"

    print("storage self-check ok")

