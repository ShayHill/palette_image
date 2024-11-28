"""Crop an image before converting to binary and including in the svg file.

:author: Shay Hill
:created: 2024-11-20
"""

import base64
import io
from pathlib import Path

import svg_ultralight as su
from lxml import etree
from lxml.etree import _Element as EtreeElement  # type: ignore
from PIL import Image
from PIL.Image import Image as ImageType
from svg_ultralight import NSMAP


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

    if not all(0 < x < 1 for x in center):
        msg = "Center must be between (0, 0) and (1, 1)"
        raise ValueError(msg)

    xd, yd = (min(x, 1 - x) for x in center)
    left, right = sorted(x * image.width for x in (center[0] - xd, center[0] + xd))
    top, bottom = sorted(x * image.height for x in (center[1] - yd, center[1] + yd))

    return image.crop((left, top, right, bottom))


def _crop_image_to_bbox_ratio(
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


def _get_svg_embedded_image_str(image: ImageType) -> str:
    """Return the string you'll need to embed an image in an svg.

    :param image: PIL.Image instance
    :return: argument for xlink:href
    """
    in_mem_file = io.BytesIO()
    image.save(in_mem_file, format="PNG")
    _ = in_mem_file.seek(0)
    img_bytes = in_mem_file.read()
    base64_encoded_result_bytes = base64.b64encode(img_bytes)
    base64_encoded_result_str = base64_encoded_result_bytes.decode("ascii")
    return "data:image/png;base64," + base64_encoded_result_str


def new_image_elem_in_bbox(
    filename: Path | str, bbox: su.BoundingBox, center: tuple[float, float] | None
) -> EtreeElement:
    """Create a new svg image element inside a bounding box.

    :param filename: filename of source image
    :param bbox: bounding box for the image
    :param center: center point for cropping. Proportions of image width and image
        height, so the default value, (0.5, 0.5), is the true center of the image.
        (0.4, 0.5) would crop 20% off the right side of the image.
    :return: an etree image element with the cropped image embedded
    """
    image = _crop_image_to_bbox_ratio(Image.open(filename), bbox, center)
    svg_image = su.new_element("image", **su.bbox_dict(bbox))
    svg_image.set(
        etree.QName(NSMAP["xlink"], "href"), _get_svg_embedded_image_str(image)
    )
    return svg_image
