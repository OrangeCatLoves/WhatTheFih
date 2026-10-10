# Stage 3: crop report

GroundingDINO looked for "fish" in all 7,106 photos. A photo counts as **fish found** when its best box scores at least **0.35**; the others are skipped (doc §5). Each crop is the best box plus 15% on each side, made square with grey borders.

- Fish found: **6,948** of 7,106 photos (97.8%).
- In-list photos left for training and testing: 4,633 train / 990 val / 996 test.
- Classes left with fewer than 100 photos: none.

## Per class

| Class | Photos | No fish found | Left | Left: train / val / test | |
|---|---:|---:|---:|---|---|
| Channa micropeltes | 279 | 15 (5%) | 264 | 185 / 40 / 39 |  |
| Channa striata | 300 | 10 (3%) | 290 | 203 / 42 / 45 |  |
| Oxyeleotris marmorata | 246 | 4 (2%) | 242 | 171 / 34 / 37 |  |
| Lates calcarifer | 300 | 5 (2%) | 295 | 206 / 45 / 44 |  |
| Megalops cyprinoides | 294 | 0 (0%) | 294 | 206 / 45 / 43 |  |
| Anabas testudineus | 300 | 4 (1%) | 296 | 206 / 45 / 45 |  |
| Mayaheros urophthalmus | 300 | 4 (1%) | 296 | 209 / 43 / 44 |  |
| Etroplus suratensis | 300 | 1 (0%) | 299 | 209 / 45 / 45 |  |
| Astronotus ocellatus | 300 | 5 (2%) | 295 | 206 / 44 / 45 |  |
| Piaractus brachypomus | 274 | 4 (1%) | 270 | 188 / 41 / 41 |  |
| Osphronemus goramy | 129 | 2 (2%) | 127 | 91 / 19 / 17 |  |
| Pangasianodon hypophthalmus | 182 | 14 (8%) | 168 | 118 / 24 / 26 |  |
| Scatophagus argus | 300 | 3 (1%) | 297 | 209 / 43 / 45 |  |
| Cichla | 300 | 2 (1%) | 298 | 209 / 44 / 45 |  |
| Oreochromis | 300 | 6 (2%) | 294 | 205 / 44 / 45 |  |
| Clarias | 300 | 18 (6%) | 282 | 196 / 43 / 43 |  |
| Pterygoplichthys | 300 | 16 (5%) | 284 | 197 / 44 / 43 |  |
| Chitala | 112 | 0 (0%) | 112 | 78 / 16 / 18 |  |
| Geophagus | 300 | 7 (2%) | 293 | 205 / 44 / 44 |  |
| Amphilophus | 300 | 3 (1%) | 297 | 208 / 44 / 45 |  |
| Mystus | 153 | 2 (1%) | 151 | 106 / 21 / 24 |  |
| Toxotes | 300 | 3 (1%) | 297 | 208 / 45 / 44 |  |
| Barbonymus | 300 | 5 (2%) | 295 | 207 / 45 / 43 |  |
| Monopterus | 300 | 12 (4%) | 288 | 200 / 45 / 43 |  |
| Cyprinus | 300 | 5 (2%) | 295 | 207 / 45 / 43 |  |

## Out-of-list fish (test only)

| Fish | Photos | No fish found | Left |
|---|---:|---:|---:|
| Spotted gar | 25 | 2 | 23 |
| Alligator gar | 26 | 0 | 26 |
| Zebra tilapia | 25 | 2 | 23 |
| Asian arowana | 26 | 1 | 25 |
| Redtail catfish | 25 | 0 | 25 |
| Arapaima | 25 | 1 | 24 |
| Baung | 88 | 1 | 87 |
| Banded leporinus | 25 | 1 | 24 |
| Sultan fish | 37 | 0 | 37 |
| Flowerhorn | 23 | 0 | 23 |
| Tigerfish | 12 | 0 | 12 |

## Box scores (all photos)

| Score | Photos |
|---|---:|
| 0.00 to 0.20 | 3 |
| 0.20 to 0.35 | 155 |
| 0.35 to 0.50 | 1,024 |
| 0.50 to 0.70 | 1,576 |
| 0.70 to 1.00 | 4,348 |

## Eye-check sheets (local only, not in git: the photos' licences need credit)

- `data/review/random_crops.jpg` (and the 20 files in `data/review/random_crops/`): 20 random crops.
- `data/review/near_threshold.jpg`: 10 photos just under the threshold (no fish) and 10 just over (fish), with the box in red. Use it to judge whether 0.35 is right.
- `data/review/long_fish.jpg`: featherbacks, swamp eels and snakeheads, to check heads and tails.

## Run settings

- code_hash: `b38c5b3af117da26`
- detector: `IDEA-Research/grounding-dino-base@12bdfa3120f3e7ec7b434d90674b3396eccf88eb`
- prompt: `fish`
- padding: `0.15`
- border: `[123, 117, 104]`
- max_side: `1024`
- bioclip: `imageomics/bioclip-2@2957b322090f9cb17ae72c71981c7218a28d81e0`
- torch: `2.14.1+cu126`
- git_commit: `d2b59d488885e48ebe4fe786687abcc765075701`
- python: `3.12.3`
- device: `Tesla T4`
