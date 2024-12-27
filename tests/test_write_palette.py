"""Pruebas de percepción para diseños de barras de colores.

:author: Shay Hill
:created: 2024-12-23
"""

from conftest import TEST_OUTPUT, TEST_RESOURCES

from palette_image import svg_display
from palette_image.color_block_ops import (
    avant_garde_color_blocks,
    avant_garde_color_blocks_args,
    classic_color_blocks,
    classic_color_blocks_args,
    sliver_color_blocks, sliver_color_blocks_args
)
import itertools as it

TEST_IMAGE = TEST_RESOURCES / "Sam Francis - Middle Blue.jpg"

TEST_COLORS = ["#382736", "#005780", "#d05100", "#d0b890", "#10a8b0", "#205031"]


class TestLayouts:
    """Tests (some perceptual) for color-bar layouts."""

    def test_classic_args(self):
        """Ignore the dist argument."""
        color_blocks_args = classic_color_blocks_args(TEST_COLORS, list(range(1, 7)))
        assert color_blocks_args[0] == TEST_COLORS
        assert color_blocks_args[1] == [[1], [1], [1], [1], [1, 1]]

    def test_classic(self):
        """Ignore the dist argument."""
        color_blocks = classic_color_blocks(TEST_COLORS, list(range(1, 7)))
        outfile = TEST_OUTPUT / "classic.svg"
        svg_display.write_palette(TEST_IMAGE, color_blocks, outfile)

    def test_avant_garde_args_no_dist(self):
        """Fall back to classic layout if no dist argument."""
        color_blocks_args = avant_garde_color_blocks_args(TEST_COLORS)
        assert color_blocks_args[0] == TEST_COLORS
        assert color_blocks_args[1] == [[1], [1], [1], [1], [1, 1]]

    def test_avant_garde_no_dist(self):
        """Fall back to classic layout if no dist argument."""
        color_blocks = avant_garde_color_blocks(TEST_COLORS)
        outfile = TEST_OUTPUT / "avant_garde_no_dist.svg"
        svg_display.write_palette(TEST_IMAGE, color_blocks, outfile)

    def test_avant_garde_args_flat(self):
        """Fall back to dist when all heights are the same."""
        color_blocks_args = avant_garde_color_blocks_args(
            TEST_COLORS, [2, 2, 2, 2, 2, 2]
        )
        assert color_blocks_args[0] == TEST_COLORS
        assert color_blocks_args[1] == [[1], [1], [1], [1], [1, 1]]

    def test_avant_garde_args_small_double(self):
        """Use classic arrangement for 1s."""
        color_blocks_args = avant_garde_color_blocks_args(
            TEST_COLORS, [20, 20, 1, 1, 1, 20]
        )
        assert color_blocks_args[0] == TEST_COLORS
        assert color_blocks_args[1] == [[3], [3], [1], [1, 1], [3]]

    def test_avant_garde_small_double(self):
        """Use classic arrangement for 1s."""
        color_blocks = avant_garde_color_blocks(
            TEST_COLORS, [20, 20, 1, 1, 1, 20]
        )
        outfile = TEST_OUTPUT / "avant_garde_small_double.svg"
        svg_display.write_palette(TEST_IMAGE, color_blocks, outfile)

    def test_sliver_args_no_1s(self):
        """Fall back to avant garde layout if too many 1s."""
        color_blocks_args = sliver_color_blocks_args(TEST_COLORS, [2, 4, 6, 8, 2, 2])
        assert color_blocks_args[0] == TEST_COLORS
        assert color_blocks_args[1] == [[1], [2], [3], [4], [1, 1]]

    def test_sliver_args_flat(self):
        """Fall back to classic layout all dist equal."""
        color_blocks_args = sliver_color_blocks_args(TEST_COLORS, [2, 2, 2, 2, 2, 2])
        assert color_blocks_args[0] == TEST_COLORS
        assert color_blocks_args[1] == [[1], [1], [1], [1], [1, 1]]

    def test_sliver_args_no_endpoints_or_adjacent(self):
        """Do not allow 1s on endpoints of adjacent to 1s."""
        dist = [2, 2, 11, 11, 11, 11.0]
        for dist_ in map(list, it.permutations(dist)):
            groups = sliver_color_blocks_args(TEST_COLORS, dist_)[1]
            assert len(groups) == 6
            assert groups[0] != [1]
            assert groups[-1] != [1]
            assert (1, 1) not in list(zip(groups, groups[1:], strict=False))

    def test_sliver_perceptual(self):
        """Test a perceptual layout."""
        color_blocks = sliver_color_blocks(TEST_COLORS, [1, 2, 3, 4, 5, 6])
        outfile = TEST_OUTPUT / "sliver.svg"
        svg_display.write_palette(TEST_IMAGE, color_blocks, outfile)




