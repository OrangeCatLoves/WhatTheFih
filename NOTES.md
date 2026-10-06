# NOTES — WhatTheFih fish classification pipeline

Short log of what was done and why. Newest stage at the bottom.
Source of truth: the three files in `docs/`.

## Stage 1 — Setup (2026-10-06)

**Machine**
- Lenovo 83AQ laptop, Windows 11, Intel i7-13700H (14 cores), 16 GB RAM, 1.3 TB free disk.
- NVIDIA GeForce RTX 3050 6GB Laptop GPU (compute capability 8.6), driver 610.62. No Apple Silicon.
- So: local NVIDIA GPU path (doc §10).

**Environment**
- `.venv` with Python 3.12.14, created with uv. The system Python is 3.14; 3.12 was chosen because
  it is the safest version for torch / open_clip / transformers.
- PyTorch 2.14.1 CUDA 12.6 build (the default PyPI torch on Windows is CPU-only).
- `requirements.txt`: top-level packages pinned to the installed versions (checked: installing it
  into the current env makes no changes).
- Models in the Hugging Face cache: GroundingDINO base 0.87 GB, BioCLIP 2 1.59 GB.
- `scripts/check_env.py`: loads GroundingDINO + BioCLIP 2, runs them on one photo, prints speeds.

**Smoke test** (one CC BY-NC toman photo, iNaturalist obs 406033029 — test only, not in the dataset)
- GroundingDINO found the fish (box score 0.871). BioCLIP 2 vectors have 768 numbers.
- BioCLIP 2's own preprocessing is resize 224 → centre-crop 224 → normalise. This confirms doc §5:
  crops must already be square (plain borders), or the centre-crop would cut long fish.

**Problem found: the GPU is power-capped**
- Under 100% load the GPU stays in its lowest power state (P8) at 210 MHz (max 2100 MHz).
  Power limit 15 W (default 60 W, max 90 W). "SW Power Cap" and "SW Thermal Slowdown" active at 45 °C,
  on AC power. Raw speed 0.42 TFLOPS.
- Measured speeds:

  | | GroundingDINO | BioCLIP 2 |
  |---|---|---|
  | GPU, capped at 15 W | 13.6 s/photo | 1.7 s/photo |
  | CPU only | 30.5 s/photo | 1.6 s/photo |

- At these speeds, cropping ~8,600 photos would take ~32 h (GPU capped) or ~73 h (CPU).
- Likely cause: the laptop's power mode (Lenovo Quiet / battery-saving). Needs the user to switch it
  to Performance; then re-run `scripts/check_env.py`.
- CPU itself is fine (~390 GFLOPS, 2.2–2.4 GHz all-core); the models are just heavy for a CPU.

**Follow-up (same day)**
- User decision: out-of-list fish = **200 photos in total** (~25 for each of the 8 fish), not 200 each.
- User set Windows power mode to Best performance. Re-checked under load: no change (still P8,
  210 MHz, 15 W limit, 0.42 TFLOPS). Charger is fine (plugged in, battery charging at ~20 W).
- Lenovo's own cooling mode is already **Performance** (user confirmed; registry `MMC CurrentSetting=3`
  = Performance on Windows — I first misread it as low-power). So the cooling mode is not the cause.
- Lenovo's WMI charger check (`IsACFitForOC`) needs admin rights; not run.
- Remaining suspects, in order: GPU stuck after 14 days without a restart → restart; charger not the
  original / too low wattage (battery fell 99% → 90% while plugged in during benchmarks) → check it.
  Fallback: run Stage 3 on Colab. Must be fixed before Stage 3; Stage 2 doesn't use the GPU.

## Stage 2 — Dataset (2026-10-06)

**Code**
- `fishid/species.py`: the species list as code (28 classes, `*` flags, out-of-list fish, `DROPPED`).
- `scripts/download_inat.py`: `--count-only` writes `reports/inat_counts.md`; the full run lists
  observations, picks photos, splits, downloads and writes `data/manifest.csv`.
- Listing uses the iNaturalist **v2** API with a field list: ~0.7 KB per observation. The v1 API returns
  ~110 KB per observation (one page of 200 carp = 22.5 MB), which would mean GBs of JSON — not gentle.
