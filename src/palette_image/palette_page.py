"""Create palette pages from image files and color lists.

Each palette is created from a list of paths to svg images created by this project.
These will have the metadata required to create palette pages in my
JekyllProjects/content folder.

Example on the bottom.

To create a new palette page (or several), call `create_new_palette_pages_on_site()`
with one or more lists of paths to svg files.

I've got 18 pallete pages now, and I'm capped at 31 with the current date-based
sorting. If you run this sometime in the future and Jekyll gives you an "invalid
date" error, you'll need to do something more robust with the palette-file date
attributes.

:author: Shay Hill
:created: 2022-12-22
"""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import cast

from titlecase import titlecase as untyped_titlecase  # type: ignore

PROJECT_ROOT = Path(__file__).parents[2]

with open(PROJECT_ROOT / "templates" / "palette", encoding="utf-8") as _f:
    _PALETTE_TEMPLATE = Template(_f.read())

with open(PROJECT_ROOT / "templates" / "palette_page", encoding="utf-8") as _f:
    _PALETTE_PAGE_TEMPLATE = Template(_f.read())

_SITE = Path.home() / "JekyllProjects" / "content"

_SITE_PALETTES = _SITE / "_palettes"
_SITE_BINARIES = _SITE / "assets" / "img" / "blog" / "ai-generated-palettes"

_SITE_PALETTES.mkdir(parents=True, exist_ok=True)
_SITE_BINARIES.mkdir(parents=True, exist_ok=True)

# words that should always be all-capped
_ALL_CAPS = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII"}

_PaletteArgs = tuple[str, list[str]]


def _titlecase(text: str) -> str:
    """Limited titlecase.titlecase with types.

    :param string_: string to titlecase
    :return: titlecased string

    Ignoring some of the titlecase.titlecase params.
    """
    return cast(str, untyped_titlecase(text))


