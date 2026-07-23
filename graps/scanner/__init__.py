"""Scanner public interface — data carriers shared across parsers.

Defines the data carriers (ParsedFile / ParsedFunction / ParsedImport) used by
both parsers (safe_parse for .py, TreeSitterParser for everything else —
dispatched by file suffix in cli.py). graph_builder and layers above import
ONLY from here — never from a concrete parser module — so Phase 4 tree-sitter
does not cascade.

ponytail: legacy Phase 1 fields that tests/graph_builder/risk_analyzer/resolver
read are preserved with defaults + comments (one set of dataclasses, not two —
deletion over addition).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedCall:
    """A direct static call site inside a function body (data-contracts call_sequence).

    ``name``  : flattened callee expression text (``foo``, ``self.bar``, ``mod.fn``).
    ``line``  : 1-based source line of the call.
    Order is source order (list position); graph_builder assigns deterministic
    ``order`` and resolves target/candidates/confidence at build time.
    ponytail: kept parser-agnostic — no target here; resolution is graph layer.
    """
    name: str
    line: int = 0


@dataclass
class ParsedBranch:
    """A control-flow branch marker inside a function body (data-contracts control_flow).

    ``kind``  : branch type (``if``, ``elif``, ``else``, ``for``, ``while``,
                ``try``, ``except``, ``finally``, ``return``).
    ``line``  : 1-based source line of the branch keyword.
    Order is source order (list position); graph_builder assigns ``order`` at build.
    ponytail: no condition text — structural fact only, no AI.
    """
    kind: str
    line: int = 0


@dataclass
class ParsedRoute:
    """An HTTP route decorator on a function (data-contracts request_flow).

    ``method`` : HTTP method (``GET``, ``POST``, ``PUT``, ``DELETE``, ``PATCH``).
    ``path``   : route path string (``/users``, ``/items/{id}``).
    ``line``   : 1-based source line of the decorator.
    ponytail: no query/param schema — structural route identity only, no AI.
    """
    method: str
    path: str
    line: int = 0


@dataclass
class ParsedFunction:
    name: str
    line_start: int = 0
    line_end: int = 0
    decorators: list[str] = field(default_factory=list)
    is_private: bool = False
    # --- ponytail: legacy Phase 1 fields; tests + graph_builder/risk_analyzer read them ---
    qualified_name: str = ""
    lineno: int = 0
    is_nested: bool = False      # Section 14: nested funcs are children, not top-level
    is_property: bool = False    # Section 14: @property flag
    parent: str | None = None    # enclosing func/class qualified_name
    # --- experimental-graps FEAT-0017: direct static call sites in source order ---
    calls: list[ParsedCall] = field(default_factory=list)
    # --- experimental-graps FEAT-0019: control-flow branch markers in source order ---
    branches: list[ParsedBranch] = field(default_factory=list)
    # --- experimental-graps FEAT-0019: HTTP route decorators (request_flow) ---
    routes: list[ParsedRoute] = field(default_factory=list)


@dataclass
class ParsedImport:
    """ponytail: not in BLUEPRINT §4 — preserved (resolver/risk_analyzer/tests read its fields)."""
    target: str
    lineno: int = 0
    is_conditional: bool = False  # Section 14: try/except import
    is_star: bool = False         # Section 14: from X import * (weight -1)
    is_dynamic: bool = False      # Section 14: importlib → warning, no edge


@dataclass
class ParsedFile:
    # --- BLUEPRINT §4 fields ---
    id: str = ""                                   # relative path from scan root
    # ponytail: BLUEPRINT §4 says path:str (relative); actual parser stores the
    # absolute Path here (resolver uses .parent, graph_builder._rel wraps in Path).
    # `id` carries the BLUEPRINT relative-path semantic. Preserve until Phase 4 rewrite.
    path: Path = field(default_factory=lambda: Path(""))
    functions: list[ParsedFunction] = field(default_factory=list)
    # ponytail: BLUEPRINT §4 says imports:list[dict]; ParsedImport preserved because
    # resolver/risk_analyzer/tests read .target/.is_star/.is_dynamic/.is_conditional.
    imports: list[ParsedImport] = field(default_factory=list)
    constants: list[dict[str, object]] = field(default_factory=list)
    classes: list[dict[str, object]] = field(default_factory=list)
    exported_names: list[str] = field(default_factory=list)
    file_modified_at: str = ""
    language: str = "python"
    # --- ponytail: preserved from Phase 1; graph_builder/risk_analyzer iterate warnings ---
    warnings: list[str] = field(default_factory=list)


# ponytail: legacy alias so risk_analyzer (`from .ast_parser import ParseResult`)
# keeps working untouched. Canonical name is ParsedFile (BLUEPRINT §4).
ParseResult = ParsedFile
