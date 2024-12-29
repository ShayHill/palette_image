"""Organize colornames from https://github.com/meodai/color-names/tree/master/dist.

The colornames file has about 30k color names. This uses brute force to find the
closest by squared Euclidean distance. Takes about a quarter of a second for six
colors.

:author: Shay Hill
:created: 5/22/2020
"""

import functools as ft

from basic_colormath import get_sqeuclidean, hex_to_rgb

from palette_image import update_colornames_csv
from palette_image.globs import COLORNAMES_CSV

update_colornames_csv.update_colornames_csv()


def _map_colornames() -> dict[tuple[float, float, float], str]:
    """Read colornames from a file.

    :return: a dict[rgb_tuple, colorname]
    """
    with COLORNAMES_CSV.open(encoding="utf-8") as namefile:
        _ = namefile.readline()  # skip header
        colornames = namefile.readlines()
    name_hex_tuples = (x.split(",") for x in colornames)
    return {hex_to_rgb(hex_): name for name, hex_ in name_hex_tuples}


rgb2colorname = _map_colornames()


def get_colorname(color: tuple[float, float, float] | str) -> str:
    """Get the closest (by Euclidean) color name for a given rgb.

    :param color: a color in rgb ([0, 255], [0, 255], [0, 255]) or hex format
    :return: the closest color name
    """
    rgb = hex_to_rgb(color) if isinstance(color, str) else color
    distance_from_color = ft.partial(get_sqeuclidean, rgb)
    closest_neighbor = min(rgb2colorname, key=distance_from_color)
    return rgb2colorname[closest_neighbor]


def get_colornames(*colors: str | tuple[float, float, float]) -> list[str]:
    """From a string of palette rgb values, return a list of colors.

    :param palette_str: e.g., ffffff-123324-12ff22
    :return: one color name for every 16-bit hex value
    """
    return [get_colorname(h) for h in colors]
