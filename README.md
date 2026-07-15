# graps

Interactive visual dependency graph for Python codebases. Scans a directory, builds a structural dependency + risk graph, and serves an interactive visualization on `http://localhost:8765`.

## Install

```bash
pip install graps
# with optional AI chat:
pip install "graps[anthropic]"
pip install "graps[openai]"
pip install "graps[ai]"
```

## Usage

```bash
graps ./src
graps ./src --port 8080 --no-browser
graps ./src --host 0.0.0.0 --ai-provider anthropic
graps ./src --exclude node_modules --exclude .venv
```

Open `http://localhost:8765` in your browser.

### CLI options

| Flag | Default | Description |
|---|---|---|
| `[PATH]` | `.` | Directory to scan |
| `--port` | `8765` | HTTP server port |
| `--host` | `127.0.0.1` | Bind address (`0.0.0.0` exposes on LAN/VPS) |
| `--no-browser` | off | Don't auto-open browser |
| `--no-cache` | off | Delete cache on exit |
| `--exclude` | — | Skipped directory pattern (repeatable) |
| `--ai-provider` | — | `openai` or `anthropic` for AI chat |
| `--version` | — | Show version |

## API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/graph` | GET | Structural dependency graph |
| `/api/source?file=&fn=` | GET | Source code for a file or function |
| `/api/modules/{id}` | GET | Module overview with member files/functions |
| `/api/flows/{id}` | GET | Flow view with call sequence steps |
| `/api/scan` | POST | Manual rescan |
| `/api/scan/status` | GET | Scan metadata (file/function/edge counts) |
| `/api/settings` | GET/PUT | Project-local settings (whitelisted keys only) |
| `/api/ai/chat` | POST | Stateless AI chat with bounded source context |
| `/api/ai/summary` | POST | Deprecated — use `/api/ai/chat` |

## Security

- **Path traversal** — file lookups resolve under scan root; escape attempts (`../`, absolute paths) return 400.
- **Credential files** — `.env`, `.pem`, `.key`, `.p12`, `.pfx`, `credentials.json`, `secrets.json` are blocked at `/api/source` (404) and excluded from AI context.
- **CSRF guard** — `POST`/`PUT`/`DELETE` require valid `Origin` header (fail-closed: no Origin → 403).
- **DNS rebinding** — `Host` header must match `localhost`/`127.0.0.1` on loopback bind.
- **No absolute paths** — error responses never serialize filesystem paths.
- **AI isolation** — AI output is passthrough text, cannot alter graph truth. AI failure (no key, auth error, rate limit, SDK missing) returns structured error, structural browsing continues.
- **Non-loopback relaxation** — binding to `0.0.0.0` (VPS/LAN) relaxes Origin/Host middleware; user assumes responsibility.

## Performance

Benchmark on graps's own codebase (129 files, 463 functions, 2483 edges):

| Operation | Time |
|---|---|
| Scan (cold) | 1.44s |
| Cache load (warm) | 0.073s |
| Speedup | ~20x |

## License

MIT — see [LICENSE](LICENSE).

> **Note:** This branch is for experimental features.
