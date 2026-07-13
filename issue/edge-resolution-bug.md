# PLAN: Edge Resolution Bug — tree-sitter adapter mengisi `ParsedImport.target` dengan raw statement

**Repo:** `Maouv/graps`, branch dasar: `feature/edge-direction-arrow` (atau `development` setelah arrow di-merge — bug ini pre-existing, independen dari arrow)
**File utama:** `graps/scanner/tree_sitter_parser.py`

---

## Phase 0 — Context Intake

- **Branch baru:** `fix/edge-resolution-tree-sitter` (dari `feature/edge-direction-arrow` atau `development` — bug pre-existing sejak Phase 4 tree-sitter adapter ditulis, tidak tergantung arrow)
- **File yang kena dampak:**
  - `graps/scanner/tree_sitter_parser.py` — fungsi `_extract_imports` diedit (normalisasi `imp.source` → dotted module path)
  - `tests/test_tree_sitter_parser.py` — assertion Python import diperkuat + test edge-via-ts-path ditambah
  - `tests/test_graph_builder.py` — test edge ditambah yang lewat `TreeSitterParser` (bukan synthetic `ParsedFile`)
  - `tests/test_resolver.py` — test tambahan: resolver dengan input raw-statement harus return None (regression guard kontrak)
- **Fungsi yang akan diedit:** `_extract_imports(imports)` di `tree_sitter_parser.py:144-162`
- **Fungsi baru yang akan dibuat:** `_normalize_import_source(source: str, is_wildcard: bool) -> list[str]` — helper pure-function di `tree_sitter_parser.py`, parse raw statement → list dotted target (1 statement bisa produce multiple target, e.g. `from X import Y, Z` → `["X.Y", "X.Z"]`, matching ast behavior 1 ParsedImport per alias)
- **Fungsi yang dihapus:** Tidak ada
- **Tanggal mulai:** 2026-07-13

---

## Phase 1 — Definition

**Problem statement:** CLI path (`graps <path>`) memakai `TreeSitterParser` first, `ASTParser` fallback. Tree-sitter adapter `_extract_imports` mengisi `ParsedImport.target` dengan `imp.source` = **raw statement text** (`"from graps.scanner import ParsedFile, ParsedImport"`), bukan dotted module path (`"graps.scanner.ParsedFile"`) yang diharapkan resolver. Akibatnya `resolve_import` memanggil `_try_module(root, "from graps.scanner import ParsedFile, ParsedImport".split("."), root)` → cari file `root/from graps/...py` → None → semua edge drop. CLI log: "Found 0 import relationships". User lihat 0 edge di canvas (termasuk arrow task sebelumnya tidak ada edge buat digambar).

**Done criteria (draft — koreksi/tambah kalau ada yang kurang):**
- CLI `graps <repo-sendiri> --no-browser` melaporkan `Found N import relationships` dengan N > 0 (match inline ast-path yang menghasilkan 39 edge untuk repo ini)
- `ParsedImport.target` dari `TreeSitterParser` untuk Python memiliki format identik dengan `ASTParser` untuk 5 bentuk import: `import X`, `from X import Y`, `from X import Y, Z` (multi-alias), `from .X import Y` (relative), `from X import *` (star)
- Resolver `resolve_import` menerima output `TreeSitterParser` tanpa modifikasi (resolver untouched — single format input)
- Test `tests/test_tree_sitter_parser.py::TestPython` assert format target eksplisit (bukan substring match lemah)
- Test regression: edge dibuat lewat pipeline `TreeSitterParser → build_graph` (bukan synthetic `ParsedFile`)

**Out of scope (konfirmasi — ini TIDAK dikerjakan di task ini):**
- Tidak mengubah `resolver.py` — resolver correct untuk dotted input (39 edge via ast bukti). Fix di adapter, bukan resolver.
- Tidak memperbaiki gap `is_conditional` (tree-sitter `_extract_imports` tidak set `is_conditional=True` untuk try/except import) — itu bug terpisah, affects risk_analyzer bukan edges. Dicatat di Phase 2.
- Tidak menambah normalisasi untuk bahasa selain Python (Go/TS/JS/Rust) — resolver Python-only (`_try_module` bangun `.py`/`__init__.py`), edge non-Python memang tidak pernah dibuat. Normalisasi multi-language = task terpisah kalau resolver multi-language dibuat.
- Tidak mengubah dispatch `cli.py:_parse_file` (tree-sitter first, ast fallback) — dispatch policy benar, yang salah adalah adapter output.
- Tidak menyentuh `graph.js` frontend — bug ini backend-only, arrow task frontend tetap valid.

