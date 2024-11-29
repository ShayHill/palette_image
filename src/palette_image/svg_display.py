#!/usr/bin/env python3
"""Alternate (to ``show``) display library.

:author: Shay Hill
:created: 12/2/2019

"""

# padding reference: t, r, b, l

import json
import os
from collections.abc import Iterable, Sequence
from pathlib import Path

import svg_ultralight as su
from basic_colormath import rgb_to_hex
from lxml import etree
from svg_ultralight import write_png, write_svg
from svg_ultralight.constructors import new_sub_element


from palette_image.color_block_ops import position_blocks
from palette_image.globs import BINARIES, INKSCAPE_EXE
from palette_image.image_ops import new_image_elem_in_bbox

# internal unit size of the svg
SIZE = (256, 144)  # 16:9

# space to leave between palette colors
PALETTE_GAP = 1.2

# width of thin white border around the image
_PAD = 1

# radius of rounded corners
_RAD = 4


_CLIP_ID = "content_clip"


def _serialize_palette_data(
    filename: str | os.PathLike[str],
    colors: Iterable[tuple[float, float, float]] | Iterable[str],
    ratios: Iterable[float],
    center: tuple[float, float] | None = None,
    comment: str = "",
) -> str:
    """Serializar datos de paleta en una cadena json.

    :param filename: ruta a la imaged de origen a partir de la cual se creó la paleta
    :param colors: los colores utilizados en la paleta. Pueden ser cadenas
        hexadecimales o tuplas RGB
    :param ratios: la proporción de cada color en la paleta. No es necesario que
        sumen uno.
    :param center: el punto central de la imagen, si es relevante. Si no se da, la
        imagen se recortará  alredador del centro verdadero.
    :param comment: un comentario opcional para la paleta. Esto se puede utilizar
        para anotar los detalles del algoritmo utilizado para generar la paleta.
    :return: una cadena json que contiene los datos de la paleta

    Esta información se puede utilizar para recrear la paleta en el futuro.
    """
    palette_data = {
        "filename": Path(filename).name,
        "colors": [x if isinstance(x, str) else rgb_to_hex(x) for x in colors],
        "ratios": list(ratios),
        "center": center,
        "comment": comment,
    }
    return json.dumps(palette_data)


crops = {
    # 'John James Audubon - Cardinal.jpg' : (0, 0, 0, .4),
    "Technicolor - Leslie Caron.jpg": (0, 0, 0, 0.4),
    "John James Audubon - Brown Pelican.jpg": (0, 0, 0, 0.4),
    "American Novel - The Sun Also Rises.jpg": (0, 0, 0, 0.4),
    "American Novel - Eldorado Red.jpg": (0, 0, 0, 0.1),
    "American Novel - Moby Dick.jpg": (0, 0, 0, 0.4),
    "American Novel - The Great Gatsby.jpg": (0, 0, 0, 0.2),
    "Finch Davies - Green Pigeon.jpg": (0, 0, 0, 0.4),
    "Finch Davies - Pygmy Falcon.jpg": (0, 0, 0, 0.3),
    "Finch Davies - flamingo.jpg": (0, 0, 0, 0.5),
    "Finch Davies - Piciformes.jpg": (0, 0, 0, 0.4),
    "Finch Davies - Sparrowhawk.jpg": (0, 0, 0, 0.4),
    "Finch Davies - Plicatus.jpg": (0.2, 0, 0.1, 0.4),
    "Finch Davies - Heron.jpg": (0, 0, 0, 0.4),
    "Kees van Dongen - Femme Arabe.jpg": (0, 0, 0, 0.2),
    "Kees van Dongen - Lady in a Black Hat.jpg": (0, 0, 0, 0.1),
    "Jane Avril.jpg": (0, 0, 0, 0.4),
    "Alphonse Mucha - Austria 1900.jpg": (0, 0, 0, 0.5),
    "Alphonse Mucha - Moon.jpg": (0, 0, 0, 0.5),
    "Arthur Rackham - Rhinegold and Valkyrie.jpg": (0, 0, 0, 0.5),
    "Alphonse Mucha - Princess Hyacinth.jpg": (0, 0, 0, 0.35),
    "Alphonse Mucha - Lady of the Camellias.jpg": (0, 0, 0, 0.5),
    "Alphonse Mucha - Rêverie.jpg": (0, 0, 0, 0.4),
    "Alphonse Mucha - Salammbô.jpg": (0, 0, 0, 0.4),
    "Alphonse Mucha - North Star.jpg": (0, 0, 0, 0.6),
}


