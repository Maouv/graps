"""Semantic validation for AI enrichment output (FEAT-0019 phase gate).

Validates AI-generated labels/summaries against the structural allowlist before
any enrichment is applied. Invalid output is rejected atomically — it cannot
alter graph truth or stop structural browsing.

Rules (data-contracts §semantic enrichment):
1. Must be valid JSON object.
2. Must NOT contain structural keys (edges, order, calls, contains, imports).
3. All referenced node IDs must exist in the graph (structural allowlist).
4. Any rule violation → None (atomic reject, all-or-nothing).

Two layers:
- ``SemanticEnrichment`` Pydantic model → Instructor uses this for structured
  extraction from LLM responses. Schema itself forbids structural keys.
- ``validate_semantic_enrichment`` → stdlib validation for raw JSON (fallback
  when Instructor is unavailable or for manual verification).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class NodeLabel(BaseModel):
    """A semantic label or summary for a single graph node."""
    model_config = ConfigDict(extra="forbid")

    node_id: str
    label: str = ""
    summary: str = ""


class SemanticEnrichment(BaseModel):
    """AI semantic enrichment output — labels/summaries only.

    FEAT-0019 acceptance: "AI payload contains labels/summaries but no edges
    or order." This schema enforces that — ``extra='forbid'`` rejects any
    structural key (edges, calls, order, etc.) that the LLM might hallucinate.
    """
    model_config = ConfigDict(extra="forbid")

    labels: list[NodeLabel] = Field(default_factory=list)
    summaries: list[NodeLabel] = Field(default_factory=list)

# Keys that belong to structural truth only — AI must not provide these.
_FORBIDDEN_KEYS = frozenset({
    "edges", "calls", "contains", "imports", "module_depends",
    "order", "line", "line_start", "line_end",
    "schema_version", "content_hash", "scan",
})


def _build_allowlist(graph: dict[str, Any]) -> set[str]:
    """Collect all known node IDs from graph (structural allowlist)."""
    ids: set[str] = set()
    nodes = graph.get("nodes") or {}
    for collection in nodes.values():
        if isinstance(collection, list):
            for node in collection:
                if isinstance(node, dict) and "id" in node:
                    ids.add(str(node["id"]))
    return ids


def _check_ids(obj: Any, allowlist: set[str]) -> bool:
    """Recursively verify all ``id``-like fields reference known nodes."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _FORBIDDEN_KEYS:
                return False
            if k in ("id", "node_id", "target", "source", "function_id", "file_id"):
                if str(v) not in allowlist:
                    return False
            elif not _check_ids(v, allowlist):
                return False
    elif isinstance(obj, list):
        return all(_check_ids(item, allowlist) for item in obj)
    return True


def validate_semantic_enrichment(
    ai_output: str,
    graph: dict[str, Any],
) -> dict[str, Any] | None:
    """Validate AI enrichment output against structural allowlist.

    Returns parsed dict if valid, ``None`` if invalid (atomic reject).
    Invalid output cannot alter graph truth or stop structural browsing.
    """
    if not ai_output or not ai_output.strip():
        return None

    try:
        data = json.loads(ai_output)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("semantic enrichment rejected: invalid JSON (%s)", type(e).__name__)
        return None

    if not isinstance(data, dict):
        logger.warning("semantic enrichment rejected: not a JSON object")
        return None

    # Check for forbidden structural keys.
    for key in data:
        if key in _FORBIDDEN_KEYS:
            logger.warning("semantic enrichment rejected: forbidden key %r", key)
            return None

    # All referenced IDs must be in the structural allowlist.
    allowlist = _build_allowlist(graph)
    if not _check_ids(data, allowlist):
        logger.warning("semantic enrichment rejected: ID not in structural allowlist")
        return None

    return data


def validate_enrichment_model(
    enrichment: SemanticEnrichment,
    graph: dict[str, Any],
) -> SemanticEnrichment | None:
    """Validate a parsed ``SemanticEnrichment`` model against structural allowlist.

    Use after Instructor extraction (``instructor.from_messages``) to verify all
    ``node_id`` references exist in the graph. Pydantic schema already forbids
    structural keys (edges, order, etc.) — this adds the allowlist check.

    Returns the model if valid, ``None`` if any ID is unknown (atomic reject).
    """
    allowlist = _build_allowlist(graph)
    for item in enrichment.labels + enrichment.summaries:
        if item.node_id not in allowlist:
            logger.warning(
                "enrichment model rejected: node_id %r not in allowlist", item.node_id
            )
            return None
    return enrichment


if __name__ == "__main__":
    """Self-check: validation rules."""
    graph = {
        "nodes": {
            "files": [{"id": "a.py"}],
            "functions": [{"id": "a.py::foo"}],
            "classes": [],
            "modules": [],
        },
        "edges": {},
    }

    # 1. Valid enrichment — labels only, known IDs.
    ok = validate_semantic_enrichment(
        '{"function_id": "a.py::foo", "label": "entry point"}', graph
    )
    assert ok is not None and ok["label"] == "entry point", ok

    # 2. Invalid JSON → None.
    assert validate_semantic_enrichment("not json{", graph) is None

    # 3. Not a dict (array) → None.
    assert validate_semantic_enrichment("[1,2,3]", graph) is None

    # 4. Forbidden key (edges) → None.
    assert validate_semantic_enrichment('{"edges": []}', graph) is None

    # 5. Unknown ID → None.
    assert validate_semantic_enrichment(
        '{"function_id": "b.py::bar"}', graph
    ) is None

    # 6. Empty/whitespace → None.
    assert validate_semantic_enrichment("", graph) is None
    assert validate_semantic_enrichment("   ", graph) is None

    # 7. Valid with nested structure.
    ok2 = validate_semantic_enrichment(
        '{"summaries": [{"file_id": "a.py", "text": "main module"}]}', graph
    )
    assert ok2 is not None, ok2

    # 8. Pydantic model — valid enrichment accepted.
    from graps.ai.validator import NodeLabel, SemanticEnrichment, validate_enrichment_model
    model = SemanticEnrichment(
        labels=[NodeLabel(node_id="a.py::foo", label="entry point")],
        summaries=[NodeLabel(node_id="a.py", summary="main module")],
    )
    ok3 = validate_enrichment_model(model, graph)
    assert ok3 is not None and ok3.labels[0].label == "entry point", ok3

    # 9. Pydantic model — unknown node_id rejected.
    bad = SemanticEnrichment(labels=[NodeLabel(node_id="z.py::nope")])
    assert validate_enrichment_model(bad, graph) is None

    # 10. Pydantic schema rejects forbidden keys (edges).
    from pydantic import ValidationError
    try:
        SemanticEnrichment.model_validate({"edges": [], "labels": []})
        raise AssertionError("Pydantic should reject unknown 'edges' field")
    except ValidationError:
        pass  # expected — schema doesn't have 'edges' field

    print("validator.py self-check OK")
