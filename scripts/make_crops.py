"""Stage 3 on the laptop: turn Colab's boxes into crops, counts and eye-check sheets.

    python scripts/make_crops.py --from-zip <Downloads>/stage3_results.zip

1. Puts Colab's results in place: data/detections.csv, data/detections_run_info.json, embeddings/all.npz.
2. Applies the "fish found" threshold: a photo whose best box scores under 0.35 is skipped (doc §5).
3. Saves the crops of the photos with a fish to data/crops/<class>/, rebuilt from the exact pixel
   rectangles Colab cropped, so they match the crops that were fingerprinted.
4. Counts per class how many photos had no fish, and flags classes left with fewer than 100 photos.
5. Saves eye-check sheets to data/review/ and writes reports/crop_report.md.
"""

import argparse
import json
import random
import shutil
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fishid.crop import MIN_SCORE, load_image, square_with_borders  # noqa: E402
from fishid.species import CLASSES  # noqa: E402

MINIMUM = 100  # doc §4: drop a class with fewer than 100 photos after filtering
SEED = 42
TILE = 240
LONG_FISH = ["Chitala", "Monopterus", "Channa micropeltes", "Channa striata"]  # head or tail could be cut off
RESULTS = {"detections.csv": "data/detections.csv", "run_info.json": "data/detections_run_info.json",
           "embeddings.npz": "embeddings/all.npz"}


