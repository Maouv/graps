"""CLI entry point graps (lihat BLUEPRINT.md §6).

Flow utama: scan .py rekursif → build_graph → create_app → uvicorn + auto-open
browser. Sengaja flat — satu fungsi `main`, satu helper `_build` agar
self-check bisa memanggil tanpa menjalankan server.

ponytail: tidak pakai Rich/Click/colorama. typer.echo + print biasa cukup.
"""

from __future__ import annotations

import errno
import logging
import os
import socket
import tempfile
import threading
import webbrowser
from pathlib import Path
from typing import Any

import typer
import uvicorn

# ponytail: dipanggil sebagai `python graps/cli.py` (self-check) butuh repo
# root di sys.path. No-op untuk `python -m graps.cli`.
if __name__ == "__main__":
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from graps import (
    __version__,  # noqa: E402
    storage,  # noqa: E402
)
from graps.scanner import ParsedFile  # noqa: E402
from graps.scanner.ast_parser import safe_parse
from graps.scanner.graph_builder import build_graph
from graps.scanner.ids import to_posix_rel
from graps.scanner.tree_sitter_parser import TreeSitterParser  # Phase 4
from graps.server.app import create_app  # noqa: E402

app = typer.Typer(add_completion=False)

logger = logging.getLogger(__name__)

# FEAT-0016: exclude .graps, VCS, dependencies, build dirs, and credential/binary
# files from scanning. Dirs are matched by name on any path segment; credential
# and binary files are filtered by name/extension in _discover.
_DEFAULT_EXCLUDES = (
    "__pycache__", ".graps",
    ".git", ".hg", ".svn", ".idea", ".vscode",
    ".venv", "venv", "env", "site-packages", ".tox", ".eggs",
    "node_modules", "bower_components", "jspm_packages",
    "dist", "build", "target", "out", "egg-info",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", ".impeccable",
)
_CREDENTIAL_FILE_NAMES = {
    ".env", ".env.local", ".env.production", ".env.development", ".env.staging",
    "credentials.json", "secrets.json", "secret.json",
    "id_rsa", "id_ecdsa", "id_ed25519",
}
_CREDENTIAL_FILE_EXTS = {".pem", ".key", ".p12", ".pfx"}
_BINARY_FILE_EXTS = {".so", ".pyc", ".pyo", ".dylib", ".dll", ".exe", ".bin", ".o", ".a", ".wasm"}


def _is_excluded_file(rel_path: Path) -> bool:
    """Hard-exclude credential and binary files (FEAT-0016 / security)."""
    name = rel_path.name.lower()
    if name in _CREDENTIAL_FILE_NAMES:
        return True
    ext = rel_path.suffix.lower()
    return ext in _CREDENTIAL_FILE_EXTS or ext in _BINARY_FILE_EXTS


def _discover(path: Path, exclude: set[str]) -> list[Path]:
    """Cari file rekursif yang didukung tree-sitter-language-pack (306 bahasa).

    Fallback ke ``*.py`` kalau library tidak terinstall.
    """
    try:
        from tree_sitter_language_pack import detect_language_from_path
        use_tslp = True
    except ImportError:
        use_tslp = False

    files: list[Path] = []
    for p in path.rglob("*"):
        if not p.is_file():
            continue
        if set(p.parts) & exclude:
            continue
        if _is_excluded_file(p):
            continue
        if use_tslp:
            if detect_language_from_path(str(p)) is not None:
                files.append(p)
        elif p.suffix == ".py":
            files.append(p)
    return files


def _parse_file(path: Path, root: Path) -> ParsedFile | None:
    """Dispatch parser per file.

    TreeSitterParser dulu. Kalau gagal dan file .py → fallback ke ASTParser.
    Non-Python tanpa fallback → None (unsupported).
    """
    ts_parser = TreeSitterParser()
    result = ts_parser.parse_file(path, root)

    if result is not None:
        return result

    if path.suffix == ".py":
        logger.debug("tree-sitter failed for %s, falling back to ASTParser", path)
        return safe_parse(path)

    return None


def _build(path: Path, exclude: set[str]) -> dict[str, Any]:
    """Discover + parse + build_graph. Dipisah supaya self-check bisa panggil tanpa server."""
    files = _discover(path, exclude)
    results = [r for r in (_parse_file(p, path) for p in files) if r is not None]
    for r in results:
        r.id = r.id or to_posix_rel(r.path, path)
    return build_graph(results, root=path)


def _count_diagnostics(graph: dict[str, Any]) -> dict[str, int]:
    """Count scan diagnostics by level (FEAT-0017: risks/warnings live in scan.diagnostics)."""
    counts = {"error": 0, "warning": 0}
    for d in graph.get("scan", {}).get("diagnostics", []) or []:
        level = str(d.get("level", "warning")).lower()
        if level in counts:
            counts[level] += 1
    return counts


