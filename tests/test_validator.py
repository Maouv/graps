"""Tests for semantic enrichment validation (FEAT-0019 phase gate)."""
from __future__ import annotations

from graps.ai.validator import validate_semantic_enrichment

# Minimal graph for allowlist tests.
_GRAPH = {
    "nodes": {
        "files": [{"id": "a.py", "type": "file"}],
        "functions": [{"id": "a.py::foo", "type": "function"}],
        "classes": [],
        "modules": [{"id": "a", "type": "module"}],
    },
    "edges": {},
}


def test_valid_enrichment__labels_only():
    """Labels on known IDs pass."""
    r = validate_semantic_enrichment(
        '{"function_id": "a.py::foo", "label": "entry point"}', _GRAPH
    )
    assert r is not None
    assert r["label"] == "entry point"


def test_invalid_json__rejected():
    assert validate_semantic_enrichment("not json{", _GRAPH) is None


def test_empty_string__rejected():
    assert validate_semantic_enrichment("", _GRAPH) is None
    assert validate_semantic_enrichment("   ", _GRAPH) is None


def test_not_object__rejected():
    assert validate_semantic_enrichment("[1,2,3]", _GRAPH) is None
    assert validate_semantic_enrichment('"string"', _GRAPH) is None
    assert validate_semantic_enrichment("42", _GRAPH) is None


def test_forbidden_key_edges__rejected():
    assert validate_semantic_enrichment('{"edges": []}', _GRAPH) is None


def test_forbidden_key_calls__rejected():
    assert validate_semantic_enrichment('{"calls": []}', _GRAPH) is None


def test_forbidden_key_order__rejected():
    assert validate_semantic_enrichment('{"order": 1}', _GRAPH) is None


def test_forbidden_key_scan__rejected():
    assert validate_semantic_enrichment('{"scan": {}}', _GRAPH) is None


def test_unknown_id__rejected():
    assert validate_semantic_enrichment(
        '{"function_id": "b.py::bar"}', _GRAPH
    ) is None


def test_unknown_file_id__rejected():
    assert validate_semantic_enrichment(
        '{"file_id": "z.py"}', _GRAPH
    ) is None


def test_known_module_id__accepted():
    r = validate_semantic_enrichment(
        '{"target": "a", "label": "core module"}', _GRAPH
    )
    assert r is not None
    assert r["label"] == "core module"


def test_nested_unknown_id__rejected():
    """Unknown ID in nested structure is caught."""
    assert validate_semantic_enrichment(
        '{"summaries": [{"file_id": "z.py", "text": "bad"}]}', _GRAPH
    ) is None


def test_nested_known_id__accepted():
    r = validate_semantic_enrichment(
        '{"summaries": [{"file_id": "a.py", "text": "ok"}]}', _GRAPH
    )
    assert r is not None


def test_nested_forbidden_key__rejected():
    """Forbidden key in nested structure is caught."""
    assert validate_semantic_enrichment(
        '{"items": [{"line": 42}]}', _GRAPH
    ) is None


def test_arbitrary_labels__accepted():
    """Arbitrary label/summary text is fine — only IDs are checked."""
    r = validate_semantic_enrichment(
        '{"function_id": "a.py::foo", "summary": "this calls bar()"}', _GRAPH
    )
    assert r is not None
    assert "bar()" in r["summary"]


def test_empty_graph__all_ids_rejected():
    """Empty graph → no IDs in allowlist → all ID references rejected."""
    empty_graph = {
        "nodes": {"files": [], "functions": [], "classes": [], "modules": []},
        "edges": {},
    }
    assert validate_semantic_enrichment(
        '{"function_id": "a.py::foo"}', empty_graph
    ) is None
    # But no-ID enrichment is fine.
    r = validate_semantic_enrichment('{"label": "hello"}', empty_graph)
    assert r is not None


# --- Pydantic model tests (Instructor extraction layer) ---------------------


def test_pydantic_model__valid_enrichment_accepted():
    """SemanticEnrichment model accepts valid labels with known IDs."""
    from graps.ai.validator import NodeLabel, SemanticEnrichment, validate_enrichment_model
    model = SemanticEnrichment(
        labels=[NodeLabel(node_id="a.py::foo", label="entry point")],
        summaries=[NodeLabel(node_id="a.py", summary="main module")],
    )
    r = validate_enrichment_model(model, _GRAPH)
    assert r is not None
    assert r.labels[0].label == "entry point"


def test_pydantic_model__unknown_id_rejected():
    """Model with unknown node_id → None (atomic reject)."""
    from graps.ai.validator import NodeLabel, SemanticEnrichment, validate_enrichment_model
    bad = SemanticEnrichment(labels=[NodeLabel(node_id="z.py::nope")])
    assert validate_enrichment_model(bad, _GRAPH) is None


def test_pydantic_schema__rejects_edges_field():
    """Pydantic schema forbids 'edges' — extra='forbid' enforcement."""
    import pytest
    from pydantic import ValidationError

    from graps.ai.validator import SemanticEnrichment
    with pytest.raises(ValidationError):
        SemanticEnrichment.model_validate({"edges": [], "labels": []})


def test_pydantic_schema__rejects_calls_field():
    """Pydantic schema forbids 'calls' — structural truth only."""
    import pytest
    from pydantic import ValidationError

    from graps.ai.validator import SemanticEnrichment
    with pytest.raises(ValidationError):
        SemanticEnrichment.model_validate({"calls": [], "labels": []})


def test_pydantic_schema__rejects_order_field():
    """Pydantic schema forbids 'order' — flow order is structural-only."""
    import pytest
    from pydantic import ValidationError

    from graps.ai.validator import SemanticEnrichment
    with pytest.raises(ValidationError):
        SemanticEnrichment.model_validate({"order": 1, "labels": []})


def test_pydantic_schema__node_label_rejects_extra_fields():
    """NodeLabel also forbids extra fields (e.g. line numbers)."""
    import pytest
    from pydantic import ValidationError

    from graps.ai.validator import NodeLabel
    with pytest.raises(ValidationError):
        NodeLabel.model_validate({"node_id": "a.py::foo", "line": 42})


def test_pydantic_model__empty_model_accepted():
    """Empty SemanticEnrichment (no labels/summaries) is valid — just useless."""
    from graps.ai.validator import SemanticEnrichment, validate_enrichment_model
    empty = SemanticEnrichment()
    assert validate_enrichment_model(empty, _GRAPH) is not None
