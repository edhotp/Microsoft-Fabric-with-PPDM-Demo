"""Convert workshop notebook sources (`# %%` cells) into Fabric-importable .ipynb files."""

from __future__ import annotations

import json
import re
from pathlib import Path

MARKER = re.compile(r"^# %%(?: \[(markdown|parameters)\])?\s*$")


def parse_cells(source: str) -> list[dict]:
    cells, kind, lines = [], None, []

    def flush():
        if kind is None:
            return
        while lines and not lines[-1].strip():
            lines.pop()
        if kind == "markdown":
            text = [re.sub(r"^# ?", "", line) for line in lines]
        else:
            text = list(lines)
        cells.append({"kind": kind, "lines": text})

    for line in source.splitlines():
        match = MARKER.match(line)
        if match:
            flush()
            kind, lines = match.group(1) or "code", []
        elif kind is not None:
            lines.append(line)
    flush()
    return cells


def _source(lines: list[str]) -> list[str]:
    return [line + "\n" for line in lines[:-1]] + lines[-1:]


def to_ipynb(stem: str, source: str) -> dict:
    cells = []
    for index, cell in enumerate(parse_cells(source)):
        base = {"id": f"{stem.replace('_', '-')}-{index:02d}", "source": _source(cell["lines"])}
        if cell["kind"] == "markdown":
            cells.append({"cell_type": "markdown", "metadata": {}, **base})
        else:
            metadata = {"tags": ["parameters"]} if cell["kind"] == "parameters" else {}
            cells.append({"cell_type": "code", "execution_count": None, "metadata": metadata,
                          "outputs": [], **base})
    return {
        "cells": cells,
        "metadata": {
            "kernel_info": {"name": "synapse_pyspark"},
            "kernelspec": {"display_name": "Synapse PySpark", "language": "Python", "name": "synapse_pyspark"},
            "language_info": {"name": "python"},
            "microsoft": {"language": "python", "language_group": "synapse_pyspark"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def build_all(source_dir: Path, output_dir: Path) -> list[Path]:
    written = []
    for path in sorted(source_dir.glob("nb_*.py")):
        notebook = to_ipynb(path.stem, path.read_text(encoding="utf-8"))
        target = output_dir / f"{path.stem}.ipynb"
        target.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(target)
    return written
