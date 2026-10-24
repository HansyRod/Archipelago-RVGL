from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .cars import DC_CARS, STOCK_CARS, CarData
from .cups import STOCK_CUPS, CupData
from .items import ITEM_DATA, SourceData, get_archipelago_item_name
from .locations import EVENT_KEY_TO_LOCATION_ID, get_championship_event_key
from .tracks import DC_TRACKS, STOCK_TRACKS, TrackData

if TYPE_CHECKING:
    from .world import RVGLWorld


RANDOMIZER_CONFIG_VERSION = "0.2.0"
ARCHIPELAGO_SCHEMA_VERSION = 1

# The DLL uses positional track slots, including Rooftops at index 4.
TRACK_SLOTS = (*STOCK_TRACKS[:4], *DC_TRACKS, *STOCK_TRACKS[4:])

# Match the PC and DC default stage layouts in the randomizer's cups.rs.
# Each stage is (track folder, laps, reverse, mirror).
CUP_STAGES = {
    "bronze": (
        ("nhood1", 3, False, False),
        ("market2", 4, False, False),
        ("muse2", 3, False, False),
        ("garden1", 5, False, False),
    ),
    "silver": (
        ("toylite", 6, False, False),
        ("nhood1", 4, False, True),
        ("wild_west1", 4, False, False),
        ("toy2", 4, False, False),
    ),
    "silver-dc": (
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
    source: SourceData,
    obtain_key: str = "obtain",
) -> dict[str, Any]:
    # Starting items arrive through Archipelago's precollected inventory, so
    # every unlock uses the same item condition, including starting content.
    return {
        obtain_key: 13,
        "customUnlock": {
            "trackFolder": [],
            "requiredCount": 0,
            "archipelagoItem": get_archipelago_item_name(source),
        },
    }


def _build_car_config(car: CarData) -> dict[str, Any]:
    return {
        "folder": car.folder,
        "rating": car.rating,
        "selectable_player": True,
        "selectable_cpu": True,
        **_get_unlock_fields(car),
    }


def _build_track_config(track: TrackData) -> dict[str, Any]:
    return {
        "folder": track.folder,
        "difficulty": track.difficulty,
        **_get_unlock_fields(track),
    }


def _build_cup_config(cup: CupData, include_rooftops: bool) -> dict[str, Any]:
    stages = CUP_STAGES["silver-dc" if cup.folder == "silver" and include_rooftops else cup.folder]
    return {
        "name": cup.display_name,
        "difficulty": cup.difficulty,
        **_get_unlock_fields(cup, "obtainCondition"),
        "numCars": 8,
        "numTries": 3,
        "perRaceRequiredPlace": 3,
        "overallRequiredPlace": 1,
        "carsPerClass": list(CUP_CARS_PER_CLASS[cup.folder]),
        "pointsTable": [10, 6, 4, 3, 2, 1] + [0] * 24,
        "stages": [
            {"trackFolder": folder, "numLaps": laps, "isReverse": reverse, "isMirror": mirror}
            for folder, laps, reverse, mirror in stages
        ],
    }


def _build_archipelago_config(world: RVGLWorld) -> dict[str, Any]:
    # regions.py already determines which locations exist for this player.
    # Export only their event-key mappings to the DLL's JSON, skipping internal
    # events such as Victory, whose address is None because they have no network ID.
    active_location_ids = {location.address for location in world.get_locations() if location.address is not None}
    return {
        "schemaVersion": ARCHIPELAGO_SCHEMA_VERSION,
        "slotNumber": world.player,
        "slotName": world.player_name,
        "locations": {
            event_key: location_id
            for event_key, location_id in EVENT_KEY_TO_LOCATION_ID.items()
            if location_id in active_location_ids
        },
        "items": {get_archipelago_item_name(item.source): item.id for item in ITEM_DATA},
        "goalEventKey": get_championship_event_key(world.goal_cup),
    }


def build_randomizer_config(world: RVGLWorld) -> dict[str, Any]:
    """Build the DLL config and AP mappings without changing the generated content or AP state."""
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
            # Both flags describe PC-only stock mode for their content type.
            "is_stock_cars": not world.options.include_dreamcast_cars,
            "is_stock_tracks": not world.options.include_rooftops,
            "enable_30_car_mode": False,
            "enable_knockout_mode": False,
        },
        "stockCars": [_build_car_config(car) for car in STOCK_CARS],
        # Keep AP-locked definitions even when their items are excluded; an empty
        # list makes the DLL fall back to vanilla Dreamcast car unlocks.
        "dcCars": [_build_car_config(car) for car in DC_CARS],
        "extraCars": [],
        "tracks": [
            _build_track_config(track)
            for track in (TRACK_SLOTS if world.options.include_rooftops else STOCK_TRACKS)
        ],
        "cups": [_build_cup_config(cup, bool(world.options.include_rooftops)) for cup in STOCK_CUPS],
        "archipelago": _build_archipelago_config(world),
    }


def generate_output(world: RVGLWorld, output_directory: str) -> None:
    filename = world.multiworld.get_out_file_name_base(world.player) + ".rvgl.json"
    path = Path(output_directory) / filename
    with path.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(build_randomizer_config(world), output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")
