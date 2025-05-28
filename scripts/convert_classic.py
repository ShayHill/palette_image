"""Convert old classic palettes from their txt files.

:author: Shay Hill
:created: 2024-12-27
"""

import dataclasses
import json
import re
from pathlib import Path
from typing import Iterator, TypeAlias

Title: TypeAlias = str
Colors: TypeAlias = list[str]
Source: TypeAlias = Path

_PROJECT_ROOT = Path(__file__).parent.parent
_PYTHON_BINARIES = Path(r"C:\Users\shaya\OneDrive\python_project_binaries")
_SOURCE = _PYTHON_BINARIES / "palette" / "issued_with_source"
_PALETTE_INFO = _PROJECT_ROOT / "issued_info.json"

_SOURCE_IMAGES = _PROJECT_ROOT / "binaries" / "issued_with_source" / "source_images"

_COLOR_LINE = re.compile(r"^[^:]+:\s*(?P<hex>[0-9a-fA-F]{6})")
_SOURCE_LINE = re.compile(r"^[^:]*source:\s*(?P<source>.*)")


@dataclasses.dataclass
class PaletteInfo:
    """Everything required to create a palette image."""

    title: str
    colors: list[str]
    source: str
    dist: list[float] | None


def iter_palette_txt_files() -> Iterator[Path]:
    yield from _SOURCE.rglob("*.txt")


def extract_args_from_palette_txt_file(txt_file: Path) -> tuple[Title, Colors, Source]:
    with open(txt_file, encoding="utf-8") as f:
        lines = f.readlines()
    color_lines = filter(None, (_COLOR_LINE.match(x) for x in lines))
    colors = ["#" + str(m["hex"].lower()) for m in color_lines]

    source_line = next(filter(None, (_SOURCE_LINE.match(x) for x in lines)))
    source_path = Path(source_line["source"])
    return txt_file.stem, colors, source_path


def create_issued_info() -> None:
    """Create `issued_info.json`."""
    infos: list[PaletteInfo] = []
    for d in iter_palette_txt_files():
        title, colors, source = extract_args_from_palette_txt_file(d)
        if len(colors) == 7:
            print(f"warning: do something about 7 colors in {title}")
        infos.append(PaletteInfo(title, colors, str(source), None))
    with _PALETTE_INFO.open("w", encoding="utf-8") as f:
        json.dump([x.__dict__ for x in infos], f, indent=2)
    print("'issued_info.json' created")
