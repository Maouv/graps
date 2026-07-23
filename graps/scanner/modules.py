"""Structural module resolution (FEAT-0018, architecture §Module boundary precedence).

A module is the canonical language boundary relative to scan root. For Python
the boundary is the package, then folder: each source file maps to exactly one
deterministic module (its dotted module identity). Boundaries that fall back to
a folder (no ``__init__.py``) carry explicit ``namespace_fallback`` confidence;
regular packages carry ``regular_package``. AI may rename/summarize/merge-view
existing module IDs but cannot define boundaries (DEC-0003) — that is enforced
in the semantic validator (Phase 2); here structure is the only truth.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from graps.scanner import ParsedFile
from graps.scanner.ids import class_id, function_id, python_module_id, to_posix_rel
from graps.scanner.resolver import resolve_import


def _confidence_for(rel_posix: str, root: Path) -> str:
    """Package confidence for the file at ``rel_posix`` under ``root``.

    ``regular_package``  : every ancestor dir up to root has ``__init__.py``.
    ``namespace_fallback``: at least one ancestor dir lacks ``__init__.py``.
    ``top_level``        : the file lives directly in the scan root.
    """
    parts = [seg for seg in rel_posix.split("/") if seg]
    if len(parts) <= 1:
        return "top_level"
    # Ancestor dirs = all dirs above the file (exclude the file itself).
    ancestors = parts[:-1]
    cur = root
    for seg in ancestors:
        cur = cur / seg
        if not (cur / "__init__.py").is_file():
            return "namespace_fallback"
    return "regular_package"


def resolve_modules(results: list[ParsedFile], root: Path) -> list[dict[str, Any]]:
    """Build deterministic module nodes from parsed files.

    One module node per source file (its dotted module identity). Each module
    carries its file_id, member function/class IDs, resolved module
    dependencies, and boundary confidence. Output is sorted by module id.
    """
    modules: dict[str, dict[str, Any]] = {}

    for result in results:
        rel = result.id or to_posix_rel(result.path, root)
        if not rel:
            continue
        mid = python_module_id(rel) or "<root>"
        confidence = _confidence_for(rel, root)

        func_ids = [function_id(rel, f.qualified_name) for f in result.functions]
        cls_ids = [class_id(rel, c.get("qualified_name", c.get("name", "")))
                   for c in result.classes]

        dep_ids: list[str] = []
        for imp in result.imports:
            if imp.is_dynamic or imp.is_star:
                continue
            target = resolve_import(imp, result.path, root)
            if target is None:
                continue
            dep_mid = python_module_id(target.as_posix())
            if dep_mid and dep_mid not in dep_ids and dep_mid != mid:
                dep_ids.append(dep_mid)

        modules[mid] = {
            "id": mid,
            "type": "module",
            "language": result.language,
            "file_id": rel,
            "confidence": confidence,
            "member_function_ids": sorted(func_ids),
            "member_class_ids": sorted(cls_ids),
            "dependency_ids": sorted(dep_ids),
        }

    return sorted(modules.values(), key=lambda m: m["id"])


if __name__ == "__main__":
    import tempfile

    from graps.scanner.ast_parser import safe_parse

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pkg = root / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "sub.py").write_text("def helper():\n    return 1\n")
        (pkg / "main.py").write_text("from .sub import helper\n\ndef run():\n    return helper()\n")
        ns = root / "nsdir"
        ns.mkdir()
        (ns / "loose.py").write_text("x = 1\n")

        results = [safe_parse(p) for p in sorted(root.rglob("*.py"))]
        # safe_parse stores path but not id relative to root; set it.
        for r in results:
            r.id = to_posix_rel(r.path, root)

        mods = resolve_modules(results, root)
        by_id = {m["id"]: m for m in mods}
        assert "pkg.sub" in by_id and "pkg.main" in by_id and "nsdir.loose" in by_id, \
            [m["id"] for m in mods]
        assert by_id["pkg.sub"]["confidence"] == "regular_package"
        assert by_id["pkg.main"]["confidence"] == "regular_package"
        assert by_id["nsdir.loose"]["confidence"] == "namespace_fallback"
        assert "pkg.sub" in by_id["pkg.main"]["dependency_ids"], by_id["pkg.main"]
        assert "pkg/main.py::main.run" in by_id["pkg.main"]["member_function_ids"]
        # determinism: same input -> same output order
        assert [m["id"] for m in mods] == sorted(by_id)

    print("modules self-check ok")
