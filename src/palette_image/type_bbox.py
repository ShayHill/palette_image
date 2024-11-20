"""A bounding box for positioning svg elements.

The BoundingBox type from svg_ultralight is limited to operations that make sense for
bounding an svg element. BoundingBox setters do not alter the BoundingBox instance,
they just update a transformation matrix, so transformations that cannot be expressed
as transformation matrices are not implemented in BoundingBox. Even some
transformations that *can* be expressed as transformation matrices are intentionally
not implemented. One big example is non-uniform scaling.  If you set
BoundingBox.width, you update the BoundingBox._transformation to scale both width and
height.

I'm using BoundingBox here, because it is will tested, but I'm extending it to create
copies of itself with non-matrix transformations.

:author: Shay Hill
:created: 2024-11-20
"""

from svg_ultralight import BoundingBox
from typing import Self

def _expand_pad(pad: float | tuple[float, ...]) -> tuple[float, float, float, float]:
    """Expand a pad argument into a 4-tuple."""
    if isinstance(pad, (int, float)):
        return pad, pad, pad, pad
    if len(pad) == 1:
        return pad[0], pad[0], pad[0], pad[0]
    if len(pad) == 2:
        return pad[0], pad[1], pad[0], pad[1]
    if len(pad) == 3:
        return pad[0], pad[1], pad[2], pad[1]
    return pad[0], pad[1], pad[2], pad[3]


class Bbox(BoundingBox):
    """Extend svg_ultralight.BoundingBox with a few copy methods.

    Implement some getters for unpacking bounding box arguments into functions.
    """

    @property
    def dict(self) -> dict[str, float]:
        """Return the dimensions of a bounding box."""
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @property
    def values(self) -> tuple[float, float, float, float]:
        """Return the dimensions of a bounding box."""
        x, y, width, height = self.dict.values()
        return x, y, width, height

    def reset_dims(
        self, *, width: float | None = None, height: float | None = None
    ) -> Self:
        """Return a new bounding box with updated dimensions."""
        width = self.width if width is None else width
        height = self.height if height is None else height
        return type(self)(self.x, self.y, width, height)

    def reset_lims(
        self,
        *,
        x: float | None = None,
        y: float | None = None,
        x2: float | None,
        y2: float | None,
    ) -> Self:
        """Return a new bounding box with updated limits."""
        x = self.x if x is None else x
        y = self.y if y is None else y
        x2 = self.x2 if x2 is None else x2
        y2 = self.y2 if y2 is None else y2
        width = x2 - x
        height = y2 - y
        return type(self)(x, y, width, height)

    def pad(self, pad: float | tuple[float, ...]) -> Self:
        """Return a new bounding box with padding."""
        top, right, bottom, left = _expand_pad(pad)
        return self.reset_lims(
            x=self.x - left, y=self.y - top, x2=self.x2 + right, y2=self.y2 + bottom
        )

    def copy(self) -> Self:
        """Return a copy of this bounding box after applying transforms."""
        return type(self)(self.x, self.y, self.width, self.height)
