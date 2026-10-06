"""Build the photo dataset from iNaturalist (pipeline doc §4).

    python scripts/download_inat.py --count-only   # count usable photos per class, download nothing
    python scripts/download_inat.py                # pick, split and download photos, write data/manifest.csv

Rules from the doc: research grade only; photo licence CC0 / CC-BY / CC-BY-NC; "large" photos (1024 px);
1 photo per observation; target 300 per class, drop a class under 100; at most 1 request per second,
retry on errors; split by observation 70/15/15; out-of-list fish: 200 photos in total, test only.
Re-running is safe: API answers are cached in data/cache/ and photos already on disk are skipped.
"""

import argparse
import csv
import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from itertools import zip_longest
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import requests
from PIL import Image
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fishid.species import CLASSES, DROPPED, OUT_OF_LIST  # noqa: E402

API_V1 = "https://api.inaturalist.org/v1"
API_V2 = "https://api.inaturalist.org/v2"
LICENCES = ("cc0", "cc-by", "cc-by-nc")
SINGAPORE = 6734  # iNaturalist place id
LIFE_STAGE, JUVENILE = 1, 8  # iNaturalist annotation ids
TARGET, MINIMUM = 300, 100
OUT_OF_LIST_TOTAL = 200  # user decision: 200 in total, not 200 each
TRAIN, VAL = 0.70, 0.15  # test gets the rest
SEED = 42
PREFERRED_CICHLA = ("Cichla orinocensis", "Cichla temensis")  # species list: Singapore's peacock bass
KOI = "Cyprinus rubrofuscus"  # iNaturalist's name for koi / Amur carp

# The v2 API returns only these fields: ~0.7 KB per observation instead of ~110 KB from v1.
FIELDS = (
    "(id:!t,observed_on:!t,taxon:(id:!t,name:!t,rank:!t),user:(login:!t,name:!t),"
    "photos:(id:!t,url:!t,license_code:!t,attribution:!t,flags:(id:!t),hidden:!t),"
    "annotations:(controlled_attribute_id:!t,controlled_value_id:!t))"
)
COLUMNS = ["class", "species", "observation_id", "photo_url", "licence", "photographer", "split",
           "photo_id", "taxon_id", "attribution", "observed_on", "tags", "file"]


