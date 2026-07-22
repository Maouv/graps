# Spike: Flow-Worthiness Classification

> **Summary Block:** Defines which functions should render a Flow tab versus fall back to Source, and why. Blocks any implementation of flow-fallback UX until taxonomy is validated against multi-language fixtures and external repos. Detailed implementation contracts (once validated) belong in design/data-contracts, not here.

## Problem

Clicking a function currently opens a Flow tab unconditionally. Functions with no internal calls, branches, or loops (e.g. `ids.py::class_id`) render "no flow step found" — read by non-technical (vibe-coder) users as a tool failure rather than an accurate "this function is simple" signal. Root cause is UX, not a scanner bug: some functions genuinely have no flow to draw.

## Taxonomy (draft, decided 2026-07-22)

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

No classifier implementation exists yet. No fixture or external-repo measurement has been run. This taxonomy is a design hypothesis pending:
1. Unit tests against existing `tests/fixtures/` (per-language) to check classification accuracy.
2. Battle test against 3-4 external repos (utility library, backend/web framework, non-Python-family language) to check the taxonomy generalizes beyond this codebase's own style.

No task should move to `06-tasks` until both steps above produce a written ratio/accuracy result in this file.

