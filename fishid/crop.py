"""Pipeline step 1 (doc §5): find the fish with GroundingDINO and crop it.

The same code crops the training photos and the app's photos (doc §5). If anything here changes,
re-crop everything and retrain.
"""

import math

import torch
from PIL import Image, ImageOps

DETECTOR = "IDEA-Research/grounding-dino-base"
DETECTOR_REVISION = "12bdfa3120f3e7ec7b434d90674b3396eccf88eb"  # pinned, so training and the app use the same weights
PROMPT = "fish"
MIN_SCORE = 0.35  # box score needed for "fish found"; the doc gives no value, 0.35 is GroundingDINO's own default
PADDING = 0.15  # added on each side, as a share of the box's width or height (doc: 10-15%)
MAX_SIDE = 1024  # photos are shrunk to this first, the size of the iNaturalist training photos
BORDER = (123, 117, 104)  # BioCLIP 2's mean colour: it becomes 0 after BioCLIP's normalisation, so it adds nothing


def load_image(source):
    """Open a photo the same way for training and for the app: upright (EXIF), RGB, at most MAX_SIDE px."""
    with Image.open(source) as raw:
        image = ImageOps.exif_transpose(raw).convert("RGB")
    if max(image.size) > MAX_SIDE:
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    return image


class Detector:
    """GroundingDINO with the text prompt "fish". Used as it is, no training."""

    def __init__(self, device="cpu"):
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.device = device
        self.processor = AutoProcessor.from_pretrained(DETECTOR, revision=DETECTOR_REVISION)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(DETECTOR, revision=DETECTOR_REVISION)
        self.model.to(device).eval()

    @torch.inference_mode()
    def best_box(self, image):
        """The highest-scoring "fish" box: ((x0, y0, x1, y1) in pixels, score from 0 to 1)."""
        inputs = self.processor(images=image, text=[[PROMPT]], return_tensors="pt").to(self.device)
        outputs = self.model(**inputs)
        result = self.processor.post_process_grounded_object_detection(
            outputs, inputs.input_ids, threshold=0.0, text_threshold=0.0, target_sizes=[image.size[::-1]]
        )[0]
        best = int(result["scores"].argmax())
        return tuple(result["boxes"][best].tolist()), float(result["scores"][best])


def padded_rect(image_size, box):
    """The box plus PADDING on each side, in whole pixels and kept inside the photo.

    Returns (left, top, right, bottom), or None for an empty box.
    """
    image_width, image_height = image_size
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    left = max(0, math.floor(x0 - PADDING * width))
    top = max(0, math.floor(y0 - PADDING * height))
    right = min(image_width, math.ceil(x1 + PADDING * width))
    bottom = min(image_height, math.ceil(y1 + PADDING * height))
    if width <= 0 or height <= 0 or right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def square_with_borders(image, rect):
    """Cut out rect and make it square by adding plain borders.

    Never centre-cut: long fish (snakeheads, featherbacks, eels) would lose their head or tail.
    """
    region = image.crop(rect)
    side = max(region.size)
    square = Image.new("RGB", (side, side), BORDER)
    square.paste(region, ((side - region.width) // 2, (side - region.height) // 2))
    return square


def crop_fish(image, box):
    """The square crop for a box, or None for an empty box."""
    rect = padded_rect(image.size, box)
    return None if rect is None else square_with_borders(image, rect)
