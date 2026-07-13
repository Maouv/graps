"""Phase 4 tests — TreeSitterParser, 1 file per language.

Verifies: function extraction, import extraction, class extraction, export
extraction, Go import dedup, visibility detection, graceful failure on
unsupported/oversized files.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from graps.scanner.tree_sitter_parser import (
    TreeSitterParser,
    _normalize_import_source,
)

FIX = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parent.parent  # codemap root

# Skip seluruh module kalau tree-sitter-language-pack tidak terinstall.
pytestmark = pytest.mark.skipif(
    pytest.importorskip("tree_sitter_language_pack", reason="tslp not installed") is None,
    reason="tree-sitter-language-pack not installed",
)


@pytest.fixture()
def parser() -> TreeSitterParser:
    return TreeSitterParser()


# ── Per-language: 1 file per bahasa ──────────────────────────────────


class TestPython:
    def test_parse(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "simple.py", ROOT)
        assert pf is not None
        assert pf.language == "python"
        assert any(f.name == "hello" for f in pf.functions)
        # Python imports → target = dotted module path (exact match, bukan
        # substring lemah). Regression guard edge-resolution-bug: sebelum fix
        # target = "import os" (raw statement) → resolver drop semua edge.
        assert pf.imports, "simple.py harus punya >= 1 import"
        assert "os" in [i.target for i in pf.imports]
        assert all("import" not in i.target for i in pf.imports), \
            f"target must be dotted, got raw statement: {[i.target for i in pf.imports]}"


class TestPythonTargetFormat:
    """edge-resolution-bug: ``ParsedImport.target`` dari TreeSitterParser untuk
    Python harus identik format dengan ASTParser (dotted module path), bukan raw
    statement text. Verifies 5 bentuk import lewat fixture end-to-end."""

    def test_parse_all_forms(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "python_imports.py", ROOT)
        assert pf is not None
        targets = [i.target for i in pf.imports]
        # import os → "os"
        assert "os" in targets
        # import a.b.c as d → "a.b.c" (alias stripped)
        assert "a.b.c" in targets
        # from graps.scanner import ParsedFile, ParsedImport → 2 entries
        assert "graps.scanner.ParsedFile" in targets
        assert "graps.scanner.ParsedImport" in targets
        # from .sub import helper → ".sub.helper" (relative, leading dot preserved)
        assert ".sub.helper" in targets
        # from . import other → ".other"
        assert ".other" in targets
        # from ..pkg import mod → "..pkg.mod"
        assert "..pkg.mod" in targets
        # from os import * → is_star=True, target="os" (base saja, bukan "os.*")
        star_imports = [i for i in pf.imports if i.is_star]
        assert star_imports, "expected >= 1 star import"
        assert any(i.target == "os" for i in star_imports), \
            f"star target must be base module 'os', got {[i.target for i in star_imports]}"
        # multi-line paren: from functools import (lru_cache, wraps) → 2 entries
        assert "functools.lru_cache" in targets
        assert "functools.wraps" in targets
        # Tidak ada target yang masih raw statement (regression guard inti)
        assert all("import" not in t and "from" not in t for t in targets), \
            f"all targets must be dotted, found raw: {[t for t in targets if 'import' in t or 'from' in t]}"


# ── Unit test helper pure-function (no fixture file needed) ──────────────


class TestNormalizeImportSource:
    """Unit test ``_normalize_import_source`` — pure-function, testable tanpa
    fixture file. Match ast_parser ``visit_Import``/``visit_ImportFrom`` contract."""

    def test_plain_import(self) -> None:
        assert _normalize_import_source("import os", False) == ["os"]
        assert _normalize_import_source("import a.b.c", False) == ["a.b.c"]
        assert _normalize_import_source("import a as b", False) == ["a"]
        assert _normalize_import_source("import x, y", False) == ["x", "y"]

    def test_from_import(self) -> None:
        assert _normalize_import_source("from x import y", False) == ["x.y"]
        assert _normalize_import_source("from x import y, z", False) == ["x.y", "x.z"]
        assert _normalize_import_source("from a.b import c, d", False) == ["a.b.c", "a.b.d"]

    def test_relative(self) -> None:
        assert _normalize_import_source("from . import x", False) == [".x"]
        assert _normalize_import_source("from .a import b", False) == [".a.b"]
        assert _normalize_import_source("from ..a import b", False) == ["..a.b"]
        assert _normalize_import_source("from ...pkg import mod", False) == ["...pkg.mod"]

    def test_star(self) -> None:
        # from x import * → base module saja (caller set is_star=True)
        assert _normalize_import_source("from x import *", True) == ["x"]
        assert _normalize_import_source("from a.b import *", True) == ["a.b"]

    def test_multiline_paren(self) -> None:
        # Multi-line paren import — tree-sitter preserve parens + newline.
        s = "from functools import (\n    lru_cache,\n    wraps,\n)"
        assert _normalize_import_source(s, False) == ["functools.lru_cache", "functools.wraps"]

    def test_invalid_returns_empty(self) -> None:
        assert _normalize_import_source("not an import", False) == []
        assert _normalize_import_source("", False) == []
        assert _normalize_import_source("def foo(): pass", False) == []
        # false-positive tree-sitter (comment/string) — jangan crash, emit 0
        assert _normalize_import_source("# import os", False) == []


class TestTypeScript:
    def test_simple(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "typescript" / "simple.ts", ROOT)
        assert pf is not None
        assert pf.language == "typescript"
        assert any(f.name == "greet" for f in pf.functions)
        assert len(pf.imports) == 1

    def test_class_methods(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "typescript" / "class_methods.ts", ROOT)
        assert pf is not None
        # Method ter-flatten dengan parent = class name
        names = {f.name for f in pf.functions}
        assert {"add", "multiply"} <= names
        assert all(f.parent == "Calculator" for f in pf.functions)
        # Class masuk ke classes list
        assert len(pf.classes) == 1
        assert pf.classes[0]["name"] == "Calculator"
        methods = cast(list[str], pf.classes[0]["methods"])
        assert sorted(methods) == ["add", "multiply"]

    def test_exports(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "typescript" / "export_patterns.ts", ROOT)
        assert pf is not None
        assert len(pf.exported_names) >= 2  # square + default main
        assert any("square" in e for e in pf.exported_names)


class TestJavaScript:
    def test_parse(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "javascript" / "simple.js", ROOT)
        assert pf is not None
        assert pf.language == "javascript"
        assert any(f.name == "baz" for f in pf.functions)
        assert len(pf.imports) == 1


class TestGo:
    def test_simple(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "go" / "simple.go", ROOT)
        assert pf is not None
        assert pf.language == "go"
        assert any(f.name == "main" for f in pf.functions)

    def test_import_dedup(self, parser: TreeSitterParser) -> None:
        """Go return 2 entries per import — adapter harus dedup by lineno."""
        pf = parser.parse_file(FIX / "go" / "simple.go", ROOT)
        assert pf is not None
        fmt_imports = [i for i in pf.imports if "fmt" in i.target]
        assert len(fmt_imports) == 1, f"expected 1 deduped import, got {fmt_imports}"

    def test_unexported(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "go" / "unexported.go", ROOT)
        assert pf is not None
        names = {f.name: f for f in pf.functions}
        assert "ExportedFunc" in names
        assert "unexportedFunc" in names


class TestRust:
    def test_simple(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "rust" / "simple.rs", ROOT)
        assert pf is not None
        assert pf.language == "rust"
        assert any(f.name == "main" for f in pf.functions)

    def test_pub_private(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "rust" / "pub_private.rs", ROOT)
        assert pf is not None
        names = {f.name: f for f in pf.functions}
        assert "public_function" in names
        assert "private_function" in names


# ── Failure modes ────────────────────────────────────────────────────


class TestFailureModes:
    def test_unsupported_extension(self, parser: TreeSitterParser, tmp_path: Path) -> None:
        f = tmp_path / "weird.xyz"
        f.write_text("hello")
        assert parser.parse_file(f, tmp_path) is None

    def test_oversized_file(self, parser: TreeSitterParser, tmp_path: Path) -> None:
        f = tmp_path / "big.py"
        f.write_text("x = 1\n" * 200_000)  # > 1MB
        assert parser.parse_file(f, tmp_path) is None

    def test_nonexistent_file(self, parser: TreeSitterParser, tmp_path: Path) -> None:
        assert parser.parse_file(tmp_path / "nope.py", tmp_path) is None

    def test_supported_extensions(self, parser: TreeSitterParser) -> None:
        # Protocol compliance — returns []
        assert parser.supported_extensions() == []


# ── Line numbers are 1-indexed ───────────────────────────────────────


class TestLineNumbers:
    def test_function_line_start(self, parser: TreeSitterParser) -> None:
        pf = parser.parse_file(FIX / "typescript" / "simple.ts", ROOT)
        assert pf is not None
        greet = next(f for f in pf.functions if f.name == "greet")
        assert greet.line_start >= 1  # 1-indexed, tree-sitter 0-indexed +1
