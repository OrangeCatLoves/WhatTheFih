"""Check this machine can run the pipeline: GPU, GroundingDINO and BioCLIP 2.

Usage:
    python scripts/check_env.py [photo.jpg]

The first run downloads both models into the Hugging Face cache (~0.9 GB + ~1.7 GB).
Prints the top "fish" box for the photo and how fast each model runs.
"""

import os
import sys
import time

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")  # Windows without Developer Mode: harmless

import open_clip
import torch
from PIL import Image
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

DINO_ID = "IDEA-Research/grounding-dino-base"
BIOCLIP_ID = "hf-hub:imageomics/bioclip-2"


def sync(device):
    if device == "cuda":
        torch.cuda.synchronize()


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"torch {torch.__version__} | device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")

    if len(sys.argv) > 1:
        image = Image.open(sys.argv[1]).convert("RGB")
    else:
        image = Image.new("RGB", (1024, 768), (90, 120, 140))  # no photo given: speed test only
    print(f"photo size: {image.size}")

    # --- GroundingDINO ---
    t0 = time.perf_counter()
    processor = AutoProcessor.from_pretrained(DINO_ID)
    dino = AutoModelForZeroShotObjectDetection.from_pretrained(DINO_ID).to(device).eval()
    print(f"\nGroundingDINO loaded in {time.perf_counter() - t0:.1f}s")

    inputs = processor(images=image, text=[["fish"]], return_tensors="pt").to(device)
    runs = 10 if device == "cuda" else 3
    with torch.no_grad():
        dino(**inputs)  # warm-up
        sync(device)
        t0 = time.perf_counter()
        for _ in range(runs):
            outputs = dino(**inputs)
        sync(device)
    dino_s = (time.perf_counter() - t0) / runs
    result = processor.post_process_grounded_object_detection(
        outputs, inputs.input_ids, threshold=0.0, text_threshold=0.0, target_sizes=[image.size[::-1]]
    )[0]
    best = int(result["scores"].argmax())
    box = [round(v) for v in result["boxes"][best].tolist()]
    print(f"top 'fish' box: {box}  score: {result['scores'][best]:.3f}")
    print(f"GroundingDINO: {dino_s:.3f} s/photo")
    if device == "cuda":
        print(f"peak VRAM so far: {torch.cuda.max_memory_allocated() / 1024**3:.2f} GB")
    del dino
    if device == "cuda":
        torch.cuda.empty_cache()

    # --- BioCLIP 2 ---
    t0 = time.perf_counter()
    model, _, preprocess = open_clip.create_model_and_transforms(BIOCLIP_ID)
    model = model.to(device).eval()
    print(f"\nBioCLIP 2 loaded in {time.perf_counter() - t0:.1f}s")
    print(f"preprocess: {preprocess}")

    crop = image.crop(box)
    batch = torch.stack([preprocess(crop)] * 32).to(device)
    with torch.no_grad():
        model.encode_image(batch[:2])  # warm-up
        sync(device)
        t0 = time.perf_counter()
        vectors = model.encode_image(batch)
        sync(device)
    clip_s = (time.perf_counter() - t0) / len(batch)
    print(f"vector length: {vectors.shape[1]}")
    print(f"BioCLIP 2: {clip_s * 1000:.1f} ms/photo ({1 / clip_s:.0f} photos/s, batch of 32)")
    if device == "cuda":
        print(f"peak VRAM: {torch.cuda.max_memory_allocated() / 1024**3:.2f} GB")


if __name__ == "__main__":
    main()
