from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

from BaseClasses import Item, ItemClassification

from .cars import DC_CARS, STOCK_CARS, CarData
from .cups import STOCK_CUPS, CupData
from .tracks import DC_TRACKS, STOCK_TRACKS, TrackData

if TYPE_CHECKING:
    from .world import RVGLWorld


CAR_ID_OFFSET = 1000000
TRACK_ID_OFFSET = 2000000
CUP_ID_OFFSET = 3000000
STUNT_ARENA_ID_OFFSET = 4000000
STOCK_ID_OFFSET = 0
DC_ID_OFFSET = 5000
ITEM_ID_STEP = 100

SourceData: TypeAlias = CarData | TrackData | CupData

@dataclass(frozen=True)
class ItemData:
    id: int
    name: str
    classification: ItemClassification
    source: SourceData | None = None


def get_car_item_name(car:CarData) -> str:
    return f"Car: {car.display_name}"

def get_track_item_name(track:TrackData) -> str:
    return f"Track: {track.display_name}"

def get_cup_item_name(cup:CupData) -> str:
    return cup.display_name


def get_archipelago_item_name(source: SourceData | None) -> str:
    if isinstance(source, CarData):
        return f"car:{source.folder}"
    if isinstance(source, TrackData):
        return f"track:{source.folder}"
    if isinstance(source, CupData):
        return f"cup:{source.difficulty}"
    return ""


def get_car_item_data(cars: tuple[CarData, ...], set_offset: int) -> tuple[ItemData, ...]:
    return tuple(
        ItemData(
            CAR_ID_OFFSET + set_offset + index * ITEM_ID_STEP,
            get_car_item_name(car),
            ItemClassification.useful,
            car
        )
        for index, car in enumerate(cars)
    )

def get_track_item_data(tracks: tuple[TrackData, ...], set_offset: int) -> tuple[ItemData, ...]:
    return tuple(
        ItemData(
            TRACK_ID_OFFSET + set_offset + index * ITEM_ID_STEP,
            get_track_item_name(track),
            ItemClassification.progression,
            track
        )
        for index, track in enumerate(tracks)
    )

def get_cup_item_data(cups: tuple[CupData, ...], set_offset: int) -> tuple[ItemData, ...]:
    return tuple(
        ItemData(
            CUP_ID_OFFSET + set_offset + index * ITEM_ID_STEP,
            get_cup_item_name(cup),
            ItemClassification.progression,
            cup
        )
        for index, cup in enumerate(cups)
    )


STOCK_CAR_ITEMS = get_car_item_data(STOCK_CARS, STOCK_ID_OFFSET)
DC_CAR_ITEMS = get_car_item_data(DC_CARS, DC_ID_OFFSET)
STOCK_TRACK_ITEMS = get_track_item_data(STOCK_TRACKS, STOCK_ID_OFFSET)
DC_TRACK_ITEMS = get_track_item_data(DC_TRACKS, DC_ID_OFFSET)
STOCK_CUP_ITEMS = get_cup_item_data(STOCK_CUPS, STOCK_ID_OFFSET)

FILLER_ITEM = ItemData(99, "Filler", ItemClassification.filler)

ITEM_DATA: tuple[ItemData, ...] = (
    *STOCK_CAR_ITEMS,
    *DC_CAR_ITEMS,
    *STOCK_TRACK_ITEMS,
    *DC_TRACK_ITEMS,
    *STOCK_CUP_ITEMS,
    FILLER_ITEM,
)

# Required Archipelago mapping ITEM_NAME_TO_ID
ITEM_NAME_TO_ID = {
    item.name: item.id
    for item in ITEM_DATA
}


# Each Item instance must correctly report the "game" it belongs to.
# To make this simple, it is common practice to subclass the basic Item class and override the "game" field.
class RVGLItem(Item):
    game = "RVGL"
