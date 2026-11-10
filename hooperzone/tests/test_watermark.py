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


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def product(db):
    from products.models import Category, Product

    cat = Category.objects.create(name="Knee", slug="knee")
    return Product.objects.create(category=cat, name="Brace", slug="brace", description="d", price=100)


def files_in(media):
    return sorted(str(p.relative_to(media)) for p in media.rglob("*") if p.is_file())


def test_apply_watermark_keeps_the_clean_upload(product, media):
    from products.models import ProductImage

    upload = photo()
    clean_bytes = upload.read()
    image = ProductImage.objects.create(product=product, image=upload)
    first_url = image.image.name

    assert image.apply_watermark() is True
    image.refresh_from_db()
    assert image.has_watermark
    assert image.image.name != first_url and image.thumbnail.name  # new URLs: caches can't show the old photo
    assert image.original.read() == clean_bytes
    assert "brace" not in image.original.name and "p." not in image.original.name  # not guessable
    assert image.image.read() != clean_bytes
    # Exactly the shown photo, the original and one thumbnail are on disk.
    assert files_in(media) == sorted([image.image.name, image.original.name, image.thumbnail.name])

    assert image.apply_watermark() is False  # already has the logo


def test_apply_watermark_force_renders_again_from_the_original(product, media):
    from products.models import ProductImage

    image = ProductImage.objects.create(product=product, image=photo())
    image.apply_watermark()
    original, shown = image.original.name, image.image.name
    with Image.open(image.image.path) as once:
        once = once.copy()

    assert image.apply_watermark(force=True) is True
    image.refresh_from_db()
    assert image.original.name == original and image.image.name != shown
    with Image.open(image.image.path) as twice:
        assert list(twice.tobytes()) == list(once.tobytes())  # the logo isn't stacked on itself
    assert len(files_in(media)) == 3


def test_remove_watermark_restores_the_clean_upload(product, media):
    from products.models import ProductImage

    upload = photo()
    clean_bytes = upload.read()
    image = ProductImage.objects.create(product=product, image=upload)
    assert image.remove_watermark() is False  # nothing to remove
    image.apply_watermark()

    assert image.remove_watermark() is True
    image.refresh_from_db()
    assert not image.has_watermark and image.image.read() == clean_bytes
    assert files_in(media) == sorted([image.image.name, image.thumbnail.name])


def test_small_photo_is_stored_without_logo(product, media):
    from products.models import ProductImage

    image = ProductImage.objects.create(product=product, image=photo(size=(50, 50)))
    assert image.apply_watermark() is False
    image.refresh_from_db()
    assert not image.has_watermark and len(files_in(media)) == 2


def test_deleting_an_image_removes_its_original(product, media):
    from products.models import ProductImage

    image = ProductImage.objects.create(product=product, image=photo())
    image.apply_watermark()
    image.delete()
    assert files_in(media) == []


def test_logo_setting_is_on_by_default_and_staff_only(db):
    from django.contrib.auth import get_user_model
    from django.urls import reverse
    from rest_framework.test import APIClient

    client = APIClient()
    assert "watermark_product_images" not in client.get(reverse("orders:shop-info")).data  # not public
    client.force_authenticate(get_user_model().objects.create_superuser(phone="09129990000", password="securepass123"))
    assert client.get(reverse("orders:admin-settings")).data["watermark_product_images"] is True


@pytest.fixture
def staff_client(db):
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(get_user_model().objects.create_superuser(phone="09129990000", password="securepass123"))
    return client


def upload_photo(client, **photo_kwargs):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.urls import reverse

    data = photo(**photo_kwargs).read()
    res = client.post(
        reverse("products:admin-product-images", kwargs={"slug": "brace"}),
        {"image": SimpleUploadedFile("knee.jpg", data, content_type="image/jpeg")},
        format="multipart",
    )
    assert res.status_code == 200, res.data
    return data, res.data


def test_uploaded_product_photo_gets_the_logo(product, media, staff_client):
    from products.models import ProductImage

    clean_bytes, rows = upload_photo(staff_client)
    image = ProductImage.objects.get()
    assert image.has_watermark and image.original.read() == clean_bytes
    # The API hands out the logo copy and its thumbnail, never the clean original.
    assert rows[0]["image"].endswith(image.image.url) and "originals" not in str(rows)
    assert "original" not in rows[0]
    left, top, w, h = logo_box(1000, 800)
    with Image.open(image.image.path) as shown:
        assert shown.convert("RGB").crop((left, top, left + w, top + h)).getextrema()[0][0] < 150
    with Image.open(image.thumbnail.path) as thumb:  # built from the logo copy
        assert thumb.format == "WEBP"
        assert thumb.convert("RGB").crop((480, 440, 590, 470)).getextrema()[0][0] < 200


def test_upload_stays_clean_when_the_logo_is_switched_off(product, media, staff_client):
    from orders.models import ShopSettings
    from products.models import ProductImage

    ShopSettings.objects.update_or_create(pk=1, defaults={"watermark_product_images": False})
    clean_bytes, _ = upload_photo(staff_client)
    image = ProductImage.objects.get()
    assert not image.has_watermark and image.image.read() == clean_bytes
