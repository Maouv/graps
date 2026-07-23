# graps (experimental branch) — Session Handoff

Context for continuing work on this repo. Covers what was already fixed/removed
and facts you should not re-derive from scratch.

## Task for you: docstring cleanup

Translate all docstrings/comments in `graps/` to English. Keep them short and
information-dense — no filler, no restating the function signature, no `---`
separator lines. If a docstring makes a claim about the code that's no longer
true (see "BLUEPRINT.md doesn't exist" below), fix the claim, don't just
translate it.

Files with mixed Indonesian/English docstrings needing this pass:
`cli.py`, `server/app.py`, `ai/provider.py`, `storage.py`,
`scanner/tree_sitter_parser.py`, `scanner/ids.py`, `scanner/graph_builder.py`,
`scanner/flows.py`, `scanner/__init__.py`, `scanner/resolver.py`,
`scanner/modules.py`, `scanner/ast_parser.py`, `scanner/risk_analyzer.py`.

21 comments across these files reference "BLUEPRINT §N" — see fact below,
correct these rather than translating verbatim.

## Facts established this session (don't re-investigate)

**BLUEPRINT.md doesn't exist in this repo/branch.** `plan/00-INDEX.md`
explicitly excludes it as the controlling plan for the experimental rebuild.
Comments citing "BLUEPRINT §4" etc. are stale terminology from before this
branch existed. Not authoritative — correct or drop these references.

**`SummaryRequest` / `post_summary` route in `server/app.py` is a deliberate
deprecated stub.** Fields (`function`, `line`, `modified_at`) are unused in
the route body, but this is intentional (kept for backward-compat import) —
Pydantic still validates the body on every request, and 5+ tests in
`test_api.py` exercise this endpoint for security/response-shape checks.
**Do not delete this class or route.**

**`graps/ai/report-ai-cases.md`** is a stale bug report referencing
`ai/cache.py`, which is now deleted. Left in place as historical record, not
cleaned up.

**`test_api.py` requires `httpx2`** to run (`pip install httpx2
--break-system-packages`). It was silently erroring/skipped before this was
installed — always verify it actually runs, don't assume the skip is benign.

## What was removed/fixed this session (all verified: 119 passed, 3 skipped, ruff clean)

**Bug fix:** `graph_builder.py` recomputed `is_private` from
`name.startswith("_")`, discarding the parser-computed value — broke
non-Python languages (Go via tree-sitter). Fixed: `ast_parser.py` now
populates `is_private` properly; `graph_builder.py` trusts the field.

**Deleted — orphaned since Phase 5** (`post_summary` → `post_chat` refactor):
- `ai/cache.py`, `ai/validator.py` + their tests. Zero imports outside their
  own test files.

**Deleted — dispatch scaffolding never wired up** (`cli.py` hardcodes file-
suffix routing instead of using polymorphism):
- `scanner.ASTParser` class (zero instantiations anywhere, including tests)
- `scanner.BaseParser` Protocol
- `TreeSitterParser.supported_extensions()`

**Deleted — fields never populated or read anywhere:**
- `ParsedFunction.params/returns/callers/callees`. The Flow tab feature uses
  separate `calls`/`branches` fields instead for the same purpose.
- Dead branches in `app.py`'s `_format_function_metadata()` that read
  `fn.get("callers"/"callees"/"params"/"returns"/"risks")` — none of these
  keys are ever present on a function dict; `_build_functions()` never emits
  them, and risk data goes into a top-level `diagnostics` list instead.

**Deleted — dead CLI surface:** `--no-cache` flag + `cache_path` param
threading through `cli.py` → `create_app()`. Before Phase 5 this was
functional (unique cache file per run); after, it silently created an
abandoned temp file via `mkstemp` and had zero effect. Removed both the flag
and the param.

**Misc:** unused `logger` in both `cli.py` and `app.py` (never called),
unused `DEFAULT_CACHE_PATH` constant, dead `_rel()` wrapper in
`graph_builder.py` (duplicate of `to_posix_rel`), unused imports in
`modules.py`.

## Verification method used (repeat this, don't trust vulture alone)

`vulture` gives false positives on: FastAPI route handlers (decorated,
called by framework), Pydantic model fields read via `getattr(req, k)`
dynamically, typer CLI callback params, signal handler signatures
(`frame`/`signum`). Every vulture/ruff hit was cross-checked with
repo-wide `grep` for actual call sites before removal.