def _new_palette_group(comment: str) -> su.BoundElement:
    """Return a new bound "g" element with a comment string and white background."""
    palette = su.BoundElement(su.new_element("g"), su.BoundingBox(0, 0, *SIZE))
    palette.elem.append(etree.Comment(comment))
    rad = _RAD + _PAD
    palette.elem.append(su.new_bbox_rect(palette.bbox, rx=rad, ry=rad, fill="white"))
    return palette


def _add_masked_content(palette: su.BoundElement) -> su.BoundElement:
    """Add a masked content area to the palette."""
    content_bbox = su.pad_bbox(palette.bbox, -_PAD)

    defs = su.new_sub_element(palette.elem, "defs")

    content_mask = new_sub_element(defs, "clipPath", id=_CLIP_ID)
    rad = _RAD
    content_mask.append(su.new_bbox_rect(content_bbox, rx=rad, ry=rad))

    content_elem = su.new_sub_element(palette.elem, "g", clip_path=f"url(#{_CLIP_ID})")
    return su.BoundElement(content_elem, content_bbox)


def _split_content_into_image_and_blocks(
    content: su.BoundElement,
) -> tuple[su.BoundElement, su.BoundElement]:
    """Return image and blocks bound elements."""
    # set width so that 5-block-high stacks are made of squares
    blocks_wide = (content.height - PALETTE_GAP * 4) / 5
    blocks_x = content.x2 - blocks_wide
    image_x2 = blocks_x - PALETTE_GAP

    image_bbox = su.cut_bbox(content, x2=image_x2)
    blocks_bbox = su.cut_bbox(content, x=blocks_x)
    return (
        su.BoundElement(content.elem, image_bbox),
        su.BoundElement(content.elem, blocks_bbox),
    )


def new_palette_blem(
    filename: Path | str,
    palette_colors: Sequence[tuple[float, float, float]],
    dist: list[int],
    center: tuple[float, float] | None = None,
    comment: str = "",
) -> su.BoundElement:
    """Create an svg with an image and a color bar.

    :param filename:
    # TODO: fix new_palette_blem docstring
    :param palette_colors:
    :param accent_colors:
    :param outfile:
    :return:
    """
    comment = _serialize_palette_data(filename, palette_colors, dist, center, comment)
    palette = _new_palette_group(comment)
    content = _add_masked_content(palette)

    image, blocks = _split_content_into_image_and_blocks(content)

    image.elem.append(new_image_elem_in_bbox(filename, image.bbox, center))

    # Pad out the blocks then cut them up without dealing with gaps. Remove this
    # padding later to get PALETTE_GAP
    blocks_bbox = su.pad_bbox(blocks, PALETTE_GAP / 2)

    icolors = iter(palette_colors)
    block_bboxes = position_blocks(blocks_bbox, dist)
    block_colors = map(rgb_to_hex, icolors)
    for block, color in zip(block_bboxes, block_colors, strict=True):
        block_with_gap = su.pad_bbox(block, -PALETTE_GAP / 2)
        blocks.elem.append(su.new_bbox_rect(block_with_gap, fill=color))

    return palette


def show_svg(
    filename: Path | str,
    palette_colors: Sequence[tuple[float, float, float]],
    outfile: Path,
    dist: list[int],
    center: tuple[float, float] | None = None,
    comment: str = "",
    print_width: float = 800,
) -> None:
    pal = new_palette_blem(filename, palette_colors, dist, center, comment)
    root = su.new_svg_root_around_bounds(pal, print_width_=print_width)
    root.extend(list(pal.elem))
    outfile = Path(outfile)
    _ = write_svg(outfile.with_suffix(".svg"), root)
    _ = write_png(INKSCAPE_EXE, outfile, root)


def _main():
    show_svg(
        BINARIES / "pencils.jpg",
        [(25, 25, 25), (0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)],
        BINARIES / "output.svg",
        [1, 1, 1, 1, 1, 1],
        comment="Pencils",
    )


if __name__ == "__main__":
    _main()
