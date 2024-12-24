"""Crear un svg con una imagen de origen y colores de palete proporcionandos.

Esta imagen está destinada a ser el único resultado de un algoritmo de generación de
paleta.  No hay un formato intermedio. Tengo un puñado de algoritmos de paleta, y
este archivo svg es lo que se committed para capturar su salida. Para este propósito,
no solo los colores de la paleta de salide y las proporciones pero también los
nombres de los colores se incluirán como matadata en el archivo svg.

Actualmente, todo lo que haco con estos archivos svg (i.e., el código necesario para
mostrarlos en la web) es parte de este mismo proyecto, pero teóricamente estos
archivos svg podrían ser consultados para construir otros tipos de visualizaciones
fuera de este proyecto donde el buscador de nombres de colores no estaría disponible.

:author: Shay Hill
:created: 12/2/2019
"""

import json
import os
from pathlib import Path

import svg_ultralight as su
from lxml import etree
from svg_ultralight import write_png, write_svg
from svg_ultralight.constructors import new_sub_element

import palette_image.geometry as geo
from palette_image.color_block_ops import ColorBlocks
from palette_image.globs import INKSCAPE_EXE
from palette_image.image_ops import new_image_elem_in_bbox

_CLIP_ID = "content_clip"


def _serialize_palette_data(
    filename: str | os.PathLike[str],
    color_blocks: ColorBlocks,
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

    Esta información se puede utilizar para recrear la paleta en el futuro o crear un
    texto accompanãmiento para la paleta.
    """
    palette_data = {
        "filename": Path(filename).name,
        "colors": color_blocks.colors,
        "center": center,
        "colornames": color_blocks.names,
        "comment": comment,
    }
    return json.dumps(palette_data)


def _new_palette_group(comment: str) -> su.BoundElement:
    """Devuelve un nuevo BoundElement "g" con un comentario y fondo blanco."""
    palette = su.BoundElement(su.new_element("g"), geo.palette_bbox)
    palette.elem.append(etree.Comment(comment))
    rad = geo.RAD + geo.PAD
    palette.elem.append(su.new_bbox_rect(palette.bbox, rx=rad, ry=rad, fill="white"))
    return palette


def _add_masked_content(palette: su.BoundElement) -> su.BoundElement:
    """Añande un área de contenindo enmascaranda a la paleta."""
    defs = su.new_sub_element(palette.elem, "defs")

    content_mask = new_sub_element(defs, "clipPath", id=_CLIP_ID)
    rad = geo.RAD
    content_mask.append(su.new_bbox_rect(geo.content_bbox, rx=rad, ry=rad))

    content_elem = su.new_sub_element(palette.elem, "g", clip_path=f"url(#{_CLIP_ID})")
    return su.BoundElement(content_elem, geo.content_bbox)


def new_palette_blem(
    filename: Path | str,
    color_blocks: ColorBlocks,
    center: tuple[float, float] | None = None,
    comment: str = "",
) -> su.BoundElement:
    """Crear un svg con una imagen y una barra de color.

    :param filename: la ruta a la imagen de origen
    :param palette_colors: los colores de la paleta
    :param dist: la proporción de cada color en la paleta
    :param center: el punto central de la imagen, se is necesario. Si no se da, el
        verdadero centro se usará. Esto es para alterar el recorte de la imagen de
        origen.
    """
    comment = _serialize_palette_data(filename, color_blocks, center, comment)
    palette = _new_palette_group(comment)
    content = _add_masked_content(palette)

    content.elem.append(new_image_elem_in_bbox(filename, geo.image_bbox, center))
    for block, color in zip(color_blocks.bboxes, color_blocks.colors, strict=True):
        content.elem.append(su.new_bbox_rect(block, fill=color))

    return palette


def write_palette(
    filename: Path | str,
    color_blocks: ColorBlocks,
    outfile: str | os.PathLike[str],
    center: tuple[float, float] | None = None,
    comment: str = "",
    print_width: float = 800,
) -> None:
    pal = new_palette_blem(filename, color_blocks, center, comment)
    root = su.new_svg_root_around_bounds(pal, print_width_=print_width)
    root.extend(list(pal.elem))
    outfile = Path(outfile)
    _ = write_svg(outfile.with_suffix(".svg"), root)
    _ = write_png(INKSCAPE_EXE, outfile, root)
