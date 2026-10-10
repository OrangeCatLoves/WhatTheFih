"""Pack the photos listed in data/manifest.csv into one zip for Google Drive (Colab runs read it).

    python scripts/zip_photos.py            # writes transfer/photos.zip

One big file uploads, and copies from Drive to Colab, far faster than 7,000 small ones.
The photos are already JPEG, so the zip stores them without compressing again.
"""

import sys
import zipfile
from pathlib import Path

import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = pd.read_csv(ROOT / "data" / "manifest.csv").file
    out = ROOT / "transfer" / "photos.zip"
    out.parent.mkdir(exist_ok=True)
    missing = [f for f in files if not (ROOT / "data" / f).exists()]
    if missing:
        sys.exit(f"{len(missing)} photos missing, e.g. {missing[0]}. Run scripts/download_inat.py first.")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        for f in tqdm(files, unit="photo"):
            z.write(ROOT / "data" / f, f)  # stored as photos/<class>/<id>.jpg
    print(f"Wrote {out} ({out.stat().st_size / 1e9:.2f} GB, {len(files):,} photos)")


if __name__ == "__main__":
    main()
