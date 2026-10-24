from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Region

from .cups import STOCK_CUPS, CupData
from .items import RVGLItem
from .locations import LOCATION_DATA, RVGLLocation
from .stunt_arena import STOCK_STUNT_ARENA, StuntArenaData
from .tracks import DC_TRACKS, STOCK_TRACKS, TrackData

if TYPE_CHECKING:
    from .world import RVGLWorld


def get_track_region_name(track: TrackData) -> str:
    return f"Track: {track.display_name}"


def get_cup_region_name(cup: CupData) -> str:
    return f"Cup: {cup.display_name}"


def create_regions(world: RVGLWorld) -> None:
    """Create the starting region and a connected region for each stock track and cup.
    Create a region for Stunt Arena stars only if it's included.
    """
    menu = Region("Menu", world.player, world.multiworld)
    world.multiworld.regions.append(menu)

    for track in (*STOCK_TRACKS, *DC_TRACKS):
        _create_content_region(world, menu, get_track_region_name(track), track)

    for cup in STOCK_CUPS:
        _create_content_region(world, menu, get_cup_region_name(cup), cup)

    if world.options.include_stunt_arena_stars:
        _create_content_region(world, menu, STOCK_STUNT_ARENA.display_name, STOCK_STUNT_ARENA)

    goal_region = world.get_region(get_cup_region_name(world.goal_cup))
    goal_region.add_event("Victory", location_type=RVGLLocation, item_type=RVGLItem)


def _create_content_region(
    world: RVGLWorld,
    menu: Region,
    region_name: str,
    source: TrackData | CupData | StuntArenaData,
) -> None:
    region = Region(region_name, world.player, world.multiworld)
    world.multiworld.regions.append(region)

    region.add_locations({
        location.name: location.id
        for location in LOCATION_DATA
        if location.source == source
    }, RVGLLocation)

    # Access requirements are applied separately in rules.py.
    menu.connect(region, f"{menu.name} to {region.name}")
