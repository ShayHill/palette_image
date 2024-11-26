"""Crop an image before converting to binary and including in the svg file.

:author: Shay Hill
:created: 2024-11-20
"""

import svg_ultralight as su
from PIL.Image import Image as ImageType


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


def crop_image_to_bbox_ratio(
    image: ImageType, bbox: su.BoundingBox, center: tuple[float, float] | None = None
) -> ImageType:
    """Crop an image to the ratio of a bounding box.

    :param image: PIL.Image instance
    :param bbox: BoundingBox instance
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
