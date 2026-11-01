"""Table of cars that are considered in-logic to get each location check
depending on the difficulty setting.

"None" can mean either physically impossible or generally out of logic at every difficulty.
"""

from .options import LogicDifficulty

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
