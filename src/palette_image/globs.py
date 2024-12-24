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

COLORNAMES_CSV = RESOURCES / "colornames.csv"

with TemporaryFile() as f:
    CACHE_DIR = Path(f.name).parent / "palette_image_cache"

for path in (BINARIES, RESOURCES, CACHE_DIR):
    path.mkdir(exist_ok=True)


# ===================================================================================
#   Metaparàmetros
# ===================================================================================

# tamaño de la *unit* interna del svg
SIZE = (256, 144)  # 16:9

# espacio para dejar entre la imagen y los bloques de color
PALETTE_GAP = 1.2

# ancho del borde blanco delgado alrededor de la imagen
PAD = 1

# radio de las esquinas redondeadas
RAD = 4


# ===================================================================================
#   hacer inferencias a partir de metaparàmetros
# ===================================================================================

# El ancho de la bloque de colores. Establecer el ancho para que las pilas de 5
# bloques de altura estén hechas de cuadrados
blocks_wide = (SIZE[1] - PAD * 2 - PALETTE_GAP * 4) / 5
