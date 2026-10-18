from __future__ import annotations

from dataclasses import dataclass

from BaseClasses import Location

from .cups import CupData
from .items import DC_TRACK_ITEMS, STOCK_CUP_ITEMS, STOCK_TRACK_ITEMS, ItemData
from .tracks import TrackData


# Location IDs use the owning item's ID plus a check-specific offset.
SINGLE_RACE_ID_OFFSET = 1
PRACTICE_STAR_ID_OFFSET = 2
TIME_TRIAL_ID_OFFSET = 10
REVERSE_TIME_TRIAL_ID_OFFSET = TIME_TRIAL_ID_OFFSET + 1
MIRROR_TIME_TRIAL_ID_OFFSET = TIME_TRIAL_ID_OFFSET + 2
CHAMPIONSHIP_ID_OFFSET = 5


@dataclass(frozen=True)
class LocationData:
    id: int
    name: str
    event_key: str
    source: TrackData | CupData


def get_single_race_location_name(track: TrackData) -> str:
    return f"Win Single Race: {track.display_name}"

def get_practice_star_location_name(track: TrackData) -> str:
    return f"Find Practice Star: {track.display_name}"

def get_time_trial_location_name(track: TrackData) -> str:
    return f"Beat Normal Time Trial: {track.display_name}"


def get_reverse_time_trial_location_name(track: TrackData) -> str:
    return f"Beat Reverse Time Trial: {track.display_name}"


def get_mirror_time_trial_location_name(track: TrackData) -> str:
    return f"Beat Mirror Time Trial: {track.display_name}"

def get_championship_location_name(cup: CupData) -> str:
    return f"Win {cup.display_name}"

def get_single_race_event_key(track: TrackData) -> str:
    return f"single_race_win:{track.folder}"

def get_practice_star_event_key(track: TrackData) -> str:
    return f"practice_star:{track.folder}"

def get_time_trial_event_key(track: TrackData) -> str:
    return f"time_trial_normal:{track.folder}"


def get_reverse_time_trial_event_key(track: TrackData) -> str:
    return f"time_trial_reverse:{track.folder}"


def get_mirror_time_trial_event_key(track: TrackData) -> str:
    return f"time_trial_mirror:{track.folder}"

def get_championship_event_key(cup: CupData) -> str:
    return f"championship_win:{cup.difficulty}"


def get_track_location_data(track_items: tuple[ItemData, ...]) -> tuple[LocationData, ...]:
    locations: list[LocationData] = []

    for item in track_items:
        track = item.source
        if not isinstance(track, TrackData):
            raise TypeError(f"Expected a track item, got {item.name!r}.")

        locations.extend((
            LocationData(
                item.id + SINGLE_RACE_ID_OFFSET,
                get_single_race_location_name(track),
                get_single_race_event_key(track),
                track,
            ),
            LocationData(
                item.id + PRACTICE_STAR_ID_OFFSET,
                get_practice_star_location_name(track),
                get_practice_star_event_key(track),
                track,
            ),
            LocationData(
                item.id + TIME_TRIAL_ID_OFFSET,
                get_time_trial_location_name(track),
                get_time_trial_event_key(track),
                track,
            ),
            LocationData(
                item.id + REVERSE_TIME_TRIAL_ID_OFFSET,
                get_reverse_time_trial_location_name(track),
                get_reverse_time_trial_event_key(track),
                track,
            ),
            LocationData(
                item.id + MIRROR_TIME_TRIAL_ID_OFFSET,
                get_mirror_time_trial_location_name(track),
                get_mirror_time_trial_event_key(track),
                track,
            ),
        ))

    return tuple(locations)


def get_cup_location_data(cup_items: tuple[ItemData, ...]) -> tuple[LocationData, ...]:
    locations: list[LocationData] = []

    for item in cup_items:
        cup = item.source
        if not isinstance(cup, CupData):
            raise TypeError(f"Expected a cup item, got {item.name!r}.")

        # The current DLL championship event identifies the cup by difficulty tier.
        locations.append(LocationData(
            item.id + CHAMPIONSHIP_ID_OFFSET,
            get_championship_location_name(cup),
            get_championship_event_key(cup),
            cup,
        ))

    return tuple(locations)


STOCK_TRACK_LOCATIONS = get_track_location_data(STOCK_TRACK_ITEMS)
DC_TRACK_LOCATIONS = get_track_location_data(DC_TRACK_ITEMS)
STOCK_CUP_LOCATIONS = get_cup_location_data(STOCK_CUP_ITEMS)

LOCATION_DATA: tuple[LocationData, ...] = (
    *STOCK_TRACK_LOCATIONS,
    *DC_TRACK_LOCATIONS,
    *STOCK_CUP_LOCATIONS,
)

LOCATION_NAME_TO_ID = {
    location.name: location.id
    for location in LOCATION_DATA
}

EVENT_KEY_TO_LOCATION_ID = {
    location.event_key: location.id
    for location in LOCATION_DATA
}


class RVGLLocation(Location):
    game = "RVGL"
