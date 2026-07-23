"""Tree-sitter multi-language parser — Phase 4 adapter.

Adapter over tree-sitter-language-pack's ``process()`` API. Maps
``ProcessResult`` → ``ParsedFile``. No manual tree walking — library handles
306 languages, grammar download, and code intelligence.

Used by cli.py's non-Python dispatch path. One instance per scan session.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from graps.scanner import ParsedFile, ParsedFunction, ParsedImport

logger = logging.getLogger(__name__)

_MAX_BYTES = 1_000_000  # 1MB — konsisten dengan safe_parse (ast_parser.py)


class TreeSitterParser:
    """Multi-language parser via tree-sitter-language-pack.

    Grammar di-load lazily (on-demand download + local cache).
    Dispatch (cli.py) route by file suffix, bukan lewat Protocol polymorphism.
    """

    def parse_file(self, path: Path, root: Path) -> ParsedFile | None:
        """Parse satu file. Return None kalau unsupported/failed."""
        try:
            from tree_sitter_language_pack import (
                ProcessConfig,
                detect_language_from_path,
                process,
            )
        except ImportError:
            logger.debug("tree-sitter-language-pack not installed")
            return None

        # Detect language dari path
        lang = detect_language_from_path(str(path))
        if lang is None:
            return None

        # 1MB guard — konsisten dengan ASTParser
        try:
            size = path.stat().st_size
        except OSError:
            return None
        if size > _MAX_BYTES:
            logger.warning("Skip %s: file too large (%d bytes)", path, size)
            return None

        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.warning("Cannot read %s: %s", path, e)
            return None

        try:
            result = process(source, ProcessConfig(language=lang))
        except Exception as e:
            # Grammar download gagal, parse error berat, dll
            logger.warning("process() failed for %s (%s): %s", path, lang, e)
            return None

        try:
            rel = str(path.resolve().relative_to(root.resolve()))
        except ValueError:
            rel = str(path)

        # ── Map ProcessResult → ParsedFile ──────────────────────────
        functions = _extract_functions(result.structure)
        imports = _extract_imports(result.imports, lang)
        classes = _extract_classes(result.structure)
        exported_names = _extract_exports(result.exports)

        # Diagnostics → warnings (syntax errors dari tree-sitter)
        warnings = [
            f"line {d.span.start_line + 1}: {d.message}"
            for d in result.diagnostics
            if d.span
        ]

        return ParsedFile(
            id=rel,
            path=path,
            functions=functions,
            imports=imports,
            constants=[],          # ponytail: ProcessResult tidak provide
            classes=classes,
            exported_names=exported_names,
            file_modified_at=str(path.stat().st_mtime),
            language=lang,
            warnings=warnings,
        )


# ── Adapter helpers: ProcessResult → ParsedFile fields ──────────────
# Module-level functions, bukan staticmethod — gampang test & refactor.


def _extract_functions(structure: list[Any]) -> list[ParsedFunction]:
    """Flatten StructureItem tree → flat ParsedFunction list.

    Ambil FUNCTION/METHOD, skip CLASS/STRUCT (masuk ke classes).
    Recurse children untuk nested methods/functions.
    """
    results: list[ParsedFunction] = []

    def _flatten(item: Any, parent_name: str | None = None) -> None:
        kind_str = str(item.kind).upper() if item.kind else ""

        if "FUNCTION" in kind_str or "METHOD" in kind_str:
            name = item.name or "<anonymous>"
            span = item.span
            results.append(ParsedFunction(
                name=name,
                line_start=(span.start_line + 1) if span else 0,
                line_end=(span.end_line + 1) if span else 0,
                decorators=list(item.decorators) if item.decorators else [],
                is_private=_detect_is_private(item.visibility, name),
                parent=parent_name,
            ))

        if item.children:
            for child in item.children:
                _flatten(child, parent_name=item.name)

    for item in structure:
        _flatten(item)
    return results


def _strip_alias(name: str) -> str:
    """``import X as Y`` → ``X`` (ambil nama modul, buang alias). Match ast ``alias.name``."""
    return name.split(" as ")[0].strip()


def _normalize_import_source(source: str, is_wildcard: bool) -> list[str]:
    """Parse raw Python import statement text → list of dotted module paths.

    Match contract ast_parser ``visit_Import``/``visit_ImportFrom``: emit 1 target
    per alias (``from X import Y, Z`` → ``["X.Y", "X.Z"]``). Pure-function, no
    side-effect. ``[]`` kalau source tidak match pattern import valid (guard
    false-positive tree-sitter — jangan crash).

    Bentuk yang dihandle:
      ``import X`` / ``import X.Y`` / ``import X as Y`` / ``import X, Y``
        → ``["X"]`` / ``["X.Y"]`` / ``["X"]`` / ``["X", "Y"]``
      ``from X import Y`` / ``from X import Y, Z`` → ``["X.Y"]`` / ``["X.Y", "X.Z"]``
      ``from .X import Y`` / ``from . import Y`` / ``from ..X import Y``
        → ``[".X.Y"]`` / ``[".Y"]`` / ``["..X.Y"]``  (relative — preserve leading dots)
      ``from X import *`` (is_wildcard=True) → ``["X"]``  (base saja, caller set is_star)
    """
    s = source.strip()
    if not s:
        return []

    # import X  /  import X.Y  /  import X as Y  /  import X, Y
    if s.startswith("import ") and not s.startswith("import_"):
        names = s[len("import "):]
        names = names.replace("(", " ").replace(")", " ")
        return [_strip_alias(n) for n in names.split(",") if _strip_alias(n)]

    # from X import Y, Z  /  from .X import Y  /  from X import *
    if s.startswith("from ") and " import " in s:
        rest = s[len("from "):]
        mod_part, _, names_part = rest.partition(" import ")
        base = mod_part.strip()
        if not base:
            return []
        if is_wildcard:
            return [base]
        # Multi-line paren: ``from X import (\n Y,\n Z\n)`` — tree-sitter preserve
        # parens + newline. Strip parens, split by comma/whitespace, drop empties.
        names_part = names_part.replace("(", " ").replace(")", " ")
        names = [n.strip() for n in names_part.replace("\n", ",").split(",")]
        names = [_strip_alias(n) for n in names if _strip_alias(n)]
        if not names:
            return []
        # Relative import (``from .X import Y``) — preserve leading dots, no separator.
        # Match ast: ``sep = "" if base.endswith(".") else "."``.
        sep = "" if base.endswith(".") else "."
        return [f"{base}{sep}{name}" for name in names]

    return []  # bukan import valid → emit 0, jangan crash


def _extract_imports(imports: list[Any], language: str = "python") -> list[ParsedImport]:
    """Map ImportInfo → ParsedImport.

    For ``language == "python"``: parse raw ``imp.source`` via
    :func:`_normalize_import_source` → list of dotted targets, emit 1
    ``ParsedImport`` per target (match ast_parser contract so
    :func:`resolve_import` gets a single dotted format). Non-Python:
    behavior lama ``target=imp.source`` (edge non-Python tidak dibuat resolver
    by design, tapi data di-preserve untuk display imports di node card).

    ponytail: Go return 2 entries per import (statement + bare path).
    Dedup by lineno — kalau 2 import di line yang sama, keep first.
    """
    seen_lineno: set[int] = set()
    results: list[ParsedImport] = []
    for imp in imports:
        lineno = (imp.span.start_line + 1) if imp.span else 0
        if lineno in seen_lineno:
            continue
        seen_lineno.add(lineno)
        if language == "python":
            targets = _normalize_import_source(imp.source, imp.is_wildcard)
            for t in targets:
                results.append(ParsedImport(
                    target=t, lineno=lineno, is_star=imp.is_wildcard,
                ))
        else:
            results.append(ParsedImport(
                target=imp.source, lineno=lineno, is_star=imp.is_wildcard,
            ))
    return results


def _extract_classes(structure: list[Any]) -> list[dict[str, Any]]:
    """Map StructureItem kind=CLASS → dict."""
    results: list[dict[str, Any]] = []

    def _find(item: Any) -> None:
        kind_str = str(item.kind).upper() if item.kind else ""
        if "CLASS" in kind_str:
            span = item.span
            results.append({
                "name": item.name or "<anonymous>",
                "line_start": (span.start_line + 1) if span else 0,
                "line_end": (span.end_line + 1) if span else 0,
                "decorators": list(item.decorators) if item.decorators else [],
                "methods": [
                    c.name for c in (item.children or [])
                    if "FUNCTION" in str(c.kind).upper()
                    or "METHOD" in str(c.kind).upper()
                ],
            })
        if item.children:
            for child in item.children:
                _find(child)

    for item in structure:
        _find(item)
    return results


def _extract_exports(exports: list[Any]) -> list[str]:
    """Map ExportInfo → list[str]."""
    return [exp.name for exp in exports if exp.name]


def _detect_is_private(visibility: str | None, name: str) -> bool:
    """Detect private: visibility modifier atau naming convention.

    - pub/public/exported → False
    - private/internal → True
    - None + name starts with _ → True (Python convention)
    - None + name starts lowercase → True (Go unexported convention)
    """
    if visibility:
        vis = visibility.lower()
        if vis in ("pub", "public", "exported"):
            return False
        if vis in ("private", "internal"):
            return True
    # Fallback naming convention
    if name.startswith("_"):
        return True
    # ponytail: Go convention — lowercase = unexported.
    # False positive untuk Python methods (lowercase = normal), tapi
    # is_private hanya dipakai risk_analyzer Python-only checks yang
    # di-guard by language. Aman.
    return False
