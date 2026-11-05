"""Table of cars that are considered in-logic to get each location check
depending on the difficulty setting.

"None" can mean either physically impossible or generally out of logic at every difficulty.
"""

from typing import cast

from .cups import CupData
from .items import DC_TRACK_ITEMS, STOCK_CUP_ITEMS, STOCK_TRACK_ITEMS
from .options import LogicDifficulty
from .tracks import TrackData

CASUAL = LogicDifficulty.option_casual
STANDARD = LogicDifficulty.option_standard
EXPERT = LogicDifficulty.option_expert

PRACTICE_STAR_UNRESTRICTED_TRACKS = frozenset({
    "nhood1", "muse2", "garden1", "toylite", "wild_west1", "toy2", "roof",
})

PRACTICE_STAR_RESTRICTED_TRACKS = ("market2", "nhood2", "ship1", "muse1", "market1", "wild_west2", "ship2")
PRACTICE_STAR_CAR_DATA: dict[str, tuple[int | None, ...]] = {
    "rc":         (CASUAL,     EXPERT,   None,     None,     None,     None,     None),
    "mite":       (EXPERT,     EXPERT,   None,     None,     None,     None,     None),
    "phat":       (EXPERT,     EXPERT,   None,     None,     None,     None,     None),
    "moss":       (STANDARD,   EXPERT,   None,     None,     None,     None,     None),
    "mud":        (None,       None,     None,     None,     None,     None,     None),
    "beatall":    (CASUAL,     EXPERT,   None,     None,     None,     None,     None),
    "volken":     (None,       None,     None,     None,     None,     None,     None),
    "tc6":        (STANDARD,   None,     None,     None,     None,     None,     None),
    "dino":       (CASUAL,     EXPERT,   None,     None,     None,     None,     None),
    "candy":      (CASUAL,     EXPERT,   None,     None,     None,     None,     None),
    "gencar":     (STANDARD,   EXPERT,   None,     None,     None,     None,     None),
    "tc4":        (CASUAL,     EXPERT,   None,     None,     None,     EXPERT,   None),
    "mouse":      (CASUAL,     EXPERT,   None,     None,     None,     None,     None),
    "flag":       (CASUAL,     EXPERT,   None,     None,     None,     None,     None),
    "tc2":        (CASUAL,     STANDARD, None,     None,     None,     EXPERT,   None),
    "r5":         (CASUAL,     STANDARD, None,     None,     None,     None,     None),
    "tc5":        (CASUAL,     STANDARD, None,     None,     None,     None,     None),
    "sgt":        (CASUAL,     EXPERT,   None,     None,     None,     None,     None),
    "tc3":        (EXPERT,     EXPERT,   EXPERT,   None,     None,     None,     EXPERT),
    "adeon":      (CASUAL,     CASUAL,   None,     EXPERT,   None,     STANDARD, None),
    "fone":       (CASUAL,     STANDARD, None,     None,     None,     None,     None),
    "tc1":        (CASUAL,     CASUAL,   None,     EXPERT,   None,     STANDARD, None),
    "rotor":      (EXPERT,     EXPERT,   None,     None,     None,     None,     None),
    "cougar":     (CASUAL,     CASUAL,   STANDARD, STANDARD, STANDARD, CASUAL,   STANDARD),
    "sugo":       (CASUAL,     CASUAL,   STANDARD, STANDARD, None,     CASUAL,   STANDARD),
    "toyeca":     (CASUAL,     CASUAL,   CASUAL,   CASUAL,   CASUAL,   CASUAL,   CASUAL),
    "amw":        (CASUAL,     CASUAL,   STANDARD, STANDARD, EXPERT,   CASUAL,   STANDARD),
    "panga":      (CASUAL,     CASUAL,   CASUAL,   CASUAL,   CASUAL,   CASUAL,   CASUAL),
    "bigvolt":    (CASUAL,     EXPERT,   None,     None,     None,     EXPERT,   None),
    "bossvolt":   (CASUAL,     STANDARD, None,     None,     None,     EXPERT,   None),
    "jg6rc":      (None,       None,     None,     None,     None,     None,     None),
    "tc12":       (CASUAL,     EXPERT,   None,     None,     None,     None,     None),
    "tc10":       (CASUAL,     EXPERT,   None,     None,     None,     EXPERT,   None),
    "tc8":        (CASUAL,     STANDARD, None,     None,     None,     EXPERT,   None),
    "tc11":       (CASUAL,     STANDARD, None,     None,     None,     None,     None),
    "tc9":        (CASUAL,     STANDARD, None,     None,     None,     None,     None),
    "jg1jg7":     (CASUAL,     CASUAL,   None,     None,     None,     STANDARD, None),
    "tc7":        (CASUAL,     CASUAL,   None,     None,     None,     STANDARD, None),
    "jg3loco":    (EXPERT,     None,     None,     None,     None,     None,     None),
    "jg4snw35":   (CASUAL,     CASUAL,   STANDARD, STANDARD, EXPERT,   CASUAL,   STANDARD),
    "jg5purpxl":  (CASUAL,     CASUAL,   CASUAL,   CASUAL,   CASUAL,   CASUAL,   CASUAL),
    "jg2fulonx":  (CASUAL,     STANDARD, None,     None,     None,     EXPERT,   None),
}

