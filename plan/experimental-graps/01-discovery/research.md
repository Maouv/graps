# Research

> **Summary Block:** Research conclusions derived from the current Graps scanner, resolver, server, AI seams, and UX constraints. Detailed implementation contracts live in requirement, design, and architecture SSoTs.

## Findings
- Existing AST/tree-sitter parser seams can retain more source facts instead of replacing the scanner.
- Existing graph builder and resolver are the deterministic extension points.
- Existing server source/origin/path protections must remain invariants.
- AI provider/cache seams can host optional enrichment without scanner coupling.
- Static analysis cannot guarantee complete runtime behavior for dynamic Python/JavaScript.
- Mobile use requires drawers/overlays, 44px targets, and a small bundle.

## Evidence boundary
No dependency or implementation experiment has been authorized. Claims remain design hypotheses until tested against fixtures and the current codebase.
