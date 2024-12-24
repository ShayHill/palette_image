"""Create palette pages from image files and color lists.

Each palette created from a tuple of (image_filename, color_list).

    E.g., (
        "wes_anderson-kind_of_bird.jpg",
        [
            "Merin's Fire: ff9506",
            "Trojan Horse Brown: 7b571e",
            "Minestrone: c4280d",
            "Punch of Yellow: efd185",
            "Root Brew: 2b0f0b",
            "Green Ink: 12887f",
        ]
    )

Each palette page is created from a list of such palette-arg tuples.

    E.g., [
        ("wes_anderson-kind_of_bird.jpg", [...]),
        ("wes_anderson-moonrise_kingdom.jpg", [...]),
        ...
    ]

To create a new palette page (or several), call `create_new_palette_pages()` with one
or more lists of palette-arg tuples.

The page will be written to a local Jekyll `_palettes` directory. To change
this, edit `palette_page/paths.py`.

I've got 17 pallete pages now, and I'm capped at 31 with the current date-based
sorting. If you run this sometime in the future and Jekyll gives you an "invalid
date" error, you'll need to do something more robust with the palette-file date
attributes.

:author: Shay Hill
:created: 2022-12-22
"""

from dataclasses import dataclass
from pathlib import Path
from string import Template
from typing import cast

from palette_article.paths import PROJECT_ROOT, SITE
from titlecase import titlecase as untyped_titlecase  # type: ignore

with open(PROJECT_ROOT / "templates" / "palette", encoding="utf-8") as _f:
    _PALETTE_TEMPLATE = Template(_f.read())

with open(PROJECT_ROOT / "templates" / "palette_page", encoding="utf-8") as _f:
    _PALETTE_PAGE_TEMPLATE = Template(_f.read())

_SITE_PALETTES = SITE / "_palettes"

# words that should always be all-capped
_ALL_CAPS = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII"}

_PaletteArgs = tuple[str, list[str]]


def _titlecase(string_: str) -> str:
    """Limited titlecase.titlecase with types.

    :param string_: string to titlecase
    :return: titlecased string

    Ignoring some of the titlecase.titlecase params.
    """
    return cast(str, untyped_titlecase(string_))


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
        slug = group_part.replace("_", "-")
        # e.g., "palettes-wes-anderson.md"
        self.md_page_filename = f"palettes-{slug}.md"

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


def _new_palette(filename: str, color_list: list[str]) -> str:
    """Create a new Palette object from a filename and color list.

    :param filename: filename of the palette image
    :param color_list: list of color names
    :return: markdown table-row as a string

    """
    return _PALETTE_TEMPLATE.substitute(
        {
            "title": PaletteFilename(filename).title,
            "image": filename,
            "colors": "<br>".join(color_list),
        }
    )


def _new_palette_page(i: int, palette_page: list[_PaletteArgs]) -> str:
    """Create a new palette page from a list of palettes.

    :param palette_page: list of palettes
    :return: markdown table as a string

    """
    fname = PaletteFilename(palette_page[0][0])
    palettes = "\n\n".join(_new_palette(n, cs) for n, cs in palette_page)
    return _PALETTE_PAGE_TEMPLATE.substitute(
        {
            "subtitle": fname.group_title,
            "image": fname.filename,
            "alt_image": PaletteFilename(palette_page[1][0]).filename,
            "date": f"1912{i:02}",
            "palettes": palettes,
        }
    )


def create_palette_pages_in_local_site(*palette_page_args: list[_PaletteArgs]) -> None:
    """Write new pallet-page markdown files to JekyllProject.

    :param palette_page_args: list of palette-page arguments
        (see pallete_page.py docstring)
    :effect: writes new markdown files to JekyllProject
    """
    for i, page_args in enumerate(palette_page_args, start=1):
        fname = PaletteFilename(page_args[0][0])
        page_path = _SITE_PALETTES / fname.md_page_filename
        with open(page_path, "w", encoding="utf-8") as f:
            _ = f.write(_new_palette_page(i, page_args))
