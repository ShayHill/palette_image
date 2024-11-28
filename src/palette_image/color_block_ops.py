"""Operations for the color blocks on the right side of the palette.

Boxes are defined by a dist of integers. For example, [1, 1, 1, 1, 1, 2] would create
a stack of color blocks where the first five are the same height and the last is
twice as tall.

I bend this rule for aesthetics. Firstly, by grouping the last consecutive 1s into a
vertical stack.

00000
11111
22222
33 44
55555

Secondly, by attempting to make all such vertical stacks the same height. Thirdly, by
attempting to keep all dist=1 to the same height. Where possible, only dist values >
1 will be stretched.

:author: Shay Hill
:created: 2024-11-20
"""

from collections.abc import Iterator, Sequence

import svg_ultralight as su


def _group_double_1s(slices: list[int]) -> list[list[int]]:
    """Working from the end of a list, group first two consecutive 1s.

    :param slices: a list of integers
    :return: a list of lists of integers, where each list is a single integer or [1, 1]

    Given a list of integers, when 1, 1 appears, group them together as [1, 1]. Group
    other values as singles.

        >>> _group_double_1s([1, 2, 3, 4, 1, 1])
        [[1], [2], [3], [4], [1, 1]]

    Starts from -1 and stops after the first [1, 1] is created.
    Slices = [1, 1, 1, 1, 1, 2] -> [[1], [1], [1], [1, 1], [2]]
    """
    groups: list[list[int]] = []
    for i in reversed(slices):
        if any(len(x) > 1 for x in groups):
            groups.append([i])
            continue
        if i == 1 and groups and groups[-1] == [1]:
            groups[-1].append(1)
        else:
            groups.append([i])
    return list(reversed(groups))


def _divvy_height(
    bbox: su.BoundingBox,
    groups: list[list[int]],
    *,
    locks: Sequence[tuple[list[int], float]] | None = None,
) -> list[float]:
    """Divide a height into segments based on vertical groupings.

    :param bbox: the bounding box to divide vertically
    :param groups: a list of horizontal groupings. The output of _group_double_1s
    :param locks: a list of tuples. Each tuple is a group and a height. For any g, h
        in locks, the height of g will be set to h. If None, the default is to set
        [1] to half the width and [1, 1] to the full width. List locks in order of
        priority, starting with the highest priority. If all groups are locked, there
        won't be any groups to scale to fill the bbox height, so divvy_height will
        remove locks from the right of the lock sequence until scalable groups are
        found.

    :return: a list of heights summing to bbox.height

    _group_double_1s will group consecutive 1s in a dist into a double. This mimics
    some of the earlier palette images in my project. Possible returned values are
    [[3], [4], [1, 1]], [[3], [4], [2], [1]], etc. Where possible, [1, 1], and [1]
    are set to specific heights, whereas [2], [3], [4], [5], etc. are allowed to
    stretch to fill the vertical space.

    As of right now, _group_double_1s is intentionally restricted from producing any
    grouping (like [[1], [1, 1]]) that would prevent locking all singles and doubles,
    but I created this function to handle any conceivable grouping _group_double_1s
    might produce in the future.

    What _group_double_1s will never do (because nothing is implemented for this) is
    create a group longer than 2 or a group of two with any values other than 1.
    """
    if not groups:
        msg = "No groups to divvy in divvy_height."
        raise ValueError(msg)
    if locks is None:
        single_height = bbox.width / 2
        double_height = bbox.width
        locks = [([1, 1], double_height), ([1], single_height)]

    heights: list[float | None] = [None] * len(groups)

    def zip_hg() -> Iterator[tuple[float | None, list[int]]]:
        return zip(heights, groups, strict=True)

    for lock in locks:
        heights = [lock[1] if g == lock[0] else h for h, g in zip_hg()]

    if None not in heights:
        if not locks:
            msg = "Failed to find scalable groups in divvy_height."
            raise RuntimeError(msg)
        return _divvy_height(bbox, groups, locks=locks[:-1])

    free_height = bbox.height - sum(filter(None, heights))
    free_slices = [sum(g) for h, g in zip_hg() if h is None]
    scale = free_height / sum(free_slices)
    for i, height in enumerate(heights):
        heights[i] = height if height is not None else free_slices.pop(0) * scale

    if None in heights:
        msg = "Failed to fill bbox height in divvy_height."
        raise RuntimeError(msg)
    return list(filter(None, heights))


def position_blocks(bbox: su.BoundingBox, dist: list[int]) -> Iterator[su.BoundingBox]:
    """Yield a BoundingBox for each block in the palette."""
    groups = _group_double_1s(dist)
    heights = _divvy_height(bbox, groups)

    at_y = bbox.y
    for group, height in zip(groups, heights, strict=True):
        at_x = bbox.x
        for width in (bbox.width * g / len(group) for g in group):
            yield su.BoundingBox(at_x, at_y, width, height)
            at_x += width
        at_y += height