def place_results(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        for name, target in RESULTS.items():
            (ROOT / target).parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as src, open(ROOT / target, "wb") as dst:
                shutil.copyfileobj(src, dst)
    print(f"Unpacked {zip_path} into " + ", ".join(RESULTS.values()))


def folder_of(label):
    return label.replace(" ", "_")


def rect_of(row):
    return int(row.left), int(row.top), int(row.right), int(row.bottom)


def save_crop(row, data_dir, crops_dir):
    path = crops_dir / row.folder / f"{row.observation_id}.jpg"
    if not path.exists():
        image = load_image(data_dir / row.file)
        if image.size != (row.width, row.height):
            raise ValueError(f"{row.file}: size {image.size} differs from Colab's {(row.width, row.height)}")
        path.parent.mkdir(parents=True, exist_ok=True)
        square_with_borders(image, rect_of(row)).save(path, quality=95)
    return path


def tile(image, caption):
    image = image.copy()
    image.thumbnail((TILE, TILE))
    out = Image.new("RGB", (TILE, TILE + 18), "white")
    out.paste(image, ((TILE - image.width) // 2, 18 + (TILE - image.height) // 2))
    ImageDraw.Draw(out).text((3, 3), caption, fill="black")
    return out


def sheet(tiles, path, columns=5):
    rows = -(-len(tiles) // columns)
    out = Image.new("RGB", (columns * TILE, rows * (TILE + 18)), "white")
    for i, t in enumerate(tiles):
        out.paste(t, ((i % columns) * TILE, (i // columns) * (TILE + 18)))
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path, quality=90)


def photo_with_box(row, data_dir):
    image = load_image(data_dir / row.file)
    ImageDraw.Draw(image).rectangle((row.x0, row.y0, row.x1, row.y1), outline=(255, 0, 0), width=4)
    return image


def name_of(row):
    return row.tags if row.label == "out_of_list" else row.label


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-zip", type=Path, help="stage3_results.zip downloaded from Google Drive")
    ap.add_argument("--detections", type=Path, default=ROOT / "data" / "detections.csv")
    ap.add_argument("--run-info", type=Path, default=ROOT / "data" / "detections_run_info.json")
    ap.add_argument("--manifest", type=Path, default=ROOT / "data" / "manifest.csv")
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data", help="folder that holds photos/")
    ap.add_argument("--crops-dir", type=Path, default=ROOT / "data" / "crops")
    ap.add_argument("--review-dir", type=Path, default=ROOT / "data" / "review")
    ap.add_argument("--report", type=Path, default=ROOT / "reports" / "crop_report.md")
    args = ap.parse_args()
    if args.from_zip:
        place_results(args.from_zip)

    df = pd.read_csv(args.manifest).merge(pd.read_csv(args.detections), on="observation_id", validate="1:1")
    df = df.rename(columns={"class": "label"})  # "class" is a Python keyword: unusable as a row attribute
    df["folder"] = df.label.map(folder_of)
    df["found"] = (df.score >= MIN_SCORE) & (df.left >= 0)
    found = df[df.found]

    print(f"Saving {len(found):,} crops to {args.crops_dir} ...", flush=True)
    with ThreadPoolExecutor(8) as pool:
        kept = set(pool.map(lambda r: save_crop(r, args.data_dir, args.crops_dir), found.itertuples()))
    stale = [p for p in args.crops_dir.rglob("*.jpg") if p not in kept]  # e.g. after raising the threshold
    for p in stale:
        p.unlink()

    # Eye-check sheets
    rng = random.Random(SEED)
    inlist = found[found.label != "out_of_list"]
    picks = inlist.loc[rng.sample(list(inlist.index), min(20, len(inlist)))]
    random_dir = args.review_dir / "random_crops"
    shutil.rmtree(random_dir, ignore_errors=True)
    random_dir.mkdir(parents=True)
    tiles = []
    for n, row in enumerate(picks.itertuples(), 1):
        crop = Image.open(args.crops_dir / row.folder / f"{row.observation_id}.jpg")
        crop.save(random_dir / f"{n:02d}_{row.folder}_{row.observation_id}.jpg", quality=95)
        tiles.append(tile(crop, f"{n}. {row.label} ({row.score:.2f})"))
    sheet(tiles, args.review_dir / "random_crops.jpg")

    below = df[(df.score < MIN_SCORE)].nlargest(10, "score")
    above = df[df.found].nsmallest(10, "score")
    sheet([tile(photo_with_box(r, args.data_dir), f"NO FISH {r.score:.3f} {name_of(r)}") for r in below.itertuples()]
          + [tile(photo_with_box(r, args.data_dir), f"FISH {r.score:.3f} {name_of(r)}") for r in above.itertuples()],
          args.review_dir / "near_threshold.jpg")

    long_tiles = []
    for name in LONG_FISH:
        rows = inlist[inlist.label == name]
        for r in rows.loc[rng.sample(list(rows.index), min(3, len(rows)))].itertuples():
            crop = Image.open(args.crops_dir / r.folder / f"{r.observation_id}.jpg")
            long_tiles.append(tile(crop, f"{name} ({r.score:.2f})"))
    sheet(long_tiles, args.review_dir / "long_fish.jpg", columns=6)

    # Counts and report
    lines, flagged = [], []
    in_df = df[df.label != "out_of_list"]
    order = [c.name for c in CLASSES if c.name in set(in_df.label)]
    for name in order:
        c = in_df[in_df.label == name]
        left = c[c.found]
        split = left.split.value_counts()
        flag = "**under 100**" if len(left) < MINIMUM else ""
        if flag:
            flagged.append(name)
        lines.append(f"| {name} | {len(c)} | {(~c.found).sum()} ({(~c.found).mean():.0%}) | {len(left)} | "
                     f"{split.get('train', 0)} / {split.get('val', 0)} / {split.get('test', 0)} | {flag} |")
    ool = df[df.label == "out_of_list"]
    ool_lines = [f"| {fish} | {len(g)} | {(~g.found).sum()} | {g.found.sum()} |"
                 for fish, g in ool.groupby("tags", sort=False)]
    split_totals = in_df[in_df.found].split.value_counts()
    edges = [0, 0.2, MIN_SCORE, 0.5, 0.7, 1]
    labels = [f"{a:.2f} to {b:.2f}" for a, b in zip(edges, edges[1:])]
    bands = pd.cut(df.score, edges[:-1] + [1.01], right=False, labels=labels).value_counts(sort=False)
    info = json.loads(args.run_info.read_text())["settings"] if args.run_info.exists() else {}

    report = [
        "# Stage 3: crop report",
        "",
        f"GroundingDINO looked for \"fish\" in all {len(df):,} photos. A photo counts as **fish found** when its "
        f"best box scores at least **{MIN_SCORE}**; the others are skipped (doc §5). Each crop is the best box "
        "plus 15% on each side, made square with grey borders.",
        "",
        f"- Fish found: **{df.found.sum():,}** of {len(df):,} photos ({df.found.mean():.1%}).",
        f"- In-list photos left for training and testing: {split_totals.get('train', 0):,} train / "
        f"{split_totals.get('val', 0):,} val / {split_totals.get('test', 0):,} test.",
        "- Classes left with fewer than 100 photos: " + (", ".join(flagged) if flagged else "none") + ".",
        "",
        "## Per class",
        "",
        "| Class | Photos | No fish found | Left | Left: train / val / test | |",
        "|---|---:|---:|---:|---|---|",
        *lines,
        "",
        "## Out-of-list fish (test only)",
        "",
        "| Fish | Photos | No fish found | Left |",
        "|---|---:|---:|---:|",
        *ool_lines,
        "",
        "## Box scores (all photos)",
        "",
        "| Score | Photos |",
        "|---|---:|",
        *[f"| {band} | {n:,} |" for band, n in bands.items()],
        "",
        "## Eye-check sheets (local only, not in git: the photos' licences need credit)",
        "",
        "- `data/review/random_crops.jpg` (and the 20 files in `data/review/random_crops/`): 20 random crops.",
        "- `data/review/near_threshold.jpg`: 10 photos just under the threshold (no fish) and 10 just over "
        "(fish), with the box in red. Use it to judge whether 0.35 is right.",
        "- `data/review/long_fish.jpg`: featherbacks, swamp eels and snakeheads, to check heads and tails.",
        "",
        "## Run settings",
        "",
        *[f"- {k}: `{v}`" for k, v in info.items()],
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Fish found: {df.found.sum():,} of {len(df):,}. Under 100: {flagged or 'none'}. Report: {args.report}")


if __name__ == "__main__":
    main()
