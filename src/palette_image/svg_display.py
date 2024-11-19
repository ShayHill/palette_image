#!/usr/bin/env python3
"""Alternate (to ``show``) display library.

:author: Shay Hill
:created: 12/2/2019

"""

import base64
import io
import os
from pathlib import Path
from typing import Any, List, Sequence

from lxml import etree
from lxml.etree import _Element as EtreeElement  # type: ignore
from PIL import Image, ImageOps
from svg_ultralight import NSMAP, new_svg_root, write_png, write_svg
from svg_ultralight.constructors import new_sub_element

# import palette.metaparemeters as metaparameters
# from palette.color_conversion import rgb_to_hex
from basic_colormath import rgb_to_hex

from palette_image.globs import INKSCAPE_EXE, BINARIES

_RGB = tuple[float, float, float]

# overall scalar. This scales the pixel width of the output images. That value could
# also be changed by setting "print_width" and "print_height" in the svg root
# element, but this is what I went with years before that functionality was
# available. Also, there is no reason these must be ints. It is an artifact of a very
# early bug in svg_ultralight that has since been fixed. Leaving it this way, because
# I want to be able to re-render old images and keep them as close to the originals
# as possible / preferable.
_RESOLUTION = 100

# ratio scalars. These also scale the output image to _RATIO[0] * _RESOLUTION by
# _RATIO[1] * _RESOLUTION
_RATIO = (16, 9)

# add a bit of transparent horizontal margin to the image. This was a naive fix for
# how Twitter cut off the sides of my images. That cutting was a result of skewing my
# image ratios by adding padding. The root of the problem is that terms like "pad"
# and "margin" are hard to define when you are dealing with fixed geometry like SVG.
# With svg_ultralight, padding is padding relative to the output image boundary, but
# it's margin relative to the geometry of the SVG. For instance, a (0, 0, 1, 1)
# rectangle, padded any amount will still be at (0, 0, 1, 1). Here, interpret margin
# as page margin.
_HORI_MARGIN_SCALE = 1 / 10

# relative space to leave between palette colors
_PALETTE_GAP_SCALE = 1.5 / 20

# padding (white boundary) around the image. This is *not* padding around the
# geometry. There is no padding around the geometry, because I've filled it with a
# white rounded-box element.
_PADDING = max(1, round(_RESOLUTION / 15))


# inferred values
_ROOT_WIDE = round(_RATIO[0] * _RESOLUTION) - _PADDING
_ROOT_HIGH = round(_RATIO[1] * _RESOLUTION) - _PADDING
_HORI_MARGIN = round(_HORI_MARGIN_SCALE * _RESOLUTION)
_PALETTE_GAP = round(_PALETTE_GAP_SCALE * _RESOLUTION)
_SHOW_X = _HORI_MARGIN
_SHOW_WIDE = _ROOT_WIDE - _HORI_MARGIN * 2
# width of palette entries
_COLS_WIDE = (_ROOT_HIGH - _PALETTE_GAP * 4) / 5


def _get_svg_embedded_image_str(image: Image) -> str:
    """
    The string you'll need to embed an image in an svg

    :param image: PIL.Image instance
    :return: argument for xlink:href
    """
    in_mem_file = io.BytesIO()
    image.save(in_mem_file, format="PNG")
    in_mem_file.seek(0)
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

from typing import Iterable

from basic_colormath import rgb_to_hex


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


def _expand_pad_argument(
    pad: float | tuple[float, ...]
) -> tuple[float, float, float, float]:
    """Expand < 4 pad values to a 4-tuple (top, left, bottom, right).

    :param pad: a float or a tuple of floats
    :return: a 4-tuple of floats (top, left, bottom, right)
    """
    if not isinstance(pad, tuple):
        return (pad, pad, pad, pad)
    if len(pad) == 3:
        return (pad[0], pad[1], pad[2], pad[1])
    return (pad * 4)[:4]


def _pad_rect(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    pad: float | tuple[float, ...] = 0,
    rad: float = 0,
) -> dict[str, float]:
    """Pad a rectangle by a given amount

    :param x: the x-coordinate of the rectangle
    :param y: the y-coordinate of the rectangle
    :param width: the width of the rectangle
    :param height: the height of the rectangle
    :param pad: the amount of padding to add to each side of the rectangle
    :param rad: the corner radius of the rectangle
    :return: a dictionary of the padded rectangle's coordinates
    """
    top, left, bottom, right = _expand_pad_argument(pad)
    rect_args = dict(
        x=x - left, y=y - top, width=width + left + right, height=height + top + bottom
    )
    if rad:
        rect_args["rx"] = rect_args["ry"] = rad + min(top, left, bottom, right)
    return rect_args


def _group_double_1s(slices: list[int]) -> list[list[int]]:
    """Working from the end of a list, group any two consecutive 1s

    :param slices: a list of integers
    :return: a list of lists of integers, where each list is a single integer or [1, 1]

    Given a list of integers, when 1, 1 appears, group them together as [1, 1]. Group
    other values as singles.

        >>> _group_double_1s([1, 2, 3, 4, 1, 1])
        [[1], [2], [3], [4], [1, 1]]
    """
    groups: list[list[int]] = []
    for i in reversed(slices):
        if i == 1 and groups and groups[-1] == [1]:
            groups[-1].append(1)
        else:
            groups.append([i])
    return list(reversed(groups))


