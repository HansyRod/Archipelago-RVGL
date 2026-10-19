from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .cars import DC_CARS, STOCK_CARS, CarData
from .cups import STOCK_CUPS, CupData
from .items import SourceData, get_archipelago_item_name, get_car_item_name, get_cup_item_name, get_track_item_name
from .tracks import DC_TRACKS, STOCK_TRACKS, TrackData

if TYPE_CHECKING:
    from .world import RVGLWorld


RANDOMIZER_CONFIG_VERSION = "0.2.0"

# The DLL uses positional track slots, including Rooftops at index 4.
TRACK_SLOTS = (*STOCK_TRACKS[:4], *DC_TRACKS, *STOCK_TRACKS[4:])

# Match the 14-track default stage layout in the randomizer's cups.rs.
# Each stage is (track folder, laps, reverse, mirror).
CUP_STAGES = {
    "bronze": (
        ("nhood1", 3, False, False),
        ("market2", 4, False, False),
        ("muse2", 3, False, False),
        ("garden1", 5, False, False),
    ),
    "silver": (
        ("roof", 4, False, False),
        ("toylite", 6, False, False),
        ("wild_west1", 4, False, False),
        ("toy2", 4, False, False),
    ),
    "gold": (
        ("nhood2", 5, False, False),
        ("toylite", 8, False, True),
        ("ship1", 5, False, False),
        ("muse1", 5, False, False),
    ),
    "platinum": (
        ("market1", 6, False, False),
        ("wild_west2", 6, False, False),
        ("toylite", 10, True, True),
        ("muse1", 6, False, True),
        ("ship2", 6, False, False),
    ),
}

CUP_CARS_PER_CLASS = {
    "bronze": (7, 0, 0, 0, 0, 0),
    "silver": (0, 4, 3, 0, 0, 0),
    "gold": (0, 0, 4, 3, 0, 0),
    "platinum": (0, 0, 1, 3, 3, 0),
}


def _get_unlock_fields(
    item_name: str,
    source: SourceData,
    starting_names: set[str],
    obtain_key: str = "obtain",
) -> dict[str, Any]:
    if item_name in starting_names:
        return {obtain_key: 0}

    return {
        obtain_key: 13,
        "customUnlock": {
            "trackFolder": [],
            "requiredCount": 0,
            "archipelagoItem": get_archipelago_item_name(source),
        },
    }


def _build_car_config(car: CarData, starting_names: set[str]) -> dict[str, Any]:
    return {
        "folder": car.folder,
        "rating": car.rating,
        "selectable_player": True,
        "selectable_cpu": True,
        **_get_unlock_fields(get_car_item_name(car), car, starting_names),
    }


def _build_track_config(track: TrackData, starting_names: set[str]) -> dict[str, Any]:
    return {
        "folder": track.folder,
        "difficulty": track.difficulty,
        **_get_unlock_fields(get_track_item_name(track), track, starting_names),
    }


def _build_cup_config(cup: CupData, starting_names: set[str]) -> dict[str, Any]:
    return {
        "name": cup.display_name,
        "difficulty": cup.difficulty,
        **_get_unlock_fields(get_cup_item_name(cup), cup, starting_names, "obtainCondition"),
        "numCars": 8,
        "numTries": 3,
        "perRaceRequiredPlace": 3,
        "overallRequiredPlace": 1,
        "carsPerClass": list(CUP_CARS_PER_CLASS[cup.folder]),
        "pointsTable": [10, 6, 4, 3, 2, 1] + [0] * 24,
        "stages": [
            {"trackFolder": folder, "numLaps": laps, "isReverse": reverse, "isMirror": mirror}
            for folder, laps, reverse, mirror in CUP_STAGES[cup.folder]
        ],
    }


def build_randomizer_config(world: RVGLWorld) -> dict[str, Any]:
    """Build the existing DLL config schema without changing the generated content or AP state."""
    starting_names = {item.name for item in world.multiworld.precollected_items[world.player]}
    profile_identity = f"{world.multiworld.seed_name}:{world.player}"
    profile_name = "ap_" + hashlib.sha256(profile_identity.encode("utf-8")).hexdigest()[:12]

    return {
        "metadata": {
            "seed": world.multiworld.seed_name,
            "version": RANDOMIZER_CONFIG_VERSION,
            "profileName": profile_name,
        },
        "global_options": {
            "load_extra_cars": False,
            "load_extra_tracks": False,
            "load_extra_cups": False,
            # Both flags describe PC-only stock mode; this world includes DC content.
            "is_stock_cars": False,
            "is_stock_tracks": False,
            "enable_30_car_mode": False,
            "enable_knockout_mode": False,
        },
        "stockCars": [_build_car_config(car, starting_names) for car in STOCK_CARS],
        "dcCars": [_build_car_config(car, starting_names) for car in DC_CARS],
        "extraCars": [],
        "tracks": [_build_track_config(track, starting_names) for track in TRACK_SLOTS],
        "cups": [_build_cup_config(cup, starting_names) for cup in STOCK_CUPS],
    }


def generate_output(world: RVGLWorld, output_directory: str) -> None:
    filename = world.multiworld.get_out_file_name_base(world.player) + ".rvgl.json"
    path = Path(output_directory) / filename
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(build_randomizer_config(world), output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")
