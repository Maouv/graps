# Handoff — Phase 1 (Foundation) Experimental Graps

Branch: `experimental`. Kontrak: `plan/experimental-graps/06-tasks/task-0001-foundation.md` (FEAT-0016/0017/0018/0020). Otorisasi implementasi sudah diberikan user (mulai Phase 1 tanpa dep baru; tanya approval exact-pin Instructor/Pydantic sebelum Phase 2).

## Selesai (self-check lulus, `python <file>` ok)

- `graps/scanner/__init__.py` — data carrier `ParsedCall` + field `calls`/`line_end` di `ParsedFunction`.
- `graps/scanner/ast_parser.py` — capture `line_end` (end_lineno), call sites per-fungsi (call-stack), ekstrak `classes`; self-check diperluas.
- `graps/scanner/ids.py` (NEW) — ID POSIX stabil (file/function/class/module/flow) + `content_hash` deterministik (timestamp di-exclude).
- `graps/scanner/modules.py` (NEW) — resolusi modul Python (package→folder), confidence `regular_package`/`namespace_fallback`/`top_level`, member + dependency IDs.
- `graps/scanner/flows.py` (NEW) — call edges `call_sequence` MVP (self/cls method, same-file bare, cross-file from-import; unresolved bawa `reason`+`candidates`).
- `graps/scanner/graph_builder.py` — REWRITE ke graph schema_versioned: typed nodes (files/functions/classes/modules), typed edges (imports/calls/contains/module_depends), flows, `scan.diagnostics`, `content_hash`, urutan deterministik, no abs-path leak, malformed→diagnostic, C-01 redaksi. `build_graph`+`_sanitized_constants` dipertahankan (di-import tests).
- `graps/storage.py` (NEW) — `.graps/` atomic write (graph/architecture/settings + cache/file_index), schema check, hash-join architecture, settings whitelist+safe default (ai_enrichment default ON), file-index + `affected_modules`.
- `tests/bug_test/test_scanner_bug.py` → rename `scanner_bug_ledger.py` (ledger bug lama, di-decollect dari pytest; usang vs rebuild).

## Setengah jadi / rusak

- `graps/cli.py` — excludes diperluas (`.graps`/VCS/deps/builds/binaries/credentials), `_discover` filter cred/binary, `_build` set `r.id`, `_count_risks`→`_count_diagnostics`. **TAPI blok `main()` scan+build BELUM diupdate** (edit gagal: text mismatch) → masih refer `graph["meta"]` + `_count_risks` (sudah dihapus) → **`main()` rusak (NameError)**. Self-check bawah `cli.py` juga masih shape lama. `import graps.cli` OK; `python graps/cli.py` self-check & `graps <path>` akan gagal.

## Belum mulai

- `graps/server/app.py` — perlu: adapter `_file_view()` (typed collections → view file lama untuk `build_ai_context`+`get_source`), adapt `get_source`+`build_ai_context` ke shape baru, tambah endpoint structural (`GET /api/source` adapt, `GET /api/scan/status`, `POST /api/scan`, `GET/PUT /api/settings`, `GET /api/modules/{id}`, `GET /api/flows/{id}`); pertahankan `/api/ai/chat` + security (origin/host/CORS, credential exclusion). `GET /api/graph` otomatis serve shape baru.
- Migrasi tests shape-dependent (semua akan gagal): `tests/test_graph_builder.py`, `tests/test_api.py`, `tests/test_cli_dispatch.py` → rewrite ke kontrak baru + tambah tes Phase 1 (test_storage ada self-check, perlu test_modules/structural/.graps-exclusion/determinism/malformed/atomic/no-abs-path/no-secret).
- Update metadata plan: `task-0001` + `FEAT-0016/0017/0018/0020` status `backlog`/`planning` → `in_progress` saat benar-benar dikerjakan (belum diubah).
- Verifikasi Phase 1: full `pytest`, `ruff`, `mypy`, build, smoke end-to-end — belum jalan (suite pecah + cli main rusak).
- Phase 2/3/4 belum mulai.

## Status gate Phase 1

"A Python fixture produces reusable graph.json without AI; .graps never appears as a node" — **terbukti di self-check `storage.py` + `graph_builder.py`** (read reusable, hash stabil, `.graps` bukan node, malformed→diagnostic). **TAPI belum ter-wire end-to-end lewat CLI** (cli main rusak) dan belum lewat pytest penuh.

## Lanjutan berikutnya (urutan)

1. Selesaikan blok `main()` + self-check `cli.py` ke shape baru + tulis `.graps` (sudah ada storage helper).
2. Update `server/app.py` (`_file_view` adapter + endpoint structural + adapt AI/source).
3. Migrasi + tambah tests; jalankan `pytest`/`ruff`/`mypy`/build/smoke.
4. Update metadata plan task-0001 + 4 FEAT → `in_progress`; isi evidence saat lulus.
