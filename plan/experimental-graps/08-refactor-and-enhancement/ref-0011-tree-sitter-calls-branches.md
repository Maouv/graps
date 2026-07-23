---
id: REF-0011
type: refactor
status: ready
owner: Maou
created: 2026-07-23
updated: 2026-07-23
depends_on: []
related: [REF-0012]
---

# REF-0011: Tree-sitter Adapter — Extract Calls + Branches for Non-Python

> **Summary Block:** Add generic AST walker to `tree_sitter_parser.py` so non-Python files (JS/TS/Go/Rust/Java/C#/PHP/Ruby) emit `calls` and `branches` — unblocking cross-language flow-worthiness taxonomy validation.

## 1. Background

Flow-worthiness taxonomy (spike validated 2026-07-22, 85.2% accuracy) works for Python only. `tree_sitter_parser.py` uses `process()` which returns `structure/imports/exports` but **no calls/branches**. All non-Python functions get empty `calls`/`branches` → taxonomy classifies everything as not-flow-worthy → silent regression (Source tab for functions that should have Flow).

**Evidence (2026-07-22):** `probe_classifier.py` on `tests/fixtures/{javascript,typescript,go,rust}/*` — 14 functions, **0 calls, 0 branches** across all.

## 2. Architecture Decision

**Hybrid approach:** keep `process()` for structure/imports/exports, add `get_parser()` for raw tree walking.

```
File → detect_language_from_path()
            │
            ▼
    ┌───────────────┐
    │  process()    │ ← structure, imports, exports (existing, keep)
    │  (language)   │
    └───────┬───────┘
            │ ProcessResult
            ▼
    ┌───────────────┐
    │ get_parser()  │ ← NEW: raw tree_sitter.Tree
    │  (language)   │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │ GenericWalker │ ← walks raw tree with node config
    │  + NodeConfig │
    └───────┬───────┘
            │
    ┌───────┴───────┐
    ▼               ▼
  calls         branches
```

**Why not `process()` for calls?** `ProcessResult` doesn't expose raw tree. Library gives `get_parser()` for manual parse.

**Why keep `process()`?** Structure extraction (functions, classes, imports, exports) is generic across 306 languages — no need to reimplement.

## 3. Node Type Configuration

### Default (works for JS/TS/Go/C/C++/Kotlin/Swift/Dart)

```python
DEFAULT_CALL_NODES = {"call_expression"}
DEFAULT_BRANCH_NODES = {
    "if_statement", "for_statement", "while_statement",
    "try_statement", "except_clause", "finally_clause",
}
```

### Overrides (grammar-specific node names)

```python
CALL_NODE_OVERRIDES = {
    "python": {"call"},
    "java": {"method_invocation"},
    "csharp": {"invocation_expression"},
    "php": {"function_call_expression"},
    "ruby": {"call"},
}

BRANCH_NODE_OVERRIDES = {
    "rust": {
        "if_expression", "match_expression", "for_expression",
        "loop_expression", "while_expression", "try_expression",
    },
    "ruby": {"if", "rescue", "while", "until", "for"},
    "go": {
        "if_statement", "for_statement", "select_statement",
        "type_switch_statement", "switch_statement",
    },
}
```

### Per-Language Call Name Extraction Rules

| Language | Call Node | Function Field Path | Example Output |
|---|---|---|---|
| JS/TS | `call_expression` | `function` → `identifier`/`member_expression` | `foo`, `console.log`, `obj.method` |
| Go | `call_expression` | `function` → `identifier`/`selector_expression` | `fmt.Println` |
| Rust | `call_expression` | `function` → `identifier`/`field_expression` | `foo`, `self.bar` |
| Java | `method_invocation` | `name` + optional `object` | `method`, `obj.method` |
| C# | `invocation_expression` | `function` | `foo`, `obj.Method` |

### Branch Kind Mapping

| Tree-sitter Node | `ParsedBranch.kind` |
|---|---|
| `if_statement` / `if_expression` | `if` |
| `for_statement` / `for_expression` | `for` |
| `while_statement` / `while_expression` | `while` |
| `try_statement` / `try_expression` | `try` |
| `except_clause` / `rescue` | `except` |
| `finally_clause` | `finally` |
| `match_expression` / `switch_statement` | `match`/`switch` |

## 4. Implementation Slices

### Slice 1: Walker Core + JS/TS

**Files:** `graps/scanner/tree_sitter_parser.py`

- Add `_walk_tree(node, config)` — generic recursive walker
- Add `_extract_calls(tree, language)` — returns `list[ParsedCall]`
- Add `_extract_branches(tree, language)` — returns `list[ParsedBranch]`
- Wire into `parse_file()`: after `process()`, call `get_parser()` + walk
- Populate `ParsedFunction.calls` and `ParsedFunction.branches`

**Test fixtures:** `tests/fixtures/javascript/calls.js`, `tests/fixtures/typescript/calls.ts`

**Expected:** `calls.js` with `foo(); bar();` → 2 calls. `if (x) { ... }` → 1 branch.

### Slice 2: Go + Rust

**Files:** `graps/scanner/tree_sitter_parser.py`

- Add Go call extraction (`selector_expression` for `pkg.Func`)
- Add Rust call extraction (`field_expression` for `recv.Method`)
- Add Rust branch overrides (`if_expression`, `match_expression`, etc.)

**Test fixtures:** `tests/fixtures/go/calls.go`, `tests/fixtures/rust/calls.rs`

**Expected:** `fmt.Println("hello")` → 1 call. `if x > 0 { ... }` → 1 branch.

### Slice 3: Java/C#/PHP/Ruby Overrides

**Files:** `graps/scanner/tree_sitter_parser.py`

- Add override configs for Java (`method_invocation`), C# (`invocation_expression`), PHP (`function_call_expression`), Ruby (`call`)

**Test fixtures:** Minimal per language (1 file each)

### Slice 4: Route Detection (JS/TS Only)

**Files:** `graps/scanner/tree_sitter_parser.py`

- Detect route decorators: `@app.get("/path")`, `@router.post("/path")`
- Populate `ParsedFunction.routes` with `ParsedRoute(method, path, line)`

**Out of scope for Slice 4:** Go/Rust route detection (attributes/macros) — phase 2.

### Slice 5: Integration + Validation

**Files:** `probe_classifier.py` (if exists), or manual probe script

- Run probe on all fixture directories
- Verify non-zero calls/branches for fixtures that contain them
- Update `spike-flow-classification.md` with cross-language evidence

## 5. Data Contract

### Input

```python
# From get_parser(language).parse(source_bytes)
tree: tree_sitter.Tree
language: str  # e.g. "javascript", "go", "rust"
```

### Output

```python
# Populated on ParsedFunction
calls: list[ParsedCall]      # name, line
branches: list[ParsedBranch]  # kind, line
```

### Walker Pseudocode

```python
def _walk_tree(node, config, calls, branches):
    if node.type in config.call_nodes:
        name = _extract_call_name(node, config.language)
        line = node.start_point.row + 1
        calls.append(ParsedCall(name=name, line=line))

    if node.type in config.branch_nodes:
        kind = _map_branch_kind(node.type)
        line = node.start_point.row + 1
        branches.append(ParsedBranch(kind=kind, line=line))

    for child in node.children:
        _walk_tree(child, config, calls, branches)
```

## 6. Chained Call Collapse

**Decision:** Walker emits all calls (dumb). Classifier collapses (smart).

**Rationale:** Separation of concerns. Walker is extraction layer; classifier is interpretation layer. Existing classifier already handles same-line collapse via `len({c.line for c in calls})`.

**Example:**
```javascript
"-".join(name.split()).lower()
// Walker emits: 3 ParsedCall (join, split, lower) — all line 3
// Classifier collapses: 1 logical call
```

## 7. Function-to-Calls Association

**Problem:** Walker walks entire file tree. Calls/branches must be associated with the correct function.

**Solution:** Track function boundaries during walk. When entering `function_declaration`/`function_item`/`method_definition`, push function context. When exiting, pop.

```python
def _walk_tree(node, config, calls, branches, current_func=None):
    if _is_function_node(node, config.language):
        current_func = _extract_function_name(node)
        # ... create new ParsedFunction, or find existing from structure

    if node.type in config.call_nodes and current_func:
        # ... associate call with current_func

    for child in node.children:
        _walk_tree(child, config, calls, branches, current_func)
```

**Alternative (simpler):** Post-process — walk entire tree, collect all calls with line numbers, then associate by line range using `ProcessResult.structure` spans.

**Decision:** Post-process approach. Simpler, no context tracking. Structure already has function spans.

## 8. File Changes

```
graps/scanner/
├── tree_sitter_parser.py    # ADD: _walk_tree, _extract_calls, _extract_branches
│                            # MODIFY: parse_file() — add raw tree parse + walk
└── __init__.py              # NO CHANGE

tests/
├── fixtures/
│   ├── javascript/
│   │   ├── calls.js         # NEW: cat 4,5,6,8 coverage
│   │   └── branches.js      # NEW
│   ├── typescript/
│   │   ├── calls.ts         # NEW
│   │   └── branches.ts      # NEW
│   ├── go/
│   │   ├── calls.go         # NEW
│   │   └── branches.go      # NEW
│   ├── rust/
│   │   ├── calls.rs         # NEW
│   │   └── branches.rs      # NEW
│   ├── java/
│   │   └── calls.java       # NEW (minimal)
│   ├── csharp/
│   │   └── calls.cs         # NEW (minimal)
│   ├── php/
│   │   └── calls.php        # NEW (minimal)
│   └── ruby/
│       └── calls.rb         # NEW (minimal)
└── test_tree_sitter_parser.py  # ADD: TestCalls, TestBranches, TestRoutes
```

## 9. Validation Gates

| Gate | Command | Expected |
|---|---|---|
| Unit tests | `pytest tests/test_tree_sitter_parser.py -q` | All pass |
| Self-check | `python -m graps.scanner.tree_sitter_parser` | OK |
| Lint | `ruff check graps/scanner/tree_sitter_parser.py` | Clean |
| Type check | `mypy graps/scanner/tree_sitter_parser.py` | Clean |
| Probe JS | `python probe_classifier.py tests/fixtures/javascript/` | Non-zero calls |
| Probe TS | `python probe_classifier.py tests/fixtures/typescript/` | Non-zero calls |
| Probe Go | `python probe_classifier.py tests/fixtures/go/` | Non-zero calls |
| Probe Rust | `python probe_classifier.py tests/fixtures/rust/` | Non-zero calls |

## 10. Out of Scope

| Item | Reason |
|---|---|
| Vue/Svelte 2-pass | REF-0012 — needs script extraction first |
| SQL taxonomy | No control flow — separate spike needed |
| Async visual (cat 9) | Needs own spike on representation |
| Go/Rust route detection | Phase 2 — JS/TS only for now |
| Tree-sitter grammar fixes | Library upstream — not our code |

## 11. Rollback Plan

1. Revert `tree_sitter_parser.py` to pre-REF-0011 state
2. Remove new fixture files
3. Remove new test classes
4. Taxonomy falls back to Python-only behavior (no regression — was already the case)

---

## Mandatory Review Section

### Potential Bugs

| Bug | Mitigation |
|---|---|
| Grammar download fails mid-scan | `get_parser()` raises → catch → log warning → return None (file becomes unsupported node) |
| Walker infinite recursion on malformed tree | Depth limit (e.g. 100) — tree-sitter trees are finite, but guard against cycles |
| Call name extraction returns empty | Filter out empty names — don't emit `ParsedCall(name="")` |
| Function boundary mismatch (structure vs raw tree) | Post-process association by line range — structure spans are authoritative |

### Known Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Per-language grammar differences break walker | High | Override config per language; test fixtures per language |
| Performance: 2x parsing (process + get_parser) | Medium | Measure; if slow, cache raw tree or switch entirely to manual parse |
| Tree-sitter node names change across grammar versions | Low | Pin `tree-sitter-language-pack` version; node names are stable |

### Edge Cases

| Case | Handling |
|---|---|
| Empty function body | No calls/branches emitted — correct |
| Nested functions | Post-process associates calls to innermost function by line range |
| Arrow functions (JS/TS) | `lexical_declaration` + `arrow_function` — structure handles, walker sees calls inside |
| Macros (Rust) | `macro_invocation` ≠ `call_expression` — not emitted as call (correct — macros expand at compile time) |
| Generic functions (Rust/Java/C#) | Type parameters don't affect call extraction — name only |

### Failure Cases

| Failure | Behavior |
|---|---|
| `get_parser()` raises (grammar not found) | Log warning, return None — file unsupported |
| `parse()` returns None (syntax error) | Log warning, return None — file unparsable |
| Walker encounters unknown node type | Skip silently — config-driven, no crash |

### Negative Test Cases

| Test | Expected |
|---|---|
| File with 0 calls | `calls == []` |
| File with 0 branches | `branches == []` |
| Unsupported language | `parse_file()` returns None |
| Oversized file (>1MB) | Skip with warning |

### Regression Risk

| Area | Risk | Mitigation |
|---|---|---|
| Python parsing | None — ASTParser unchanged | Python tests still pass |
| Existing non-Python structure | Low — `process()` unchanged | Structure tests still pass |
| Graph builder | None — consumes `calls`/`branches` uniformly | Graph tests still pass |

### Rollback Plan

See §11 above.

### Validation Checklist

- [ ] Slice 1: JS/TS calls + branches extracted
- [ ] Slice 2: Go/Rust calls + branches extracted
- [ ] Slice 3: Java/C#/PHP/Ruby overrides working
- [ ] Slice 4: JS/TS route detection working
- [ ] Slice 5: Probe validation on all fixtures
- [ ] All unit tests pass
- [ ] ruff + mypy clean
- [ ] Self-check OK

### Review Checklist

- [ ] Code review: walker logic correct
- [ ] Security review: no new attack surface (local file parsing only)
- [ ] Performance review: 2x parsing acceptable for MVP
- [ ] Compatibility review: Python-only behavior unchanged

### Acceptance Checklist

- [ ] `ParsedFunction.calls` populated for JS/TS/Go/Rust fixtures
- [ ] `ParsedFunction.branches` populated for JS/TS/Go/Rust fixtures
- [ ] `ParsedFunction.routes` populated for JS/TS fixtures with route decorators
- [ ] `probe_classifier.py` shows non-zero calls/branches for non-Python fixtures
- [ ] No regression on Python parsing
- [ ] No regression on existing structure extraction

### User Testing Result

*To be filled after implementation*

### Post Implementation Review

*To be filled after implementation*

### Lessons Learned

*To be filled after implementation*

### Future Improvement

- Vue/Svelte 2-pass extraction (REF-0012)
- Go/Rust route detection
- SQL taxonomy spike
- Async/callback visual representation (cat 9)
- Performance optimization: single-pass parse (drop `process()`, manual structure extraction)
