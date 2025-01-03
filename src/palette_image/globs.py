"""Constantes y rutas para el proyecto.

:author: Shay Hill
:created: 2024-11-19
"""

from pathlib import Path
from tempfile import TemporaryFile

# ===================================================================================
#   Rutas
# ===================================================================================


INKSCAPE_EXE = Path("C:/Program Files/Inkscape/bin/inkscape")

_PROJECT = Path(__file__).parent.parent.parent

BINARIES = _PROJECT / "binaries"
RESOURCES = _PROJECT / "resources"

with TemporaryFile() as f:
    CACHE_DIR = Path(f.name).parent / "palette_image_cache"
    COLORNAMES_CSV = Path(f.name).parent / "colornames.csv"

for path in (BINARIES, RESOURCES, CACHE_DIR):
    path.mkdir(exist_ok=True)
