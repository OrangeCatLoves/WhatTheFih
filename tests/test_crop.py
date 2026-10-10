"""Crop rules from the pipeline doc §5, checked on synthetic images (no models needed)."""

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fishid.crop import BORDER, MAX_SIDE, PADDING, crop_fish, load_image, padded_rect, square_with_borders  # noqa: E402

FISH = (200, 40, 40)


def photo(width=1000, height=800):
    return Image.new("RGB", (width, height), FISH)


def test_box_gets_padding_on_each_side():
    crop = crop_fish(photo(), (100, 100, 300, 200))  # 200 x 100 box
    region_w, region_h = 200 * (1 + 2 * PADDING), 100 * (1 + 2 * PADDING)
    assert crop.size == (round(region_w), round(region_w))  # square, as wide as the padded box
    assert crop.getpixel((crop.width // 2, crop.height // 2)) == FISH
    border_rows = (crop.height - round(region_h)) // 2
    assert crop.getpixel((crop.width // 2, 0)) == BORDER
    assert crop.getpixel((crop.width // 2, border_rows)) == FISH


def test_padding_stops_at_the_photo_edge():
    crop = crop_fish(photo(), (0, 0, 100, 50))
    # Only the right and bottom padding fit inside the photo.
    assert crop.size == (115, 115)


def test_long_fish_keeps_head_and_tail():
    image = Image.new("RGB", (1000, 800), (0, 0, 0))
    image.paste(FISH, (10, 400, 990, 450))  # a long, thin fish
    crop = crop_fish(image, (10, 400, 990, 450))
    assert crop.width == crop.height == 1000  # the whole width is kept, borders are added above and below
    middle = crop.height // 2
    assert crop.getpixel((10, middle)) == FISH and crop.getpixel((989, middle)) == FISH


def test_empty_box_gives_no_crop():
    assert crop_fish(photo(), (50, 50, 50, 90)) is None


def test_border_is_bioclip_mean_colour():
    open_clip = pytest.importorskip("open_clip")
    assert BORDER == tuple(round(255 * m) for m in open_clip.OPENAI_DATASET_MEAN)


def test_large_photo_is_shrunk_like_training_photos(tmp_path):
    path = tmp_path / "phone.jpg"
    photo(4000, 3000).save(path)
    image = load_image(path)
    assert image.size == (MAX_SIDE, 768)


def test_training_size_photo_is_unchanged(tmp_path):
    path = tmp_path / "inat.jpg"
    photo(1024, 683).save(path)
    assert load_image(path).size == (1024, 683)


def test_photo_is_turned_upright_from_exif(tmp_path):
    path = tmp_path / "rotated.jpg"
    exif = Image.Exif()
    exif[0x0112] = 6  # "rotate 90 degrees" tag that phones write
    photo(800, 600).save(path, exif=exif)
    assert load_image(path).size == (600, 800)


def test_saved_rect_rebuilds_the_same_crop():
    # Colab saves the pixel rectangle, so the laptop can rebuild exactly the crop that was fingerprinted.
    image = Image.effect_noise((640, 480), 60).convert("RGB")
    box = (101.37, 52.81, 402.66, 300.05)
    assert square_with_borders(image, padded_rect(image.size, box)).tobytes() == crop_fish(image, box).tobytes()
