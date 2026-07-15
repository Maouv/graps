# Bug Backlog

> **Summary Block:** Reports where existing behavior fails its contract. Planning risks are not bugs and remain in entity review sections.

## BUG-0001: TreeSitterParser missing call extraction → 0 call_sequence flows

- **Reported:** 2026-07-15
- **Severity:** Medium — call_sequence flows empty when TreeSitterParser is active
- **Root cause:** `tree_sitter_parser.py` returns `ParsedFile` with `calls=[]` (default). `flows.py:113` `if not func.calls: continue` → all functions skipped → 0 call_sequence flows. ASTParser (`ast_parser.py`) has `visit_Call` (line 230) and populates `ParsedCall`, but TreeSitterParser succeeds parse → AST fallback never fires.
- **Plan contract:** `architecture.md` — Scanner/parsers own "calls"; structural scanning must retain "call sites [...] where supported".
- **Affected:** `graps/scanner/tree_sitter_parser.py`, `graps/scanner/flows.py`
- **Fix options:**
  - **A:** Add `call_expression` query to TreeSitterParser → extract callee + line → `ParsedCall`. Medium effort, duplicates AST work.
  - **B (recommended):** Flip dispatch — ASTParser first for `.py`, TreeSitter for non-Python only. 1-line change, YAGNI, AST more accurate for Python.
- **Status:** Fixed (commit `b323f3f`). Option B implemented.

## BUG-0002: Symlink bypass in credential file check

- **Reported:** 2026-07-15
- **Severity:** Low — requires filesystem write access to create symlink
- **Root cause:** `_is_credential_file(file)` checks query param string, not resolved `target.name`. Symlink `link.txt` → `.env` passes credential check (name is `link.txt`), file content served.
- **Affected:** `graps/server/app.py` — `/api/source` endpoint, `build_ai_context`
- **Fix:** Also check `_is_credential_file(target.name)` after `.resolve()`. 2-line change.
- **Status:** Open — pending fix.
