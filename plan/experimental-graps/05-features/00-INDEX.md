# Feature Index

> **Summary Block:** 20 approved capabilities, one entity per capability. IDs and dependencies are authoritative here and in entity metadata; execution details belong to phase tasks.

| ID | Feature | Status | Depends on |
|---|---|---|---|
| FEAT-0001 | [Three-panel application shell](feature-0001-three-panel-application-shell.md) | implemented | — |
| FEAT-0002 | [dir-panel explorer](feature-0002-dir-panel-explorer.md) | implemented | FEAT-0001, FEAT-0008 |
| FEAT-0003 | [workspace primary area](feature-0003-workspace-area.md) | implemented | FEAT-0001 |
| FEAT-0004 | [ai-panel with input bar](feature-0004-ai-panel-input.md) | implemented | FEAT-0001, FEAT-0014, FEAT-0019 |
| FEAT-0005 | [Panel open and close split controls](feature-0005-panel-split-controls.md) | implemented | FEAT-0001 |
| FEAT-0006 | [Resizable left and right panels](feature-0006-resizable-side-panels.md) | implemented | FEAT-0001, FEAT-0005 |
| FEAT-0007 | [Responsive panel layout](feature-0007-responsive-panel-layout.md) | implemented | FEAT-0001, FEAT-0005, FEAT-0006 |
| FEAT-0008 | [Folder package and module tree](feature-0008-structural-tree.md) | implemented | FEAT-0016, FEAT-0017, FEAT-0018 |
| FEAT-0009 | [Expandable file and function hierarchy](feature-0009-file-function-hierarchy.md) | implemented | FEAT-0008, FEAT-0017 |
| FEAT-0010 | [Source-code tabs](feature-0010-source-code-tabs.md) | implemented | FEAT-0003, FEAT-0009, FEAT-0017 |
| FEAT-0011 | [Function flow tabs](feature-0011-function-flow-tabs.md) | implemented | FEAT-0003, FEAT-0009, FEAT-0019 |
| FEAT-0012 | [Module overview tabs](feature-0012-module-overview-tabs.md) | implemented | FEAT-0003, FEAT-0008, FEAT-0018 |
| FEAT-0013 | [VS Code-like tab lifecycle](feature-0013-vscode-tab-lifecycle.md) | implemented | FEAT-0003, FEAT-0010, FEAT-0011, FEAT-0012 |
| FEAT-0014 | [AI Enrichment settings](feature-0014-ai-enrichment-settings.md) | implemented | FEAT-0019, FEAT-0020 |
| FEAT-0015 | [Manual scan command](feature-0015-manual-scan-command.md) | implemented | FEAT-0004, FEAT-0016, FEAT-0020 |
| FEAT-0016 | [Automatic structural project scan](feature-0016-automatic-structural-scan.md) | planning | — |
| FEAT-0017 | [Extended structural knowledge graph](feature-0017-extended-knowledge-graph.md) | planning | FEAT-0016 |
| FEAT-0018 | [Structural module resolution](feature-0018-structural-module-resolution.md) | planning | FEAT-0017 |
| FEAT-0019 | [Hybrid structural and semantic flow engine](feature-0019-hybrid-flow-engine.md) | planning | FEAT-0017, FEAT-0018 |
| FEAT-0020 | [Project-local incremental storage and cache](feature-0020-project-local-storage-cache.md) | planning | FEAT-0016, FEAT-0017 |
