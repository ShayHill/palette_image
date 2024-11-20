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

from collections.abc import Iterator

from palette_image.type_bbox import Bbox


def group_double_1s(slices: list[int]) -> list[list[int]]:
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


def _is_single(group: list[int]) -> bool:
    """Identify singles in divvy_height."""
    return group == [1]


def _is_double(group: list[int]) -> bool:
    """Identify doubles in divvy_height."""
    return group == [1, 1]


def divvy_height(
    bbox: Bbox,
    groups: list[list[int]],
    *,
    _lock_singles: bool = True,
    _lock_doubles: bool = True,
) -> list[float]:
    """Divide a height into segments based on vertical groupings.

    :param bbox: the bounding box to divide vertically
    :param groups: a list of horizontal groupings. The output of _group_double_1s

    # don't use these. For recursion only
    :param _lock_singles: whether to lock [1] groups to a specific height
    :param _lock_doubles: whether to lock [1, 1] groups to a specific height

    :return: a list of heights

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
    single_height = bbox.width / 2
    double_height = bbox.width
    heights: list[float | None] = [None] * len(groups)

    def zip_hg() -> Iterator[tuple[float | None, list[int]]]:
        return zip(heights, groups, strict=True)

    if _lock_singles:
        heights = [single_height if _is_single(g) else h for h, g in zip_hg()]
    if _lock_doubles:
        heights = [double_height if _is_double(g) else h for h, g in zip_hg()]

    if None not in heights:
        # nothing to stretch - try (False, True) then (False, False)
        return divvy_height(
            bbox, groups, _lock_singles=False, _lock_doubles=_lock_singles
        )

    free_height = bbox.height - sum(filter(None, heights))
    per_slice = free_height / sum(sum(g) for h, g in zip_hg() if h is None)
    heights = [h or sum(g) * per_slice for h, g in zip_hg()]

    return list(filter(None, heights))
