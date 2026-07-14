# Work Breakdown Structure

> **Summary Block:** Four dependency-driven phase tasks. Detailed execution and review live in `06-tasks/`; capability contracts live in `05-features/`.

1. **TASK-0001 Foundation** — scanner, schema, graph, modules, storage.
2. **TASK-0002 Intelligence** — flow resolution, semantic validation, optional AI fallback.
3. **TASK-0003 Application UI** — shell, tree, tabs, AI panel, responsive behavior.
4. **TASK-0004 Hardening** — APIs, security, accessibility, performance, migration, docs.

## Dependency order
`TASK-0001 → TASK-0002 → TASK-0003 → TASK-0004`

No phase may claim completion while its feature acceptance or mandatory review evidence is missing.
