# Spike: Flow-Worthiness Classification

> **Summary Block:** Defines which functions should render a Flow tab versus fall back to Source, and why. Blocks any implementation of flow-fallback UX until taxonomy is validated against multi-language fixtures and external repos. Detailed implementation contracts (once validated) belong in design/data-contracts, not here.

## Problem

Clicking a function currently opens a Flow tab unconditionally. Functions with no internal calls, branches, or loops (e.g. `ids.py::class_id`) render "no flow step found" — read by non-technical (vibe-coder) users as a tool failure rather than an accurate "this function is simple" signal. Root cause is UX, not a scanner bug: some functions genuinely have no flow to draw.

## Taxonomy (draft, decided 2026-07-22)

> **Validation status (updated 2026-07-22):** Validated: **Python only** — confirmed against 1970 functions across 6 Python repos (fixtures + graps self + requests + fastapi + click + tenacity + httpx). Non-Python: **blocked on parser** — tree-sitter adapter does not extract `calls`/`branches`/`routes` for JS/TS/Go/Rust (see backlog [REF-0011](../00-backlog/backlog-refactor-enhancement.md)). Python-only scope is **temporary, not final** — lifting the restriction is gated on REF-0011.

| # | Category | Structural signal | Flow-worthy | Notes |
|---|---|---|---|---|
| 1 | Pure/Trivial | Single statement, direct return, no calls | No | Route to Source directly |
| 2 | Data definition | Returns/builds a data literal only (dict, dataclass, struct) | No | Route to Source directly |
| 3 | Delegator | Exactly one call, immediately returned | No | Treated as trivial per decision below |
| 4 | Linear sequence | ≥2 sequential calls/statements, no branch | Yes | Threshold = 2, see open question |
| 5 | Branching logic | if/else, match/switch present | Yes | |
| 6 | Loop/iteration | for/while/map-reduce present | Yes | |
| 7 | Unresolved call | Calls something the resolver can't link (dynamic import, external lib) | Partial | Show what's known, never render empty |
| 8 | Error handling | try/catch/except present | Yes | Treated as implicit branch |
| 9 | Async/callback | async/await, promise, callback pattern | Yes — separate track | Needs own visual representation, not sequential flow. Not yet designed. |
| 10 | Empty/stub | Empty body, `pass`, `...`, `NotImplementedError`, TODO-only | No | Distinct message from trivial: "not yet implemented," not "simple by design" |

## Decisions made this session

- Delegator (#3) counts as **not flow-worthy** — a single pass-through call is treated as trivial, not as a 1-edge flow.
- Async/callback (#9) is **out of scope for the linear-flow fallback rule** — requires its own spike on visual representation before implementation.
- Linear sequence (#4) threshold is **2 calls/statements minimum** to qualify as flow-worthy.

## Open questions

- Does the 2-call threshold hold across languages, or does it need per-language tuning (e.g. Rust `match` arms, Go multi-return idioms)?
- Should "no flow" functions skip the Flow tab entirely, or show a disabled/labeled tab instead of not rendering it?
- What's the actual trivial-vs-flow-worthy ratio in real codebases? Needs measurement, not assumption.

## Evidence boundary

> **Updated 2026-07-22 — Python-only MVP validated.** Stratified 27-function sample (3 per in-scope category) drawn from a 1954-function pool across 6 Python repos (graps self + requests + fastapi + click + tenacity + httpx). Each function labeled independently from daily-user expectation (Flow tab useful vs Source tab correct) by reading source body, not parser category.

**Accuracy:**

| Rule | Correct | Accuracy |
|---|---|---|
| Control (today — Flow tab if ≥1 call/branch/route) | 20/27 | 74.1% |
| Experiment (taxonomy — Flow only if flow-worthy) | 23/27 | 85.2% |
| **Ratio (experiment / control)** | — | **1.15 (15% lift)** |

The lift comes from the delegator decision (cats 7-9 above): three `return foo(self, other)` / `return self.request(...)` passthroughs that today render a 1-box Flow tab (read as "is that all?") route to Source under the taxonomy — matching daily-user expectation.

**Two taxonomy gaps surfaced (refinements for v2, not blockers for MVP):**

1. **Cat 4 (linear sequence) misfires on chained method calls.** `"-".join(name.split()).lower()` is one expression, not a linear sequence of distinct operations — but the parser counts 3 calls, so the taxonomy routes it to Flow. Daily user reads it as a one-liner → expects Source. **Refinement:** collapse chained method calls on a single expression into one logical call before counting, or require calls to be on separate statements.
2. **Cat 7 (unresolved partial) misfires on single-call attribute-set and NotImplementedError stubs.** `self.x = foo()` and `raise NotImplementedError(...); yield b""` are not flow-worthy — they're trivial or stubs — but the taxonomy's "≥1 call" rule routes them to Flow. **Refinement:** cat 7 should require the call to be in a return statement or control-flow context, not a bare expression statement; NotImplementedError stubs should fall under cat 10.

Both gaps are documented as v2 refinements. The 15% lift + 85.2% accuracy on the labeled sample justifies adopting the taxonomy as Python-only MVP. Non-Python remains blocked on [REF-0011](../00-backlog/backlog-refactor-enhancement.md).

**Status:** evidence boundary for Python (step 2 — battle test against external repos) is **lifted**. Step 1 (per-language fixtures) remains **blocked on REF-0011** for non-Python. A task entity may now be created in `06-tasks/` for the Python-only MVP implementation, scoped to:
- `classify_flow_worthiness(func)` in `flows.py` per the taxonomy above.
- Skip `call_sequence` flow emission for not-flow-worthy functions; emit a `source_only` marker (or equivalent) so the frontend can render Source tab with a category-specific label instead of "no flow step found."
- Apply v2 refinements (cat 4 chained-method collapse, cat 7 return-statement gate, NotImplementedError stub routing) when implementing — see gap notes above.

