"""Constants and paths for the project.

:author: Shay Hill
:created: 2024-11-19
"""

from pathlib import Path

INKSCAPE_EXE = Path("C:/Program Files/Inkscape/bin/inkscape")

_PROJECT = Path(__file__).parent.parent.parent

BINARIES = _PROJECT / "binaries"
RESOURCES = _PROJECT / "resources"

for path in (BINARIES, RESOURCES):
    path.mkdir(exist_ok=True)

