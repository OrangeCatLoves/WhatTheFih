# iNaturalist photo counts (count-only run)

Run on 2026-10-06. Nothing downloaded. Rules from the pipeline doc §4: research grade only, photo licence CC0 / CC-BY / CC-BY-NC, 1 photo per observation, target 300 per class, drop a class under 100.

- **Usable** = research-grade observations worldwide with a photo under an allowed licence (= usable photos, since we take 1 photo per observation).
- **Take** = what the download will pick (up to 300).
- **All RG** = research-grade observations with any licence (shows how many the licence rule removes).
- **SG** = research-grade observations in Singapore, any licence. Evidence for the `*` check ("actually caught in Singapore freshwater"): it shows the fish is seen in Singapore, not that it was caught in fresh water.

| # | Class | Common name | Usable | Take | Status | All RG | SG | Notes |
|---|---|---|---:|---:|---|---:|---:|---|
| 1 | Channa micropeltes | Toman, Giant snakehead | 279 | 279 | below target | 432 | 141 | 22 tagged juvenile (picked first) |
| 2 | Channa striata | Haruan, Common snakehead | 2169 | 300 | OK | 3232 | 846 |  |
| 3 | Oxyeleotris marmorata | Soon hock, Marble goby | 246 | 246 | below target | 369 | 49 |  |
| 4 | Lates calcarifer | Barramundi, Siakap | 405 | 300 | OK | 589 | 43 |  |
| 5 | Megalops cyprinoides | Tarpon, Ikan bulan | 294 | 294 | below target | 370 | 4 |  |
| 6 | Anabas testudineus | Climbing perch, Puyu | 459 | 300 | OK | 732 | 6 |  |
| 7 | Mayaheros urophthalmus | Mayan cichlid | 3863 | 300 | OK | 5383 | 568 |  |
| 8 | Etroplus suratensis | Green chromide | 322 | 300 | OK | 445 | 182 |  |
| 9 | Astronotus ocellatus | Oscar | 727 | 300 | OK | 1047 | 11 |  |
| 10 | Piaractus brachypomus | Red-bellied pacu | 274 | 274 | below target | 414 | 13 |  |
| 11 | Osphronemus goramy * | Giant gourami | 129 | 129 | below target | 202 | 28 |  |
| 12 | Pangasianodon hypophthalmus * | Patin, Iridescent shark | 182 | 182 | below target | 227 | 6 |  |
| 13 | Scatophagus argus * | Spotted scat | 874 | 300 | OK | 1276 | 103 |  |
| 14 | Cichla | Peacock bass | 1274 | 300 | OK | 1956 | 238 | 175 are C. orinocensis / C. temensis (picked first); mostly *Cichla ocellaris* 74%, *Cichla temensis* 12%, *Cichla piquiti* 8% |
| 15 | Oreochromis | Tilapia (incl. red tilapia) | 7818 | 300 | OK | 10961 | 235 | mostly *Oreochromis niloticus* 37%, *Oreochromis mossambicus* 35%, *Oreochromis aureus* 18%; 460 identified only to genus, 60 hybrids |
| 16 | Clarias | Walking catfish, Keli | 1965 | 300 | OK | 2855 | 183 | mostly *Clarias gariepinus* 52%, *Clarias batrachus* 31%, *Clarias fuscus* 4% |
| 17 | Pterygoplichthys | Sailfin catfish, Pleco | 3633 | 300 | OK | 4857 | 35 | mostly *Pterygoplichthys ambrosettii* 4%, *Pterygoplichthys pardalis* 1%, *Pterygoplichthys multiradiatus* 1% |
| 18 | Chitala | Featherback, Belida | 112 | 112 | below target | 176 | 0 | mostly *Chitala ornata* 83%, *Chitala chitala* 7%, *Chitala lopis* 3% |
| 19 | Datnioides | Tigerfish | 12 | 0 | **DROP: under 100** | 22 | 0 | mostly *Datnioides polota* 50%, *Datnioides undecimradiatus* 25%, *Datnioides microlepis* 17%; all 12 go to the out-of-list test instead |
| 20 | Geophagus | Eartheater | 747 | 300 | OK | 1260 | 33 | mostly *Geophagus brasiliensis* 81%, *Geophagus iporangensis* 6%, *Geophagus altifrons* 3% |
| 21 | Amphilophus | Midas cichlid, Red devil | 610 | 300 | OK | 820 | 44 | mostly *Amphilophus citrinellus* 54%, *Amphilophus labiatus* 23%, *Amphilophus trimaculatus* 12%; Flowerhorn left out (out-of-list) |
| 22 | Leptobarbus | Sultan fish | 37 | 0 | **DROP: under 100** | 59 | 0 | mostly *Leptobarbus rubripinna* 49%, *Leptobarbus hoevenii* 38%, *Leptobarbus hosii* 11%; all 37 go to the out-of-list test instead |
| 23 | Mystus | Mystus catfish | 153 | 153 | below target | 271 | 1 | mostly *Mystus gulio* 23%, *Mystus singaringan* 16%, *Mystus bimaculatus* 7% |
| 24 | Toxotes * | Archerfish | 1936 | 300 | OK | 2533 | 590 | mostly *Toxotes chatareus* 51%, *Toxotes jaculatrix* 47%, *Toxotes kimberleyensis* 1% |
| 25 | Barbonymus * | Lampam, Tinfoil barb | 499 | 300 | OK | 775 | 40 | mostly *Barbonymus gonionotus* 51%, *Barbonymus schwanefeldii* 30%, *Barbonymus altus* 9% |
| 26 | Hemibagrus * | Baung | 88 | 0 | **DROP: under 100** | 148 | 2 | mostly *Hemibagrus wyckioides* 25%, *Hemibagrus capitulum* 25%, *Hemibagrus nemurus* 9%; all 88 go to the out-of-list test instead |
| 27 | Monopterus * | Swamp eel | 704 | 300 | OK | 1064 | 80 | mostly *Monopterus albus* 55%, *Monopterus javanensis* 20% |
| 28 | Cyprinus | Common carp, Koi | 27480 | 300 | OK | 37324 | 7 | half the picks are *C. rubrofuscus* (koi / Amur carp), half the rest; mostly *Cyprinus carpio* 80%, *Cyprinus rubrofuscus* 20%, *Cyprinus carpio × rubrofuscus* 0% |

## Out-of-list fish (test only, 200 in total)

Plus every photo of the dropped classes above (user decision): fish the model doesn't know that are actually caught in Singapore.

| Fish | iNaturalist taxon | Usable | Take |
|---|---|---:|---:|
| Asian arowana | *Scleropages formosus* | 71 | 26 |
| Alligator gar | *Atractosteus spatula* | 565 | 26 |
| Spotted gar | *Lepisosteus oculatus* | 2412 | 25 |
| Redtail catfish | *Phractocephalus hemioliopterus* | 62 | 25 |
| Flowerhorn | *Amphilophus labiatus × trimaculatus* | 23 | 23 |
| Arapaima | *Arapaima* | 127 | 25 |
| Banded leporinus | *Leporinus fasciatus* | 35 | 25 |
| Zebra tilapia | *Heterotilapia buettikoferi* | 247 | 25 |

## Download estimate

- Photos: 7,106. API listing pages: 325. At 1 request per second: about 2.2 hours.
- Disk: about 2.1 GB (≈0.3 MB per 1024 px photo).
