---
id: REF-0010
type: refactor
status: reported
owner: Maou
created: 2026-07-16
updated: 2026-07-16
depends_on: []
related: []
---

# Frontend relocation — graps/public/ → frontend/

> **Summary Block:** Frontend files live inside the Python package at `graps/public/`. Bad for development — frontend and backend concerns mixed in same directory tree. Move to `frontend/` at repo root. Only `graps/server/app.py` references the path. Fixes issue.md refactor #2.

## 1. Deskripsi Masalah / Tujuan Perubahan

**Current structure:**
```
graps/                      ← repo root
  graps/                    ← Python package
    public/                 ← frontend files (app.css, app.js, index.html, icon/)
    server/
      app.py
    scanner/
    ...
```

**Target structure:**
```
graps/                      ← repo root
  frontend/                 ← frontend files (app.css, app.js, index.html, icon/)
  graps/                    ← Python package
    server/
      app.py
    scanner/
    ...
```

## 2. Root Cause Analysis

**Why current is wrong:** issue.md says "right now the frontend file its in public folder right? its bad for development maybe smart move if we put it in the new folder frontend/". Mixing static assets inside the Python package directory couples frontend and backend concerns — changes to frontend files shouldn't require navigating the package tree.

**What references `public/`:** Only one line in `graps/server/app.py` (line ~620):
```python
_public = Path(__file__).resolve().parent.parent / "public"
```
This resolves to `graps/public/` (two levels up from `graps/server/app.py`).

No other references found: no Dockerfile, no pyproject.toml, no `__init__.py` imports, no docker-compose, no Makefile.

## 3. Proposed Fix / Change

### 3a. Move directory

```bash
git mv graps/public/ frontend/
```

This moves the entire `graps/public/` directory to `frontend/` at repo root. Git history preserved.

### 3b. Update path in `app.py`

Change one line in `graps/server/app.py`:

```python
# Before:
_public = Path(__file__).resolve().parent.parent / "public"

# After:
_public = Path(__file__).resolve().parent.parent.parent / "frontend"
```

Path math:
- `Path(__file__).resolve()` = `/workspace/graps/graps/server/app.py`
- `.parent` = `graps/server/`
- `.parent.parent` = `graps/`
- `.parent.parent.parent` = `/workspace/graps/` (repo root)
- `/ "frontend"` = `/workspace/graps/frontend/`

### 3c. URL paths

No changes. FastAPI mounts at `/`:
```python
app.mount("/", StaticFiles(directory=str(_public), html=True), name="public")
```

All URL paths (`/icon/*.svg`, `/app.js`, `/app.css`, `/index.html`) remain identical regardless of disk location.

## 4. Scope & Impact

- **Komponen terdampak:** `graps/public/` → `frontend/` (git mv), `graps/server/app.py` (1 line).
- **Blast Radius:** Low. No code changes beyond the path constant. No URL changes. No API changes. No import changes.
- **Dependencies:** None. Can run independently of all other refactors.
- **Mobile impact:** None. Static files served identically.

## 5. Lifecycle Stage Tracking

Compact — belum ada stage yang dimulai (27 tahap, lihat 03 §3.1).
Akan di-expand ke Expanded Form begitu `status` naik ke `in-progress`.

## 6. Mandatory Review Section

### Potential Bugs
- Path resolution: if `app.py` is run from a different working directory, `Path(__file__).resolve()` still resolves correctly because it's based on `__file__`, not `cwd`.
- `git mv` preserves history. No special `.gitattributes` needed.
- `icon/` subdirectory with `LICENSE-CODICONS` moves with the parent — no orphaned license.

### Known Risks
- Very low risk. Only a filesystem path changes. The mount behavior is identical.
- If any other tool or script references `graps/public/` by path (not found in current search), it would break. Guard: search confirmed no other references.

### Edge Cases
- Running app from IDE with different `cwd`: `Path(__file__).resolve()` handles this — always resolves to the actual file location.
- Packaging (pip install): no `pyproject.toml` exists. If one is added later, `frontend/` is outside the package — would need explicit include. Not applicable now.

### Failure Cases
- If `frontend/` directory already exists: `git mv` would fail. Guard: confirmed it doesn't exist.
- If `app.py` line number shifts: the change is content-based (find-replace), not line-number-based.

### Negative Test Cases
- Verify app starts without errors after move
- Verify `GET /` returns `index.html`
- Verify `GET /app.js` returns JS
- Verify `GET /icon/package.svg` returns SVG
- Verify `GET /icon/split-horizontal-right-select.svg` returns SVG
- Verify no `FileNotFoundError` on startup

### Regression Risk
- Very low. One path constant changes. All runtime behavior identical.
- If `git mv` is done but `app.py` not updated → `FileNotFoundError` on startup. Guard: both changes in same commit.

### Rollback Plan
- `git revert` the commit. `git mv` reverse restores `graps/public/`.

### Validation Checklist
- [ ] `git mv graps/public/ frontend/` executed
- [ ] `graps/server/app.py` `_public` path updated
- [ ] App starts without `FileNotFoundError`
- [ ] `GET /` returns `index.html`
- [ ] `GET /icon/*.svg` returns SVG files
- [ ] No other references to `graps/public/` remain

### Review Checklist
- [ ] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist
- [ ] `frontend/` directory exists at repo root with all files
- [ ] `graps/public/` no longer exists
- [ ] App serves frontend from new location
- [ ] All icons load correctly

### User Testing Result
-

### Post Implementation Review
-

### Lessons Learned
-

### Future Improvement
- Add `pyproject.toml` with explicit `frontend/` include if packaging is needed later.