# TODO: this works but it's a mess
def show_svg(
    filename: Path | str,
    palette_colors: Sequence[_RGB],
    outfile: Path,
    dist: List[int],
    crop: tuple[float, float, float, float],
    comment: str,
    hori_margin_scale: float = _HORI_MARGIN_SCALE,
    palette_gap_scale: float = _PALETTE_GAP_SCALE,
    resolution: float = _RESOLUTION,
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

    padding = max(1, round(resolution / 15))
    show_wide = round(16 * resolution) - padding
    show_high = round(9 * resolution) - padding
    hori_margin = round(hori_margin_scale * resolution)
    palette_gap = round(palette_gap_scale * resolution)

    # ugly formula just de-parameterizes previous way of calculating box_wide from
    # number of palette entries. box_wide is now fixed for any number of palette
    # entries.
    box_wide = (show_high - palette_gap * 4) / 5

    # TODO: make global
    mask_round = resolution / 4

    screen = new_svg_root(
        0, 0, _ROOT_WIDE, _ROOT_HIGH, pad_=_PADDING, print_width_=f"{_ROOT_WIDE / 2}px"
    )
    if comment:
        screen.append(etree.Comment(comment))

    # white background behind entire image
    rgeo = _pad_rect(_SHOW_X, 0, _SHOW_WIDE, _ROOT_HIGH, pad=_PADDING, rad=mask_round)
    _ = new_sub_element(screen, "rect", **rgeo, fill="white")

    # palette rounded corners mask
    defs = new_sub_element(screen, "defs")
    color_bar_clip = new_sub_element(defs, "clipPath", id="color_bar_clip")
    rgeo = _pad_rect(_SHOW_X, 0, _SHOW_WIDE, _ROOT_HIGH, rad=mask_round)
    _ = new_sub_element(color_bar_clip, "rect", **rgeo)

    masked = new_sub_element(screen, "g")

    # image
    image_wide = round(show_wide - hori_margin * 2 - palette_gap - box_wide)
    image = Image.open(filename)
    if crop:  # := crops.get(os.path.basename(filename)):
        width, height = image.size
        left = width * crop[0]
        top = height * crop[1]
        right = width * (1 - crop[2])
        bottom = height * (1 - crop[3])
        image = image.crop((left, top, right, bottom))
    image = ImageOps.fit(image, (image_wide, show_high))
    svg_image = new_sub_element(
        masked, "image", x=hori_margin, y=0, width=image_wide, height=show_high
    )
    svg_image.set(
        etree.QName(NSMAP["xlink"], "href"), _get_svg_embedded_image_str(image)
    )

    # palette
    palette_gap = _PALETTE_GAP
    boxes_high = _ROOT_HIGH - _PALETTE_GAP * (len(dist) - 1)

    box_left = show_wide - hori_margin - box_wide
    box_at = 0

    # -------------------------------------------------------------------------
    # color blocks
    # -------------------------------------------------------------------------

    def _ttl_gap(boxes: list[Any]) -> float:
        return _PALETTE_GAP * (len(boxes) - 1)

    # make all doubles the same height
    consistent_double_height = (_ROOT_HIGH - _PALETTE_GAP * 4) / 5

    hori_groups = _group_double_1s(dist)
    hori_groups = [[x] for x in dist]
    total_gap = _ttl_gap(hori_groups)
    total_doubles = sum(consistent_double_height for x in hori_groups if len(x) > 1)
    # the combined vertical space occupied by all color boxes
    boxes_high = _ROOT_HIGH - total_gap - total_doubles
    free_slices = sum(x[0] for x in hori_groups if len(x) == 1)

    box_at_y = 0
    icolors = iter(palette_colors)
    for color, group in zip(palette_colors, hori_groups):
        box_at_x = box_left
        if len(group) == 1:
            box_high = boxes_high * (group[0] / free_slices)
        else:
            box_high = consistent_double_height

        each_box_wide = (box_wide - _PALETTE_GAP * (len(group) - 1)) / len(group)
        for _ in group:
            hex_color = rgb_to_hex(next(icolors))
            _ = new_sub_element(
                masked,
                "rect",
                x=box_at_x,
                y=box_at_y,
                width=each_box_wide,
                height=box_high,
                fill=hex_color,
            )
            box_at_x += each_box_wide + _PALETTE_GAP
        box_at_y += box_high + _PALETTE_GAP


    masked.set("clip-path", "url(#color_bar_clip)")

    write_svg("temp2.svg", screen)
    # TODO: return full colstr
    # colstr = get_colors_string(palette_colors + accent_colors)
    aaa = os.listdir(Path(outfile).parent)
    # if any(colstr in x for x in aaa):
    # return
    # full_name = outfile[:-4] + "_" + colstr + outfile[-4:]
    outfile = Path(outfile)
    write_svg(outfile.with_suffix(".svg"), screen)
    write_png(INKSCAPE_EXE, outfile, screen)


show_svg(
    BINARIES / "pencils.jpg",
    [(25, 25, 25), (0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)],
    BINARIES / "output.svg",
    [1, 1, 1, 1, 1, 1],
    (0, 0, 0, 0),
    "Pencils",
)