class Client:
    """At most one request per second (API calls and photos alike); retries network errors, 429 and 5xx."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "WhatTheFih-dataset-builder/0.1"
        self.last = 0.0

    def get(self, url, tries=6, **params):
        for attempt in range(tries):
            time.sleep(max(0.0, self.last + 1.0 - time.monotonic()))
            self.last = time.monotonic()
            try:
                r = self.session.get(url, params=params, timeout=60)
            except requests.RequestException as e:
                problem = type(e).__name__
            else:
                if r.ok:
                    return r
                if r.status_code != 429 and r.status_code < 500:
                    r.raise_for_status()  # e.g. 404: retrying won't help
                problem = f"HTTP {r.status_code}"
            if attempt < tries - 1:
                wait = min(10 * 2**attempt, 300)
                tqdm.write(f"    {problem} on {url} - retrying in {wait}s")
                time.sleep(wait)
        raise RuntimeError(f"gave up after {tries} tries: {url}")


def count(client, **params):
    """Number of research-grade observations matching the filters."""
    r = client.get(f"{API_V1}/observations", quality_grade="research", per_page=0, **params)
    return r.json()["total_results"]


def find_taxon(client, name, rank):
    """The fish taxon with this scientific name (or a synonym of it)."""
    for t in client.get(f"{API_V1}/taxa", q=name, per_page=30).json()["results"]:
        names = {t["name"].lower(), (t.get("matched_term") or "").lower()}
        if t.get("iconic_taxon_name") == "Actinopterygii" and t["rank"] == rank and name.lower() in names:
            return {"id": t["id"], "name": t["name"]}
    sys.exit(f"No iNaturalist taxon found for {name!r} ({rank})")


def load_taxa(client, cache):
    """iNaturalist taxa for every class and out-of-list fish (cached; only new names are looked up)."""
    path = cache / "taxa.json"
    taxa = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    wanted = {c.name: (c.name, c.rank) for c in CLASSES} | {f.common_name: (f.inat_name, f.rank) for f in OUT_OF_LIST}
    missing = [key for key in wanted if key not in taxa]
    for key in missing:
        taxa[key] = find_taxon(client, *wanted[key])
    need_ancestors = [f.common_name for f in OUT_OF_LIST if "ancestor_ids" not in taxa[f.common_name]]
    if need_ancestors:
        ids = ",".join(str(taxa[name]["id"]) for name in need_ancestors)
        ancestors = {t["id"]: t["ancestor_ids"] for t in client.get(f"{API_V1}/taxa/{ids}").json()["results"]}
        for name in need_ancestors:
            taxa[name]["ancestor_ids"] = ancestors[taxa[name]["id"]]
    if missing or need_ancestors:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(taxa, indent=1, ensure_ascii=False), encoding="utf-8")
    return taxa


def inside(taxa, class_name):
    """Out-of-list fish that iNaturalist files under this class (e.g. flowerhorn under Amphilophus)."""
    tid = taxa[class_name]["id"]
    return [f for f in OUT_OF_LIST if tid in taxa[f.common_name]["ancestor_ids"]]


def class_query(taxa, class_name):
    """API filter for one class: its taxon and everything under it, minus any out-of-list fish."""
    q = {"taxon_id": taxa[class_name]["id"]}
    excluded = inside(taxa, class_name)
    if excluded:
        q["without_taxon_id"] = ",".join(str(taxa[f.common_name]["id"]) for f in excluded)
    return q


def species_counts(client, q):
    """(species name, usable observations) within a genus, most common first."""
    r = client.get(f"{API_V1}/observations/species_counts", quality_grade="research",
                   photo_license=",".join(LICENCES), per_page=100, **q)
    return [(s["taxon"]["name"], s["count"]) for s in r.json()["results"]]


def allocate(available, total):
    """Share `total` photos as evenly as possible; fish with too few photos pass their share on."""
    alloc = dict.fromkeys(available, 0)
    left = total
    while left > 0:
        open_ = [k for k in available if alloc[k] < available[k]]
        if not open_:
            break
        share = max(1, left // len(open_))
        for k in open_:
            add = min(share, available[k] - alloc[k], left)
            alloc[k] += add
            left -= add
    return alloc


def count_only(client, taxa, report_path):
    lic = ",".join(LICENCES)
    table, photos, pages = [], 0, 0
    for i, c in enumerate(CLASSES, 1):
        q = class_query(taxa, c.name)
        usable = count(client, photo_license=lic, **q)
        all_rg = count(client, **q)
        sg = count(client, place_id=SINGAPORE, **q)
        notes = []
        if c.name == "Channa micropeltes":
            juv = count(client, photo_license=lic, term_id=LIFE_STAGE, term_value_id=JUVENILE, **q)
            notes.append(f"{juv} tagged juvenile (picked first)")
        if c.rank == "genus":
            sp = species_counts(client, q)
            if c.name == "Cichla":
                pref = sum(n for name, n in sp if name.startswith(PREFERRED_CICHLA))
                notes.append(f"{pref} are C. orinocensis / C. temensis (picked first)")
            if c.name == "Cyprinus":
                notes.append("half the picks are *C. rubrofuscus* (koi / Amur carp), half the rest")
            notes.append("mostly " + ", ".join(f"*{name}* {n / max(usable, 1):.0%}" for name, n in sp[:3]))
        if c.name == "Oreochromis":
            gen = count(client, photo_license=lic, rank="genus", **q)
            hyb = count(client, photo_license=lic, rank="hybrid", **q)
            notes.append(f"{gen} identified only to genus, {hyb} hybrids")
        for f in inside(taxa, c.name):
            notes.append(f"{f.common_name} left out (out-of-list)")
        take = min(usable, TARGET) if usable >= MINIMUM else 0
        status = "OK" if usable >= TARGET else "below target" if usable >= MINIMUM else "**DROP: under 100**"
        if not take:
            notes.append(f"all {usable} go to the out-of-list test instead")
        star = " *" if c.check_sg else ""
        table.append(f"| {i} | {c.name}{star} | {c.common_name} | {usable} | {take} | {status} | {all_rg} | {sg} | "
                     f"{'; '.join(notes)} |")
        photos += take or usable
        pages += math.ceil(usable / 200)
        print(f"{i:2} {c.name + star:32} usable {usable:6}  take {take:3}  {status:14} SG {sg:4}", flush=True)

    ool, ool_rows = {}, []
    for f in OUT_OF_LIST:
        q = {"taxon_id": taxa[f.common_name]["id"]}
        ool[f.common_name] = count(client, photo_license=lic, **q)
        pages += math.ceil(ool[f.common_name] / 200)
    plan = allocate(ool, OUT_OF_LIST_TOTAL)
    for f in OUT_OF_LIST:
        ool_rows.append(f"| {f.common_name} | *{taxa[f.common_name]['name']}* | {ool[f.common_name]} | "
                        f"{plan[f.common_name]} |")
        print(f"   out-of-list {f.common_name:20} usable {ool[f.common_name]:6}  take {plan[f.common_name]}")
    photos += sum(plan.values())

    hours = (photos + pages) * 1.05 / 3600
    lines = [
        "# iNaturalist photo counts (count-only run)",
        "",
        f"Run on {date.today()}. Nothing downloaded. Rules from the pipeline doc §4: research grade only, "
        "photo licence CC0 / CC-BY / CC-BY-NC, 1 photo per observation, target 300 per class, "
        "drop a class under 100.",
        "",
        "- **Usable** = research-grade observations worldwide with a photo under an allowed licence "
        "(= usable photos, since we take 1 photo per observation).",
        "- **Take** = what the download will pick (up to 300).",
        "- **All RG** = research-grade observations with any licence (shows how many the licence rule removes).",
        "- **SG** = research-grade observations in Singapore, any licence. Evidence for the `*` check "
        "(\"actually caught in Singapore freshwater\"): it shows the fish is seen in Singapore, not that it "
        "was caught in fresh water.",
        "",
        "| # | Class | Common name | Usable | Take | Status | All RG | SG | Notes |",
        "|---|---|---|---:|---:|---|---:|---:|---|",
        *table,
        "",
        f"## Out-of-list fish (test only, {OUT_OF_LIST_TOTAL} in total)",
        "",
        "Plus every photo of the dropped classes above (user decision): fish the model doesn't know that are "
        "actually caught in Singapore.",
        "",
        "| Fish | iNaturalist taxon | Usable | Take |",
        "|---|---|---:|---:|",
        *ool_rows,
        "",
        "## Download estimate",
        "",
        f"- Photos: {photos:,}. API listing pages: {pages:,}. At 1 request per second: about {hours:.1f} hours.",
        f"- Disk: about {photos * 0.3 / 1000:.1f} GB (≈0.3 MB per 1024 px photo).",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nPhotos to download: {photos:,}, listing pages: {pages:,}, about {hours:.1f} h. Report: {report_path}")


def to_candidate(obs):
    """One photo per observation: the first with an allowed licence that isn't hidden or flagged."""
    for p in obs.get("photos") or []:
        if p.get("license_code") in LICENCES and not p.get("hidden") and not p.get("flags"):
            juvenile = any(a.get("controlled_attribute_id") == LIFE_STAGE and a.get("controlled_value_id") == JUVENILE
                           for a in obs.get("annotations") or [])
            return {
                "observation_id": obs["id"],
                "species": obs["taxon"]["name"],
                "taxon_id": obs["taxon"]["id"],
                "photo_id": p["id"],
                "photo_url": p["url"].replace("/square.", "/large."),
                "licence": p["license_code"],
                "photographer": obs["user"].get("name") or obs["user"]["login"],
                "attribution": p["attribution"],
                "observed_on": obs.get("observed_on") or "",
                "tags": "juvenile" if juvenile else "",
            }
    return None


