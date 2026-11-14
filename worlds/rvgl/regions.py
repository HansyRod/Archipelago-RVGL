from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Region

from .cars import CarData
from .cups import STOCK_CUPS, CupData
from .items import RVGLItem
from .locations import LocationData, RVGLLocation
from .stunt_arena import STOCK_STUNT_ARENA, StuntArenaData
from .tracks import TrackData

if TYPE_CHECKING:
    from .world import RVGLWorld


def get_car_region_name(car: CarData) -> str:
    return f"Car: {car.display_name}"


def get_track_region_name(track: TrackData) -> str:
    return f"Track: {track.display_name}"


def get_cup_region_name(cup: CupData) -> str:
    return f"Cup: {cup.display_name}"


def create_regions(world: RVGLWorld) -> None:
    """Create the starting region and a connected region for each stock track and cup.
    Create a region for Stunt Arena stars only if it's included.
    Create regions for enabled cars only when Carsanity is enabled.
    Goals can enable their required check categories independently of location options.
    """
    enabled_location_data = world.get_enabled_location_data()
    menu = Region("Menu", world.player, world.multiworld)
    world.multiworld.regions.append(menu)

    if world.is_carsanity_enabled():
        for car in world.get_enabled_cars():
            _create_content_region(world, menu, get_car_region_name(car), car, enabled_location_data)

    for track in world.get_enabled_tracks():
        _create_content_region(world, menu, get_track_region_name(track), track, enabled_location_data)

    for cup in STOCK_CUPS:
        _create_content_region(world, menu, get_cup_region_name(cup), cup, enabled_location_data)

    if world.options.include_stunt_arena_stars:
        _create_content_region(world, menu, STOCK_STUNT_ARENA.display_name, STOCK_STUNT_ARENA, enabled_location_data)

    goal_region = menu
    goal_region.add_event("Victory", location_type=RVGLLocation, item_type=RVGLItem)


def _create_content_region(
    world: RVGLWorld,
    menu: Region,
    region_name: str,
    source: CarData | TrackData | CupData | StuntArenaData,
    enabled_location_data: tuple[LocationData, ...],
) -> None:
    region = Region(region_name, world.player, world.multiworld)
    world.multiworld.regions.append(region)

    region.add_locations({
        location.name: location.id
        for location in enabled_location_data
        if location.source == source
    }, RVGLLocation)

    # Access requirements are applied separately in rules.py.
    menu.connect(region, f"{menu.name} to {region.name}")