# Index by track for rule construction. All 42 supported cars have an explicit
# value for each restricted track; newly added cars must be classified before use.
PRACTICE_STAR_MIN_DIFFICULTY = {
    track: {car: difficulties[column] for car, difficulties in PRACTICE_STAR_CAR_DATA.items()}
    for column, track in enumerate(PRACTICE_STAR_RESTRICTED_TRACKS)
}


# Initial Championship requirements follow the car-rating classes:
# Standard needs Rookie / Amateur / Advanced / Semi-Pro for Bronze / Silver / Gold / Platinum.
# Casual needs one class higher; Expert needs one class lower, with Rookie as the minimum.
# Pest Control, Rotor and RV Loco qualify only in Expert, as described by LogicDifficulty.
# Edit individual entries here to adjust a specific car/cup combination.
CHAMPIONSHIP_CAR_DATA: dict[str, tuple[int | None, ...]] = {
    "rc":         (STANDARD, EXPERT,   None,     None),
    "mite":       (STANDARD, EXPERT,   None,     None),
    "phat":       (STANDARD, EXPERT,   None,     None),
    "moss":       (STANDARD, EXPERT,   None,     None),
    "mud":        (STANDARD, EXPERT,   None,     None),
    "beatall":    (STANDARD, EXPERT,   None,     None),
    "volken":     (STANDARD, EXPERT,   None,     None),
    "tc6":        (STANDARD, EXPERT,   None,     None),
    "dino":       (CASUAL,   STANDARD, EXPERT,   None),
    "candy":      (CASUAL,   STANDARD, EXPERT,   None),
    "gencar":     (STANDARD, EXPERT,   None,     None),
    "tc4":        (CASUAL,   STANDARD, EXPERT,   None),
    "mouse":      (CASUAL,   STANDARD, EXPERT,   None),
    "flag":       (CASUAL,   STANDARD, EXPERT,   None),
    "tc2":        (CASUAL,   CASUAL,   STANDARD, EXPERT),
    "r5":         (CASUAL,   CASUAL,   STANDARD, EXPERT),
    "tc5":        (CASUAL,   STANDARD, EXPERT,   None),
    "sgt":        (CASUAL,   CASUAL,   STANDARD, EXPERT),
    "tc3":        (EXPERT,   EXPERT,   EXPERT,   EXPERT),
    "adeon":      (CASUAL,   CASUAL,   CASUAL,   STANDARD),
    "fone":       (CASUAL,   CASUAL,   STANDARD, EXPERT),
    "tc1":        (CASUAL,   CASUAL,   CASUAL,   STANDARD),
    "rotor":      (EXPERT,   EXPERT,   EXPERT,   EXPERT),
    "cougar":     (CASUAL,   CASUAL,   CASUAL,   CASUAL),
    "sugo":       (CASUAL,   CASUAL,   CASUAL,   CASUAL),
    "toyeca":     (CASUAL,   CASUAL,   CASUAL,   CASUAL),
    "amw":        (CASUAL,   CASUAL,   CASUAL,   CASUAL),
    "panga":      (CASUAL,   CASUAL,   CASUAL,   CASUAL),
    "bigvolt":    (STANDARD, EXPERT,   None,     None),
    "bossvolt":   (CASUAL,   CASUAL,   STANDARD, EXPERT),
    "jg6rc":      (STANDARD, EXPERT,   None,     None),
    "tc12":       (CASUAL,   STANDARD, EXPERT,   None),
    "tc10":       (CASUAL,   STANDARD, EXPERT,   None),
    "tc8":        (CASUAL,   CASUAL,   STANDARD, EXPERT),
    "tc11":       (CASUAL,   STANDARD, EXPERT,   None),
    "tc9":        (CASUAL,   STANDARD, EXPERT,   None),
    "jg1jg7":     (CASUAL,   CASUAL,   CASUAL,   STANDARD),
    "tc7":        (CASUAL,   CASUAL,   CASUAL,   STANDARD),
    "jg3loco":    (EXPERT,   EXPERT,   EXPERT,   EXPERT),
    "jg4snw35":   (CASUAL,   CASUAL,   CASUAL,   CASUAL),
    "jg5purpxl":  (CASUAL,   CASUAL,   CASUAL,   CASUAL),
    "jg2fulonx":  (CASUAL,   CASUAL,   STANDARD, EXPERT),
}