def _port_free(port: int, host: str = "127.0.0.1") -> bool:
    """True kalau bisa bind ``host:port`` (pre-flight check)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"graps v{__version__}")
        raise typer.Exit(0)


def _warn_if_cache_not_ignored(root: Path) -> None:
    """Warning non-blocking kalau ``.graps/`` tidak di-ignore di ``root/.gitignore``.

    Hanya typer.echo, tidak pernah sys.exit — cache berisi ringkasan AI dari
    source code, kalau tidak di-ignore bisa ter-commit ke Git (BLUEPRINT H-03).
    """
    gitignore = root / ".gitignore"
    if gitignore.exists():
        try:
            content = gitignore.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return  # unreadable → skip warning silently
        if ".graps" not in content and ".graps/" not in content:
            typer.echo(
                "  WARNING ⚠ graps/ is not yet in .gitignore "
                "The cache can contain an AI summary of your source code. "
                "Add '.graps/' to .gitignore?"
            )


@app.command()
def main(
    path: str = typer.Argument(".", help="Directory to be scanned"),
    port: int = typer.Option(8765, "--port", help="Port HTTP server"),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Network address to bind (default 127.0.0.1; 0.0.0.0 to expose on LAN/VPS)",
    ),
    no_browser: bool = typer.Option(False, "--no-browser", help="Not auto open brower"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Cache deleted (deletee by OS)"),
    exclude: list[str] = typer.Option(  # noqa: B008
        None, "--exclude", help="Skipped directory pattern (may repeat)",
    ),
    ai_provider: str = typer.Option(
        None, "--ai-provider", help="use one provider ai (openai or anthropic)",
    ),
    version: bool = typer.Option(  # noqa: ARG001
        False, "--version", callback=_version_callback, is_eager=True,
        help="show version",
    ),
) -> None:
    """Scan PATH untuk file Python, jalankan server lokal + buka browser."""
    root = Path(path).resolve()

    typer.echo(f"graps v{__version__}")
    typer.echo("")
    typer.echo(f"  Scanning {root}...")

    # Validasi PATH.
    if not root.exists() or not root.is_dir():
        typer.echo(f"  Cannot read directory {path} — not found or not a directory")
        raise typer.Exit(1)
    if not os.access(root, os.R_OK):
        typer.echo(f"  Cannot read directory {path} — permission denied")
        raise typer.Exit(1)

    # Startup warning: cache .graps/ harus di-gitignore (BLUEPRINT H-03).
    _warn_if_cache_not_ignored(root)

    excl: set[str] = set(_DEFAULT_EXCLUDES)
    if exclude:
        # Buang trailing slash supaya "tests/" cocok dengan parts "tests".
        excl.update(e.rstrip("/").rstrip("\\") for e in exclude)

    files = _discover(root, excl)
    if not files:
        typer.echo(f"  No supported files found in {path}")
        raise typer.Exit(1)

    # Scan + build.
    results = [r for r in (_parse_file(p, root) for p in files) if r is not None]
    graph = build_graph(results, root=root)

    scan = graph.get("scan", {})
    files_n = scan.get("file_count", len(results))
    funcs_n = scan.get("function_count", sum(len(r.functions) for r in results))
    edges_n = scan.get("edge_count", 0)
    diag = _count_diagnostics(graph)

    typer.echo(f"  ├── Found {files_n} files")
    typer.echo(f"  ├── Found {funcs_n} functions")
    typer.echo(f"  ├── Found {edges_n} import relationships")
    typer.echo(
        f"  └── Diagnostics: {diag['error']} errors, "
        f"{diag['warning']} warnings"
    )
    # edge-resolution-bug: silent-failure guard. Kalau repo Python >= 5 file
    # punya import tapi 0 edge, kemungkinan adapter/resolver format drift lagi
    # (sebelumnya tree-sitter adapter isi target raw statement → semua edge drop).
    # Warning non-blocking — tidak exit, hanya kasih signal ke user.
    if edges_n == 0 and files_n > 5:
        py_with_imports = sum(1 for r in results if r.language == "python" and r.imports)
        if py_with_imports >= 2:
            typer.echo(
                "  ! Warning: 0 edges detected with Python imports present — "
                "possible resolver/adapter issue (target format drift)"
            )
    typer.echo("")

    # FEAT-0020: persist graph + file index to .graps/ (atomic, schema-versioned).
    file_rels = [f["id"] for f in graph["nodes"]["files"]]
    storage.write_graph(root, graph)
    storage.write_file_index(root, storage.compute_file_index(root, file_rels))

    # AI provider env masking. get_provider order Anthropic-first → ini cara
    # paling lazy untuk memaksa openai.
    if ai_provider == "openai":
        os.environ.pop("ANTHROPIC_API_KEY", None)
        if not os.environ.get("OPENAI_API_KEY"):
            typer.echo("  ! OPENAI_API_KEY tidak di-set — AI summary akan disabled")
    elif ai_provider == "anthropic":
        os.environ.pop("OPENAI_API_KEY", None)
        if not os.environ.get("ANTHROPIC_API_KEY"):
            typer.echo("  ! ANTHROPIC_API_KEY tidak di-set — AI summary akan disabled")

    # Cache path. --no-cache → tempfile OS-unik per-run (mkstemp).
    # ponytail: mkstemp lebih simple dari TemporaryDirectory context manager
    # karena server.run() block — kita gak punya tempat clean up ergonomis.
    # OS akan bersihkan /tmp eventually.
    cache_path: Path | None
    if no_cache:
        fd, name = tempfile.mkstemp(suffix=".json", prefix="graps-nocache-")
        os.close(fd)
        cache_path = Path(name)
    else:
        cache_path = None  # create_app pakai DEFAULT_CACHE_PATH

    # Pre-flight port check.
    if not _port_free(port, host):
        typer.echo(f"  Port {port} already in use. Try: graps . --port {port + 1}")
        raise typer.Exit(1)

    fastapi_app = create_app(graph, port=port, host=host, cache_path=cache_path, scan_root=root)

    # Banner nunjukin bind asli (0.0.0.0 = denger semua interface, bukan
    # cuma loopback). webbrowser.open gak bisa buka 0.0.0.0 langsung → itu
    # pakai loopback (0.0.0.0 tetep nge-bind 127.0.0.1).
    typer.echo(f"  Server running at http://{host}:{port}")
    if not no_browser:
        open_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
        typer.echo("  Opening browser...")
        timer = threading.Timer(1.0, lambda: webbrowser.open(f"http://{open_host}:{port}"))
        timer.daemon = True  # ponytail: jangan block exit kalau server.run() gagal (Finding 6)
        timer.start()
    typer.echo("  Press Ctrl+C to stop")
    typer.echo("")

    config = uvicorn.Config(
        fastapi_app, host=host, port=port, log_level="warning"
    )
    server = uvicorn.Server(config)
    try:
        server.run()
    except KeyboardInterrupt:
        typer.echo("")
        typer.echo("  Stopped.")
        raise typer.Exit(0)
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            typer.echo(f" Port {port} already in use. Try: graps . --port {port + 1}")
            raise typer.Exit(1)
        raise


if __name__ == "__main__":
    # Self-check minimal — tidak menjalankan server beneran.
    from typer.testing import CliRunner

    # 1. Import + Typer instance.
    assert isinstance(app, typer.Typer)

    # 2. --version exit 0 + output mengandung "graps v".
    runner = CliRunner()
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0, (r.exit_code, r.output)
    assert "graps v" in r.output, r.output

    # 3. Fixture dir kecil → _build hasilkan graph valid.
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "x.py").write_text("def foo(): pass\n")
        (tdp / "__pycache__").mkdir()
        (tdp / "__pycache__" / "ignored.py").write_text("syntax ( error\n")

        files = _discover(tdp, set(_DEFAULT_EXCLUDES))
        assert len(files) == 1, files  # __pycache__ ter-skip

        graph = _build(tdp, set(_DEFAULT_EXCLUDES))
        assert "nodes" in graph and isinstance(graph["nodes"], dict), graph
        assert graph["scan"]["file_count"] == 1, graph["scan"]
        assert graph["scan"]["function_count"] == 1, graph["scan"]
        assert ".graps" not in {f["id"] for f in graph["nodes"]["files"]}

    # 4. Empty dir → exit code != 0.
    with tempfile.TemporaryDirectory() as td:
        r = runner.invoke(app, [td, "--no-browser"])
        assert r.exit_code != 0, (r.exit_code, r.output)
        assert "No supported files" in r.output, r.output

    # 5. PATH tidak ada → exit code != 0.
    r = runner.invoke(app, ["/path/yang/pasti/tidak/ada/xyz123", "--no-browser"])
    assert r.exit_code != 0, (r.exit_code, r.output)

    # 6. _count_diagnostics tahan input kosong / None.
    assert _count_diagnostics({}) == {"error": 0, "warning": 0}
    assert _count_diagnostics({"scan": {}}) == {"error": 0, "warning": 0}
    assert _count_diagnostics({"scan": {"diagnostics": None}}) == {"error": 0, "warning": 0}
    assert _count_diagnostics(
        {"scan": {"diagnostics": [
            {"level": "error"}, {"level": "warning"}, {"level": "WARNING"},
        ]}}
    ) == {"error": 1, "warning": 2}

    # 7. _port_free konsisten dengan socket-bind manual.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    busy_port = s.getsockname()[1]
    assert _port_free(busy_port) is False
    s.close()

    # 8. Storage: write_graph + read_graph reusable, .graps not a node.
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "a.py").write_text("def foo(): pass\n")
        graph = _build(tdp, set(_DEFAULT_EXCLUDES))
        storage.write_graph(tdp, graph)
        reloaded = storage.read_graph(tdp)
        assert reloaded is not None
        assert reloaded["content_hash"] == graph["content_hash"]
        assert ".graps" not in {f["id"] for f in reloaded["nodes"]["files"]}

    print("cli.py self-check OK")
