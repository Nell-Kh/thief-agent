"""The two cell constructors every notebook-section module uses.

Split out so a section module can import them without importing the builder,
which would otherwise run the whole assembly on import.
"""

from __future__ import annotations

import nbformat


def md(source: str) -> nbformat.NotebookNode:
    """A markdown cell."""
    return nbformat.v4.new_markdown_cell(source)


def code(source: str) -> nbformat.NotebookNode:
    """A code cell."""
    return nbformat.v4.new_code_cell(source)
