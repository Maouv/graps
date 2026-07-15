---
id: PROJ-0001
type: project-index
status: done
owner: Maou
created: 2026-07-14
updated: 2026-07-15
depends_on: []
related: []
---

# Experimental Graps — Project Index

> **Summary Block:** Sumber masuk tunggal untuk full project instance Experimental Graps. Project membangun ulang Graps sebagai code architecture explorer dengan structural analysis sebagai sumber kebenaran dan AI sebagai enrichment opsional. Status: Done. 4/4 tasks complete, 181 tests pass, ruff+mypy clean. 2 features deferred to backlog (FEAT-0018, FEAT-0019). Stages 20-27 (user testing → archive) pending deployment.

## Status
- **Lifecycle:** Implementation complete. Done.
- **Branch:** `experimental`.
- **Owner:** Maou.
- **Implementation authorization:** Given. All 4 tasks done (2026-07-15).
- **Deferred:** FEAT-0018 (multi-language module resolution), FEAT-0019 (enrichment rejection pipeline). See backlog.

## Navigation
- [Backlog](00-backlog/00-INDEX.md)
- [Discovery](01-discovery/00-INDEX.md)
- [Requirement](02-requirement/requirement.md)
- [Planning](03-planning/00-INDEX.md)
- [Design and architecture](04-design-architecture/00-INDEX.md)
- [Features](05-features/00-INDEX.md)
- [Tasks](06-tasks/00-INDEX.md)
- [Bugs and fixes](07-bugs-and-fixes/00-INDEX.md)
- [Refactor and enhancement](08-refactor-and-enhancement/00-INDEX.md)
- [Decision Log](09-decision-log.md)
- [Review and retro](10-review-and-retro/00-INDEX.md)
- [Archive](99-archive/00-INDEX.md)

## Single Sources of Truth
| Topik | SSoT |
|---|---|
| Scope, FR/NFR, constraints, project acceptance | `02-requirement/requirement.md` |
| WBS, dependency, lifecycle, timeline, RACI | `03-planning/` |
| UI interaction and visual behavior | `04-design-architecture/design.md` |
| Structural, AI, storage, API, security architecture | `04-design-architecture/architecture.md` |
| Capability requirements and acceptance | `05-features/` |
| Executable implementation phases | `06-tasks/` |
| Durable project decisions | `09-decision-log.md` |

## Guardrails
- Structural scan always works without AI.
- AI cannot create, delete, or reorder structural nodes or edges.
- No dependency installation without explicit approval and exact pin.
- `BLUEPRINT.md` is not controlling scope.
- Historical `../experimental-graps.md` is a compatibility pointer only.