CHAMPIONSHIP_MIN_DIFFICULTY = {
    cast(CupData, item.source).folder: {
        car: difficulties[column] for car, difficulties in CHAMPIONSHIP_CAR_DATA.items()
    }
    for column, item in enumerate(STOCK_CUP_ITEMS)
}


# One entry per track applies to all of its normal, reverse and mirror Time Trial checks.
# Standard needs Rookie / Amateur / Advanced / Semi-Pro for Easy / Medium / Hard / Extreme.
# Casual, Expert and the three Expert-only cars follow the same policy as Champ
# ionship.
# Track columns use the native order, including Rooftops after Botanical Garden.
# Each car row groups Easy, Medium, Hard and Extreme tracks on separate lines.
# Entries are independent so individual car/track ratings can be edited freely.
TIME_TRIAL_CAR_DATA: dict[str, tuple[int | None, ...]] = {
    "rc":         (
        STANDARD, STANDARD, STANDARD, STANDARD,
        STANDARD, None,     STANDARD, STANDARD,
        EXPERT,   None,     None,
        None,     None,     None,
    ),
    "mite":       (
        EXPERT,   STANDARD, EXPERT,   STANDARD,
        STANDARD, None,     STANDARD, EXPERT,
        None,     None,     None,
        None,     None,     None,
    ),
    "phat":       (
        EXPERT,   STANDARD, EXPERT,   None,
        None,     None,     STANDARD, None,
        None,     None,     None,
        None,     None,     None,
    ),
    "moss":       (
        STANDARD, STANDARD, STANDARD, STANDARD,
        STANDARD, None,     STANDARD, STANDARD,
        None,     None,     None,
        None,     None,     None,
    ),
    "mud":        (
        EXPERT,   STANDARD, EXPERT,   STANDARD,
        STANDARD, None,     STANDARD, EXPERT,
        None,     None,     None,
        None,     None,     None,
    ),
    "beatall":    (
        STANDARD, STANDARD, STANDARD, STANDARD,
        STANDARD, None,     STANDARD, STANDARD,
        EXPERT,   None,     None,
        None,     None,     None,
    ),
    "volken":     (
        STANDARD, STANDARD, EXPERT,   STANDARD,
        STANDARD, None,     STANDARD, EXPERT,
        None,     None,     None,
        None,     None,     None,
    ),
    "tc6":        (
        STANDARD, STANDARD, STANDARD, STANDARD,
        STANDARD, None,     STANDARD, STANDARD,
        None,     None,     None,
        None,     None,     None,
    ),
    "dino":       (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        STANDARD, EXPERT,   STANDARD, STANDARD,
        EXPERT,   None,     EXPERT,
        None,     None,     None,
    ),
    "candy":      (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        STANDARD, EXPERT,   STANDARD, STANDARD,
        EXPERT,   EXPERT,   EXPERT,
        None,     None,     None,
    ),
    "gencar":     (
        CASUAL,   CASUAL,   CASUAL,   STANDARD,
        STANDARD, None,     STANDARD, EXPERT,
        None,     None,     None,
        None,     None,     None,
    ),
    "tc4":        (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        STANDARD, STANDARD, CASUAL,   STANDARD,
        EXPERT,   EXPERT,   EXPERT,
        None,     None,     None,
    ),
    "mouse":      (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        STANDARD, EXPERT,   STANDARD, STANDARD,
        None,     None,     None,
        None,     None,     None,
    ),
    "flag":       (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   STANDARD, CASUAL,   STANDARD,
        EXPERT,   None,     None,
        None,     EXPERT,   None,
    ),
    "tc2":        (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        STANDARD, STANDARD, EXPERT,
        EXPERT,   EXPERT,   EXPERT,
    ),
    "r5":         (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        STANDARD, STANDARD, STANDARD,
        EXPERT,   EXPERT,   EXPERT,
    ),
    "tc5":        (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   STANDARD, CASUAL,   STANDARD,
        EXPERT,   EXPERT,   None,
        None,     EXPERT,   None,
    ),
    "sgt":        (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   STANDARD, CASUAL,   CASUAL,
        STANDARD, STANDARD, EXPERT,
        EXPERT,   EXPERT,   None,
    ),
    "tc3":        (
        EXPERT,   EXPERT,   EXPERT,   EXPERT,
        EXPERT,   EXPERT,   EXPERT,   EXPERT,
        EXPERT,   EXPERT,   None,
        None,     EXPERT,   EXPERT,
    ),
    "adeon":      (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        STANDARD, STANDARD, STANDARD,
    ),
    "fone":       (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        EXPERT,   CASUAL,   EXPERT,
        None,     EXPERT,   None,
    ),
    "tc1":        (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        STANDARD, STANDARD, STANDARD,
    ),
    "rotor":      (
        EXPERT,   EXPERT,   EXPERT,   EXPERT,
        EXPERT,   EXPERT,   EXPERT,   EXPERT,
        EXPERT,   EXPERT,   None,
        None,     EXPERT,   EXPERT,
    ),
    "cougar":     (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
    ),
    "sugo":       (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
    ),
    "toyeca":     (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
    ),
    "amw":        (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
    ),
    "panga":      (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
    ),
    "bigvolt":    (
        STANDARD, STANDARD, STANDARD, STANDARD,
        STANDARD, EXPERT,   STANDARD, EXPERT,
        None,     None,     None,
        None,     None,     None,
    ),
    "bossvolt":   (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   STANDARD, CASUAL,   CASUAL,
        EXPERT,   EXPERT,   None,
        None,     EXPERT,   None,
    ),
    "jg6rc":      (
        STANDARD, STANDARD, EXPERT,   STANDARD,
        STANDARD, None,     STANDARD, EXPERT,
        None,     None,     None,
        None,     None,     None,
    ),
    "tc12":       (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        STANDARD, None,     STANDARD, STANDARD,
        EXPERT,   None,     None,
        None,     None,     None,
    ),
    "tc10":       (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        STANDARD, STANDARD, STANDARD, STANDARD,
        EXPERT,   EXPERT,   EXPERT,
        None,     None,     None,
    ),
    "tc8":        (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   STANDARD, CASUAL,   CASUAL,
        STANDARD, STANDARD, EXPERT,
        EXPERT,   EXPERT,   EXPERT,
    ),
    "tc11":       (
        STANDARD, CASUAL,   CASUAL,   CASUAL,
        CASUAL,   None,     STANDARD, STANDARD,
        EXPERT,   None,     None,
        None,     None,     None,
    ),
    "tc9":        (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   EXPERT,   STANDARD, STANDARD,
        STANDARD, None,     None,
        None,     None,     None,
    ),
    "jg1jg7":     (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        STANDARD, STANDARD, STANDARD,
    ),
    "tc7":        (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        STANDARD, STANDARD, STANDARD,
    ),
    "jg3loco":    (
        EXPERT,   EXPERT,   EXPERT,   EXPERT,
        EXPERT,   EXPERT,   EXPERT,   EXPERT,
        EXPERT,   EXPERT,   None,
        None,     EXPERT,   EXPERT,
    ),
    "jg4snw35":   (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
    ),
    "jg5purpxl":  (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,
    ),
    "jg2fulonx":  (
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        CASUAL,   CASUAL,   CASUAL,   CASUAL,
        STANDARD, CASUAL,   STANDARD,
        EXPERT,   EXPERT,   EXPERT,
    ),
}

TIME_TRIAL_MIN_DIFFICULTY = {
    cast(TrackData, item.source).folder: {
        car: difficulties[column] for car, difficulties in TIME_TRIAL_CAR_DATA.items()
    }
    # Preserve native columns: the four Easy tracks, Rooftops, then the remaining stock tracks.
    for column, item in enumerate((*STOCK_TRACK_ITEMS[:4], *DC_TRACK_ITEMS, *STOCK_TRACK_ITEMS[4:]))
}