**Consumer — kenapa ini bagus untuk user experience? Minimal 3 alasan:**
1. **Graph jadi ter-render sebagaimana mestinya.** Saat ini user buka repo, lihat node-node terpisah tanpa garis — graph terlihat "kosong/broken", user salah simpul "scanner tidak nemu dependency" padahal data ada. Fix ini restor fungsi core graps (dependency visualization). Tanpa ini, seluruh value proposition graps (lihat siapa import siapa) gagal total di CLI path yang adalah path utama user.
2. **Arrow direction marker (task sebelumnya) jadi bermakna.** Arrow yang sudah di-fix arahnya di `graph.js` tidak ada edge buat digambar selama bug ini ada. Fix ini adalah prerequisite agar arrow task deliver value-nya — user lihat panah arah import, bukan canvas kosong.
3. **Konsistensi antara path CLI (tree-sitter) dan path test/inline (ast).** Saat ini developer yang test via ast-path lihat 39 edge, user yang pakai CLI lihat 0 edge — discrepancy ini bikin bug report sulit di-trust ("di tempatku jalan"). Fix ini samakan behavior dua path, menghilangkan sumber confusion saat debugging masa depan.

---

## Phase 2 — System Impact Analysis

**File yang kena detail:**

| File | Perubahan | Detail |
|---|---|---|
| `graps/scanner/tree_sitter_parser.py` | Edit `_extract_imports` + tambah helper `_normalize_import_source` | Saat ini `target=imp.source` (raw). Diganti: parse `imp.source` → list dotted target via helper, emit 1 `ParsedImport` per target. Helper pure-function, no side-effect. |
| `tests/test_tree_sitter_parser.py` | Edit `TestPython.test_parse` + tambah test cases | Assertion `"os" in i.target` (substring lemah) → assert eksplisit `i.target == "os"`. Tambah test: `from X import Y,Z` → 2 entries `X.Y`, `X.Z`; relative `from .X import Y` → `.X.Y`; star → `is_star=True`, target=`X`. |
| `tests/test_graph_builder.py` | Tambah 1 test | `test_build_graph__edge_via_tree_sitter`: parse fixture via `TreeSitterParser`, `build_graph`, assert `len(edges) > 0`. Saat ini semua edge test pakai `_make_project()` synthetic `ParsedFile` — tidak verify ts-path end-to-end. |
| `tests/test_resolver.py` | Tambah 1 test | `test_resolve_import__raw_statement_returns_none`: kasih `ParsedImport(target="from x import y")` → assert `resolve_import(...) is None`. Regression guard: kontrak target = dotted, raw statement jelas invalid. |

**Konflik dengan kode existing:** Tidak ada. `_extract_imports` adalah private module-level function, hanya dipanggil 1x di `tree_sitter_parser.py:81`. Tidak ada caller lain. Signature `_extract_imports(imports: list[Any]) -> list[ParsedImport]` tidak berubah — hanya internal logic yang ganti.

**Bug tambahan yang ditemukan (di luar scope, dicatat saja):**
1. **`is_conditional` gap di tree-sitter adapter.** `_extract_imports` tidak set `is_conditional=True` untuk import di try/except block (ast set via `self._in_try`). Impact: `risk_analyzer` conditional-handling tidak trigger untuk ts-path. Tidak affect edges (resolver tidak baca `is_conditional`), jadi tidak block task ini. Task terpisah.
2. **Test gap struktural (5 titik)** — lihat Phase 6. Bukan bug kode, tapi gap test coverage yang membuat bug ini silent selama Phase 4 eksis. Sebagian diperbaiki di task ini (yang relate ke edge), sisanya noted.

