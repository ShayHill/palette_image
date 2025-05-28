"""Read the issued_info json file and pull all the source images into a directory.

:author: Shay Hill
:created: 2024-12-28
"""

import json
import re
import shutil
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_PYTHON_BINARIES = Path(r"C:\Users\shaya\OneDrive\python_project_binaries")
_SOURCE = _PYTHON_BINARIES / "palette" / "issued_with_source"
_PALETTE_INFO = _PROJECT_ROOT / "issued_info.json"


_SOURCE_IMAGES = _PROJECT_ROOT / "binaries" / "issued_with_source" / "source_images"


# images that were renamed by hand after creating the source text.
FOUND_BY_HAND = {"Flower - Pink Green.jpg": "Flower - Pink and Green.jpg"}


def _format_title(title: str) -> str:
    """Format 200204-Group-Name" to "Group - Name"."""
    title = re.sub(r"\d{6}\s*-\s*", "", title)
    parts = title.split("-")
    group = "-".join(parts[:-1])
    title = parts[-1].split("_")[0]
    title = re.sub(r"\(\d\)", "", title)
    return " - ".join([group, title])


def locate_source_image(title: str, image_path: str) -> Path:
    """Find the source image in _SOURCE.

    :param title: the title of the final image created from the source image. There
        may be clues in the title to help find the source image.
    :param image_path: The original cached image path from a palette text file. Many
        of these paths don't exist anymore, but the filename should be in _SOURCE.
    """
    name = Path(image_path).name
    name = FOUND_BY_HAND.get(name, name)
    candidates = list((_SOURCE / "source_images").rglob(rf"**\{name}"))
    if len(candidates) == 1:
        return candidates[0]
    candidates = list(_SOURCE.rglob(rf"**\{name}"))
    if len(candidates) == 1:
        return candidates[0]
    titled = _format_title(title) + Path(image_path).suffix
    candidates = list(_SOURCE.rglob(rf"**\{titled}"))
    if len(candidates) == 1:
        return candidates[0]
    msg = "Failed to find source image"
    raise ValueError(msg)


def copy_source_images():
    """Read issued_info.json and copy the source images to a project folder."""
    groups_seen: set[str] = set()
    with _PALETTE_INFO.open(encoding="utf-8") as f:
        infos = json.load(f)
    origins = [locate_source_image(x["title"], x["source"]) for x in infos]
    for info, orig in zip(infos, origins, strict=True):
        group, title = (x.strip() for x in _format_title(info["title"]).split(" - "))
        groups_seen.add(group)
        group_dir_name = f"{len(groups_seen)-1:03n}-{group}"
        group_dir = _SOURCE_IMAGES / group_dir_name
        group_dir.mkdir(exist_ok=True, parents=True)
        dest = (group_dir / f"{group} - {title}").with_suffix(orig.suffix)
        info["source"] = str(dest)
        shutil.copy(orig, dest)
    with _PALETTE_INFO.open("w", encoding="utf-8") as f:
        json.dump(infos, f, indent=2)


if __name__ == "__main__":
    copy_source_images()
    print("images copied")
