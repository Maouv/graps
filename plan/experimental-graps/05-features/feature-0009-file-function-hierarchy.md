---
id: FEAT-0009
type: feature
status: review
owner: Maou
created: 2026-07-14
updated: 2026-07-15
depends_on: [FEAT-0008, FEAT-0017]
related: []
---

# Expandable file and function hierarchy

> **Summary Block:** Expose files and their parsed functions beneath the structural tree. Implemented as part of TASK-0003. See task file for implementation evidence and smoke test results.

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

- Done (2026-07-15). Implemented as part of TASK-0003 Phase 3. See `graps/public/` assets.

### 9. Self Review

- Done (2026-07-15). Smoke test passed — all API endpoints return 200, response shapes verified. See TASK-0003.

### 10. AI Review

- Not started — pending formal review.

### 11. Code Review

- Not started — pending formal review.

### 12. Testing

- Partial (2026-07-15). HTTP-level smoke test done. UI-level browser test pending (Docker isolation).

### 13. QA

- Not started — pending formal review.

### 14. Potential Bug Review

- Not started — pending formal review.

### 15. Edge Case Review

- Not started — pending formal review.

### 16. Negative Scenario Review

- Not started — pending formal review.

### 17. Security Review

- Not started — pending formal review.

### 18. Performance Review

- Not started — pending formal review.

### 19. Compatibility Review

- Not started — pending formal review.

### 20. User Testing

- Not started — pending formal review.

### 21. User Feedback

- Not started — pending formal review.

### 22. Revision

- Not started — pending formal review.

### 23. Deployment

- Not started — pending formal review.

### 24. Monitoring

- Not started — pending formal review.

### 25. Post Implementation Review

- Not started — pending formal review.

### 26. Lessons Learned

- Not started — pending formal review.

### 27. Continuous Improvement / Archive

- Not started — pending formal review.

## 2. Requirement & Acceptance Criteria
### Functional Requirements
- Implement only the capability described in the Summary Block.
- Preserve structural-first, no-AI fallback, source-security, and responsive/accessibility invariants where applicable.

### Acceptance Criteria
- [ ] File expansion lists parser-backed functions only.
- [ ] Nested and duplicate simple names use stable qualified IDs.
- [ ] Unsupported syntax produces diagnostics, not invented functions.

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

- Expandable file and function hierarchy may violate its contract if dependent structural IDs, state, or fallback behavior is incomplete.

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
- [x] `git diff --check` passes.
- [ ] Failure fallback is exercised.

### Review Checklist

- [x] Self Review
- [ ] AI Review
- [ ] Code Review
- [ ] Security Review
- [ ] Performance Review
- [ ] Compatibility Review

### Acceptance Checklist

- [ ] File expansion lists parser-backed functions only.
- [ ] Nested and duplicate simple names use stable qualified IDs.
- [ ] Unsupported syntax produces diagnostics, not invented functions.

### User Testing Result

- Not started — planning stage.

### Post Implementation Review

- Not started — complete after deployment and monitoring evidence.

### Lessons Learned

- Not started — record observed learning; do not invent outcomes.

### Future Improvement

- Defer only with a linked backlog/entity and an explicit reason.

## 7. Closing
- Status: `review`. Implementation done (TASK-0003), self-review passed, formal review pending.
