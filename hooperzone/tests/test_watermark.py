import io

import pytest
from django.core.files.base import ContentFile
from PIL import Image

from products.watermark import logo_box, render_watermarked


def photo(size=(1000, 800), color="white", fmt="JPEG", mode="RGB", name="p.jpg"):
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, fmt)
    return ContentFile(buf.getvalue(), name=name)


def rendered(file):
    out = render_watermarked(file)
    return out, Image.open(io.BytesIO(out.read())).convert("RGB")


def test_logo_goes_in_the_bottom_right_corner_only():
    out, img = rendered(photo())
    assert out.name.endswith(".jpg") and img.size == (1000, 800)
    left, top, w, h = logo_box(1000, 800)
    assert w == 180 and left + w == 1000 - 24 and top + h == 800 - 24
    corner = img.crop((left, top, left + w, top + h))
    assert corner.getextrema()[0][0] < 150  # navy logo drawn on the white photo
    # Everything outside the logo's box is untouched (allowing for JPEG noise next to it).
    assert min(lo for lo, _ in img.crop((0, 0, 1000, top - 16)).getextrema()) > 240
    assert min(lo for lo, _ in img.crop((0, 0, left - 16, 800)).getextrema()) > 240


def test_white_logo_is_used_on_dark_photos():
    _, img = rendered(photo(color="black"))
    left, top, w, h = logo_box(1000, 800)
    brightest = img.crop((left, top, left + w, top + h)).getextrema()[0][1]
    assert 150 < brightest < 215  # white at 70% opacity, not solid white


def test_logo_is_semi_transparent_on_light_photos():
    _, img = rendered(photo())
    left, top, w, h = logo_box(1000, 800)
    darkest_red = img.crop((left, top, left + w, top + h)).getextrema()[0][0]
    assert darkest_red > 60  # solid navy would have red = 18


def test_big_photos_are_scaled_down():
    _, img = rendered(photo(size=(4000, 3000)))
    assert img.size == (2000, 1500)


def test_transparent_photos_stay_png():
    out = render_watermarked(photo(size=(600, 600), color=(0, 0, 0, 0), fmt="PNG", mode="RGBA", name="p.png"))
    assert out.name.endswith(".png")
    img = Image.open(io.BytesIO(out.read()))
    assert img.mode == "RGBA" and img.getpixel((5, 5))[3] == 0
    left, top, w, h = logo_box(600, 600)
    assert img.crop((left, top, left + w, top + h)).getextrema()[3][1] > 100


@pytest.mark.parametrize("file", [
    photo(size=(120, 120)),  # too small for a readable logo
    photo(size=(2000, 20)),  # no room for it
    ContentFile(b"not an image", name="p.jpg"),
])
def test_photos_that_cannot_take_a_logo_are_left_alone(file):
    assert render_watermarked(file) is None
