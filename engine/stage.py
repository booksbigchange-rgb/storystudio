"""Canvas settings shared by StoryStudio preview and video rendering.

Missing canvas metadata means legacy 1080x1920 Fill, preserving project v1.
"""
from math import isfinite

PRESETS = {
    "Portrait 9:16": (1080, 1920),
    "Landscape 16:9": (1920, 1080),
    "Square 1:1": (1080, 1080),
}
DEFAULT = {"width": 1080, "height": 1920, "fit": "fill"}
FIT_MODES = ("fill", "fit")


def validate_canvas(raw=None):
    if raw is None:
        return dict(DEFAULT)
    if not isinstance(raw, dict):
        raise ValueError("Canvas must be an object")
    try:
        width, height = int(raw.get("width", 1080)), int(raw.get("height", 1920))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Canvas width and height must be integers") from exc
    if (not 64 <= width <= 3840 or not 64 <= height <= 3840
            or width % 2 or height % 2 or width * height > 3840 * 2160):
        raise ValueError("Canvas dimensions must be even, 64..3840 and at most 8.3 million pixels")
    fit = raw.get("fit", "fill")
    if fit not in FIT_MODES:
        raise ValueError("Fit mode must be 'fill' or 'fit'")
    return {"width": width, "height": height, "fit": fit}


def resized_background(image, width, height, fit):
    """Return centered RGBA background. For Fit, use a dark matte."""
    from PIL import Image, ImageOps
    if fit == "fill":
        return ImageOps.fit(image.convert("RGBA"), (width, height),
                            method=Image.Resampling.LANCZOS)
    if fit != "fit":
        raise ValueError("Fit mode must be 'fill' or 'fit'")
    scaled = ImageOps.contain(image.convert("RGBA"), (width, height),
                              method=Image.Resampling.LANCZOS)
    background = Image.new("RGBA", (width, height), (20, 24, 32, 255))
    background.alpha_composite(scaled, ((width - scaled.width) // 2,
                                        (height - scaled.height) // 2))
    return background