- Picking: 1 photo per observation (first photo with an allowed licence that isn't hidden or flagged).
  Seeded random order (seed 42), with the species list's preferences first: toman tagged juvenile
  (iNat annotation Life Stage = Juvenile), and *C. orinocensis* / *C. temensis* for peacock bass.
- Split 70/15/15 by observation, per class, stratified by tag (so ~70% of juvenile toman go to train).
- ≤1 request/second for API calls and photo downloads alike; retries with backoff on network errors,
  429 and 5xx; a failed photo is replaced by the next candidate; re-running resumes (cache + skip files).
- Out-of-list: 200 in total, shared evenly (flowerhorn has only 23, so its 2 spare go to others).
- Test run (9 photos, into the scratchpad, not the dataset) passed: flowerhorn excluded from
  *Amphilophus*, juveniles picked first, photos are 1024 px, licences correct.

**Count-only results** (full table in `reports/inat_counts.md`)
- Under 100 → dropped by the doc §4 rule: *Datnioides* 12, *Leptobarbus* 37, *Hemibagrus* 88. → 25 classes.
- Under the 300 target but ≥100: toman 279, soon hock 246, tarpon 294, pacu 274, giant gourami 129,
  patin 182, *Chitala* 112, *Mystus* 153. Giant gourami, *Chitala* and *Mystus* could fall under 100
  after Stage 3 removes photos with no fish found.
- To download: 6,969 photos (6,769 + 200 out-of-list), ~2.1 h at 1 request/s, ~2.1 GB.

**Problems found (waiting on user decisions)**
1. Flowerhorn: iNat files it as the hybrid *Amphilophus labiatus × trimaculatus*, inside genus
   *Amphilophus* (a class). Default: follow the species list — left out of the *Amphilophus* class
   (API `without_taxon_id`), used only as out-of-list test photos.
2. Carp/koi: in Singapore, iNat has *Cyprinus rubrofuscus* 167 observations (7 research grade) vs
   *C. carpio* 2 (0 research grade). iNat files koi / Amur carp as *C. rubrofuscus* (5,587 usable
   worldwide). A *C. carpio*-only class would train on a different fish. Proposed: genus class *Cyprinus*.
3. Red tilapia: no reliable source in research-grade data. Checked 3 pools by eye (contact sheets):
   hybrids *O. mossambicus × niloticus* (60 usable) are mostly normal-coloured; genus-only (460) are
   mostly murky photos, ~1–2 of 8 red; text search "red tilapia" (464) mostly normal-coloured.
   → random sampling within the rules; known gap until field photos are added.
4. `*` classes, Singapore research-grade sightings: giant gourami 28, patin 6, spotted scat 103,
   archerfish 590, *Barbonymus* 40, swamp eel 80 (*Hemibagrus* 2, dropped anyway). Sightings show
   presence in Singapore, not that the fish is caught in fresh water. User to decide.

**Cost of each rule** (measured per class, so the user could see what is left out): licence rule removes
~30% of research-grade photos everywhere (and is the only reason baung is under 100: 148 with all
licences); research-grade rule removes unconfirmed IDs and captive photos (e.g. oscar 721 casual vs 727
usable; tilapia 10,411 unconfirmed); 300 cap uses a small slice of big classes.

**User decisions (2026-10-06)**
1. Carp/koi → genus class *Cyprinus* (only this class; the other species classes stay species-level).
   Picks are half *C. rubrofuscus* (koi / Amur carp), half other *Cyprinus* (mostly *C. carpio*), like the
   species list's peacock bass rule. 27,480 usable. Now 13 species classes + 15 genus classes.
2. Flowerhorn: left out of *Amphilophus* training; out-of-list test only.
3. All six `*` fish kept.
4. The 3 dropped classes (tigerfish 12, sultan fish 37, baung 88 = 137 photos) become extra out-of-list
   test photos, on top of the 200: realistic Singapore fish the model doesn't know.
- Also: the download asks Windows not to sleep while it runs (`SetThreadExecutionState`, released when
  the process exits). Closing the lid can still sleep the laptop.

**Full download started**: 7,106 photos (6,769 for 25 classes + 200 out-of-list + 137 dropped-class).
Log: `data/cache/download.log`.

**Download results** (`data/manifest.csv`)
- 7,106 photos, 0 failed downloads, 2.78 GB. 25 classes: 4,738 train / 1,016 val / 1,015 test.
  Out-of-list: 337 (200 + tigerfish 12, sultan fish 37, baung 88).
- Licences: CC-BY-NC 6,299 (89%), CC-BY 721, CC0 86. **If the app ever makes money, the doc's plan
  (remove CC-BY-NC photos and retrain) would leave only ~800 photos — not enough.** Commercial use needs
  a different data plan (own field photos, or licensed photos).
- Carp: 150 *C. rubrofuscus* + 150 *C. carpio*. Peacock bass: 175 *C. temensis* / *C. orinocensis* +
  125 others (mostly *C. ocellaris*). Juvenile toman: 15 train / 3 val / 4 test.
- Photographers: 77–295 different people per class; the largest single contributor has 17% of a class
  (sailfin catfish). 365 photos are under 1024 px (the originals were smaller), 39 under 500 px.
- Fix after the first run: 15 photos are attached to more than one observation, e.g. one catch photo
  filed as both climbing perch (test) and haruan (train) — the same crop would get two labels and leak
  from train into test. The script now leaves such photos out; 4 picked photos were replaced and the
  splits of those 4 classes reshuffled (nothing trained yet). 0 duplicate photos now.