**Race condition / edge case / bad path yang tercipta:**
- **Raw statement variant yang normalisasi miss** — Python import statement punya bentuk exotic: multi-line paren `from X import (\n  Y,\n  Z\n)`, backslash continuation `from X import Y, \\\n Z`, trailing comma, comment inline. Tree-sitter `imp.source` mungkin strip atau preserve whitespace/baris baru — belum diverifikasi untuk kasus ini. Mitigasi: Phase 4 dokumentasi + test fixture exotic, helper harus robust (fallback: kalau parse gagal, emit target=raw dengan warning, jangan drop).
- **Relative import dengan tree-sitter** — belum diverifikasi apakah `imp.source` untuk `from . import x` berupa `".x"` sudah ternormalisasi atau raw `from . import x`. Kalau raw, helper harus deteksi leading dots. Test fixture wajib.
- **Star import `from X import *`** — ast set `target="X"` (base tanpa alias), `is_star=True`. Tree-sitter `is_wildcard=True` tapi `source` raw. Helper harus extract base module `X` dan set target=`X` (bukan `X.*`).
- **`import X as Y`** — ast set `target="X"` (abaikan alias). Helper harus strip `as Y`.
- **Statement yang bukan import** — kalau tree-sitter false-positive deteksi comment/string sebagai import, `imp.source` bisa arbitrary text. Helper harus guard: kalau tidak match pattern import, return `[]` (emit 0 ParsedImport) daripada crash.

## Phase 3 — Design & Architecture

**Keputusan desain (eksplisit):**
1. **Lokasi fix: adapter `_extract_imports`, bukan resolver.** Resolver correct untuk dotted input (bukti: 39 edge via ast). Membebani resolver dengan parsing raw statement = melanggar separation of concerns (resolver = module-path → file-path mapping, bukan syntax parser). Adapter = tempat translate format library-specific → kontrak `ParsedImport`. Single source of truth untuk kontrak.
2. **1 ParsedImport per alias** — `from X import Y, Z` → 2 entries `X.Y`, `X.Z`. Match ast behavior (`visit_ImportFrom` loop `node.names`, 1 append per alias). Kalau emit 1 entry multi-target, `_build_edges` weight count jadi beda dengan ast path.
3. **Helper pure-function `_normalize_import_source(source, is_wildcard) -> list[str]`** — testable standalone, no `ParsedImport` construction di helper (helper return strings, caller wrap). Memungkinkan unit test tanpa fixture file.
4. **Python-only normalisasi** — helper dipanggil hanya untuk `lang == "python"` (guard di `_extract_imports` cek `pf.language` atau deteksi dari `imp.source` pattern). Bahasa lain tetap `target=imp.source` (edge non-Python memang tidak dibuat resolver). Hindari regex Python di-aplikasikan ke Go `import "fmt"`.

**Data structures (state baru):** TIDAK ADA. Tidak ada field baru di `ParsedImport` (dataclass untouched), tidak ada field baru di `ParsedFile`, tidak ada state global. Perubahan murni logika transformasi `imp.source` (str) → `list[str]` dotted target.

**Interface contracts:**

| Fungsi | Input | Output | Catatan |
|---|---|---|---|
| `_normalize_import_source(source, is_wildcard)` | `source: str` (raw statement text dari `ImportInfo.source`, mis. `"from graps.scanner import ParsedFile, ParsedImport"`); `is_wildcard: bool` (dari `ImportInfo.is_wildcard`) | `list[str]` dotted module path, 1 per alias. `[]` kalau parse gagal / bukan import valid. | Pure-function, no side-effect. Handle 5 bentuk: `import X`→`["X"]`; `import X.Y`→`["X.Y"]`; `from X import Y`→`["X.Y"]`; `from X import Y, Z`→`["X.Y","X.Z"]`; `from .X import Y`→`[".X.Y"]`; `from . import Y`→`[".Y"]`; `from ..X import Y`→`["..X.Y"]`; `from X import *` (is_wildcard=True)→`["X"]` (base saja, set is_star di caller); `import X as Y`→`["X"]` (strip alias). Guard: kalau source tidak match pattern import sama sekali → `[]` (emit 0, jangan crash). |
| `_extract_imports(imports, language)` (diedit) | `imports: list[Any]` (ImportInfo objects); `language: str` (dari `result`/`pf.language`) | `list[ParsedImport]` | Untuk `language == "python"`: panggil `_normalize_import_source` per ImportInfo, emit 1 ParsedImport per dotted target. Dedup by lineno tetap (existing logic). Untuk non-Python: behavior lama `target=imp.source` (tidak dibuat edge resolver, tapi data di-preserve untuk display). `is_star` = `imp.is_wildcard`. `is_conditional` tetap default False (bug terpisah, di luar scope). |
| `resolve_import` (UNCHANGED) | `ParsedImport` dengan `target` dotted | `Path \| None` | Tidak diubah. Setelah fix adapter, input selalu dotted → resolver jalan sebagaimana didesain. |

