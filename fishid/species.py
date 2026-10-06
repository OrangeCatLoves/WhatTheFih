"""The v1 class list, copied from docs/WhatTheFih_Species_List.md (the source of truth).

28 classes: 13 species classes and 15 genus classes. A genus class stands for every species in it.
`check_sg=True` marks the `*` fish: check they are caught in Singapore freshwater before keeping them
(user decision 2026-10-06: keep all of them).

Changes from the species list, approved by the user on 2026-10-06:
- Common carp / koi is the genus class Cyprinus (list: species Cyprinus carpio). iNaturalist files koi and
  Amur carp as C. rubrofuscus, and Singapore's carp are almost all filed there.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FishClass:
    name: str  # class label, also the iNaturalist taxon name
    rank: str  # "species" or "genus"
    common_name: str
    native: str
    check_sg: bool = False

    @property
    def genus(self) -> str:
        return self.name.split()[0]

    @property
    def slug(self) -> str:
        return self.name.replace(" ", "_")


CLASSES = [
    # Species classes
    FishClass("Channa micropeltes", "species", "Toman, Giant snakehead", "Introduced"),
    FishClass("Channa striata", "species", "Haruan, Common snakehead", "Native"),
    FishClass("Oxyeleotris marmorata", "species", "Soon hock, Marble goby", "Native"),
    FishClass("Lates calcarifer", "species", "Barramundi, Siakap", "Native"),
    FishClass("Megalops cyprinoides", "species", "Tarpon, Ikan bulan", "Native"),
    FishClass("Anabas testudineus", "species", "Climbing perch, Puyu", "Native"),
    FishClass("Mayaheros urophthalmus", "species", "Mayan cichlid", "Introduced"),
    FishClass("Etroplus suratensis", "species", "Green chromide", "Introduced"),
    FishClass("Astronotus ocellatus", "species", "Oscar", "Introduced"),
    FishClass("Piaractus brachypomus", "species", "Red-bellied pacu", "Introduced"),
    FishClass("Osphronemus goramy", "species", "Giant gourami", "Introduced", check_sg=True),
    FishClass("Pangasianodon hypophthalmus", "species", "Patin, Iridescent shark", "Introduced", check_sg=True),
    FishClass("Scatophagus argus", "species", "Spotted scat", "Native", check_sg=True),
    # Genus classes
    FishClass("Cichla", "genus", "Peacock bass", "Introduced"),
    FishClass("Oreochromis", "genus", "Tilapia (incl. red tilapia)", "Introduced"),
    FishClass("Clarias", "genus", "Walking catfish, Keli", "Mixed"),
    FishClass("Pterygoplichthys", "genus", "Sailfin catfish, Pleco", "Introduced"),
    FishClass("Chitala", "genus", "Featherback, Belida", "Introduced"),
    FishClass("Datnioides", "genus", "Tigerfish", "Introduced"),
    FishClass("Geophagus", "genus", "Eartheater", "Introduced"),
    FishClass("Amphilophus", "genus", "Midas cichlid, Red devil", "Introduced"),
    FishClass("Leptobarbus", "genus", "Sultan fish", "Introduced"),
    FishClass("Mystus", "genus", "Mystus catfish", "Mixed"),
    FishClass("Toxotes", "genus", "Archerfish", "Native", check_sg=True),
    FishClass("Barbonymus", "genus", "Lampam, Tinfoil barb", "Check", check_sg=True),
    FishClass("Hemibagrus", "genus", "Baung", "Check", check_sg=True),
    FishClass("Monopterus", "genus", "Swamp eel", "Native", check_sg=True),
    FishClass("Cyprinus", "genus", "Common carp, Koi", "Introduced"),  # list: species Cyprinus carpio
]

# Classes removed for v1, with the reason (user decisions and the under-100-photos rule).
DROPPED: dict[str, str] = {}


@dataclass(frozen=True)
class OutOfListFish:
    common_name: str
    inat_name: str  # taxon name on iNaturalist
    rank: str


# Test only. The app should not confidently identify these.
OUT_OF_LIST = [
    OutOfListFish("Asian arowana", "Scleropages formosus", "species"),
    OutOfListFish("Alligator gar", "Atractosteus spatula", "species"),
    OutOfListFish("Spotted gar", "Lepisosteus oculatus", "species"),
    OutOfListFish("Redtail catfish", "Phractocephalus hemioliopterus", "species"),
    OutOfListFish("Flowerhorn", "Amphilophus labiatus × trimaculatus", "hybrid"),  # iNaturalist's flowerhorn taxon
    OutOfListFish("Arapaima", "Arapaima", "genus"),
    OutOfListFish("Banded leporinus", "Leporinus fasciatus", "species"),
    OutOfListFish("Zebra tilapia", "Heterotilapia buettikoferi", "species"),  # list's Tilapia buttikoferi
]
