"""FastAPI app factory untuk graps (lihat BLUEPRINT.md §10–§12).

Module ini hanya tahu cara menyusun :class:`FastAPI` dengan:

- middleware keamanan ``enforce_origin`` + ``validate_host`` (BLUEPRINT §11),
- route ``GET /api/graph`` yang mengembalikan ``graph_data`` apa adanya,
- route ``POST /api/ai/chat`` (Phase 5) yang assemble context via
  ``build_ai_context`` lalu dispatch ke ``graps.ai.provider.chat``,
- route ``POST /api/ai/summary`` (DEPRECATED Phase 5 — keep route, return
  deprecation response; logic provider/cache tidak jalan).

Default bind ``127.0.0.1`` (loopback) ditetapkan caller (``cli.py``) via
param ``host``. Loopback → envelope security ketat (CORS + CSRF + DNS
rebinding). Bind non-loopback (``0.0.0.0`` / IP LAN, untuk VPS) → user
sengaja expose, middleware di-relax karena Host/Origin LAN gak akan pernah
cocok ``localhost``.

ponytail: tidak pakai ``APIRouter``/DI framework — semua route di satu file,
``cache_path`` + ``scan_root`` di-close-over dari ``create_app``. Pindah ke
router kalau endpoint sudah lewat ~10.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ponytail: dipanggil sebagai `python graps/server/app.py` (self-check) butuh
# repo root di sys.path supaya `import graps.ai...` ketemu. Tambah sebelum
# import graps.* di bawah. No-op kalau dijalankan via `python -m`.
if __name__ == "__main__":
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# ponytail: import modul, BUKAN ``from ... import get_provider``. Supaya test
# (dan integrasi lain) bisa monkeypatch ``provider_module.get_provider`` dan
# perubahan terlihat di sini juga.
from graps import storage  # noqa: E402
from graps.ai import provider as provider_module  # noqa: E402
from graps.ai.provider import AIError  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_CACHE_PATH: Path = Path.cwd() / ".graps" / "cache.json"


class SummaryRequest(BaseModel):
    """Body untuk ``POST /api/ai/summary`` (DEPRECATED Phase 5).

    Dipertahankan supaya test/import lama tidak break. Logic provider/cache
    tidak jalan — route hanya return deprecation response.
    """

    file: str
    function: str
    line: int
    modified_at: str
    source: str


class ChatRequest(BaseModel):
    """Body untuk ``POST /api/ai/chat`` (Phase 5).

    ``message``  : pertanyaan user (raw text).
    ``tagged``   : list tag ``"file.py"`` atau ``"file.py::function"``.
    ``history``  : ``[{"role": "user"|"assistant", "content": "..."}]``.
    """

    message: str
    tagged: list[str] = []
    history: list[dict[str, str]] = []


class SettingsUpdate(BaseModel):
    """Body untuk ``PUT /api/settings`` — whitelisted fields only."""

    ai_enrichment: bool | None = None
    overrides: dict[str, Any] | None = None
    panel_widths: dict[str, int] | None = None
    tabs: list[Any] | None = None


# --- Credential file exclusion (Option C — user tidak intend share) ----------

_CREDENTIAL_FILES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "credentials.json", "secrets.json", "secret.json",
}
_CREDENTIAL_EXTS = {".pem", ".key", ".p12", ".pfx"}


def _is_credential_file(rel_path: str) -> bool:
    """True kalau ``rel_path`` adalah file credential yang di-hard-exclude
    dari AI context."""
    name = Path(rel_path).name.lower()
    if name in _CREDENTIAL_FILES:
        return True
    if Path(rel_path).suffix.lower() in _CREDENTIAL_EXTS:
        return True
    if name.startswith(".env."):
        return True
    return False


def _approx_tokens(text: str) -> int:
    """Estimasi token kasar. ponytail: ``len(text)//4`` (~4 chars/token untuk
    English + code). Ceiling: kadang under/over budget. Upgrade path: tiktoken
    kalau provider OpenAI + akurasi critical."""
    return max(len(text) // 4, 1)


def _truncate(text: str, budget_tokens: int) -> str:
    """Truncate ``text`` ke ~``budget_tokens`` token, marker
    ``... [truncated, N lines omitted]`` kalau terpotong."""
    if _approx_tokens(text) <= budget_tokens:
        return text
    lines = text.split("\n")
    out: list[str] = []
    used = 0
    for ln in lines:
        cost = _approx_tokens(ln) + 1  # +1 for the newline
        if used + cost > budget_tokens:
            break
        out.append(ln)
        used += cost
    omitted = len(lines) - len(out)
    if omitted > 0:
        out.append(f"... [truncated, {omitted} lines omitted]")
    return "\n".join(out)


def _format_function_metadata(fn: dict[str, Any], rel: str) -> str:
    """Susun [Graph Context] block untuk satu function."""
    name = fn.get("name", "?")
    ls = fn.get("line_start")
    le = fn.get("line_end")
    rng = f"{ls}-{le}" if ls and le else str(ls or "?")
    callers = fn.get("callers") or []
    callees = fn.get("callees") or []
    risks = fn.get("risks") or []
    params = fn.get("params") or []
    returns = fn.get("returns")
    lines = [f"Function: {name} ({rel}:{rng})"]
    if callers:
        lines.append("Called by: " + ", ".join(str(c) for c in callers))
    if callees:
        lines.append("Calls: " + ", ".join(str(c) for c in callees))
    if params:
        lines.append("Params: " + ", ".join(str(p) for p in params))
    if returns:
        lines.append(f"Returns: {returns}")
    if risks:
        lines.append("Risk flags: " + "; ".join(
            r.get("message") or r.get("type") or str(r) for r in risks
        ))
    return "\n".join(lines)


def _format_file_metadata(node: dict[str, Any]) -> str:
    """Susun [Graph Context] block untuk satu file node."""
    rel = node.get("path") or node.get("id") or "?"
    fns = node.get("functions") or []
    consts = node.get("constants") or []
    lines = [f"File: {rel}"]
    if fns:
        lines.append("Functions: " + ", ".join(f.get("name", "?") for f in fns))
    if consts:
        lines.append("Constants: " + ", ".join(
            f"{c.get('name','?')}={c.get('value','?')}" for c in consts
        ))
    return "\n".join(lines)


def _extract_function_body(source: str, line_start: int | None, line_end: int | None) -> str:
    """Ambil baris ``line_start..line_end`` (1-based) dari ``source``.
    ponytail: kalau line_end None, ambil sampai EOF. Kalau line_start None,
    return seluruh source (fallback aman)."""
    if line_start is None:
        return source
    src_lines = source.split("\n")
    start = max(line_start - 1, 0)
    if line_end is None:
        return "\n".join(src_lines[start:])
    end = min(line_end, len(src_lines))
    return "\n".join(src_lines[start:end])


# Map file suffix → Prism.js language id (PHASE5 §10 / F2). ponytail: only the
# languages Prism loads via CDN in index.html — unknown → "none" (plain text).
_LANGUAGE_FOR_SUFFIX: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".sql": "sql",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".html": "markup",
    ".xml": "markup",
    ".md": "markdown",
}


def _language_for_suffix(suffix: str) -> str:
    """Prism language id untuk ``suffix`` (mis. ``".py"`` → ``"python"``)."""
    return _LANGUAGE_FOR_SUFFIX.get(suffix.lower(), "none")


def _file_view(graph: dict[str, Any], file_id: str) -> dict[str, Any] | None:
    """Typed collections → file-centric view (compat for build_ai_context / get_source).

    New schema separates files and functions into typed collections. This adapter
    reassembles a file node with its functions attached, matching the old shape
    that ``build_ai_context`` and ``get_source`` expect.
    """
    files = (graph.get("nodes") or {}).get("files") or []
    fnode = next((f for f in files if f.get("id") == file_id), None)
    if fnode is None:
        return None
    fns = (graph.get("nodes") or {}).get("functions") or []
    return {**fnode, "functions": [f for f in fns if f.get("file_id") == file_id]}


def build_ai_context(
    tagged: list[str],
    graph: dict[str, Any],
    scan_root: Path | None,
    max_tokens: int = 8000,
) -> tuple[str, list[dict[str, str]]]:
    """Assemble context dari tagged items untuk dikirim ke AI (Option C).

    Per tagged item (format ``"file.py"`` atau ``"file.py::function"``):
    1. Graph metadata (callers, callees, risk flags, params, returns, range).
    2. Source dari disk — function body kalau tag fungsi, file truncated
       kalau tag file.
    3. ``.env``/credential exclusion → skip source, catat warning.
    4. Token budget per item, truncate dengan ``... [truncated]``.

    Return ``(context_str, warnings)`` di mana ``warnings =
    [{file, reason}, ...]``.
    """
    if not tagged or scan_root is None:
        return "", []

    per_item = max(max_tokens // max(len(tagged), 1), 1)

    parts: list[str] = []
    warnings: list[dict[str, str]] = []

    for tag in tagged:
        if "::" in tag:
            rel_path, fn_name = tag.split("::", 1)
        else:
            rel_path, fn_name = tag, None

        node = _file_view(graph, rel_path)
        meta_block = ""
        if node is not None:
            if fn_name is not None:
                fns = node.get("functions") or []
                fn = next((f for f in fns if f.get("name") == fn_name), None)
                if fn is not None:
                    meta_block = _format_function_metadata(fn, rel_path)
                else:
                    warnings.append({"file": rel_path, "reason": "function_not_found"})
                    meta_block = f"Function: {fn_name} (not found in {rel_path})"
            else:
                meta_block = _format_file_metadata(node)
        else:
            warnings.append({"file": rel_path, "reason": "file_not_in_graph"})
            meta_block = f"File: {rel_path} (not in graph)"

        # Credential hard-exclude — source tidak dibaca, warning dicatat.
        if _is_credential_file(rel_path):
            warnings.append({"file": rel_path, "reason": "credential_file_excluded"})
            parts.append(
                f"[Graph Context]\n{meta_block}\n\n[Source Context]\n"
                "<credential file excluded — source not sent>"
            )
            continue

        # Baca source dari disk.
        source_text: str | None = None
        try:
            raw = (scan_root / rel_path).read_text(errors="replace")
            if fn_name is not None and node is not None:
                fns = node.get("functions") or []
                fn = next((f for f in fns if f.get("name") == fn_name), None)
                if fn is not None:
                    source_text = _extract_function_body(
                        raw, fn.get("line_start"), fn.get("line_end")
                    )
                else:
                    source_text = raw
            else:
                source_text = raw
        except (OSError, UnicodeDecodeError):
            warnings.append({"file": rel_path, "reason": "source_unreadable"})
            source_text = None

        src_budget = per_item - _approx_tokens(meta_block)
        if source_text is not None and src_budget > 0:
            src_block = _truncate(source_text, src_budget)
        else:
            src_block = "<no source available>"

        parts.append(f"[Graph Context]\n{meta_block}\n\n[Source Context]\n{src_block}")

    return "\n\n---\n\n".join(parts), warnings


def create_app(
    graph_data: dict[str, Any],
    port: int,
    cache_path: Path | None = None,
    scan_root: Path | None = None,
    host: str = "127.0.0.1",
) -> FastAPI:
    """Bangun :class:`FastAPI` lengkap dengan middleware, route, dan static mount.

    Parameters
    ----------
    graph_data:
        Dict graph hasil scanner. Dikembalikan apa adanya oleh ``GET /api/graph``.
    port:
        Port yang akan dipakai uvicorn — dipakai untuk membentuk daftar origin
        & host yang sah (``localhost:<port>`` / ``127.0.0.1:<port>``).
    cache_path:
        Lokasi file cache AI summary (DEPRECATED Phase 5). ``None`` →
        :data:`DEFAULT_CACHE_PATH`. Caller (CLI) yang boleh memilih.
    scan_root:
        Path absolut untuk baca source dari disk (Option C). ``None`` untuk
        backward-compat test yang tidak butuh baca source. Tidak masuk graph
        JSON (M-03 aman — meta.root tetap relatif ".").
    host:
        Alamat bind uvicorn (default ``127.0.0.1``). Loopback
        (``127.0.0.1``/``localhost``/``::1``) → CORS + ``enforce_origin`` +
        ``validate_host`` aktif (envelope security ketat). Non-loopback
        (mis. ``0.0.0.0`` untuk VPS/LAN) → ketiganya di-relax passthrough
        karena user sengaja expose; tanggung jawab keamanan jadi milik user.
    """
    app = FastAPI()
    # ponytail: loopback bind → envelope security ketat (CORS + CSRF + DNS
    # rebinding). Bind ke 0.0.0.0/IP LAN (VPS) → user sengaja expose, middleware
    # di-relax (allowed/host_ok kosong) karena Host/Origin LAN gak akan pernah
    # cocok localhost. Default tetap aman 127.0.0.1 (BLUEPRINT H-01).
    loopback = host in ("127.0.0.1", "localhost", "::1")
    if loopback:
        allowed: tuple[str, ...] = (f"http://localhost:{port}", f"http://127.0.0.1:{port}")
        host_ok: tuple[str, ...] = (f"localhost:{port}", f"127.0.0.1:{port}")
    else:
        allowed = ()
        host_ok = ()

    # CORS — Phase 1 hanya GET/POST, tidak ada cookie (allow_credentials=False).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed) if loopback else ["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def enforce_origin(
        request: Request, call_next: Callable[[Request], Awaitable[Any]]
    ) -> Any:
        """Tolak POST/PUT/DELETE tanpa Origin valid (CSRF guard, BLUEPRINT §11).

        Fail-closed: state-mutating methods WAJIB membawa Origin yang sah.
        Browser selalu set Origin pada same-origin POST; non-browser client
        (curl/script) yang omit Origin ditolak 403
        supaya tidak bisa bypass CSRF guard (report-bug-finder Finding 2).

        Di-relax (passthrough) saat bind non-loopback — user sengaja expose.
        """
        if loopback and request.method in ("POST", "PUT", "DELETE"):
            origin = request.headers.get("origin", "")
            if origin not in allowed:
                return JSONResponse({"error": "Forbidden"}, status_code=403)
        return await call_next(request)

    @app.middleware("http")
    async def validate_host(
        request: Request, call_next: Callable[[Request], Awaitable[Any]]
    ) -> Any:
        """DNS rebinding protection — Host header harus localhost/127.0.0.1.

        Di-relax (passthrough) saat bind non-loopback.
        """
        if loopback:
            h = request.headers.get("host", "").lower()
            if h not in host_ok:
                return JSONResponse({"error": "Invalid Host"}, status_code=400)
        return await call_next(request)

    @app.get("/api/graph")
    def get_graph() -> dict[str, object]:
        """Return graph hasil scanner apa adanya."""
        return graph_data

    @app.post("/api/ai/summary")
    def post_summary(req: SummaryRequest) -> dict[str, object]:
        """DEPRECATED — Phase 5. Gunakan ``/api/ai/chat``.

        Route + ``SummaryRequest`` + cache import tetap (handoff: keep tapi
        disable) supaya tidak break import/test lama. Logic provider/cache
        tidak jalan.
        """
        return {"deprecated": True, "reason": "use /api/ai/chat"}

    @app.post("/api/ai/chat")
    def post_chat(req: ChatRequest) -> dict[str, Any]:
        """Chat endpoint (Phase 5, stateless).

        Semua error AI dikembalikan sebagai HTTP 200 dengan ``error_type``
        supaya caller bisa menangani error tanpa dialog auth (BLUEPRINT §10).
        """
        if not req.message.strip():
            return {"enabled": False, "reason": "empty_message", "warnings": []}

        # FEAT-0019: ai_enrichment OFF → disabled (structural browsing continues).
        if scan_root is not None:
            _settings = storage.read_settings(scan_root)
            if not _settings.get("ai_enrichment", True):
                return {"enabled": False, "reason": "ai_enrichment_off", "warnings": []}

        context, warnings = build_ai_context(req.tagged, graph_data, scan_root)

        provider = provider_module.get_provider()
        if provider is None:
            return {"enabled": False, "reason": "no_api_key", "warnings": warnings}

        messages = req.history + [{"role": "user", "content": req.message}]
        try:
            reply = provider.chat(messages, context)
        except AIError as e:
            if e.error_type == "sdk_not_installed":
                return {"enabled": False, "reason": "sdk_not_installed", "warnings": warnings}
            payload: dict[str, Any] = {
                "enabled": True,
                "error_type": e.error_type,
                "warnings": warnings,
            }
            if e.error_type == "rate_limited" and e.retry_after is not None:
                payload["retry_after"] = e.retry_after
            return payload
        # ponytail: SENGAJA tidak catch ``Exception`` di sini — bug nyata harus
        # bubble jadi 500 supaya kelihatan, bukan dibungkus jadi error_type="unknown".

        return {"enabled": True, "reply": reply, "warnings": warnings}

    @app.get("/api/source")
    def get_source(file: str, fn: str | None = None) -> Any:
        """Source code untuk file (atau satu function) — Phase 5 §10 (F1).

        Query params:
          ``file``: relative path dari scan_root (e.g. ``"services/user.py"``).
          ``fn``  : nama function (optional). Kalau ada, return hanya function
                    body via :func:`_extract_function_body` (line_start/line_end
                    dari graph metadata — bukan ``ast``, plan.md: jangan duplikat).
                    Kalau tidak ada, return seluruh file.

        Security:
          Path traversal guard — ``file`` di-resolve lalu ``relative_to``
          scan_root. Escape (``../``) → 400. Tidak ada absolute path
          di-expose (M-03).
        """
        if scan_root is None:
            return JSONResponse({"error": "scan_root not set"}, status_code=500)

        # Path traversal guard: file harus tetap di dalam scan_root setelah resolve.
        try:
            target = (scan_root / file).resolve()
            target.relative_to(scan_root.resolve())
        except (ValueError, OSError):
            return JSONResponse({"error": "Invalid path"}, status_code=400)

        if not target.exists() or not target.is_file():
            return JSONResponse({"error": "File not found"}, status_code=404)

        # Security: credential files blocked at source endpoint too (FEAT-0020).
        # 404 to avoid revealing existence — same as not-found.
        if _is_credential_file(file):
            return JSONResponse({"error": "File not found"}, status_code=404)

        try:
            raw = target.read_text(errors="replace")
        except OSError:
            # Security: never serialize OSError details (may contain absolute path).
            return JSONResponse({"error": "Failed to read file"}, status_code=500)

        language = _language_for_suffix(target.suffix)

        if fn:
            # Lookup function line_start/line_end dari graph metadata, lalu
            # reuse _extract_function_body (plan.md: jangan duplikat).
            node = _file_view(graph_data, file)
            fn_meta = None
            if node is not None:
                fn_meta = next(
                    (f for f in (node.get("functions") or []) if f.get("name") == fn),
                    None,
                )
            if fn_meta is None:
                return JSONResponse(
                    {"error": f"Function '{fn}' not found"}, status_code=404
                )
            body = _extract_function_body(
                raw, fn_meta.get("line_start"), fn_meta.get("line_end")
            )
            return {"file": file, "fn": fn, "source": body, "language": language}

        return {"file": file, "fn": None, "source": raw, "language": language}

    # --- Structural endpoints (FEAT-0016/0017/0018/0020) -------------------

    @app.get("/api/scan/status")
    def get_scan_status() -> dict[str, Any]:
        """Return scan metadata (file/function/edge counts, diagnostics)."""
        return dict(graph_data.get("scan") or {})

    @app.post("/api/scan")
    def post_scan() -> Any:
        """Manual rescan — re-discover, re-parse, rebuild graph (FEAT-0015)."""
        if scan_root is None:
            return JSONResponse({"error": "scan_root not set"}, status_code=500)
        # Lazy import to avoid circular dependency (cli imports server.app).
        from graps.cli import _DEFAULT_EXCLUDES, _discover, _parse_file
        from graps.scanner.graph_builder import build_graph
        from graps.scanner.ids import to_posix_rel

        files = _discover(scan_root, set(_DEFAULT_EXCLUDES))
        results = [r for r in (_parse_file(p, scan_root) for p in files) if r is not None]
        for r in results:
            r.id = r.id or to_posix_rel(r.path, scan_root)
        new_graph = build_graph(results, root=scan_root)
        # Mutate in-memory graph_data (closure variable).
        graph_data.clear()
        graph_data.update(new_graph)
        # Persist to .graps/.
        file_rels = [f["id"] for f in new_graph["nodes"]["files"]]
        storage.write_graph(scan_root, new_graph)
        storage.write_file_index(scan_root, storage.compute_file_index(scan_root, file_rels))
        return new_graph.get("scan", {})

    @app.get("/api/settings")
    def get_settings() -> dict[str, Any]:
        """Read project-local settings (safe defaults if missing)."""
        if scan_root is None:
            return storage.default_settings()
        return storage.read_settings(scan_root)

    @app.put("/api/settings")
    def put_settings(req: SettingsUpdate) -> Any:
        """Update project-local settings (whitelist only, unknown keys dropped)."""
        if scan_root is None:
            return JSONResponse({"error": "scan_root not set"}, status_code=500)
        current = storage.read_settings(scan_root)
        updates: dict[str, Any] = {}
        for k in ("ai_enrichment", "overrides", "panel_widths", "tabs"):
            v = getattr(req, k)
            if v is not None:
                updates[k] = v
        merged = {**current, **updates}
        return storage.write_settings(scan_root, merged)

    @app.get("/api/modules/{module_id}")
    def get_module(module_id: str) -> Any:
        """Module overview — module node + member file/function IDs."""
        modules = (graph_data.get("nodes") or {}).get("modules") or []
        mod = next((m for m in modules if m.get("id") == module_id), None)
        if mod is None:
            return JSONResponse({"error": "Module not found"}, status_code=404)
        # Members: files whose module_id matches.
        files = (graph_data.get("nodes") or {}).get("files") or []
        fns = (graph_data.get("nodes") or {}).get("functions") or []
        member_files = [f["id"] for f in files if f.get("module_id") == module_id]
        member_functions = [f["id"] for f in fns if f.get("module_id") == module_id]
        return {**mod, "member_files": member_files, "member_functions": member_functions}

    @app.get("/api/flows/{flow_id}")
    def get_flow(flow_id: str) -> Any:
        """Flow view — steps for a resolved flow (call_sequence MVP)."""
        flows = graph_data.get("flows") or []
        flow = next((f for f in flows if f.get("id") == flow_id), None)
        if flow is None:
            return JSONResponse({"error": "Flow not found"}, status_code=404)
        return flow

    # --- Static frontend (FEAT-0001 shell) ---------------------------------
    # ponytail: mount public/ at root. API routes registered above take
    # precedence (checked first). StaticFiles(html=True) serves index.html
    # at GET / and other assets at their paths. No CDN, no build step.
    _public = Path(__file__).resolve().parent.parent / "public"
    if _public.is_dir():
        app.mount("/", StaticFiles(directory=str(_public), html=True), name="public")

    return app


if __name__ == "__main__":
    # Self-check: pakai TestClient supaya tidak perlu jalan uvicorn beneran.
    import os
    import tempfile

    from fastapi.testclient import TestClient

    PORT = 8765
    HOST_OK = f"127.0.0.1:{PORT}"
    ORIGIN_OK = f"http://127.0.0.1:{PORT}"
    GRAPH: dict[str, Any] = {
        "schema_version": "1.0.0", "scan": {}, "content_hash": "",
        "nodes": {"files": [], "functions": [], "classes": [], "modules": []},
        "edges": {"imports": [], "calls": [], "contains": [], "module_depends": []},
        "flows": [],
    }

    # Save env supaya self-check tidak bocor key dev ke logika "no_api_key".
    saved_env = {
        "ANTHROPIC_API_KEY": os.environ.pop("ANTHROPIC_API_KEY", None),
        "OPENAI_API_KEY": os.environ.pop("OPENAI_API_KEY", None),
    }
    saved_get_provider = provider_module.get_provider
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            scan_root = Path(tmpdir)
            (scan_root / "a.py").write_text("def foo():\n    return 42\n")
            graph = {
                "schema_version": "1.0.0",
                "scan": {"file_count": 1, "function_count": 1, "edge_count": 0, "diagnostics": []},
                "content_hash": "",
                "nodes": {
                    "files": [{"id": "a.py", "type": "file", "path": "a.py",
                               "language": "python", "module_id": "a",
                               "modified_at": "", "constants": [], "exported_names": []}],
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
            app = create_app(graph, port=PORT, scan_root=scan_root)
            client = TestClient(app, base_url=f"http://{HOST_OK}")

            # 1. GET /api/graph mengembalikan dict apa adanya.
            r = client.get("/api/graph", headers={"host": HOST_OK})
            assert r.status_code == 200, r.status_code
            assert r.json() == graph, r.json()

            # 1b–1e. GET /api/source (Phase 5 §10 / F1) — path traversal + fn lookup.
            # 1b. valid file (no fn) → full source + language.
            r = client.get("/api/source", params={"file": "a.py"}, headers={"host": HOST_OK})
            assert r.status_code == 200, r.status_code
            j = r.json()
            assert j["file"] == "a.py" and j["fn"] is None, j
            assert "def foo" in j["source"], j
            assert j["language"] == "python", j
            # 1c. valid file + valid fn → function body via _extract_function_body.
            r = client.get(
                "/api/source",
                params={"file": "a.py", "fn": "foo"},
                headers={"host": HOST_OK},
            )
            assert r.status_code == 200, r.status_code

            j = r.json()
            assert j["fn"] == "foo" and "return 42" in j["source"], j
            # 1d. path traversal (..) → 400.
            r = client.get("/api/source", params={"file": "../a.py"}, headers={"host": HOST_OK})
            assert r.status_code == 400, r.status_code
            assert r.json() == {"error": "Invalid path"}, r.json()
            # 1e. fn not found in graph metadata → 404.
            r = client.get(
                "/api/source",
                params={"file": "a.py", "fn": "nope"},
                headers={"host": HOST_OK},
            )
            assert r.status_code == 404, r.status_code
            # 1f. missing file on disk → 404.
            r = client.get("/api/source", params={"file": "missing.py"}, headers={"host": HOST_OK})
            assert r.status_code == 404, r.status_code

            # 2. /api/ai/summary deprecated response.
            body = {"file": "a.py", "function": "foo", "line": 1,
                    "modified_at": "2026-01-01", "source": "def foo(): pass"}
            r = client.post("/api/ai/summary", json=body,
                            headers={"host": HOST_OK, "origin": ORIGIN_OK})
            assert r.status_code == 200, r.status_code
            assert r.json() == {"deprecated": True, "reason": "use /api/ai/chat"}, r.json()

            # 3. Origin asing + Host valid → 403 (CSRF guard).
            r = client.post("/api/ai/chat", json={"message": "hi"},
                            headers={"host": HOST_OK, "origin": "http://evil.com"})
            assert r.status_code == 403, r.status_code
            assert r.json() == {"error": "Forbidden"}, r.json()

            # 3b. Tanpa Origin (curl-style) → 403 (fail-closed CSRF guard).
            r = client.post("/api/ai/chat", json={"message": "hi"},
                            headers={"host": HOST_OK})
            assert r.status_code == 403, r.status_code

            # 4. /api/ai/chat empty message → empty_message.
            r = client.post("/api/ai/chat", json={"message": "   "},
                            headers={"host": HOST_OK, "origin": ORIGIN_OK})
            assert r.status_code == 200, r.status_code
            assert r.json() == {
                "enabled": False,
                "reason": "empty_message",
                "warnings": [],
            }, r.json()

            # 5. /api/ai/chat tanpa API key → no_api_key.
            r = client.post("/api/ai/chat", json={"message": "why?", "tagged": ["a.py"]},
                            headers={"host": HOST_OK, "origin": ORIGIN_OK})
            assert r.status_code == 200, r.status_code
            j = r.json()
            assert j["enabled"] is False and j["reason"] == "no_api_key", j
            # context tetap dibuild (warnings [] karena a.py ada di graph & readable).
            assert j["warnings"] == [], j

            # 6. Mocked provider returns reply.
            class _FakeOK:
                name = "fake"
                last_ctx = ""
                def chat(self, messages: list[dict[str, str]], context: str) -> str:
                    _FakeOK.last_ctx = context
                    return "debug answer"

            provider_module.get_provider = lambda: _FakeOK()  # type: ignore[assignment,return-value]
            r = client.post("/api/ai/chat",
                            json={"message": "why return 42?", "tagged": ["a.py::foo"]},
                            headers={"host": HOST_OK, "origin": ORIGIN_OK})
            assert r.status_code == 200, r.status_code
            j = r.json()
            assert j["enabled"] is True and j["reply"] == "debug answer", j
            # context mengandung function body dari disk.
            assert "def foo" in _FakeOK.last_ctx, _FakeOK.last_ctx
            assert "return 42" in _FakeOK.last_ctx, _FakeOK.last_ctx

            # 7. Mocked auth_failed → error_type.
            class _FakeAuthFail:
                name = "fake"
                def chat(self, messages: list[dict[str, str]], context: str) -> str:
                    raise AIError("auth_failed")

            provider_module.get_provider = lambda: _FakeAuthFail()  # type: ignore[assignment,return-value]
            r = client.post("/api/ai/chat", json={"message": "hi"},
                            headers={"host": HOST_OK, "origin": ORIGIN_OK})
            assert r.status_code == 200, r.status_code
            assert r.json()["error_type"] == "auth_failed", r.json()
            assert "key" not in r.text.lower() and "apikey" not in r.text.lower()

            # 8. Credential file (.env) excluded — warning, source tidak dikirim.
            provider_module.get_provider = lambda: _FakeOK()  # type: ignore[assignment,return-value]
            (scan_root / ".env").write_text("SECRET=hunter2")
            r = client.post("/api/ai/chat", json={"message": "x", "tagged": [".env"]},
                            headers={"host": HOST_OK, "origin": ORIGIN_OK})
            j = r.json()
            assert any(w["reason"] == "credential_file_excluded" for w in j["warnings"]), j
            assert "hunter2" not in _FakeOK.last_ctx, _FakeOK.last_ctx

            # 8b. /api/source blocks credential files (TASK-0004 hardening).
            r = client.get("/api/source", params={"file": ".env"},
                           headers={"host": HOST_OK})
            assert r.status_code == 404, r.status_code
            assert "hunter2" not in r.text, r.text

            # 9. scan_root=None → context kosong (backward-compat).
            provider_module.get_provider = saved_get_provider  # clear mock
            app2 = create_app(GRAPH, port=PORT + 1, scan_root=None)
            client2 = TestClient(app2, base_url=f"http://127.0.0.1:{PORT+1}")
            r = client2.post("/api/ai/chat", json={"message": "hi", "tagged": ["a.py"]},
                             headers={"host": f"127.0.0.1:{PORT+1}", "origin": f"http://127.0.0.1:{PORT+1}"})
            j = r.json()
            assert j["enabled"] is False and j["reason"] == "no_api_key", j
            assert j["warnings"] == [], j  # no scan_root → no warnings

        print("app.py self-check OK")
    finally:
        provider_module.get_provider = saved_get_provider
        for k, v in saved_env.items():
            if v is not None:
                os.environ[k] = v
