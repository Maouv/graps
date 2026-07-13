"""Fixture import-target format test — semua bentuk Python import.

Dipakai test_tree_sitter_parser::TestPythonTargetFormat untuk assert exact
``ParsedImport.target`` match ast_parser contract (dotted module path, bukan
raw statement text).
"""
import os
import a.b.c as d
from graps.scanner import ParsedFile, ParsedImport
from .sub import helper
from . import other
from ..pkg import mod
from os import *
from functools import (
    lru_cache,
    wraps,
)
