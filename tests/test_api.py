"""Integration tests for graps server API (BLUEPRINT §13.4).

Phase 5: ``/api/ai/summary`` deprecated (keep route, return deprecation).
``/api/ai/chat`` endpoint baru (stateless, build_ai_context + provider.chat).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from graps.ai.provider import AIError
from graps import storage
from graps.server.app import build_ai_context, create_app

from pathlib import Path

# --- fixtures & helpers -------------------------------------------------------

PORT = 8765


@pytest.fixture()
def simple_graph():
    return {
        "schema_version": "1.0.0",
        "scan": {
            "file_count": 1,
            "function_count": 1,
            "edge_count": 0,
            "diagnostics": [],
            "scanned_at": "2026-01-01T00:00:00",
        },
        "content_hash": "",
        "nodes": {
            "files": [{"id": "a.py", "type": "file", "path": "a.py", "language": "python",
                       "module_id": "a", "modified_at": "2026-01-01T00:00:00",
                       "constants": [], "exported_names": []}],
            "functions": [{"id": "a.py::foo", "type": "function", "file_id": "a.py",
                           "module_id": "a", "name": "foo", "qualified_name": "foo",
                           "line_start": 1, "line_end": 2, "decorators": [],
                           "is_private": False, "is_nested": False,
                           "is_property": False, "parent": None}],
            "classes": [],
            "modules": [],
        },
        "edges": {"imports": [], "calls": [], "contains": [], "module_depends": []},
        "flows": [],
    }


@pytest.fixture()
def ai_body():
    return {
        "file": "a.py",
        "function": "foo",
        "line": 1,
        "modified_at": "2026-01-01",
        "source": "def foo(): pass",
    }


def _client(graph_data, tmp_path, port=PORT, scan_root=None):
    app = create_app(graph_data, port=port, cache_path=tmp_path / "cache.json", scan_root=scan_root)
    return TestClient(app, base_url=f"http://127.0.0.1:{port}")


def _hdr(host=None, origin=None):
    h = {}
    if host:
        h["host"] = host
    if origin:
        h["origin"] = origin
    return h


# --- 1-3: GET /api/graph ------------------------------------------------------


def test_get_graph__returns_200_with_schema(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path).get("/api/graph", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert r.status_code == 200
    j = r.json()
    for k in ("schema_version", "scan", "content_hash", "nodes", "edges", "flows"):
        assert k in j
    assert j["scan"]["file_count"] > 0


def test_get_graph__nodes_match_schema(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path).get("/api/graph", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    files = r.json()["nodes"]["files"]
    assert files, "files collection not empty"
    f = files[0]
    for k in ("id", "type", "path", "language"):
        assert k in f, f"missing {k}"
    fns = r.json()["nodes"]["functions"]
    fn = fns[0]
    for k in ("name", "qualified_name", "file_id"):
        assert k in fn, f"missing {k}"


def test_get_graph__sanitized_constants_phase1_default(simple_graph, tmp_path):
    files = _client(simple_graph, tmp_path).get(
        "/api/graph", headers=_hdr(host=f"127.0.0.1:{PORT}")
    ).json()["nodes"]["files"]
    assert files[0]["constants"] == []


# --- 4-9: security middleware --------------------------------------------------


def test_security__invalid_host_header_400(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path).get("/api/graph", headers=_hdr(host="evil.com"))
    assert r.status_code == 400
    assert r.json() == {"error": "Invalid Host"}


def test_security__valid_host_passes(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path).get("/api/graph", headers=_hdr(host=f"localhost:{PORT}"))
    assert r.status_code == 200


def test_security__valid_127_host_passes(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path).get("/api/graph", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert r.status_code == 200


def test_security__non_loopback_host_relaxes_middleware(simple_graph, tmp_path):
    """--host 0.0.0.0 (VPS/LAN) → Host/Origin dari IP non-loopback diterima.

    Default (127.0.0.1) masih nolak Host/Origin asing — test ini cuma jaga
    cabang relax-nya gak rusak kalau ada refactor.
    """
    lan = "192.168.1.10"
    app = create_app(simple_graph, port=PORT, host="0.0.0.0",
                     cache_path=tmp_path / "cache.json", scan_root=tmp_path)
    client = TestClient(app, base_url=f"http://{lan}:{PORT}")
    # GET dari LAN Host → 200 (validate_host di-relax).
    r = client.get("/api/graph", headers=_hdr(host=f"{lan}:{PORT}"))
    assert r.status_code == 200, r.status_code
    # POST dari LAN Origin → 200 (enforce_origin di-relax). Cuma cek status,
    # bukan isi body — env API key di mesin test bisa ter-set (enabled=True),
    # yang diuji di sini cuma cabang relax middleware, bukan provider logic.
    r = client.post("/api/ai/chat", json={"message": "hi"},
                    headers=_hdr(host=f"{lan}:{PORT}", origin=f"http://{lan}:{PORT}"))
    assert r.status_code == 200, r.status_code


def test_security__post_invalid_origin_403(simple_graph, tmp_path, ai_body):
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/summary", json=ai_body, headers=_hdr(host=f"127.0.0.1:{PORT}", origin="http://evil.com")
    )
    assert r.status_code == 403
    assert r.json() == {"error": "Forbidden"}


def test_security__post_origin_prefix_bypass_rejected_403(simple_graph, tmp_path, ai_body):
    # CSRF guard must exact-match Origin, not startswith() (report-bug-server Finding 1).
    attack_origins = [
        f"http://localhost:{PORT}.evil.com",
        f"http://localhost:{PORT}@evil.com",
        f"http://localhost:{PORT}x",
        f"http://127.0.0.1:{PORT}.attacker.com",
        f"http://127.0.0.1:{PORT}@attacker.com",
    ]
    for origin in attack_origins:
        r = _client(simple_graph, tmp_path).post(
            "/api/ai/summary", json=ai_body, headers=_hdr(host=f"127.0.0.1:{PORT}", origin=origin)
        )
        assert r.status_code == 403, f"bypass leaked for origin={origin!r}: {r.status_code}"
        assert r.json() == {"error": "Forbidden"}


def test_security__post_no_origin_rejected_403(simple_graph, tmp_path, ai_body):
    # Fail-closed CSRF guard: no Origin header → 403 (report-bug-finder Finding 2).
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/summary", json=ai_body, headers=_hdr(host=f"127.0.0.1:{PORT}")
    )
    assert r.status_code == 403
    assert r.json() == {"error": "Forbidden"}


def test_security__chat_post_invalid_origin_403(simple_graph, tmp_path):
    # Chat juga POST → CSRF guard tetap jalan.
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/chat", json={"message": "hi"}, headers=_hdr(host=f"127.0.0.1:{PORT}", origin="http://evil.com")
    )
    assert r.status_code == 403
    assert r.json() == {"error": "Forbidden"}


def test_security__chat_post_no_origin_rejected_403(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/chat", json={"message": "hi"}, headers=_hdr(host=f"127.0.0.1:{PORT}")
    )
    assert r.status_code == 403


def test_security__post_valid_origin_passes(simple_graph, tmp_path, ai_body, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/summary", json=ai_body, headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://localhost:{PORT}")
    )
    assert r.status_code != 403


# --- /api/ai/summary DEPRECATED (Phase 5) ------------------------------------


def test_ai_summary__deprecated_response(simple_graph, tmp_path, ai_body):
    # Route tetap, return deprecation response (logic provider/cache tidak jalan).
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/summary", json=ai_body, headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}")
    )
    assert r.status_code == 200
    assert r.json() == {"deprecated": True, "reason": "use /api/ai/chat"}


# --- /api/ai/chat (Phase 5) --------------------------------------------------


def test_chat__empty_message_rejected(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/chat", json={"message": "   "}, headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}")
    )
    assert r.status_code == 200
    assert r.json() == {"enabled": False, "reason": "empty_message", "warnings": []}


def test_chat__no_api_key_returns_disabled(simple_graph, tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/chat", json={"message": "why?", "tagged": ["a.py"]},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    assert r.status_code == 200
    j = r.json()
    assert j["enabled"] is False and j["reason"] == "no_api_key", j
    # no scan_root → build_ai_context returns ("", []).
    assert j["warnings"] == [], j


def test_chat__mocked_provider_returns_reply(simple_graph, tmp_path, monkeypatch):
    captured = {}

    class Fake:
        name = "fake"
        def chat(self, messages, context):
            captured["messages"] = messages
            captured["context"] = context
            return "debug answer"

    monkeypatch.setattr("graps.ai.provider.get_provider", lambda: Fake())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/chat",
        json={
            "message": "why foo?",
            "tagged": [],
            "history": [{"role": "assistant", "content": "hi"}],
        },
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    j = r.json()
    assert j["enabled"] is True and j["reply"] == "debug answer", j
    # history + message appended.
    assert captured["messages"] == [
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "why foo?"},
    ], captured["messages"]


def test_chat__mocked_auth_failed(simple_graph, tmp_path, monkeypatch):
    class Fake:
        name = "fake"
        def chat(self, messages, context):
            raise AIError("auth_failed")

    monkeypatch.setattr("graps.ai.provider.get_provider", lambda: Fake())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/chat", json={"message": "hi"},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    j = r.json()
    assert j["enabled"] is True and j["error_type"] == "auth_failed", j
    body_text = r.text.lower()
    assert "key" not in body_text and "apikey" not in body_text


def test_chat__rate_limited_with_retry_after(simple_graph, tmp_path, monkeypatch):
    class Fake:
        name = "fake"
        def chat(self, messages, context):
            raise AIError("rate_limited", retry_after=15)

    monkeypatch.setattr("graps.ai.provider.get_provider", lambda: Fake())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    r = _client(simple_graph, tmp_path).post(
        "/api/ai/chat", json={"message": "hi"},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    j = r.json()
    assert j["error_type"] == "rate_limited" and j["retry_after"] == 15, j


def test_chat__sdk_not_installed_returns_disabled(simple_graph, tmp_path, monkeypatch):
    class Fake:
        name = "fake"
        def chat(self, messages, context):
            raise AIError("sdk_not_installed")

    monkeypatch.setattr("graps.ai.provider.get_provider", lambda: Fake())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    r = _client(simple_graph, tmp_path, scan_root=tmp_path).post(
        "/api/ai/chat", json={"message": "hi"},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    j = r.json()
    assert j["enabled"] is False and j["reason"] == "sdk_not_installed", j


def test_chat__ai_enrichment_off_returns_disabled(simple_graph, tmp_path, monkeypatch):
    """FEAT-0019: ai_enrichment=False in settings → chat disabled, structure works."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")  # key exists but toggle OFF
    storage.write_settings(tmp_path, {"ai_enrichment": False})
    r = _client(simple_graph, tmp_path, scan_root=tmp_path).post(
        "/api/ai/chat", json={"message": "why?", "tagged": ["a.py"]},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    j = r.json()
    assert j["enabled"] is False and j["reason"] == "ai_enrichment_off", j
    # Graph endpoint still works — structural browsing not affected.
    g = _client(simple_graph, tmp_path, scan_root=tmp_path).get(
        "/api/graph", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert g.status_code == 200


def test_chat__ai_enrichment_on_allows_chat(simple_graph, tmp_path, monkeypatch):
    """ai_enrichment=True (default) → chat proceeds normally."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    storage.write_settings(tmp_path, {"ai_enrichment": True})

    class Fake:
        name = "fake"
        def chat(self, messages, context):
            return "answer"

    monkeypatch.setattr("graps.ai.provider.get_provider", lambda: Fake())
    r = _client(simple_graph, tmp_path, scan_root=tmp_path).post(
        "/api/ai/chat", json={"message": "why?"},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    j = r.json()
    assert j["enabled"] is True and j["reply"] == "answer", j


def test_chat__invalid_ai_output_preserves_graph_truth(simple_graph, tmp_path, monkeypatch):
    """Phase gate: invalid AI output cannot alter graph truth or stop browsing."""
    import copy

    class FakeMalicious:
        name = "fake"
        def chat(self, messages, context):
            return '{"action": "delete", "target": "all_edges"}'

    monkeypatch.setattr("graps.ai.provider.get_provider", lambda: FakeMalicious())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")

    graph_before = copy.deepcopy(simple_graph)
    client = _client(simple_graph, tmp_path, scan_root=tmp_path)

    r = client.post(
        "/api/ai/chat",
        json={"message": "delete all edges", "tagged": ["a.py"]},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    assert r.status_code == 200
    j = r.json()
    assert j["enabled"] is True, j
    assert "delete" in j["reply"], j  # reply passed through as-is, not interpreted

    # Graph unchanged — AI output cannot alter structural truth.
    g = client.get("/api/graph", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert g.status_code == 200
    assert g.json() == graph_before, "graph truth was altered by AI output!"

    # Structural browsing still works.
    assert g.json()["scan"]["file_count"] == 1
    assert len(g.json()["nodes"]["functions"]) == 1


# --- build_ai_context + scan_root --------------------------------------------


def test_chat__build_context_with_scan_root(simple_graph, tmp_path, monkeypatch):
    # Tulis source asli ke scan_root (tmp_path) supaya build_ai_context baca disk.
    (tmp_path / "a.py").write_text("def foo():\n    return 42\n\ndef bar(): pass\n")
    # Update function dengan line_start/line_end supaya function body di-extract presisi.
    graph = {
        **simple_graph,
        "nodes": {
            **simple_graph["nodes"],
            "functions": [{
                **simple_graph["nodes"]["functions"][0],
                "line_start": 1, "line_end": 2,
            }],
        },
    }
    captured = {}

    class Fake:
        name = "fake"
        def chat(self, messages, context):
            captured["context"] = context
            return "ok"

    monkeypatch.setattr("graps.ai.provider.get_provider", lambda: Fake())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    r = _client(graph, tmp_path, scan_root=tmp_path).post(
        "/api/ai/chat", json={"message": "why 42?", "tagged": ["a.py::foo"]},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    j = r.json()
    assert j["enabled"] is True and j["reply"] == "ok", j
    # context mengandung function body dari disk (hanya foo, bukan bar).
    assert "def foo" in captured["context"], captured["context"]
    assert "return 42" in captured["context"], captured["context"]
    assert "def bar" not in captured["context"], captured["context"]


def test_chat__credential_file_excluded(simple_graph, tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("SECRET=hunter2\nDB_PASSWORD=hunter3")
    captured = {}

    class Fake:
        name = "fake"
        def chat(self, messages, context):
            captured["context"] = context
            return "ok"

    monkeypatch.setattr("graps.ai.provider.get_provider", lambda: Fake())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    r = _client(simple_graph, tmp_path, scan_root=tmp_path).post(
        "/api/ai/chat", json={"message": "x", "tagged": [".env"]},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    j = r.json()
    assert any(w["reason"] == "credential_file_excluded" for w in j["warnings"]), j
    assert "hunter2" not in captured["context"], captured["context"]
    assert "hunter3" not in captured["context"], captured["context"]


def test_chat__no_scan_root_empty_context(simple_graph, tmp_path, monkeypatch):
    # scan_root=None → build_ai_context return ("", []) — backward-compat test.
    captured = {}

    class Fake:
        name = "fake"
        def chat(self, messages, context):
            captured["context"] = context
            return "ok"

    monkeypatch.setattr("graps.ai.provider.get_provider", lambda: Fake())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    r = _client(simple_graph, tmp_path, scan_root=None).post(
        "/api/ai/chat", json={"message": "hi", "tagged": ["a.py"]},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"),
    )
    j = r.json()
    assert j["enabled"] is True and j["reply"] == "ok", j
    assert captured["context"] == "", captured["context"]
    assert j["warnings"] == [], j


# --- build_ai_context unit (isolated) ----------------------------------------


def test_build_ai_context__empty_when_no_tagged(simple_graph, tmp_path):
    ctx, warns = build_ai_context([], simple_graph, tmp_path)
    assert ctx == "" and warns == []


def test_build_ai_context__empty_when_no_scan_root(simple_graph, tmp_path):
    ctx, warns = build_ai_context(["a.py"], simple_graph, None)
    assert ctx == "" and warns == []


def test_build_ai_context__credential_file_warning(simple_graph, tmp_path):
    (tmp_path / ".env").write_text("SECRET=x")
    ctx, warns = build_ai_context([".env"], simple_graph, tmp_path)
    assert any(w["reason"] == "credential_file_excluded" for w in warns), warns
    assert "SECRET=x" not in ctx, ctx


def test_build_ai_context__file_not_in_graph_warning(simple_graph, tmp_path):
    (tmp_path / "unknown.py").write_text("x = 1")
    ctx, warns = build_ai_context(["unknown.py"], simple_graph, tmp_path)
    assert any(w["reason"] == "file_not_in_graph" for w in warns), warns


# --- /api/source hardening (TASK-0004) ----------------------------------------


def test_source__credential_file_blocked_404(simple_graph, tmp_path):
    """GET /api/source?file=.env → 404 (credential files blocked, not leaked)."""
    (tmp_path / ".env").write_text("SECRET=hunter2")
    r = _client(simple_graph, tmp_path, scan_root=tmp_path).get(
        "/api/source", params={"file": ".env"},
        headers=_hdr(host=f"127.0.0.1:{PORT}"),
    )
    assert r.status_code == 404, r.status_code
    assert "hunter2" not in r.text, r.text


def test_source__credential_ext_blocked_404(simple_graph, tmp_path):
    """Credential extensions (.pem, .key) also blocked."""
    (tmp_path / "server.pem").write_text("PRIVATE KEY DATA")
    r = _client(simple_graph, tmp_path, scan_root=tmp_path).get(
        "/api/source", params={"file": "server.pem"},
        headers=_hdr(host=f"127.0.0.1:{PORT}"),
    )
    assert r.status_code == 404, r.status_code


def test_source__read_error_no_path_leak(simple_graph, tmp_path, monkeypatch):
    """500 on read failure must not serialize OSError (absolute path leak)."""
    (tmp_path / "a.py").write_text("def foo(): pass")

    real_read = Path.read_text
    def _boom(self, *a, **kw):
        if self.suffix == ".py":
            raise OSError(13, "Permission denied", str(self))
        return real_read(self, *a, **kw)

    monkeypatch.setattr(Path, "read_text", _boom)
    r = _client(simple_graph, tmp_path, scan_root=tmp_path).get(
        "/api/source", params={"file": "a.py"},
        headers=_hdr(host=f"127.0.0.1:{PORT}"),
    )
    assert r.status_code == 500, r.status_code
    assert str(tmp_path) not in r.text, r.text
    assert "Permission" not in r.text, r.text
    assert r.json() == {"error": "Failed to read file"}, r.json()


# --- /api/modules, /api/flows, /api/settings, /api/scan (TASK-0004) ------------


_GRAPH_WITH_MODULES_FLOWS = {
    "schema_version": "1.0.0",
    "scan": {"file_count": 2, "function_count": 2, "edge_count": 0, "diagnostics": []},
    "content_hash": "",
    "nodes": {
        "files": [
            {"id": "a.py", "type": "file", "path": "a.py", "language": "python",
             "module_id": "mod_a", "modified_at": "", "constants": [], "exported_names": []},
            {"id": "b.py", "type": "file", "path": "b.py", "language": "python",
             "module_id": "mod_b", "modified_at": "", "constants": [], "exported_names": []},
        ],
        "functions": [
            {"id": "a.py::foo", "type": "function", "file_id": "a.py", "module_id": "mod_a",
             "name": "foo", "qualified_name": "foo", "line_start": 1, "line_end": 2,
             "decorators": [], "is_private": False, "is_nested": False,
             "is_property": False, "parent": None},
            {"id": "b.py::bar", "type": "function", "file_id": "b.py", "module_id": "mod_b",
             "name": "bar", "qualified_name": "bar", "line_start": 1, "line_end": 2,
             "decorators": [], "is_private": False, "is_nested": False,
             "is_property": False, "parent": None},
        ],
        "classes": [],
        "modules": [
            {"id": "mod_a", "type": "module", "name": "a", "file_id": "a.py"},
            {"id": "mod_b", "type": "module", "name": "b", "file_id": "b.py"},
        ],
    },
    "edges": {"imports": [], "calls": [], "contains": [], "module_depends": []},
    "flows": [
        {"id": "flow_1", "type": "call_sequence", "steps": [{"fn": "a.py::foo", "label": "call"}]},
    ],
}


def test_modules__valid_returns_members():
    r = _client(_GRAPH_WITH_MODULES_FLOWS, Path("/tmp")).get(
        "/api/modules/mod_a", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert r.status_code == 200, r.status_code
    j = r.json()
    assert j["id"] == "mod_a"
    assert "a.py" in j["member_files"]
    assert "a.py::foo" in j["member_functions"]


def test_modules__unknown_returns_404():
    r = _client(_GRAPH_WITH_MODULES_FLOWS, Path("/tmp")).get(
        "/api/modules/nonexistent", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert r.status_code == 404
    assert r.json() == {"error": "Module not found"}


def test_flows__valid_returns_flow():
    r = _client(_GRAPH_WITH_MODULES_FLOWS, Path("/tmp")).get(
        "/api/flows/flow_1", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert r.status_code == 200, r.status_code
    assert r.json()["id"] == "flow_1"


def test_flows__unknown_returns_404():
    r = _client(_GRAPH_WITH_MODULES_FLOWS, Path("/tmp")).get(
        "/api/flows/nope", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert r.status_code == 404
    assert r.json() == {"error": "Flow not found"}


def test_settings__get_returns_defaults_no_scan_root(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path, scan_root=None).get(
        "/api/settings", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert r.status_code == 200
    j = r.json()
    assert j["ai_enrichment"] is True  # default ON
    assert j["panel_widths"]["dir"] == 280


def test_settings__get_returns_stored(simple_graph, tmp_path):
    storage.write_settings(tmp_path, {"ai_enrichment": False, "panel_widths": {"dir": 500}})
    r = _client(simple_graph, tmp_path, scan_root=tmp_path).get(
        "/api/settings", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert r.status_code == 200
    j = r.json()
    assert j["ai_enrichment"] is False
    assert j["panel_widths"]["dir"] == 500


def test_settings__put_whitelist_drops_unknown(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path, scan_root=tmp_path).put(
        "/api/settings",
        json={"ai_enrichment": False, "evil_key": "drop_me"},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin=f"http://127.0.0.1:{PORT}"))
    assert r.status_code == 200
    j = r.json()
    assert j["ai_enrichment"] is False
    assert "evil_key" not in j, "unknown key must be dropped"


def test_settings__put_csrf_rejected(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path, scan_root=tmp_path).put(
        "/api/settings",
        json={"ai_enrichment": True},
        headers=_hdr(host=f"127.0.0.1:{PORT}", origin="http://evil.com"))
    assert r.status_code == 403


def test_scan_status__returns_metadata(simple_graph, tmp_path):
    r = _client(simple_graph, tmp_path).get(
        "/api/scan/status", headers=_hdr(host=f"127.0.0.1:{PORT}"))
    assert r.status_code == 200
    j = r.json()
    assert "file_count" in j
    assert j["file_count"] == 1
