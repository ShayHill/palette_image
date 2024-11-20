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
from typing import Any, List, Sequence, Iterator
from svg_ultralight import BoundingBox

from lxml import etree
from lxml.etree import _Element as EtreeElement  # type: ignore
from PIL import Image, ImageOps
from PIL.Image import Image as ImageType
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
_PADDING = max(1, _RESOLUTION / 15)


# inferred values
_ROOT_WIDE = _RATIO[0] * _RESOLUTION
_ROOT_HIGH = _RATIO[1] * _RESOLUTION


def _expand_pad(pad: float | tuple[float, ...]) -> tuple[float, float, float, float]:
    """Expand a pad argument into a 4-tuple."""
    if isinstance(pad, (int, float)):
        return pad, pad, pad, pad
    if len(pad) == 1:
        return pad[0], pad[0], pad[0], pad[0]
    if len(pad) == 2:
        return pad[0], pad[1], pad[0], pad[1]
    if len(pad) == 3:
        return pad[0], pad[1], pad[2], pad[1]
    return pad[0], pad[1], pad[2], pad[3]


def _padded_bbox(bbox: BoundingBox, pad: float | tuple[float, ...] = 0) -> BoundingBox:
    """Pad a bounding box.

    :param bbox: the bounding box to pad
    :param pad: the padding to add to the bounding box
        (top, right, bottom, left)
    :return: a new padded bounding box
    """
    top, right, bottom, left = _expand_pad(pad)
    return BoundingBox(
        bbox.x - left,
        bbox.y - top,
        bbox.width + (right + left),
        bbox.height + (top + bottom),
    )


def _bbox_dict(bbox: BoundingBox) -> dict[str, float]:
    """Return the dimensions of a bounding box."""
    return {"x": bbox.x, "y": bbox.y, "width": bbox.width, "height": bbox.height}


def _bbox_tuple(bbox: BoundingBox) -> tuple[float, float, float, float]:
    """Return the dimensions of a bounding box."""
    return bbox.x, bbox.y, bbox.width, bbox.height


def _bbox_copy(
    bbox: BoundingBox,
    *,
    x: float | None = None,
    y: float | None = None,
    width: float | None = None,
    height: float | None = None,
) -> BoundingBox:
    """Return a new bounding box with updated dimensions."""
    return BoundingBox(
        x if x is not None else bbox.x,
        y if y is not None else bbox.y,
        width if width is not None else bbox.width,
        height if height is not None else bbox.height,
    )


# _HORI_MARGIN = round(_HORI_MARGIN_SCALE * _RESOLUTION)
# _PALETTE_GAP = round(_PALETTE_GAP_SCALE * _RESOLUTION)
# _SHOW_X = _HORI_MARGIN
# _SHOW_WIDE = _ROOT_WIDE - _HORI_MARGIN * 2
# # width of palette entries
# _COLS_WIDE = (_ROOT_HIGH - _PALETTE_GAP * 4) / 5


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


def _pad_and_rad_rect_args(
    x: float, y: float, width: float, height: float, *, pad: float = 0, rad: float = 0
) -> dict[str, float]:
    """Pad and rad arguments for an svg rectangle.

    :param x: the x-coordinate of the rectangle
    :param y: the y-coordinate of the rectangle
    :param width: the width of the rectangle
    :param height: the height of the rectangle
    :param pad: the amount of padding to add to each side of the rectangle
    :param rad: the corner radius of the rectangle
    :return: a dictionary of the padded rectangle's coordinates
    """
    rect_args = {
        "x": x - pad,
        "y": y - pad,
        "width": width + pad * 2,
        "height": height + pad * 2,
    }
    if rad:
        rect_args["rx"] = rect_args["ry"] = rad + pad
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
        if any(len(x) > 1 for x in groups):
            groups.append([i])
            continue
        if i == 1 and groups and groups[-1] == [1]:
            groups[-1].append(1)
        else:
            groups.append([i])
    return list(reversed(groups))


# class Geo:
# @property


def is_single(group: list[int]) -> bool:
    return group == [1]


def is_double(group: list[int]) -> bool:
    return group == [1, 1]