def list_candidates(client, q, path):
    """Every usable observation of a taxon, 1 photo each (cached)."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    cands, last_id = [], 0
    while True:
        page = client.get(f"{API_V2}/observations", quality_grade="research", photo_license=",".join(LICENCES),
                          order_by="id", order="asc", id_above=last_id, per_page=200, fields=FIELDS,
                          **q).json()["results"]
        if not page:
            break
        if page[-1]["id"] <= last_id:
            raise RuntimeError("API paging did not advance")
        cands += filter(None, map(to_candidate, page))
        last_id = page[-1]["id"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cands, ensure_ascii=False), encoding="utf-8")
    return cands


def order(cands, rng, class_name=None):
    """Seeded random order, adjusted for the species list's notes and the user's decisions."""
    cands = sorted(cands, key=lambda c: c["observation_id"])
    rng.shuffle(cands)
    if class_name == "Cyprinus":  # user decision: half koi / Amur carp, half common carp
        koi = [c for c in cands if c["species"].startswith(KOI)]
        rest = [c for c in cands if not c["species"].startswith(KOI)]
        return [c for pair in zip_longest(koi, rest) for c in pair if c is not None]
    return sorted(cands, key=lambda c: not preferred(class_name, c))  # stable: keeps the random order


def preferred(class_name, cand):
    if class_name == "Channa micropeltes":
        return cand["tags"] == "juvenile"  # species list: juveniles must be in the training photos
    if class_name == "Cichla":
        return cand["species"].startswith(PREFERRED_CICHLA)
    return False


def keep_awake():
    """Ask Windows not to sleep while this process runs (released automatically when it exits)."""
    if sys.platform == "win32":
        import ctypes

        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


def download(client, url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    try:
        tmp.write_bytes(client.get(url).content)
        with Image.open(tmp) as im:
            im.verify()  # raises on a broken file
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def fetch(client, cands, n, folder, data_dir, failed, failed_path, bar):
    """Download photos in order until n have succeeded; failed photos are replaced by the next ones."""
    got = []
    for c in cands:
        if len(got) == n:
            break
        if str(c["photo_id"]) in failed:
            continue
        ext = PurePosixPath(urlparse(c["photo_url"]).path).suffix.lower() or ".jpg"
        path = folder / f"{c['observation_id']}{ext}"
        if not path.exists():
            try:
                download(client, c["photo_url"], path)
            except Exception as e:  # noqa: BLE001 - any failure: log it, take the next photo
                failed[str(c["photo_id"])] = f"{type(e).__name__}: {e}"
                failed_path.write_text(json.dumps(failed, indent=1), encoding="utf-8")
                tqdm.write(f"    skipped photo {c['photo_id']}: {failed[str(c['photo_id'])]}")
                continue
        got.append({**c, "file": path.relative_to(data_dir).as_posix()})
        bar.update(1)
    return got


def assign_splits(rows, rng):
    """70/15/15 by observation (1 photo each), stratified by tag so e.g. juvenile toman reach train."""
    groups = defaultdict(list)
    for r in rows:
        groups[r["tags"]].append(r)
    for tag in sorted(groups):
        g = sorted(groups[tag], key=lambda r: r["observation_id"])
        rng.shuffle(g)
        n_train, n_val = round(TRAIN * len(g)), round(VAL * len(g))
        for i, r in enumerate(g):
            r["split"] = "train" if i < n_train else "val" if i < n_train + n_val else "test"


def build(client, taxa, data_dir, per_class, ool_total, only):
    cache = data_dir / "cache"
    failed_path = cache / "failed_photos.json"
    failed = json.loads(failed_path.read_text(encoding="utf-8")) if failed_path.exists() else {}
    minimum = min(MINIMUM, per_class)  # so a small --per-class test run isn't dropped
    keep_awake()

    print("Listing observations (cached after the first run)...", flush=True)
    jobs = []  # (class label, ordered candidates, how many, folder, out-of-list fish name)
    for c in CLASSES:
        if c.name in DROPPED or (only and c.name not in only):
            continue
        cands = list_candidates(client, class_query(taxa, c.name), cache / "observations" / f"{c.slug}.json")
        print(f"  {c.name}: {len(cands)} usable", flush=True)
        rng = random.Random(f"{SEED}:{c.name}")
        if len(cands) < minimum:
            # User decision: a dropped class's photos all become extra out-of-list test photos.
            print("    under 100 photos: class dropped (doc §4); its photos go to the out-of-list test")
            jobs.append(("out_of_list", order(cands, rng), len(cands), data_dir / "photos" / "out_of_list",
                         c.common_name.split(",")[0]))
            continue
        jobs.append((c.name, order(cands, rng, c.name), per_class, data_dir / "photos" / c.slug, None))
    if ool_total:
        pools = {}
        for f in OUT_OF_LIST:
            q = {"taxon_id": taxa[f.common_name]["id"]}
            pools[f.common_name] = list_candidates(client, q, cache / "observations" / f"out_of_list_{f.common_name}.json")
        plan = allocate({k: len(v) for k, v in pools.items()}, ool_total)
        for name, cands in pools.items():
            rng = random.Random(f"{SEED}:{name}")
            jobs.append(("out_of_list", order(cands, rng), plan[name], data_dir / "photos" / "out_of_list", name))

    # A photo attached to more than one observation (e.g. one catch photo of two fish) can't be trusted to
    # show one fish, and could land in two classes or two splits: leave it out, the next photo replaces it.
    uses = Counter(c["photo_id"] for _, cands, _, _, _ in jobs for c in cands)
    shared = {pid for pid, n in uses.items() if n > 1}
    if shared:
        print(f"  leaving out {len(shared)} photo(s) attached to more than one observation")
        jobs = [(label, [c for c in cands if c["photo_id"] not in shared], n, folder, ool_name)
                for label, cands, n, folder, ool_name in jobs]

    total = sum(min(n, len(cands)) for _, cands, n, _, _ in jobs)
    print(f"\nDownloading {total:,} photos at up to 1 per second (photos already on disk are skipped)...", flush=True)
    rows = []
    with tqdm(total=total, unit="photo") as bar:
        for label, cands, n, folder, ool_name in jobs:
            got = fetch(client, cands, n, folder, data_dir, failed, failed_path, bar)
            for r in got:
                r["class"] = label
                if ool_name:
                    r["tags"], r["split"] = ool_name, "out_of_list"
            if not ool_name:
                if len(got) < minimum:
                    print(f"  {label}: only {len(got)} photos downloaded, class dropped (doc §4)")
                    continue
                assign_splits(got, random.Random(f"{SEED}:{label}:split"))
            rows += got

    rows.sort(key=lambda r: (r["class"] == "out_of_list", r["class"], r["observation_id"]))
    with open(data_dir / "manifest.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    per = Counter((r["class"], r["split"]) for r in rows)
    print(f"\nWrote {data_dir / 'manifest.csv'}: {len(rows):,} photos. Failed downloads: {len(failed)}.")
    for label in dict.fromkeys(r["class"] for r in rows):
        parts = "  ".join(f"{s} {per[label, s]}" for s in ("train", "val", "test", "out_of_list") if per[label, s])
        print(f"  {label:30} {parts}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count-only", action="store_true", help="count usable photos per class, download nothing")
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data")
    ap.add_argument("--per-class", type=int, default=TARGET)
    ap.add_argument("--out-of-list", type=int, default=OUT_OF_LIST_TOTAL, help="out-of-list photos in total")
    ap.add_argument("--classes", nargs="*", help="only these classes (for testing)")
    args = ap.parse_args()

    client = Client()
    taxa = load_taxa(client, args.data_dir / "cache")
    if args.count_only:
        count_only(client, taxa, ROOT / "reports" / "inat_counts.md")
    else:
        build(client, taxa, args.data_dir, args.per_class, args.out_of_list, args.classes)


if __name__ == "__main__":
    main()
