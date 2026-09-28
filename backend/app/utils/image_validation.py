from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError


SUPPORTED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
SUPPORTED_MIME_TYPES = set(SUPPORTED_FORMATS.values()) | {"image/jpg", "application/octet-stream"}


class ImageValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class ValidatedImage:
    width: int
    height: int
    image_format: str
    mime_type: str


def validate_image_file(path: Path, declared_mime_type: str | None) -> ValidatedImage:
    if declared_mime_type and declared_mime_type not in SUPPORTED_MIME_TYPES:
        raise ImageValidationError("unsupported_type", "Please choose a JPG, PNG, or WEBP image.")
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image_format = image.format or ""
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError):
        raise ImageValidationError("invalid_image", "This file is not a readable image.") from None

    if image_format not in SUPPORTED_FORMATS:
        raise ImageValidationError("unsupported_type", "Please choose a JPG, PNG, or WEBP image.")
    return ValidatedImage(width=width, height=height, image_format=image_format, mime_type=SUPPORTED_FORMATS[image_format])