**State ownership:** Independen. Tidak menyentuh `store.state` (frontend), tidak menyentuh `graphOpenDirs`, tidak menyentuh visibility/draw logic. Pure backend scanner-layer fix. Arrow task frontend (`graph.js`) independen total — setelah fix ini, edge keluar dari backend, arrow otomatis punya edge buat digambar.

**Flow (pseudocode):**

```
# tree_sitter_parser.py
def _normalize_import_source(source, is_wildcard):
    s = source.strip()
    # import X  /  import X.Y  /  import X as Y  /  import X, Y
    if s.startswith("import "):
        names = s[len("import "):]
        return [_strip_alias(n.strip()) for n in names.split(",") if n.strip()]
    # from X import Y, Z  /  from .X import Y  /  from X import *
    if s.startswith("from "):
        rest = s[len("from "):]
        "import" in rest → split module_part, names_part
        base = module_part.strip()          # "graps.scanner" atau ".X" atau "..X"
        if is_wildcard:
            return [base]                    # from X import * → target = X (base)
        names = names_part.strip()
        # relative: base sudah punya leading dots, sep = ""
        sep = "" if base.startswith(".") else "."
        return [f"{base}{sep}{name.strip()}" for name in names.split(",") if name.strip()]
    return []  # bukan import valid → emit 0

def _extract_imports(imports, language):
    seen_lineno = set()
    results = []
    for imp in imports:
        lineno = imp.span.start_line + 1 if imp.span else 0
        if lineno in seen_lineno: continue
        seen_lineno.add(lineno)
        if language == "python":
            targets = _normalize_import_source(imp.source, imp.is_wildcard)
            for t in targets:
                results.append(ParsedImport(target=t, lineno=lineno, is_star=imp.is_wildcard))
        else:
            results.append(ParsedImport(target=imp.source, lineno=lineno, is_star=imp.is_wildcard))
    return results

# cli.py:_parse_file UNCHANGED — ts first, ast fallback.
# resolver.py UNCHANGED — terima dotted, return path.
# build_graph UNCHANGED — edge dibuat untuk target yang resolve.
```

---

## Phase 4 — Edge Cases & Failure Modes

