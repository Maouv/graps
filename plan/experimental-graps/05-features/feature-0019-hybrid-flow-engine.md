---
id: FEAT-0019
type: feature
status: planning
owner: Maou
created: 2026-07-14
updated: 2026-07-14
depends_on: [FEAT-0017, FEAT-0018]
related: []
---

# Hybrid structural and semantic flow engine

> **Summary Block:** Build structural flow order and overlay only validated AI labels onto existing node IDs. This entity is planning-only and cannot enter implementation before its dependencies and Definition of Ready are satisfied.

## 1. Lifecycle

### 1. Idea

- Captured in project discovery; feature-specific validation remains open.

### 2. Research

- Captured in project discovery; feature-specific validation remains open.

### 3. Analysis

- Captured in project discovery; feature-specific validation remains open.

### 4. Requirement

- Defined below; awaiting user approval.

### 5. Planning

- Planning in progress; use linked project SSoT.

### 6. Design

- Planning in progress; use linked project SSoT.

### 7. Architecture

- Planning in progress; use linked project SSoT.

### 8. Implementation

- Not started — implementation is not yet authorized.

### 9. Self Review

- Not started — implementation is not yet authorized.

### 10. AI Review

- Not started — implementation is not yet authorized.

### 11. Code Review

- Not started — implementation is not yet authorized.

### 12. Testing

- Not started — implementation is not yet authorized.

### 13. QA

- Not started — implementation is not yet authorized.

### 14. Potential Bug Review

- Not started — implementation is not yet authorized.

### 15. Edge Case Review

- Not started — implementation is not yet authorized.

### 16. Negative Scenario Review

- Not started — implementation is not yet authorized.

### 17. Security Review

- Not started — implementation is not yet authorized.

### 18. Performance Review

- Not started — implementation is not yet authorized.

### 19. Compatibility Review

- Not started — implementation is not yet authorized.

### 20. User Testing

- Not started — implementation is not yet authorized.

### 21. User Feedback

- Not started — implementation is not yet authorized.

### 22. Revision

- Not started — implementation is not yet authorized.

### 23. Deployment

- Not started — implementation is not yet authorized.

### 24. Monitoring

- Not started — implementation is not yet authorized.

### 25. Post Implementation Review

- Not started — implementation is not yet authorized.

### 26. Lessons Learned

- Not started — implementation is not yet authorized.

### 27. Continuous Improvement / Archive

- Not started — implementation is not yet authorized.

## 2. Requirement & Acceptance Criteria
### Functional Requirements
- Implement only the capability described in the Summary Block.
- Preserve structural-first, no-AI fallback, source-security, and responsive/accessibility invariants where applicable.

### Acceptance Criteria
- [ ] Direct calls use `direct_call/resolved`.
- [ ] Dynamic or ambiguous calls retain uncertainty and reason.
- [ ] AI payload contains labels/summaries but no edges or order.
- [ ] Invalid enrichment is rejected atomically.

## 3. Design
- Follow `../04-design-architecture/design.md`; do not redefine shared interaction behavior here.

## 4. Architecture / Technical Notes
- Follow `../04-design-architecture/architecture.md` and `data-contracts.md`.
- Structural IDs and graph relationships remain deterministic; semantic output is optional.

## 5. Prioritization and Implementation Notes
- Impact: required within its dependency phase.
- Effort: estimate only when the related TASK enters ready state.
- Implementation must be sliced into tested coherent changes; no unapproved dependency.

## 6. Mandatory Review Section

### Potential Bugs

- Hybrid structural and semantic flow engine may violate its contract if dependent structural IDs, state, or fallback behavior is incomplete.

### Known Risks

- Static analysis and UI state may diverge if stable IDs or cache hashes are not enforced.

### Edge Cases

- Empty data, malformed source, stale IDs, unavailable AI, and narrow mobile viewport.

### Failure Cases

- Component failure must preserve deterministic structural fallback or fail without corrupting persisted state.

### Negative Test Cases

- Reject unknown IDs, invalid state, traversal-like inputs, and AI claims outside the structural allowlist.

### Regression Risk

- Existing scanner, resolver, API, CLI, cache, and source-security behavior may regress.

### Rollback Plan

- Revert the coherent implementation commit; retain schema-version fallback and disable AI without disabling structure.

### Validation Checklist

- [ ] Targeted unit/API/UI tests pass.
- [ ] `git diff --check` passes.
- [ ] Failure fallback is exercised.

### Review Checklist

- [ ] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist

- [ ] Direct calls use `direct_call/resolved`.
- [ ] Dynamic or ambiguous calls retain uncertainty and reason.
- [ ] AI payload contains labels/summaries but no edges or order.
- [ ] Invalid enrichment is rejected atomically.

### User Testing Result

- Not started — planning stage.

### Post Implementation Review

- Not started — complete after deployment and monitoring evidence.

### Lessons Learned

- Not started — record observed learning; do not invent outcomes.

### Future Improvement

- Defer only with a linked backlog/entity and an explicit reason.

## 7. Closing
- Status remains `planning`; PIR, lessons, and archive decision must be evidence-backed.