def _slugify(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.strip()
    text = re.sub(r"[^a-z0-9]", "-", text)
    return re.sub("-+", "-", text)


@dataclass
class PaletteFilename:
    """Strings inferred from the palette filename."""

    filename: str  # e.g., "wes_anderson-moonrise_kingdom.jpg"

    def __init__(self, filename: str) -> None:
        self.filename = filename
        # e.g., "wes_anderson", "moonrise_kingdom"
        group_part, name_part = self._split_filename()
        # e.g., "Wes Anderson"
        self.group_title = self._titleize(group_part)
        # e.g., "Moonrise Mingdom"
        self.name_title = self._titleize(name_part)
        # e.g., "Wes Anderson - Moonrise Kingdom"
        self.title = f"{self.group_title} - {self.name_title}"
        # e.g., "wes-anderson"
        group_slug = _slugify(group_part)
        # e.g., "moonrise-kingdom"
        title_slug = _slugify(name_part)
        # e.g., "wes_anderson-moonrise_kingdom.jpg"
        group_file_part = group_slug.replace("-", "_")
        title_file_part = title_slug.replace("-", "_")
        self.output_filename = f"{group_file_part}-{title_file_part}.svg"
        # e.g., "palettes-wes-anderson.md"
        self.md_page_filename = f"palettes-{group_slug}.md"

    def _split_filename(self) -> tuple[str, str]:
        """Split the filename into a group and palette name.

        :return: (group, name), e.g., ("wes_anderson", "kind_of_bird")

        I foolishly named one of my groups "avant-garde", so this is noisier than it
        has to be.
        """
        stem = Path(self.filename).stem
        phrases = stem.split("-")
        return "-".join(phrases[:-1]), phrases[-1]

    @staticmethod
    def _titleize(filename_part: str) -> str:
        """Titleize a string, e.g., "kind_of_bird" -> "Kind of Bird".

        :param filename_part: name_part or group_part, e.g., "kind_of_bird"
            or "wes_anderson"
        :return: e.g., "Kind of Bird" or "Wes Anderson"

        Replace underscores with spaces, capitalize words except articles, special
        cases for short roman numerals.
        """
        filename_part = filename_part.replace("_", " ")
        filename_part = _titlecase(filename_part)
        words = filename_part.split()
        words = [w.upper() if w.upper() in _ALL_CAPS else w for w in words]
        return " ".join(words)


import lxml
import json


def _extract_svg_data(palette: Path) -> dict[str, str | list[str] | None]:
    """Extract the svg data packed into a comment string.

    :param palette: Path to the palette file
    :return: a dict of
        'filename', 'colors', 'center', 'colornames', 'input-args', 'comment'

    The palette is an SVG file with a comment string on the second line of the file.
    """
    with open(palette, encoding="utf-8") as f:
        _ = f.readline()
        line = f.readline()
        line = line.replace("<!--", "").replace("-->", "").strip()
        return json.loads(line)


def _new_palette(filename: Path) -> str:
    """Create a new Palette object from a filename and color list.

    :param filename: filename of the palette image
    :param color_list: list of color names
    :return: markdown table-row as a string

    """
    data = _extract_svg_data(filename)
    palette_filename = PaletteFilename(filename.name)
    colornames = cast(list[str], data["colornames"])
    colors = cast(list[str], data["colors"])
    colors = [f"{n}: {c}" for n, c in zip(colornames, colors)]

    return _PALETTE_TEMPLATE.substitute(
        {
            "title": palette_filename.title,
            "image": palette_filename.output_filename,
            "colors": "<br>".join(colors),
        }
    )


def _new_palette_page(palette_page: list[Path]) -> str:
    """Create a new palette page from a list of palettes.

    :param palette_page: list of palettes
    :return: markdown table as a string

    """
    fname = PaletteFilename(palette_page[0].name)
    palettes = "\n\n".join([_new_palette(p) for p in palette_page])
    i = len(list(_SITE_PALETTES.glob("*.md"))) + 1
    return _PALETTE_PAGE_TEMPLATE.substitute(
        {
            "subtitle": fname.group_title,
            "image": fname.output_filename,
            "alt_image": PaletteFilename(palette_page[1].name).output_filename,
            "date": f"1912{i:02}",
            "palettes": palettes,
        }
    )


def _copy_palette_images_to_site(palette_page: list[Path]) -> None:
    """Copy palette images to JekyllProject.

    :param palette_page: list of palettes
    :effect: copies palette images to JekyllProject
    """
    for palette in palette_page:
        fname = PaletteFilename(palette.name)
        dest = _SITE_BINARIES / fname.output_filename
        with open(palette, "rb") as f:
            with open(dest, "wb") as dest_f:
                _ = dest_f.write(f.read())


def create_palette_pages_in_local_site(*palette_page_args: list[Path]) -> None:
    """Write new pallet-page markdown files to JekyllProject.

    :param palette_page_args: list of palette-page arguments
        (see pallete_page.py docstring)
    :effect: writes new markdown files to JekyllProject
    """
    for page_args in palette_page_args:
        _copy_palette_images_to_site(page_args)
        fname = PaletteFilename(page_args[0].name)
        page_path = _SITE_PALETTES / fname.md_page_filename
        with open(page_path, "w", encoding="utf-8") as f:
            _ = f.write(_new_palette_page(page_args))


# SOURCE_DIR = Path(
#     r"C:\Users\shaya\PythonProjects\posterize\binaries\working\palettes\done"
# )
# files = [
#     SOURCE_DIR / "J Sultan Ali - Adharma.svg",
#     SOURCE_DIR / "J Sultan Ali - Cosmic Nandi.svg",
#     SOURCE_DIR / "J Sultan Ali - Festival Bull.svg",
#     SOURCE_DIR / "J Sultan Ali - Fisher Women.svg",
#     SOURCE_DIR / "J Sultan Ali - Mother Earth.svg",
#     SOURCE_DIR / "J Sultan Ali - Original Sin.svg",
#     SOURCE_DIR / "J Sultan Ali - Toga.svg",
#     SOURCE_DIR / "J Sultan Ali - Yanadhi.svg",
# ]

# create_palette_pages_in_local_site(files)
