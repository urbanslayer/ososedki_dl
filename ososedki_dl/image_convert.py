"""WebP to JPEG conversion for downloaded images."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from core_helpers.logs import logger
from PIL import Image, UnidentifiedImageError

from .consts import DEFAULT_JPEG_QUALITY

TRANSPARENT_MODES: set[str] = {"RGBA", "LA"}


def _flatten_onto_white(img: Image.Image) -> Image.Image:
    """Composites a transparent image onto a white background and drops alpha."""
    rgba: Image.Image = img.convert("RGBA")
    background: Image.Image = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.split()[-1])
    return background


def convert_webp_to_jpg(
    path: Path, quality: int = DEFAULT_JPEG_QUALITY
) -> Path | None:
    """
    Converts a WebP image to a JPEG next to it, deleting the WebP on success.

    Transparent images (RGBA/LA, or P with a transparency entry) are
    composited onto a white background first, since JPEG has no alpha
    channel. Animated WebPs are left untouched, since a JPEG can only keep
    the first frame. EXIF/ICC metadata is carried over when present. The
    JPEG is written to a temporary file and atomically renamed, so an
    interrupted run never leaves a half-written .jpg behind.

    Args:
        path (Path): Path to the source .webp file.
        quality (int): JPEG quality to save at. Defaults to
            `DEFAULT_JPEG_QUALITY`.

    Returns:
        Path | None: The path to the new .jpg file on success, or None if
            the image was animated (and thus skipped) or conversion failed.
            In both cases, the original .webp file is left untouched.
    """
    jpg_path: Path = path.with_suffix(".jpg")
    tmp_path: Path = jpg_path.with_name(f"{jpg_path.name}.{uuid4().hex}.tmp")

    try:
        with Image.open(path) as img:
            if getattr(img, "is_animated", False):
                logger.info(f"Skipping conversion of animated WebP: {path}")
                return None

            img.load()

            save_kwargs: dict[str, object] = {"quality": quality, "optimize": True}
            if exif := img.info.get("exif"):
                save_kwargs["exif"] = exif
            if icc_profile := img.info.get("icc_profile"):
                save_kwargs["icc_profile"] = icc_profile

            if img.mode in TRANSPARENT_MODES or (
                img.mode == "P" and "transparency" in img.info
            ):
                rgb_img: Image.Image = _flatten_onto_white(img)
            else:
                rgb_img = img.convert("RGB")

            rgb_img.save(tmp_path, "JPEG", **save_kwargs)

        tmp_path.replace(jpg_path)
    except (OSError, UnidentifiedImageError, ValueError) as e:
        logger.warning(f"Failed to convert {path} to JPG, keeping original: {e}")
        tmp_path.unlink(missing_ok=True)
        return None

    try:
        path.unlink()
    except OSError as e:
        logger.warning(f"Converted {path} to JPG but failed to delete original: {e}")

    logger.info(f"Converted {path} to {jpg_path}")
    return jpg_path
