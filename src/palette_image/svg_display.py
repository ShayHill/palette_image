#!/usr/bin/env python3
"""Alternate (to ``show``) display library.

:author: Shay Hill
:created: 12/2/2019

"""

# padding reference: t, r, b, l

import base64
import io
import os
from pathlib import Path
from typing import Iterable, Sequence

# import palette.metaparemeters as metaparameters
# from palette.color_conversion import rgb_to_hex
from basic_colormath import rgb_to_hex
from lxml import etree
from lxml.etree import _Element as EtreeElement  # type: ignore
from PIL import Image
from PIL.Image import Image as ImageType
from svg_ultralight import NSMAP, new_svg_root, write_png, write_svg
from svg_ultralight.constructors import new_sub_element

from palette_image.color_block_ops import divvy_height, group_double_1s
from palette_image.globs import BINARIES, INKSCAPE_EXE
from palette_image.type_bbox import Bbox

_RGB = tuple[float, float, float]

# width and height of output image
_RATIO = (16, 9)

# space to leave between palette colors
_PALETTE_GAP = 1.5 / 20

# width of thin white border around the image
_PADDING = 1 / 15

# radius of rounded corners
_RECT_RADIUS = 1 / 4


def _get_svg_embedded_image_str(image: ImageType) -> str:
    """
    The string you'll need to embed an image in an svg

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


def get_colors_string(colors: Iterable[tuple[float, float, float]]) -> str:
    """
    Print a formatted string of color-channel values

    :param colors: a list of colors
    :return: every color value as :3n

    This is to insert a full color description (18 consecutive 000 to 255 colors)
    into an output image filename.
    """
    # breakpoint()
    # color_values = sum([list(x) for x in colors], start=[])
    return "-".join([rgb_to_hex(x)[1:] for x in colors])
    # return "-".join(f"{x:03n}" for x in color_values)

def _fit_image(image: ImageType, bbox: Bbox) -> ImageType:
    """Crop an image to the ratio of a bounding box.

    :param image: PIL.Image instance
    :param bbox: Bbox instance
    :return: PIL.Image instance

    This crops the image to the specified ratio. It's not a resize, so it will cut
    off the top and bottom or the sides of the image to fit the ratio.
    """
    ratio = bbox.width / bbox.height
    width, height = image.size
    if width / height > ratio:
        new_width = height * ratio
        left = (width - new_width) / 2
        right = width - left
        return image.crop((left, 0, right, height))
    new_height = width / ratio
    top = (height - new_height) / 2
    bottom = height - top
    return image.crop((0, top, width, bottom))


# TODO: this works but it's a mess
def show_svg(
    filename: Path | str,
    palette_colors: Sequence[_RGB],
    outfile: Path,
    dist: list[int],
    crop: tuple[float, float, float, float] = (0, 0, 0, 0),
    comment: str = "",
    print_width: float = 800,
) -> None:
    """
    The format for most of the palettes. Colors on top.

    :param filename:
    :param palette_colors:
    :param accent_colors:
    :param outfile:
    :return:

    The output images are 16/9, but I put in a transparent horizontal margin on the
    left and right of the output image so Twitter wouldn't cut off my edges. Adds a
    lot of complexity, but I'm keeping it because I'm happy with how the palettes
    look.

    There's also no reason padding, etc. must be rounded to integers. There was a bug
    in the first version of svg-ultralight that caused problems with floats. That bug
    is long-since fixed, but again I'm still rounding to integers so new palettes
    will look as close as possible to old palettes.
    """
    svg_doc = ""  # metaparameters.document_metaparameters()
    svg_doc += f"\n{outfile.stem}"

    root_bbox = Bbox(0, 0, _RATIO[0], _RATIO[1])
    content_bbox = root_bbox.pad(-_PADDING)
    palette_gap = _PALETTE_GAP

    # common case groups = [[1], [1], [1], [1], [1, 1]] will be squares.
    blocks_wide = (content_bbox.height - palette_gap * 4) / 5

    root = new_svg_root(*root_bbox.values, print_width_=print_width)
    if comment:
        root.append(etree.Comment(comment))

    # thin white border around the image
    root.append(root_bbox.get_rect(_RECT_RADIUS + _PADDING, fill = "white"))

    # palette rounded corners mask
    defs = new_sub_element(root, "defs")
    color_bar_clip = new_sub_element(defs, "clipPath", id="color_bar_clip")
    color_bar_clip.append(content_bbox.get_rect(_RECT_RADIUS))

    # image and color bar
    masked = new_sub_element(root, "g")

    # image
    image_bbox = content_bbox.pad((0, -(palette_gap + blocks_wide), 0, 0))
    image = Image.open(filename)
    # if crop:  # := crops.get(os.path.basename(filename)):
    #     width, height = image.size
    #     left = width * crop[0]
    #     top = height * crop[1]
    #     right = width * (1 - crop[2])
    #     bottom = height * (1 - crop[3])
    #     image = image.crop((left, top, right, bottom))
    # image = ImageOps.fit(image, (round(image_bbox.width), round(image_bbox.height/10)))
    image = _fit_image(image, image_bbox)
    svg_image = new_sub_element(
        masked,
        "image",
        x=image_bbox.x,
        y=image_bbox.y,
        width=image_bbox.width,
        height=image_bbox.height,
    )
    svg_image.set(
        etree.QName(NSMAP["xlink"], "href"), _get_svg_embedded_image_str(image)
    )

    # -------------------------------------------------------------------------
    # color blocks
    # -------------------------------------------------------------------------

    # todo: make this a cut
    blocks_bbox = content_bbox.reset_lims(x = image_bbox.x2 + palette_gap)
    blocks_bbox = blocks_bbox.pad(palette_gap / 2)

    hori_groups = group_double_1s(dist)
    heights = divvy_height(blocks_bbox, hori_groups)

    blocks: list[Bbox] = []
    for height, block in zip(heights, hori_groups):
        if len(block) == 1:
            block_bbox = blocks_bbox.reset_dims(height=height)
            if blocks:
                block_bbox.y = blocks[-1].y2
            blocks.append(block_bbox)
        else:
            width = blocks_bbox.width / 2
            block_a_bbox = blocks_bbox.reset_dims(width=width, height=height)
            if blocks:
                block_a_bbox.y = blocks[-1].y2
            block_b_bbox = block_a_bbox.copy()
            block_b_bbox.x = block_a_bbox.x2
            blocks += [block_a_bbox, block_b_bbox]

    icolors = iter(palette_colors)
    for block in (x.pad(-palette_gap / 2) for x in blocks):
        hex_color = rgb_to_hex(next(icolors))
        _ = new_sub_element(masked, "rect", **block.as_dict, fill=hex_color)

    masked.set("clip-path", "url(#color_bar_clip)")

    # write_svg("temp2.svg", screen)
    # TODO: return full colstr
    # colstr = get_colors_string(palette_colors + accent_colors)
    aaa = os.listdir(Path(outfile).parent)
    # if any(colstr in x for x in aaa):
    # return
    # full_name = outfile[:-4] + "_" + colstr + outfile[-4:]
    outfile = Path(outfile)
    write_svg(outfile.with_suffix(".svg"), root)
    write_png(INKSCAPE_EXE, outfile, root)


show_svg(
    BINARIES / "pencils.jpg",
    [(25, 25, 25), (0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)],
    BINARIES / "output.svg",
    [1, 1, 1, 1, 1, 1],
    (0, 0, 0, 0),
    "Pencils",
)
