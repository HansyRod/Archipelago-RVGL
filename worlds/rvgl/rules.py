from __future__ import annotations

from typing import TYPE_CHECKING

from rule_builder.rules import CanReachLocation, Has, HasAny

from .cups import STOCK_CUPS
from .items import get_car_item_name, get_cup_item_name, get_track_item_name
from .locations import get_championship_location_name
from .regions import get_car_region_name, get_cup_region_name, get_track_region_name

if TYPE_CHECKING:
    from .world import RVGLWorld


def set_rules(world: RVGLWorld) -> None:
    """Require each region's unlock item and define completion as winning the goal cup."""
    if world.options.carsanity:
        # Track ownership is required even when per-track Single Race checks are disabled.
        has_raceable_track = HasAny(*(get_track_item_name(track) for track in world.get_enabled_tracks()))
        for car in world.get_enabled_cars():
            entrance = world.get_entrance(f"Menu to {get_car_region_name(car)}")
            world.set_rule(entrance, Has(get_car_item_name(car)) & has_raceable_track)

    for track in world.get_enabled_tracks():
        entrance = world.get_entrance(f"Menu to {get_track_region_name(track)}")
        world.set_rule(entrance, Has(get_track_item_name(track)))

    for cup in STOCK_CUPS:
        entrance = world.get_entrance(f"Menu to {get_cup_region_name(cup)}")
        world.set_rule(entrance, Has(get_cup_item_name(cup)))

    # In generation logic, reaching the cup-win check represents being able to win it.
    world.set_rule(world.get_location("Victory"), CanReachLocation(get_championship_location_name(world.goal_cup)))
    world.set_completion_rule(Has("Victory"))
