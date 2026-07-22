"""Flow-worthiness classifier probe — spike-flow-classification.md evidence.

Walks a tree, classifies each parsed function per taxonomy, and reports:
  - per-category counts
  - control metric = does the current graps flow builder emit any flow? (>=1 call,
    >=1 branch marker, or >=1 route -> Flow tab shown today; else "no flow step found")
  - experiment metric = does the proposed taxonomy route this function to Flow?
  - delta = functions that change hands under the new rule

Run: python probe_classifier.py <path>
"""
from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from graps.scanner.ast_parser import safe_parse
from graps.scanner.ids import to_posix_rel


@dataclass
class Classification:
    category: str          # taxonomy row 1-10 short name
    flow_worthy: bool      # experiment: should Flow tab render?
    control_has_flow: bool  # current graps behavior: any flow emitted today?
    reason: str            # one-line structural justification


BRANCH_KINDS = {"if", "for", "while", "try", "except"}


def classify(func, source_text: str) -> Classification:
    n_calls = len(func.calls)
    branch_kinds = {b.kind for b in func.branches}
    has_control = bool(branch_kinds & BRANCH_KINDS)   # if/for/while/try/except
    has_return = "return" in branch_kinds
    has_route = bool(func.routes)
    body = source_text.strip()

    # ponytail: stub detection by body text — parser doesn't expose body AST here.
    # Upgrade path: extend ParsedFunction with is_stub flag (parser-level).
    STUB_MARKERS = ("pass", "...", "NotImplementedError", "TODO", "raise NotImplementedError")
    is_stub = any(s in body for s in STUB_MARKERS) and n_calls == 0 and not has_control

    # Category 10: empty/stub
    if is_stub:
        return Classification("10_stub", False, has_route or has_control or n_calls > 0,
                              "empty body / pass / NotImplementedError")

    # Category 1+2: pure trivial or data definition (no calls, no control flow)
    if n_calls == 0 and not has_control and not has_route:
        return Classification("1or2_trivial", False, False,
                              "no calls, no branches, no routes")

    # Category 3: delegator — exactly one call, no control flow, single return
    if n_calls == 1 and not has_control and not has_route and has_return:
        return Classification("3_delegator", False, True,
                              "single call returned directly (taxonomy decision: trivial)")

    # Category 4: linear sequence — >=2 calls, no control branch
    if n_calls >= 2 and not has_control and not has_route:
        return Classification("4_linear", True, True,
                              ">=2 sequential calls, no branch")

    # Category 5: branching logic
    if "if" in branch_kinds:
        return Classification("5_branch", True, True, "if/elif/else")

    # Category 6: loop
    if "for" in branch_kinds or "while" in branch_kinds:
        return Classification("6_loop", True, True, "for/while")

    # Category 8: error handling
    if "try" in branch_kinds or "except" in branch_kinds:
        return Classification("8_error", True, True, "try/except")

    # Category 7: unresolved call (has calls but none would resolve — needs edges
    # to know; proxy here as "has calls, no control, no routes, and >=1 call
    # but not category 4 because n_calls<2"). Treat as partial.
    if n_calls >= 1 and not has_control and not has_route:
        return Classification("7_unresolved_partial", True, True,
                              "single unresolved call (partial — show what's known)")

    # Fallback: routes, mixed — Flow-worthy
    return Classification("misc_flow", True, True, "routes or mixed markers")


def scan(root: Path) -> list[tuple[Classification, str, str]]:
    rows: list[tuple[Classification, str, str]] = []
    files = sorted(root.rglob("*.py"))
    for p in files:
        try:
            r = safe_parse(p)
        except Exception:
            continue
        if not r.id:
            r.id = to_posix_rel(p, root)
        for f in r.functions:
            try:
                src = p.read_text(errors="replace")
                body = src.splitlines()[f.line_start - 1: f.line_end] if f.line_end else []
                body_text = "\n".join(body)
            except Exception:
                body_text = ""
            cls = classify(f, body_text)
            rows.append((cls, r.id, f.qualified_name))
    return rows


def report(rows: list[tuple[Classification, str, str]], label: str) -> None:
    print(f"\n===== {label} =====")
    print(f"total functions: {len(rows)}")

    cat = Counter(r[0].category for r in rows)
    print("\ncategory counts (experiment taxonomy):")
    for k in sorted(cat):
        print(f"  {k:24s} {cat[k]:4d}  ({cat[k] / len(rows) * 100:5.1f}%)")

    control = sum(1 for r in rows if r[0].control_has_flow)
    exper = sum(1 for r in rows if r[0].flow_worthy)
    pct_c = control / len(rows) * 100
    pct_e = exper / len(rows) * 100
    print(f"\ncontrol (today):    Flow tab on {control}/{len(rows)} = {pct_c:.1f}%")
    print(f"experiment (prop):  Flow tab on {exper}/{len(rows)} = {pct_e:.1f}%")
    delta = control - exper
    print(f"delta:              {delta:+d} functions routed to Source instead of Flow")

    moved = [(c, fid, qn) for c, fid, qn in rows if c.control_has_flow != c.flow_worthy]
    print(f"\nfunctions whose tab changes under experiment: {len(moved)}")
    for c, fid, qn in moved[:20]:
        sign = "Flow->Source" if c.control_has_flow else "Source->Flow"
        print(f"  [{sign}] {c.category:22s} {fid}::{qn}")
    if len(moved) > 20:
        print(f"  ... +{len(moved) - 20} more")


if __name__ == "__main__":
    root = Path(sys.argv[1])
    rows = scan(root)
    report(rows, root.name)
