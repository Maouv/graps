# Experimental Graps Requirements

> **Summary Block:** Project-level functional/non-functional requirements, constraints, non-goals, and Definition of Done. Capability-level acceptance is owned by the linked FEAT entities.

## Functional Requirements
- **FR-001:** Always scan and expose deterministic project structure without AI.
- **FR-002:** Navigate folders/packages/modules/files/functions using the exact click contract.
- **FR-003:** Open source, structural flow, and module overview tabs by stable ID.
- **FR-004:** Optionally enrich existing structural IDs with validated semantic metadata.
- **FR-005:** Persist versioned project-local graph, architecture, settings, and cache data.
- **FR-006:** Support structural readiness, status, settings, modules, flows, source, and manual scan APIs safely.
- **FR-007:** Preserve the canonical `dir-panel | workspace | ai-panel` mental model responsively.

## Non-Functional Requirements
- Deterministic output ordering and stable scan-root-relative IDs.
- Graceful per-file parser diagnostics; one malformed source file cannot abort the project.
- Source-root enforcement, traversal defense, credential-context exclusion, and no absolute path disclosure.
- Accessible keyboard behavior, visible focus, ARIA state, reduced motion, and 44px touch targets.
- Minimal frontend bundle; no heavy UI library without approval.
- Atomic storage writes and schema/hash compatibility checks.

## Constraints and Assumptions
- Instructor is not authorized until package name, exact version, rationale, and explicit approval are recorded.
- Structural scanning cannot be toggled off; AI Enrichment defaults ON but is optional.
- `BLUEPRINT.md` is ignored as a controlling plan.
- Existing unrelated plans remain untouched.
- Python direct-call sequence is MVP; full runtime/control flow is not assumed.

## Non-goals
- Guaranteed complete runtime graph for dynamic languages.
- Arbitrary cross-service tracing, code editing, cloud cache, plugin marketplace, or collaboration.
- AI-defined structural boundaries or AI-generated graph edges/order.
- A mandatory visual graph canvas in the first implementation.

## Project Definition of Ready
- [x] Requirements and capability entities are documented.
- [x] Dependencies are represented in entity metadata and depgraph.
- [x] Owner is set.
- [ ] User approves implementation start and any required dependency separately.

## Project Definition of Done
- [ ] All 20 feature acceptance checklists have real evidence.
- [ ] All four phase tasks complete mandatory review and reach `done`.
- [ ] Structural browsing works with AI OFF, unavailable, malformed, or failing.
- [ ] Security, cache, responsive, accessibility, compatibility, and regression tests pass.
- [ ] Deployment, monitoring, PIR, lessons learned, and archive decision are recorded.
