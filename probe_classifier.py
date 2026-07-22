"""Flow-worthiness classifier probe — spike-flow-classification.md evidence.

Walks a tree, classifies each parsed function per taxonomy (production
:class:`graps.scanner.flows.classify_flow_worthiness`), and reports:
  - per-category counts
  - control metric = does the current graps flow builder emit any flow? (>=1 call,
    >=1 branch marker, or >=1 route -> Flow tab shown today; else "no flow step found")
  - experiment metric = does the taxonomy route this function to Flow?
  - delta = functions that change hands under the new rule

Run: python probe_classifier.py <path>
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from graps.scanner.ast_parser import safe_parse
from graps.scanner.flows import Classification, classify_flow_worthiness
from graps.scanner.ids import to_posix_rel


def control_has_flow(func) -> bool:
    """Current graps behavior: any flow emitted today (call/branch/route)."""
    return bool(func.calls) or bool(func.branches) or bool(func.routes)


def scan(root: Path) -> list[tuple[Classification, bool, str, str]]:
    rows: list[tuple[Classification, bool, str, str]] = []
    for p in sorted(root.rglob("*.py")):
        try:
            r = safe_parse(p)
        except Exception:
            continue
        if not r.id:
            r.id = to_posix_rel(p, root)
        try:
            src_lines = p.read_text(errors="replace").splitlines()
        except OSError:
            src_lines = []
        for f in r.functions:
            ls = f.line_start or f.lineno
            le = f.line_end or ls
            body = "\n".join(src_lines[ls - 1:le]) if src_lines and ls > 0 else ""
            cls = classify_flow_worthiness(f, body)
            rows.append((cls, control_has_flow(f), r.id, f.qualified_name))
    return rows


def report(rows: list[tuple[Classification, bool, str, str]], label: str) -> None:
    total = len(rows)
    print(f"\n===== {label} =====")
    print(f"total functions: {total}")

    cat = Counter(r[0].category for r in rows)
    print("\ncategory counts (experiment taxonomy):")
    for k in sorted(cat):
        print(f"  {k:24s} {cat[k]:4d}  ({cat[k] / total * 100:5.1f}%)")

    control = sum(1 for r in rows if r[1])
    exper = sum(1 for r in rows if r[0].flow_worthy)
    print(f"\ncontrol (today):    Flow tab on {control}/{total} = {control / total * 100:.1f}%")
    print(f"experiment (prop):  Flow tab on {exper}/{total} = {exper / total * 100:.1f}%")
    print(f"delta:              {control - exper:+d} functions routed to Source instead of Flow")

    moved = [(c, ctrl, fid, qn) for c, ctrl, fid, qn in rows if ctrl != c.flow_worthy]
    print(f"\nfunctions whose tab changes under experiment: {len(moved)}")
    for c, ctrl, fid, qn in moved[:20]:
        sign = "Flow->Source" if ctrl else "Source->Flow"
        print(f"  [{sign}] {c.category:22s} {fid}::{qn}")
    if len(moved) > 20:
        print(f"  ... +{len(moved) - 20} more")


if __name__ == "__main__":
    root = Path(sys.argv[1])
    rows = scan(root)
    report(rows, root.name)
