# API and Security Contracts

> **Summary Block:** Additive API behavior and invariants for safe scan, graph, source, module, flow, settings, and AI interaction.

| Endpoint | Contract |
|---|---|
| `GET /api/graph` | Versioned structural graph; enrichment status remains separate. |
| `GET /api/source?file=&fn=` | Secure relative source/function lookup; no absolute path. Credential files blocked (404). |
| `GET /api/modules/{module_id}` | Structural module plus optional validated overlay/status. |
| `GET /api/flows/{flow_id}` | Structural flow, diagnostics, optional label mapping. |
| `GET /api/scan/status` | State, graph hash, affected modules, diagnostics, AI state. |
| `POST /api/scan` | Validated default/full/no-ai mode; structural success despite AI failure. |
| `GET/PUT /api/settings` | Safe defaults and whitelisted project settings only. |
| `POST /api/ai/chat` | Existing origin/security controls and bounded source context. |

## Error semantics
Unknown path/module/flow is 400/404 without stack details. Invalid settings is 422. Parser errors become diagnostics if a graph can still be produced. AI failure never fails structural graph/source/flow.

## Security invariants
Resolve source paths under scan root and reject escape. Never serialize absolute host paths. Credential files remain excluded from AI context **and** blocked at `/api/source` (404). Mutating requests retain loopback/origin/host protections. No source write/edit endpoint is in scope.
