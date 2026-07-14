---
id: TASK-0003
type: task
status: backlog
owner: Maou
created: 2026-07-14
updated: 2026-07-14
depends_on: [TASK-0002]
related: [FEAT-0001, FEAT-0002, FEAT-0003, FEAT-0004, FEAT-0005, FEAT-0006, FEAT-0007, FEAT-0008, FEAT-0009, FEAT-0010, FEAT-0011, FEAT-0012, FEAT-0013, FEAT-0014, FEAT-0015]
---

# Phase 3 — Application UI

> **Summary Block:** Build the required three-panel explorer and exact interaction contracts over stable graph IDs. Phase gate: With AI disabled, file/function/module clicks produce the exact required tabs on desktop and mobile.

## 1. Lifecycle

### 1. Idea

- Captured in project discovery; feature-specific validation remains open.

### 2. Research

- Captured in project discovery; feature-specific validation remains open.

### 3. Analysis

- Captured in project discovery; feature-specific validation remains open.

### 4. Requirement

- Planning in progress; use linked project SSoT.

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

## 2. Definition of Ready
- [ ] Related feature requirements and acceptance remain approved.
- [x] Dependency IDs are identified.
- [x] Owner/accountability is documented.
- [ ] Implementation start is explicitly authorized.

## 3. Description of Work
Build the required three-panel explorer and exact interaction contracts over stable graph IDs.

## 4. Execution Checklist
- [ ] Implement shell, split controls, resizing, and panel persistence.
- [ ] Implement explorer tree and source/flow/module tabs.
- [ ] Implement minimal AI panel and scan command.
- [ ] Vendor only consumed Codicons and verify responsive/accessibility behavior.

## 5. Definition of Done
- [ ] Execution checklist is complete with real test output.
- [ ] Related feature acceptance has evidence.
- [ ] Mandatory Review Section is filled from observed results.
- [ ] Phase gate is met: With AI disabled, file/function/module clicks produce the exact required tabs on desktop and mobile.
- [ ] Metadata status is updated only after review.

## 6. Mandatory Review Section

### Potential Bugs
- Phase 3 — Application UI can produce cross-layer regressions if phase boundaries or dependency gates are skipped.

### Known Risks
- Structural state, API contracts, and UI state may diverge if stable IDs or cache hashes are not enforced.

### Edge Cases
- Empty data, malformed source, stale IDs, unavailable AI, and narrow mobile viewport.

### Failure Cases
- Failure must preserve deterministic fallback or fail without corrupting persisted state.

### Negative Test Cases
- Reject unknown IDs, invalid state, traversal-like inputs, and semantic claims outside the structural allowlist.

### Regression Risk
- Existing scanner, resolver, API, CLI, cache, frontend packaging, and source-security behavior may regress.

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
- [ ] With AI disabled, file/function/module clicks produce the exact required tabs on desktop and mobile.

### User Testing Result
- Not started — planning stage.

### Post Implementation Review
- Not started — complete after deployment and monitoring evidence.

### Lessons Learned
- Not started — record observed learning; do not invent outcomes.

### Future Improvement
- Defer only with a linked backlog/entity and an explicit reason.

## 7. Closing
- Status remains `backlog`; no implementation outcome is claimed.
