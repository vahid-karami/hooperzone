"""Puts the shop logo on product photos.

The logo sits small and semi-transparent in the bottom-right corner, so it brands the photo
without covering the product. The clean photo is kept (ProductImage.original), so the logo can
be re-rendered or removed at any time.
"""
import io
import logging
from pathlib import Path

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

LOGO_DIR = Path(__file__).resolve().parent / "assets" / "watermark"
LOGO_ON_LIGHT = LOGO_DIR / "logo.png"  # navy
LOGO_ON_DARK = LOGO_DIR / "logo-white.png"

MAX_SIDE = 2000  # larger uploads are scaled down; nothing on the site shows more
MIN_WIDTH = 200  # smaller photos stay clean: the logo would be unreadable
LOGO_WIDTH = 0.18  # of the photo's width
MARGIN = 0.03  # of the photo's shorter side
OPACITY = 0.7
DARK_BELOW = 128  # mean brightness (0-255) of the corner under which the white logo is used


def _logo_for(corner):
    """The logo that stands out on `corner` (the part of the photo the logo will cover)."""
    from PIL import Image, ImageStat

    if corner.mode == "RGBA":  # see-through areas show the page, which is light
        flat = Image.new("RGB", corner.size, "white")
        flat.paste(corner, mask=corner.getchannel("A"))
        corner = flat
    brightness = ImageStat.Stat(corner.convert("L")).mean[0]
    return LOGO_ON_DARK if brightness < DARK_BELOW else LOGO_ON_LIGHT


def logo_box(width, height):
    """Where the logo goes on a width x height photo: (left, top, logo_width, logo_height)."""
    from PIL import Image

    with Image.open(LOGO_ON_LIGHT) as logo:
        ratio = logo.height / logo.width
    logo_w = round(width * LOGO_WIDTH)
    logo_h = max(1, round(logo_w * ratio))
    margin = round(min(width, height) * MARGIN)
    return width - margin - logo_w, height - margin - logo_h, logo_w, logo_h


def render_watermarked(image_field):
    """A copy of the photo in `image_field` with the logo on it, or None.

    None means the photo should be left as it is: it can't be read, or it is too small for a logo.
    """
    from PIL import Image, ImageOps

    try:
        image_field.open("rb")
        with Image.open(image_field) as img:
            img = ImageOps.exif_transpose(img)
            has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
            img = img.convert("RGBA" if has_alpha else "RGB")
            img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            if img.width < MIN_WIDTH:
                return None
            left, top, logo_w, logo_h = logo_box(*img.size)
            if top < 0:
                return None  # a very wide, flat banner: no room for the logo
            with Image.open(_logo_for(img.crop((left, top, left + logo_w, top + logo_h)))) as logo:
                logo = logo.convert("RGBA").resize((logo_w, logo_h), Image.LANCZOS)
            logo.putalpha(logo.getchannel("A").point(lambda a: round(a * OPACITY)))
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            layer.paste(logo, (left, top))
            out = Image.alpha_composite(img.convert("RGBA"), layer)
            buf = io.BytesIO()
            if has_alpha:
                out.save(buf, "PNG", optimize=True)
                ext = "png"
            else:
                out.convert("RGB").save(buf, "JPEG", quality=90, optimize=True, progressive=True)
                ext = "jpg"
    except Exception:
        logger.warning("Could not add the logo to %s", image_field.name, exc_info=True)
        return None
    finally:
        image_field.close()
    return ContentFile(buf.getvalue(), name=f"photo.{ext}")


def watermarks_enabled():
    from orders.models import ShopSettings

    return ShopSettings.load().watermark_product_images


def sync_watermarks(enabled=None, force=False):
    """Give every product photo the logo, or take it off, to match the shop setting.

    Safe to run again: photos already in the right state are skipped, unless `force`, which
    renders the logo again from the clean originals (after the logo file changed).
    Returns how many photos changed.
    """
    from .models import ProductImage

    if enabled is None:
        enabled = watermarks_enabled()
    changed = 0
    for image in ProductImage.objects.exclude(image="").iterator():
        if enabled:
            changed += image.apply_watermark(force=force)
        else:
            changed += image.remove_watermark()
    return changed
