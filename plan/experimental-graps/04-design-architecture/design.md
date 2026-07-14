# Product and Interaction Design

> **Summary Block:** SSoT for canonical layout, explorer clicks, workspace tabs, AI panel behavior, responsive presentation, icon policy, and accessibility.

## Canonical shell
Desktop order is exactly `dir-panel | workspace | ai-panel`. Reserved empty regions stay empty. Closing either side expands workspace; reopening restores a valid previous width.

## Explorer click contract
1. Folder/package: expand or collapse only; open no tab.
2. File: expand functions and open/deduplicate source tab.
3. Module: expand contents and open/deduplicate module overview.
4. Function: open/deduplicate flow tab, not source.
5. Flow/route: open the relevant flow tab; flow details may link to source.

## Workspace tabs
- **Source:** secure source text, language/range, flow links.
- **Flow:** structural nodes/edges, confidence, branch metadata, optional validated labels, source links.
- **Module:** structural boundary/members/routes/dependencies/diagnostics plus optional semantic metadata.
- Single click may reuse a safe preview; double-click/pin persists. Tabs deduplicate by stable ID, close individually, overflow safely, and restore only valid entities.

## ai-panel
Only status plus input bar are in first scope. It accepts chat and `/scan`, `/scan --full`, `/scan --no-ai`. AI unavailable/failure is passive and never blocks structural use.

## Responsive model
- Desktop: persistent resizable side panels.
- Tablet: toggleable drawers/overlays over full workspace.
- Phone: full-height drawer/bottom-sheet-like overlay; one side panel at a time.
- No required drag-and-drop. All actions are tap accessible with at least 44px targets.

## Visual system
- Workspace `#181818`; side panels `#1F1F1F`; text/stroke `#E4E4E4`; input surface `#404040`.
- Radius scale: 4/6/8/12/16px and full pill.
- Vendor only consumed Microsoft VS Code Codicons SVGs under `graps/public/icon/` with license attribution.
- Retain custom right split selected/unselected SVGs; mirror for the left control in CSS.
- No Font Awesome, Lucide, Material, emoji controls, CDN icons, or mixed icon system.

## Accessibility
Tree/list/tab semantics, `aria-expanded`, selected state, logical focus, visible focus, non-color confidence indicators, sufficient contrast, reduced-motion support, and keyboard operation are mandatory.
