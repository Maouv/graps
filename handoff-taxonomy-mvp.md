# Handoff: Implement Flow-Worthiness Taxonomy (Python-only MVP)

**Session:** 2026-07-22 RnD follow-up
**Single source of truth:** [`plan/experimental-graps/01-discovery/spike-flow-classification.md`](plan/experimental-graps/01-discovery/spike-flow-classification.md)
**Authorization scope:** Python-only MVP. **Non-Python is explicitly OUT of scope** — gated on backlog [REF-0011](plan/experimental-graps/00-backlog/backlog-refactor-enhancement.md) (tree-sitter adapter does not extract calls/branches/routes for JS/TS/Go/Rust). Do NOT touch non-Python code paths.

---

## Your job

Implement the taxonomy validated in the spike file. Three deliverables, in order:

1. **`classify_flow_worthiness(func: ParsedFunction, body: str) -> Classification`** in `graps/scanner/flows.py` — pure function, deterministic, no I/O. Returns `{category, flow_worthy, reason}` per the 10-row taxonomy table in the spike.
2. **Wire it into the flow builder.** When `flow_worthy=False`, skip `call_sequence` flow emission and emit a `source_only` marker (or equivalent minimal signal) so the frontend can render the Source tab with a category-specific label ("pure function" / "delegator" / "stub" / "not implemented") instead of the current misleading "no flow step found".
3. **Apply the two v2 refinements documented inline in the spike's Evidence Boundary section** (cat 4 chained-method collapse, cat 7 return-statement gate + NotImplementedError-stub routing). These were caught during the 27-sample labeling — don't re-discover them.

## Anti-drift guardrails (the user's explicit concern)

**DO NOT:**
- Rewrite `flows.py` architecture, introduce new abstractions, factories, or interfaces for "future categories." The taxonomy is 10 rows. One pure function + one marker. That's it.
- Touch `ast_parser.py` or `tree_sitter_parser.py`. Parser changes are scoped under REF-0011, a separate work item. This task consumes parser output as-is.
- Implement non-Python classification. The parser doesn't expose the signals (see REF-0011). Any non-Python path you add will silently misroute — leave it untouched.
- Add new dependencies. Stdlib + existing graps deps only.
- Edit the spike file. It's the spec — read it, don't rewrite it. If you find a contradiction, stop and ask the user.
- Skip validation gates. `pos.py validate` must exit 0, `ruff check` + `mypy` must be clean before any commit.
- Auto-push. Commit per logical unit; wait for the user to say "push."

**DO:**
- Re-read the spike file in full before writing any code.
- Re-run `probe_classifier.py` (RnD scratch, repo root) on the same 6 Python repos after implementation — accuracy must stay ≥85% (baseline was 85.2%). If it drops, you broke something; don't ship.
- Verify the 4 disagreement cases from the spike's Evidence Boundary (cat 4 chained-method, cat 7 single-call attr-set ×2, cat 7 NotImplementedError stub) now route to Source under the v2 refinements. If any still routes to Flow, the refinement wasn't applied.
- Leave `ponytail:` comments on any deliberate simplification, naming the ceiling and upgrade path. (See `~/.hermes/skills/ponytail` if unfamiliar.)

## Validation gates (in order, all must pass)

1. `pos.py validate plan/experimental-graps` → exit 0
2. `ruff check graps/` → clean
3. `mypy graps/` → clean (or matches pre-existing baseline)
4. `.venv/bin/python probe_classifier.py graps .venv/lib/python3.11/site-packages/{requests,fastapi,click,tenacity,httpx}` → accuracy ≥85%
5. Live smoke: start graps server (`--host 0.0.0.0`), open `requests/sessions.py::Session.send` in browser → Flow tab shows if/try + ≥3 calls in order. Open `httpx/_client.py::Client.options` → Source tab with "delegator" label, NOT "no flow step found."

## Out of scope (do not start)

- Non-Python classification (REF-0011)
- Frontend redesign of the Source tab UX beyond the label swap (separate feature)
- Adding `routes` extraction to `ast_parser` (already present; do not duplicate)
- New tests beyond one runnable self-check for `classify_flow_worthiness` (see ponytail: non-trivial logic leaves one check behind)

## Open questions to ask the user before proceeding

If any of these come up, stop and ask — do not guess:
- The exact frontend label format for `source_only` (e.g., "delegator" vs "delegator — see X" vs icon-only).
- Whether to keep the current "no flow step found" string as a fallback for the `misc_flow` edge case, or replace it entirely.
- Whether the `source_only` marker should be a new flow kind in `flow.py`'s discriminated union, or a separate field on the function node.

---

**Bottom line:** the spike file is the spec. Read it. Implement the 3 deliverables. Hit the 5 validation gates. Don't expand scope. If in doubt, ask.
