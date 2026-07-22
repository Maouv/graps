"""Stratified sampler for flow-worthiness labeling.

Picks N functions per in-scope Python category from the scanned pool, emits
file + qualified_name + parser-category + source body (first 8 lines) for
manual daily-user labeling.

Run: python probe_sampler.py <root> <per_category>
"""
from __future__ import annotations

import random
import sys
from collections import defaultdict
from pathlib import Path

from graps.scanner.ast_parser import safe_parse
from graps.scanner.ids import to_posix_rel

# reuse classify() from the probe
from probe_classifier import classify


def scan(root: Path):
    pool: list[tuple] = []  # (Classification, file_id, qual_name, body_text)
    for p in sorted(root.rglob("*.py")):
        try:
            r = safe_parse(p)
        except Exception:
            continue
        if not r.id:
            r.id = to_posix_rel(p, root)
        try:
            src_lines = p.read_text(errors="replace").splitlines()
        except Exception:
            continue
        for f in r.functions:
            body = "\n".join(src_lines[f.line_start - 1: f.line_end]) if f.line_end else ""
            cls = classify(f, body)
            pool.append((cls, r.id, f.qualified_name, body, f))
    return pool


def stratified_sample(pool, per_cat: int, seed: int = 42):
    by_cat: dict[str, list] = defaultdict(list)
    for row in pool:
        by_cat[row[0].category].append(row)
    rng = random.Random(seed)
    sample = []
    for cat in sorted(by_cat):
        rows = by_cat[cat]
        rng.shuffle(rows)
        sample.extend(rows[:per_cat])
    return sample


def emit(sample):
    for i, (cls, fid, qn, body, f) in enumerate(sample, 1):
        hdr = (
            f"--- [{i}] cat={cls.category}  "
            f"control_has_flow={cls.control_has_flow}  "
            f"flow_worthy={cls.flow_worthy}  reason={cls.reason}"
        )
        print(f"\n{hdr}")
        print(f"    {fid}::{qn}")
        for ln in body.splitlines():
            print(f"    | {ln}")


if __name__ == "__main__":
    roots = [Path(p) for p in sys.argv[1:-1]]
    per_cat = int(sys.argv[-1])
    pool = []
    for root in roots:
        pool.extend(scan(root))
    sample = stratified_sample(pool, per_cat)
    print(
        f"# stratified sample: {len(sample)} functions, "
        f"{per_cat} per category, pool={len(pool)} across {len(roots)} roots"
    )
    emit(sample)
