#!/usr/bin/env python3
"""Organize colornames from https://github.com/meodai/color-names/tree/master/dist

:author: Shay Hill
:created: 5/22/2020
"""

from contextlib import suppress
from pathlib import Path

from basic_colormath import float_tuple_to_8bit_int_tuple, get_sqeuclidean

from palette.color_conversion import hex_to_rgb

_RGB = tuple[float, float, float]
_RGB8Bit = tuple[int, int, int]
_RGB2Bit = tuple[int, int, int]

# from palette.color_type import Color

COLORNAMES = Path(__file__, "..", "..", "..", "resources/colornames.csv").resolve()


def _get_key(rgb: _RGB) -> _RGB2Bit:
    """A color is represented by 2 bits for each channel.

    :param color: a color in rgb ([0, 255], [0, 255], [0, 255])
    :return: a color in 2-bit rgb ([0, 3], [0, 3], [0, 3])
    """
    rgb_8bit_ints = float_tuple_to_8bit_int_tuple(rgb)
    red, grn, blu = (x >> 6 for x in rgb_8bit_ints)
    return red, grn, blu


def _map_2bit_rep_to_colors():
    """Map 2-bit color representation to (name, rgb) tuples.

    :return: a dict mapping 2-bit color representation to (name, rgb) tuples.

    This is used to narrow the search for the closest color name.
    """
    # filenam lines are like "white,#ffffff\n"
    with open(COLORNAMES, encoding="utf-8") as namefile:
        colornames = namefile.readlines()
        colornames = [x.rstrip("\n") for x in colornames]

    name_col = [x.split(",") for x in colornames]
    close2name: dict[_RGB2Bit, list[tuple[str, _RGB8Bit]]] = {}
    for name, col in name_col:
        with suppress(ValueError):
            col = hex_to_rgb(col)
            key = _get_key(col)
            try:
                close2name[key].append((name, col))
            except KeyError:
                close2name[key] = [(name, col)]
    return close2name


_color_candidates = _map_2bit_rep_to_colors()


def get_color_name(rgb: _RGB | str):
    """Get the closest color name for a given rgb.

    :param rgb: a color in rgb ([0, 255], [0, 255], [0, 255])
    :return: the closest color name
    """
    if isinstance(rgb, str):
        rgb = hex_to_rgb(rgb)
    try:
        candidates = _color_candidates[_get_key(rgb)]
    except KeyError:
        return "mud"
    winning_name, _ = min(candidates, key=lambda x: get_sqeuclidean(rgb, x[1]))
    return winning_name


def get_color_names_hex(palette_str: str) -> list[str]:
    """From a string of palette rgb values, return a list of colors.

    :param palette_str: e.g., ffffff-123324-12ff22
    :return: one color name for every 16-bit hex value
    """
    color_names: list[str] = []
    for color in palette_str.split("-"):
        col_name = get_color_name(color)
        color_names.append(f"{col_name}: {color}")
    return color_names


# TODO: delete this if not needed
# def get_color_names(palette_str: str) -> list[str]:
#     """
#     From a string of palette rgb values, return a list of colors.

#     :param palette_str: {x:03n} for every color channel.
#         I.e.: '000001244030055012' for colors (0, 1, 244), (30, 55, 12)
#     :return: one color name for every nine chars

#     Output palette png files should have a 54-character suffix with color information
#     from the palette. This will take that information and produce a text description
#     of each color. Something like:

#     Chocolate Moment: 97836a
#     Dried Dates: 4a4438
#     Ceylonese: 776855
#     Asphalt Blue: 474a55
#     Red Hook: 855947
#     Pure Cashmere: aca296
#     """
#     color_names = []
#     for color in (palette_str[i : i + 9] for i in range(0, len(palette_str), 9)):
#         assert len(color) == 9
#         rgb = [int(color[i : i + 3]) for i in range(0, 9, 3)]
#         breakpoint()
#         col_name = get_color_name(rgb)
#         hex_name = "{:02x}{:02x}{:02x}".format(*rgb)
#         color_names.append(f"{col_name}: {hex_name}")
#     return color_names
