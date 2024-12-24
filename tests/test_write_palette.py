"""Pass arguments to write_palette.

:author: Shay Hill
:created: 2024-12-23
"""

from conftest import TEST_RESOURCES

from palette_image import svg_display

TEST_IMAGE = TEST_RESOURCES / "Sam Francis - Middle Blue.jpg"

TEST_COLORS = ["382736", "005780", "d05100", "d0b890", "10a8b0", "205031"]


class TestRun:
    def test_run(self):
        svg_display.write_palette(TEST_IMAGE, TEST_COLORS, "output.png", [1, 1, 1, 1, 1, 1])

        # write_palette(TEST_IMAGE, "output.png")
        # assert Path("output.png").exists()
        # Path("output.png").unlink()
