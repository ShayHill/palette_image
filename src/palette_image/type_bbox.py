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

from typing import Self
import svg_ultralight as su

from lxml.etree import _Element as EtreeElement  # type: ignore
from PIL.Image import Image as ImageType
from svg_ultralight import BoundingBox
from svg_ultralight.constructors import new_element


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
    def as_dict(self) -> dict[str, float]:
        """Return the dimensions of a bounding box."""
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @property
    def values(self) -> tuple[float, float, float, float]:
        """Return the dimensions of a bounding box."""
        x, y, width, height = self.as_dict.values()
        return x, y, width, height

    def get_rect_args(self, rad: float, fill: str = "") -> dict[str, float]:
        """Return the arguments for drawing a rectangle."""
        if rad == 0:
            return self.as_dict
        return {**self.as_dict, "rx": rad, "ry": rad}

    def get_rect(self, rad: float = 0, fill: str = "") -> EtreeElement:
        """Return an svg rectangle element."""
        rect_args = self.as_dict
        if rad:
            rect_args.update({"rx": rad, "ry": rad})
        return new_element("rect", **rect_args, fill=fill)

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
        x2: float | None = None,
        y2: float | None = None,
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


def _symmetric_crop(
    image: ImageType, center: tuple[float, float] | None = None
) -> ImageType:
    """Crop an image symmetrically around a center point.

    :param image: PIL.Image instance
    :param center: optional center point for cropping. Proportions of image with and
        image height, so the default value, (0.5, 0.5), is the true center of the
        image. (0.4, 0.5) would crop 20% off the right side of the image.
    :return: PIL.Image instance
    """
    if center is None:
        return image
    assert all(0 < x < 1 for x in center), "center must be between 0 and 1"
    xd, yd = (min(x, 1 - x) for x in center)
    left, right = sorted(x * image.width for x in (center[0] - xd, center[0] + xd))
    top, bottom = sorted(x * image.height for x in (center[1] - yd, center[1] + yd))
    assert right > left
    assert bottom > top
    return image.crop((left, top, right, bottom))


def fit_image_to_bbox_ratio(
    image: ImageType, bbox: su.BoundingBox, center: tuple[float, float] | None = None
) -> ImageType:
    """Crop an image to the ratio of a bounding box.

    :param image: PIL.Image instance
    :param bbox: Bbox instance
    :param center: optional center point for cropping. Proportions of image with and
        image height, so the default value, (0.5, 0.5), is the true center of the
        image. (0.4, 0.5) would crop 20% off the right side of the image.
    :return: PIL.Image instance

    This crops the image to the specified ratio. It's not a resize, so it will cut
    off the top and bottom or the sides of the image to fit the ratio.
    """
    image = _symmetric_crop(image, center)
    width, height = image.size

    ratio = bbox.width / bbox.height
    if width / height > ratio:
        new_width = height * ratio
        left = (width - new_width) / 2
        right = width - left
        return image.crop((left, 0, right, height))
    new_height = width / ratio
    top = (height - new_height) / 2
    bottom = height - top
    return image.crop((0, top, width, bottom))