def divvy_height(
    bbox: BoundingBox,
    groups: list[list[int]],
    _lock_singles: bool = True,
    _lock_doubles: bool = True,
) -> list[float]:
    """Divide a height into segments based on vertical groupings.

    :param bbox: the bounding box to divide vertically
    :param groups: a list of horizontal groupings. The output of _group_double_1s

    # don't use these. For recursion only
    :param _lock_singles: whether to lock [1] groups to a specific height
    :param _lock_doubles: whether to lock [1, 1] groups to a specific height

    :return: a list of heights

    _group_double_1s will group consecutive 1s in a dist into a double. This mimics
    some of the earlier palette images in my project. Possible returned values are
    [[3], [4], [1, 1]], [[3], [4], [2], [1]], etc. Where possible, [1, 1], and [1]
    are set to specific heights, whereas [2], [3], [4], [5], etc. are allowed to
    stretch to fill the vertical space.

    As of right now, _group_double_1s is intentionally restricted from producing any
    grouping (like [[1], [1, 1]]) that would prevent locking all singles and doubles,
    but I created this function to handle any conceivable grouping _group_double_1s
    might produce in the future.

    What _group_double_1s will never do (because nothing is implemented for this) is
    create a group longer than 2 or a group of two with any values other than 1.
    """
    single_height = bbox.width / 2
    double_height = bbox.width
    heights: list[float | None] = [None] * len(groups)

    def zip_hg() -> Iterator[tuple[float | None, list[int]]]:
        return zip(heights, groups)

    if _lock_singles:
        heights = [single_height if is_single(g) else h for h, g in zip_hg()]
    if _lock_doubles:
        heights = [double_height if is_double(g) else h for h, g in zip_hg()]

    if None not in heights:
        # nothing to stretch - try (False, True) then (False, False)
        return divvy_height(bbox, groups, False, _lock_singles)

    free_height = bbox.height - sum(filter(None, heights))
    per_slice = free_height / sum(sum(g) for h, g in zip_hg() if h is None)
    heights = [h or sum(g) * per_slice for h, g in zip_hg()]

    return list(filter(None, heights))


# TODO: this works but it's a mess
def show_svg(
    filename: Path | str,
    palette_colors: Sequence[_RGB],
    outfile: Path,
    dist: List[int],
    crop: tuple[float, float, float, float],
    comment: str,
    # hori_margin_scale: float = _HORI_MARGIN_SCALE,
    # palette_gap_scale: float = _PALETTE_GAP_SCALE,
    # resolution: float = _RESOLUTION,
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

    root_bbox = BoundingBox(0, 0, _ROOT_WIDE, _ROOT_HIGH)
    content_bbox = _padded_bbox(root_bbox, -_PADDING)
    palette_gap = _PALETTE_GAP_SCALE * _RESOLUTION

    # ugly formula just de-parameterizes previous way of calculating box_wide from
    # number of palette entries. box_wide is now fixed for any number of palette
    # entries.
    box_wide = (content_bbox.height - palette_gap * 4) / 5

    # TODO: make global
    mask_round = _RESOLUTION / 4

    screen = new_svg_root(*_bbox_tuple(root_bbox), print_width_=root_bbox.width / 2)
    if comment:
        screen.append(etree.Comment(comment))

    # white background behind entire image
    rgeo = _pad_and_rad_rect_args(*_bbox_tuple(root_bbox), rad=mask_round + _PADDING)
    _ = new_sub_element(screen, "rect", **rgeo, fill="white")

    # palette rounded corners mask
    defs = new_sub_element(screen, "defs")
    color_bar_clip = new_sub_element(defs, "clipPath", id="color_bar_clip")
    rgeo = _pad_and_rad_rect_args(**_bbox_dict(content_bbox), rad=mask_round)
    _ = new_sub_element(color_bar_clip, "rect", **rgeo)

    masked = new_sub_element(screen, "g")

    # image
    image_bbox = _padded_bbox(content_bbox, (0, -(palette_gap + box_wide), 0, 0))
    image = Image.open(filename)
    # if crop:  # := crops.get(os.path.basename(filename)):
    #     width, height = image.size
    #     left = width * crop[0]
    #     top = height * crop[1]
    #     right = width * (1 - crop[2])
    #     bottom = height * (1 - crop[3])
    #     image = image.crop((left, top, right, bottom))
    image = ImageOps.fit(image, (round(image_bbox.width), round(image_bbox.height)))
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

    # palette
    # palette_gap = round(_PALETTE_GAP_SCALE * _RESOLUTION)

    # -------------------------------------------------------------------------
    # color blocks
    # -------------------------------------------------------------------------

    blocks_bbox = _padded_bbox(
        content_bbox, (0, 0, 0, -(image_bbox.width + palette_gap))
    )
    blocks_bbox = _padded_bbox(blocks_bbox, palette_gap / 2)

    hori_groups = _group_double_1s(dist)
    heights = divvy_height(blocks_bbox, hori_groups)

    blocks: list[BoundingBox] = []
    for height, block in zip(heights, hori_groups):
        if len(block) == 1:
            block_bbox = _bbox_copy(blocks_bbox, height=height)
            if blocks:
                block_bbox.y = blocks[-1].y2
            blocks.append(block_bbox)
        else:
            width = blocks_bbox.width / 2
            block_a_bbox = _bbox_copy(blocks_bbox, width=width, height=height)
            if blocks:
                block_a_bbox.y = blocks[-1].y2
            block_b_bbox = _bbox_copy(block_a_bbox)
            block_b_bbox.x = block_a_bbox.x2
            blocks += [block_a_bbox, block_b_bbox]

    icolors = iter(palette_colors)
    for block in (_padded_bbox(x, -palette_gap / 2) for x in blocks):
        hex_color = rgb_to_hex(next(icolors))
        _ = new_sub_element(masked, "rect", **_bbox_dict(block), fill=hex_color)

    masked.set("clip-path", "url(#color_bar_clip)")

    # write_svg("temp2.svg", screen)
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
