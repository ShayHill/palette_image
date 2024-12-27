"""Pass arguments to write_palette.

:author: Shay Hill
:created: 2024-12-23
"""

from conftest import TEST_RESOURCES

from palette_image import svg_display
from palette_image.color_block_ops import classic_color_blocks, avant_garde_color_blocks, sliver_color_blocks


TEST_IMAGE = TEST_RESOURCES / "Sam Francis - Middle Blue.jpg"

TEST_COLORS = ["382736", "005780", "d05100", "d0b890", "10a8b0", "205031"]


class TestRun:
    def test_run(self):
        color_blocks = classic_color_blocks(TEST_COLORS)
        color_blocks = sliver_color_blocks(TEST_COLORS, [1, 1, 1, 1, 1, 1])
        svg_display.write_palette(TEST_IMAGE, color_blocks, "output.png")

        # write_palette(TEST_IMAGE, "output.png")
        # assert Path("output.png").exists()
        # Path("output.png").unlink()f
