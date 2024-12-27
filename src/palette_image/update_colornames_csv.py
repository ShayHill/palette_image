"""Download the colornames.csv file from the meodai/color-names GitHub repository.

Checking for an updated hash takes almost as long as updating the file itself, so
this script just checks if the last write happened today and overwrites
resources/colornames.csv with GitHub's meodai/color-names version if not. This script
should be run every time palette colornames are needed. It should take ery nearly 0
seconds to check if the file is up to date, and under 1 second to download the file
if it is not.

:author: Shay Hill
:created: 2024-11-28
"""

import datetime
import sys
import warnings
from contextlib import suppress

import requests

from palette_image.globs import CACHE_DIR, COLORNAMES_CSV

today = str(datetime.datetime.now(tz=datetime.UTC).date())

_COLORNAMES_CSV_URL = (
    "https://raw.githubusercontent.com/meodai/"
    + "color-names/refs/heads/master/dist/colornames.csv"
)

_DATE_CHECKED_CACHE = CACHE_DIR / "colornames_date_checked_cache.txt"


def _clear_cache() -> None:
    """Clear the commit hash and date checked caches."""
    with suppress(FileNotFoundError):
        _DATE_CHECKED_CACHE.unlink()


def _cache_date_checked() -> None:
    """Cache the date of the last time the commit hash was checked."""
    with _DATE_CHECKED_CACHE.open("w") as f:
        _ = f.write(today)


def _read_cached_date_checked() -> str | None:
    """Get the cached date of the last time the commit hash was checked."""
    try:
        with _DATE_CHECKED_CACHE.open() as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


_REQUEST_SUCCESSFUL = 200


def _download_colornames_csv_to_resources() -> None:
    """Download the colornames.csv file from the repository."""
    response = requests.get(_COLORNAMES_CSV_URL, timeout=10)
    if response.status_code == _REQUEST_SUCCESSFUL:
        with COLORNAMES_CSV.open("w", encoding="utf-8") as f:
            _ = f.write(response.content.decode("utf-8", errors="replace") + "\n")
        _ = sys.stdout.write(f"colornames.csv downloaded to {COLORNAMES_CSV}.\n")
    else:
        msg = f"Error: Unable to download colornames.csv - {response.status_code}"
        warnings.warn(msg, stacklevel=2)


def update_colornames_csv() -> None:
    """At most once daily, check for updates to the colornames.csv file."""
    if _read_cached_date_checked() == today:
        return
    _ = sys.stdout.write("Daily update to colornames.csv\n")
    _download_colornames_csv_to_resources()
    _cache_date_checked()


if __name__ == "__main__":
    _clear_cache()
    update_colornames_csv()
