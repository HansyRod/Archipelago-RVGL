from __future__ import annotations

from typing import TYPE_CHECKING

from rule_builder.rules import CanReachLocation, Has

from .cups import STOCK_CUPS
from .items import get_cup_item_name, get_track_item_name
from .locations import get_championship_location_name
from .regions import get_cup_region_name, get_track_region_name
from .tracks import DC_TRACKS, STOCK_TRACKS

if TYPE_CHECKING:
    from .world import RVGLWorld


def set_rules(world: RVGLWorld) -> None:
    """Require each region's unlock item and define completion as winning the goal cup."""
    for track in (*STOCK_TRACKS, *DC_TRACKS):
        entrance = world.get_entrance(f"Menu to {get_track_region_name(track)}")
        world.set_rule(entrance, Has(get_track_item_name(track)))

    for cup in STOCK_CUPS:
        entrance = world.get_entrance(f"Menu to {get_cup_region_name(cup)}")
        world.set_rule(entrance, Has(get_cup_item_name(cup)))

    # In generation logic, reaching the cup-win check represents being able to win it.
    world.set_rule(world.get_location("Victory"), CanReachLocation(get_championship_location_name(world.goal_cup)))
    world.set_completion_rule(Has("Victory"))
