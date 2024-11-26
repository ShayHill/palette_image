#!/usr/bin/env python3
"""Alternate (to ``show``) display library.

:author: Shay Hill
:created: 12/2/2019

"""

# padding reference: t, r, b, l

import base64
import io
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Iterator

import svg_ultralight as su
from basic_colormath import rgb_to_hex
from lxml import etree
from lxml.etree import _Element as EtreeElement  # type: ignore
from PIL import Image
from PIL.Image import Image as ImageType
from svg_ultralight import NSMAP, write_png, write_svg
from svg_ultralight.constructors import new_sub_element

from palette_image.color_block_ops import divvy_height, group_double_1s
from palette_image.globs import BINARIES, INKSCAPE_EXE
from palette_image.crop_image import crop_image_to_bbox_ratio

# internal unit size of the svg
RATIO = (16, 9)

# The ratios are scaled so that the larger dimension will be 256. This allows a nice
# gradient for integer PALETTE_GAP, PADDING, and CORNER_RAD. This results in an
# output svg with fewer decimal places for float arguments.

# space to leave between palette colors
PALETTE_GAP = 1.2

# width of thin white border around the image
PADDING = 1

# radius of rounded corners
CORNER_RAD = 4


_CLIP_PATH_ID = "content_clip"


def _get_svg_embedded_image_str(image: ImageType) -> str:
    """Return the string you'll need to embed an image in an svg.

    :param image: PIL.Image instance
    :return: argument for xlink:href
    """
    in_mem_file = io.BytesIO()
    image.save(in_mem_file, format="PNG")
    _ = in_mem_file.seek(0)
    img_bytes = in_mem_file.read()
    base64_encoded_result_bytes = base64.b64encode(img_bytes)
    base64_encoded_result_str = base64_encoded_result_bytes.decode("ascii")
    return "data:image/png;base64," + base64_encoded_result_str


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


def flatten_meaningless_groups(elem: EtreeElement) -> None:
    """For any "g" element with an empty dict, move all items into the parent.

    :param elem: the element to flatten
    """

    def promote_children(elem: EtreeElement) -> None:
        parent = elem.getparent()
        if parent is None:
            return
        for child in elem:
            elem.addprevious(child)
        parent.remove(elem)

    children = tuple(elem)
    if elem.tag == "g" and not elem.attrib:
        promote_children(elem)
    for child in children:
        flatten_meaningless_groups(child)


def get_colors_string(colors: Iterable[tuple[float, float, float]]) -> str:
    """Return a formatted string of color-channel values

    :param colors: a list of colors
    :return: every color value as :3n

    This is to insert a full color description (18 consecutive 000 to 255 colors)
    into an output image filename.
    """
    return "-".join([rgb_to_hex(x)[1:] for x in colors])


def _new_g(bbox: su.BoundingBox, **kwargs: float | str) -> su.BoundElement:
    """Create an empty group element with a bounding box."""
    return su.BoundElement(su.new_element("g", **kwargs), bbox)


def _new_sub_g(
    parent: su.BoundElement, bbox: su.BoundingBox, **kwargs: float | str
) -> su.BoundElement:
    """Create an empty group element with a bounding box."""
    return su.BoundElement(su.new_sub_element(parent.elem, "g", **kwargs), bbox)


def _new_palette_group() -> su.BoundElement:
    """Return a new svg root and the content bounding box.

    :return: root, content area as a BoundElement
    """
    scale = min(256 / x for x in RATIO)
    width, height = (x * scale for x in RATIO)
    palette = _new_g(su.BoundingBox(0, 0, width, height))

    rad = CORNER_RAD + PADDING
    palette.elem.append(su.new_bbox_rect(palette.bbox, rx=rad, ry=rad, fill="white"))
    return palette


def _add_masked_content(palette: su.BoundElement) -> su.BoundElement:
    """Add a masked content area to the palette."""
    content_bbox = su.pad_bbox(palette.bbox, -PADDING)

    defs = su.new_element("defs")
    palette.elem.insert(0, defs)

    clip_path = new_sub_element(defs, "clipPath", id=_CLIP_PATH_ID)
    rad = CORNER_RAD + PADDING
    clip_path.append(su.new_bbox_rect(content_bbox, rx=rad, ry=rad))

    return _new_sub_g(palette, content_bbox, clip_path=f"url(#{_CLIP_PATH_ID})")


def _split_content_into_image_and_blocks(
    content: su.BoundElement,
) -> tuple[su.BoundElement, su.BoundElement]:
    """Return image and blocks group blems.

    :param content_bbox: the content area blem
    :return: image blem, blocks blem
    """
    # set 5 block stack to be squares
    blocks_wide = (content.height - PALETTE_GAP * 4) / 5
    blocks_x = content.x2 - blocks_wide
    image_x2 = blocks_x - PALETTE_GAP
    return (
        _new_sub_g(content, su.cut_bbox(content, x2=image_x2)),
        _new_sub_g(content, su.cut_bbox(content, x=blocks_x)),
    )


def _new_image_in_bbox(
    filename: Path | str, bbox: su.BoundingBox, center: tuple[float, float] | None
) -> EtreeElement:
    image = crop_image_to_bbox_ratio(Image.open(filename), bbox, center)
    svg_image = su.new_element("image", **su.bbox_dict(bbox))
    svg_image.set(
        etree.QName(NSMAP["xlink"], "href"), _get_svg_embedded_image_str(image)
    )
    return svg_image


def _position_blocks(bbox: su.BoundingBox, dist: list[int]) -> Iterator[su.BoundingBox]:
    """Yield a BoundingBox for each block in the palette."""
    groups = group_double_1s(dist)
    heights = divvy_height(bbox, groups)

    at_y = bbox.y
    for group, height in zip(groups, heights):
        at_x = bbox.x
        for width in (bbox.width * g / len(group) for g in group):
            yield su.BoundingBox(at_x, at_y, width, height)
            at_x += width
        at_y += height


def new_palette_blem(
    filename: Path | str,
    palette_colors: Sequence[tuple[float, float, float]],
    dist: list[int],
    center: tuple[float, float] | None = None,
    comment: str = "",
) -> su.BoundElement:
    """Create an svg with an image and a color bar.

    :param filename:
    :param palette_colors:
    :param accent_colors:
    :param outfile:
    :return:
    """
    palette = _new_palette_group()
    content = _add_masked_content(palette)

    # defs was inserted at zero, so wait till here to insert comment
    palette.elem.insert(0, etree.Comment(f"{Path(filename).stem}|{comment}"))

    image, blocks = _split_content_into_image_and_blocks(content)

    image.elem.append(_new_image_in_bbox(filename, image.bbox, center))

    # Pad out the blocks then cut them up without dealing with gaps. Remove this
    # padding later to get PALETTE_GAP
    blocks_bbox = su.pad_bbox(blocks, PALETTE_GAP / 2)

    icolors = iter(palette_colors)
    block_bboxes = _position_blocks(blocks_bbox, dist)
    block_colors = map(rgb_to_hex, icolors)
    for block, color in zip(block_bboxes, block_colors):
        block = su.pad_bbox(block, -PALETTE_GAP / 2)
        blocks.elem.append(su.new_bbox_rect(block, fill=color))

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
    root.append(pal.elem)
    flatten_meaningless_groups(root)
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
