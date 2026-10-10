"""Stage 3 GPU work (run on Colab): find the fish in every photo, crop it, and make its BioCLIP 2 vector.

    python scripts/detect_and_embed.py --out /content/drive/MyDrive/WhatTheFih/stage3_results

For every photo in data/manifest.csv this saves the best "fish" box with its score, and the vector of the
crop. The crop is made whatever the score, so the "fish found" threshold (0.35) can change later without a
rerun. Results are saved in parts as the run goes: after a disconnect, run it again and it continues.
Output: detections.csv, embeddings.npz, run_info.json.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fishid import crop as crop_step  # noqa: E402
from fishid import embed as embed_step  # noqa: E402

PART_SIZE = 250  # photos per saved part
EMBED_BATCH = 32
CODE_FILES = ["fishid/crop.py", "fishid/embed.py", "scripts/detect_and_embed.py"]


class Photos(Dataset):
    def __init__(self, paths):
        self.paths = paths

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        return crop_step.load_image(self.paths[i])


def settings(device):
    """Everything that decides the boxes and vectors. Parts from a resumed run must match it."""
    code = hashlib.sha256()
    for name in CODE_FILES:  # line endings unified, so Windows and Colab give the same hash
        code.update((ROOT / name).read_bytes().replace(b"\r\n", b"\n"))
    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                                check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    return {
        "code_hash": code.hexdigest()[:16],
        "detector": f"{crop_step.DETECTOR}@{crop_step.DETECTOR_REVISION}",
        "prompt": crop_step.PROMPT,
        "padding": crop_step.PADDING,
        "border": list(crop_step.BORDER),
        "max_side": crop_step.MAX_SIDE,
        "bioclip": f"{embed_step.BIOCLIP}@{embed_step.BIOCLIP_REVISION}",
        "torch": torch.__version__,
        # for the record only, not checked:
        "git_commit": commit,
        "python": platform.python_version(),
        "device": torch.cuda.get_device_name(0) if device == "cuda" else "cpu",
    }


def read_parts(out):
    parts = []
    for path in sorted((out / "parts").glob("part_*.npz")):
        try:
            with open(path, "rb") as fh, np.load(fh) as part:  # own file handle: closed before any rename
                parts.append({k: part[k] for k in part.files})
        except (OSError, ValueError, EOFError, zipfile.BadZipFile) as e:  # e.g. cut short by a disconnect
            print(f"{path.name} can't be read ({type(e).__name__}): its photos will be done again.")
            path.rename(path.with_name("broken_" + path.name))
    return parts


def next_part_number(out):
    numbers = [int(p.stem.split("_")[1]) for p in (out / "parts").glob("part_*.npz")]
    return max(numbers) + 1 if numbers else 0


def save_part(path, rows, embedder):
    crops = [r["crop"] for r in rows if r["crop"] is not None]
    vectors = iter(np.concatenate([embedder.embed(crops[i:i + EMBED_BATCH])
                                   for i in range(0, len(crops), EMBED_BATCH)]) if crops else [])
    embeddings = np.stack([next(vectors) if r["crop"] is not None else np.full(768, np.nan, np.float32)
                           for r in rows])
    unfinished = path.with_name("unfinished_" + path.name)  # not matched by part_*.npz until complete
    np.savez(unfinished, observation_id=np.array([r["observation_id"] for r in rows], np.int64),
             box=np.array([r["box"] for r in rows], np.float64),
             rect=np.array([r["rect"] or (-1, -1, -1, -1) for r in rows], np.int32),
             score=np.array([r["score"] for r in rows], np.float64),
             size=np.array([r["size"] for r in rows], np.int32), embedding=embeddings)
    unfinished.replace(path)


def merge(out, manifest):
    parts = read_parts(out)
    data = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    position = pd.Series(range(len(data["observation_id"])), index=data["observation_id"])
    idx = position.loc[manifest.observation_id].to_numpy()  # back in manifest order
    detections = pd.DataFrame({
        "observation_id": data["observation_id"][idx],
        "score": data["score"][idx],
        **{k: data["box"][idx, j] for j, k in enumerate(["x0", "y0", "x1", "y1"])},  # the box itself
        # the exact pixels that were cropped and fingerprinted (-1: empty box)
        **{k: data["rect"][idx, j] for j, k in enumerate(["left", "top", "right", "bottom"])},
        "width": data["size"][idx, 0],
        "height": data["size"][idx, 1],
    })
    detections.to_csv(out / "detections.csv", index=False)
    np.savez(out / "embeddings.npz", observation_id=data["observation_id"][idx], embedding=data["embedding"][idx])
    return detections


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True, help="results folder (on Google Drive when on Colab)")
    ap.add_argument("--manifest", type=Path, default=ROOT / "data" / "manifest.csv")
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data", help="folder that holds photos/")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    manifest = pd.read_csv(args.manifest)
    (args.out / "parts").mkdir(parents=True, exist_ok=True)
    info_path, now = args.out / "run_info.json", settings(device)
    if info_path.exists():
        before = json.loads(info_path.read_text())["settings"]
        changed = [k for k in now if k not in ("git_commit", "python", "device") and before.get(k) != now[k]]
        if changed:
            sys.exit(f"Earlier parts were made with a different {changed}. Delete {args.out} to start again.")
    else:
        info_path.write_text(json.dumps({"settings": now, "photos": len(manifest)}, indent=1))

    done = {int(i) for part in read_parts(args.out) for i in part["observation_id"]}
    todo = manifest[~manifest.observation_id.isin(done)]
    print(f"{len(manifest):,} photos: {len(done):,} done before, {len(todo):,} to go. Device: {now['device']}")

    if len(todo):
        detector, embedder = crop_step.Detector(device), embed_step.Embedder(device)
        loader = DataLoader(Photos([args.data_dir / f for f in todo.file]), batch_size=None,
                            num_workers=2 if platform.system() == "Linux" else 0)
        part_no = next_part_number(args.out)
        rows, start = [], time.time()
        for row, image in zip(tqdm(todo.itertuples(), total=len(todo), unit="photo"), loader):
            box, score = detector.best_box(image)
            rect = crop_step.padded_rect(image.size, box)
            crop = None if rect is None else crop_step.square_with_borders(image, rect)
            rows.append({"observation_id": row.observation_id, "box": box, "rect": rect, "score": score,
                         "size": image.size, "crop": crop})
            if len(rows) == PART_SIZE:
                save_part(args.out / "parts" / f"part_{part_no:04d}.npz", rows, embedder)
                part_no, rows = part_no + 1, []
        if rows:
            save_part(args.out / "parts" / f"part_{part_no:04d}.npz", rows, embedder)
        minutes = (time.time() - start) / 60
        print(f"Finished in {minutes:.1f} min ({minutes * 60 / len(todo):.2f} s per photo)")

    detections = merge(args.out, manifest)
    found = int((detections.score >= crop_step.MIN_SCORE).sum())
    print(f"Saved detections.csv and embeddings.npz in {args.out}")
    print(f"Fish found (score >= {crop_step.MIN_SCORE}): {found:,} of {len(detections):,} photos")


if __name__ == "__main__":
    main()
