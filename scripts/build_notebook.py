"""Build and execute notebooks/analysis.ipynb - the phase-8 research notebook.

The notebook is authored here as code so it can be regenerated and re-executed
deterministically: every figure in the committed .ipynb is the output of a real
run, never a pasted image. Run: ``uv run python scripts/build_notebook.py``.

The cell text lives in the ``_notebook_part*`` modules (the 150-line rule); this
file only orders them and executes the result.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _notebook_part1 import CELLS as PART1  # noqa: E402
from _notebook_part2 import CELLS as PART2  # noqa: E402
from _notebook_part3 import CELLS as PART3  # noqa: E402
from _notebook_part4 import CELLS as PART4  # noqa: E402
from _notebook_part5 import CELLS as PART5  # noqa: E402

#: Section order is the argument of the notebook and must not be reshuffled.
CELLS = PART1 + PART2 + PART3 + PART4 + PART5

def main() -> None:
    """Assemble, execute and save the notebook with real outputs."""
    notebook = nbformat.v4.new_notebook()
    notebook.cells = CELLS
    notebook.metadata.kernelspec = {
        "name": "python3", "display_name": "Python 3", "language": "python",
    }
    client = NotebookClient(notebook, timeout=1800, resources={
        "metadata": {"path": str(ROOT / "notebooks")},
    })
    client.execute()
    target = ROOT / "notebooks" / "analysis.ipynb"
    nbformat.write(notebook, target)
    print(f"executed and wrote {target}")


if __name__ == "__main__":
    main()