| # | Komponen | Kasus | Mitigasi |
|---|---|---|---|
| 1 | `_normalize_import_source` | Multi-line paren import `from X import (\n Y,\n Z\n)` — `imp.source` mungkin satu baris (tree-sitter splice) atau multi-baris | Test fixture `tests/fixtures/multiline_import.py`. Helper split by `,` handle `\n`+whitespace via `.strip()` per name. Kalau tree-sitter preserve `(...)`, strip parens sebelum split. Verify di Phase 6 manual. |
| 2 | `_normalize_import_source` | Backslash continuation `from X import Y, \\\n Z` | `.strip()` per name handle trailing `\`. Test fixture. |
| 3 | `_normalize_import_source` | Relative import `from . import x` — belum verified apakah `imp.source` = `"from . import x"` (raw) atau `".x"` | Test fixture `tests/fixtures/relative_imports/main.py` (sudah ada). Helper deteksi `base.startswith(".")` → sep="". Kalau tree-sitter ternyata sudah ternormalisasi, helper idempoten (`.x` tidak match `from ` prefix → return `[]` — BUG). Wajib verify sebelum implementasi: cek `imp.source` untuk relative import via run singkat. |
| 4 | `_normalize_import_source` | Star import `from X import *` — `is_wildcard=True`, `source` raw | Helper: kalau `is_wildcard=True`, return `[base]` (extract module sebelum `import`), abaikan `*`. Match ast: `target="X"`, `is_star=True`. |
| 5 | `_normalize_import_source` | `import X as Y` — alias | `_strip_alias`: split `as`, ambil `[0]`. Match ast `target=alias.name` (abaikan `asname`). |
| 6 | `_normalize_import_source` | Source bukan import (false positive tree-sitter) | Return `[]` → emit 0 ParsedImport. Jangan crash. Log warning debug. |
| 7 | `_extract_imports` | Non-Python language (Go/TS/JS) lewat fungsi | Guard `language == "python"` → path lama `target=imp.source`. Edge non-Python tidak dibuat resolver (by design), tapi data di-preserve untuk display imports di node card. |
| 8 | `_extract_imports` | Dedup by lineno — `from X import Y, Z` 1 lineno produce 2 target | Dedup tetap by lineno (existing). 2 ParsedImport dengan lineno sama OK — dedup mencegah duplikat statement, bukan duplikat target. `build_graph` dedup edge by `(src, tgt)` tuple (existing `edges.setdefault`). |
| 9 | End-to-end | Setelah fix, edge count ts-path vs ast-path beda (ts extract 9 import graph_builder, ast 13 — ts miss `from __future__`?) | Diverifikasi: beda count acceptable selama edge yang penting (internal repo import) ter-resolve. `__future__` resolve None (stdlib) → no edge either way. Acceptable. |

---

## Phase 5 — Resource & Constraint Check

- **Library baru:** Tidak ada. Normalisasi pakai stdlib string ops (`str.split`, `.strip`, `.startswith`). Tidak tambah dependency. Tidak pakai `ast.parse` di adapter (opsi C di-investigasi dan ditolak: double-parse cost, dan ast.parse di adapter melanggar parser-agnostic prinsip BLUEPRINT §4 — adapter tree-sitter tidak boleh depend on ast module).
- **Performance impact:** Negligible. Normalisasi regex/string-ops per ImportInfo, O(1) per import. Untuk repo 95 file × avg 3 import = ~285 normalisasi call, <1ms total. Tidak ada tradeoff — sebaliknya, fix ini ENABLE edge creation (sebelumnya 0 edge = graph useless, setelah fix 39 edge = graph useful). Net positive.
- **Environment:** Python 3.12 (venv), tree-sitter-language-pack v1.12.1 terinstall. Tidak ada constraint baru. Test butuh tslp terinstall (sudah di-guard `pytest.importorskip` di `test_tree_sitter_parser.py:21-24`).

---

## Phase 6 — Testing Plan

**Unit tests:**

| Test | File | Assertion |
|---|---|---|
| `test_normalize_import_source__plain_import` | `tests/test_tree_sitter_parser.py` (baru) | `_normalize_import_source("import os", False) == ["os"]`; `"import a.b.c"` → `["a.b.c"]`; `"import a as b"` → `["a"]` |
| `test_normalize_import_source__from_import` | sama | `"from x import y"` → `["x.y"]`; `"from x import y, z"` → `["x.y", "x.z"]` |
| `test_normalize_import_source__relative` | sama | `"from . import x"` → `[".x"]`; `"from .a import b"` → `[".a.b"]`; `"from ..a import b"` → `["..a.b"]` |
| `test_normalize_import_source__star` | sama | `"from x import *", is_wildcard=True` → `["x"]` |
| `test_normalize_import_source__invalid` | sama | `"not an import"` → `[]`; `""` → `[]` |
| `test_parse__python_target_format` (edit existing) | `tests/test_tree_sitter_parser.py:TestPython` | Ganti `"os" in i.target` → `i.target == "os"` eksplisit. Tambah `from x import y` fixture → `i.target == "x.y"`. |
| `test_build_graph__edge_via_tree_sitter` | `tests/test_graph_builder.py` (baru) | Parse fixture `fixtures/relative_imports/main.py` via `TreeSitterParser`, `build_graph`, assert `len(edges) >= 1`. Sebelum fix: 0 edge (bug). Setelah fix: >= 1. |
| `test_resolve_import__raw_statement_returns_none` | `tests/test_resolver.py` (baru) | `ParsedImport(target="from x import y")` → `resolve_import(...) is None`. Regression guard kontrak. |

**Manual test scenarios:**

| Skenario | Expected |
|---|---|
| `graps /root/graps --no-browser` (repo sendiri) | Log "Found N import relationships" dengan N > 0 (target ~39 match ast-path). Sebelum fix: 0. |
| Buka browser, load canvas, expand folder `graps/scanner/` | Edge ter-render antara `graph_builder.py` → `resolver.py`, `risk_analyzer.py`, `sanitize.py`, `__init__.py`. Sebelum fix: 0 edge, canvas kosong. |
| Klik node `graph_builder.py` | Detail panel tampilkan 13 imports (atau 9 ts-extracted), dengan `resolved_path` terisi untuk internal import. Edge ke/dari node highlight. |
| Edge arrow (task sebelumnya) | Arrow direction marker muncul di edge yang sekarang ter-render (sebelum fix: tidak ada edge → tidak ada arrow). |
| Repo proyek lain (non-graps) dengan relative + absolute import mix | Edge ter-render untuk import yang resolve ke file dalam repo. Stdlib/3rd-party import → no edge (resolver None, by design). |

**Staging/dev verification:** Jalankan `graps <path> --host 127.0.0.1 --port <port> --no-browser` (BUKAN `python -m graps.cli` — itu self-check mode), cek log "Found N import relationships" dengan N > 0, buka browser jalankan checklist. Unit test: `cd /root/graps && source venv/bin/activate && pytest tests/test_tree_sitter_parser.py tests/test_graph_builder.py tests/test_resolver.py -v`.

**Production monitoring (silent-failure detection):** Tambah assertion di `cli.py:main` setelah `build_graph`: kalau `meta.total_edges == 0` DAN `total_files > 5` DAN ada file Python dengan import internal → warning non-blocking (`typer.echo("  ! Warning: 0 edges detected — possible resolver/adapter issue")`). Ini guard silent-failure: kalau bug serupa kambuh (adapter format drift lagi), user langsung lihat warning di startup, bukan canvas kosong yang ambigu. Alternative: self-check `cli.py:__main__` assert `total_edges > 0` untuk fixture repo. Pilih assertion di main (runtime user-visible) — lebih lazy, no test fixture maintenance.

---

## Self-check (wajib dijawab sebelum plan ini final)

**Apakah ini desain paling umum? (app yang menggunakannya)**
Ya. Normalisasi import statement → dotted module path adalah pattern standar di semua dependency-graph tool Python: **pydeps**, **pyreverse** (Pylint), **pyan**, **snakefood**, **depend**. Mereka semua parse `import`/`from` statement → module path sebelum resolve ke file. Untuk JS/TS: **madge**, **dependency-cruiser** lakukan hal sama (`import x from 'y'` → module specifier). tree-sitter-language-pack sendiri return raw `source` karena language-agnostic (306 bahasa, tidak bisa assume dotted module untuk semua) — responsibility normalisasi ada di consumer per-bahasa, persis yang dilakukan ast_parser untuk Python. Fix ini bawa tree-sitter adapter ke kontrak yang sama.

**Apakah ini approach terbaik dari yang terbaik?**
Ya, untuk scope ini. 3 alternatif dievaluasi:
- (A) Toleransi 2 format di resolver: ditolak — melanggar separation of concerns, resolver jadi parser syntax (raw statement punya 5+ bentuk), bug farm.
- (B) `ast.parse` di adapter untuk dapat kontrak persis: ditolak — double-parse cost, dan melanggar BLUEPRINT §4 parser-agnostic (adapter tree-sitter depend on ast module = coupling yang dilarang blueprint).
- (C) Normalisasi string-ops di adapter (plan ini): dipilih — pure-function, testable, no coupling, single format contract, minimal blast radius (1 fungsi private). Trade-off: regex/string-ops bisa miss exotic syntax (multi-line paren) — mitigasi: test fixture exotic + fallback `[]` kalau parse gagal (jangan crash). Lazy correct.

**Apakah sudah melakukan deep research?**
Ya. Investigasi runtime dilakukan (bukan asumsi):
- Verified `ImportInfo` spec tree-sitter-language-pack v1.12.1: `source: str` (raw), `items: list[str]` (selalu [] untuk Python), `alias`, `is_wildcard`, `span`. Tidak ada field module path bersih.
- Verified ast_parser kontrak `target` untuk 5 bentuk import (baca `visit_Import`/`visit_ImportFrom` line 156-175).
- Verified resolver behavior: 39 edge via ast-path (inline `_build` system python3), 0 edge via ts-path (venv CLI). Discrepancy = smoking gun.
- Verified 5 test gap spesifik yang membuat bug silent (substring assertion lemah, synthetic ParsedFile di edge test, resolver test pakai dotted manual, Go dedup substring lemah, cli self-check tidak assert edge count).
- Verified bug pre-existing sejak Phase 4 (tree-sitter adapter commit), unrelated ke arrow task (frontend-only, 1 baris).

---

## Catatan di luar 3 kategori pertanyaan yang diizinkan

*(Tidak ada pertanyaan yang fit kriteria "plan incorrect" / "info ambiguous" / "execution direction" — investigasi thorough, semua keputusan desain didokumentasi eksplisit di Phase 3. Catatan keputusan otonom di bawah.)*

1. **Keputusan: Python-only normalisasi.** Helper di-guard `language == "python"`. Non-Python tetap `target=imp.source` (edge tidak dibuat resolver by design — resolver Python-only). Kalau masa depan resolver multi-language dibuat, helper di-extend per-bahasa. Hindari regex Python di-aplikasikan ke Go `import "fmt"` (false match).

2. **Keputusan: 1 ParsedImport per alias** (match ast). `from X import Y, Z` → 2 entries. Alternatif (1 entry dengan target multi) ditolak: `_build_edges` weight count jadi beda dengan ast-path, dan `imported_names` list semantics berubah.

3. **Keputusan: helper return `list[str]`, caller wrap `ParsedImport`.** Pure-function testable tanpa fixture file. Alternatif (helper return `list[ParsedImport]`) menambah coupling ke dataclass — tidak ada value, hanya scaffolding.

4. **Keputusan: fallback `[]` kalau parse gagal** (bukan raise). Import false-positive tree-sitter (comment/string misdeteksi) tidak boleh crash scanner. Silent-skip dengan debug log. Trade-off: kalau normalisasi miss pattern valid, edge drop silent — mitigasi: Phase 6 assertion `total_edges > 0` di CLI startup warning.

5. **Bug terpisah dicatat (di luar scope):** `is_conditional` gap di tree-sitter adapter (tidak set True untuk try/except import). Affects `risk_analyzer`, bukan edges. Task terpisah, tidak block task ini.

6. **Pre-requisite urutan task:** Fix ini SEBAIKNYA di-merge sebelum/dengan arrow task, karena arrow tidak ada edge buat digambar selama bug ini ada. Tapi secara kode independen — arrow fix `graph.js` valid tersendiri, fix ini `tree_sitter_parser.py` valid tersendiri. Urutan merge = keputusan user.

7. **Unverified saat investigasi:** `imp.source` untuk relative import (`from . import x`) dan multi-line paren belum di-run verifikasi (user stop run). Asumsi: raw statement. Phase 4 #3 flag ini sebagai wajib verify sebelum implementasi — jalankan 1 script cek `imp.source` untuk `tests/fixtures/relative_imports/main.py` sebelum tulis helper. Kalau tree-sitter ternyata sudah ternormalisasi untuk relative, helper perlu handle 2 bentuk (raw + pre-normalized) atau guard berbeda.

**Status: APPROVED untuk diimplementasikan setelah Phase 4 #3 (verifikasi relative import `imp.source`) di-run.**
