"""La geometría contra la que se construyen las imágenes de paleta.

:author: Shay Hill
:created: 2024-12-24
"""

import svg_ultralight as su

# ===================================================================================
#   Metaparàmetros
# ===================================================================================

# tamaño de la *unit* interna del svg
_SIZE = (256, 144)  # 16:9

# ancho del borde blanco delgado alrededor de la imagen
PAD = 1

# espacio para dejar entre la imagen y los bloques de color
PALETTE_GAP = 1.2

# radio de las esquinas redondeadas
RAD = 4


# ===================================================================================
#   hacer inferencias a partir de metaparàmetros
# ===================================================================================

# El ancho de la bloque de colores. Establecer el ancho para que las pilas de 5
# bloques de altura estén hechas de cuadrados
_blocks_wide = (_SIZE[1] - PAD * 2 - PALETTE_GAP * 4) / 5

palette_bbox = su.BoundingBox(0, 0, *_SIZE)
content_bbox = su.pad_bbox(palette_bbox, -PAD)

_blocks_bbox = su.cut_bbox(content_bbox, x=content_bbox.x2 - _blocks_wide)
image_bbox = su.cut_bbox(content_bbox, x2=_blocks_bbox.x - PALETTE_GAP)

# Relennar los bloques y luego cortarlos sin lidiar con los espacios. Eliminar
# este relleno màs tarde para obtener PALETTE_GAP
blocks_bbox = su.pad_bbox(_blocks_bbox, PALETTE_GAP / 2)
