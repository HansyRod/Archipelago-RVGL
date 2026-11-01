from __future__ import annotations

from typing import TYPE_CHECKING

from rule_builder.rules import And, CanReachLocation, Has, HasAny

from .cups import STOCK_CUPS
from .items import get_car_item_name, get_cup_item_name, get_track_item_name
from .locations import get_practice_star_location_name
from .logic import PRACTICE_STAR_MIN_DIFFICULTY
from .regions import get_car_region_name, get_cup_region_name, get_track_region_name

if TYPE_CHECKING:
    from .world import RVGLWorld


def set_rules(world: RVGLWorld) -> None:
    """Model which RVGL activities the player's unlock items make available.

    A track item opens that track's Single Race, Practice, and Time Trial checks.
    A cup item opens its championship, including stages on otherwise locked tracks.
    Carsanity checks need the specific car and any unlocked track to race on.
    Generation guarantees a starting car, so track and cup access does not need
    an additional car requirement.

    Car logic has been added to Practice star locations to guarantee the player
    has a suitable car capable of obtaining the track's star, according to the selected logic difficulty.
    """
    if world.is_carsanity_enabled():
        # Track ownership is required even when per-track Single Race checks are disabled.
        has_raceable_track = HasAny(*(get_track_item_name(track) for track in world.get_enabled_tracks()))
        for car in world.get_enabled_cars():
            entrance = world.get_entrance(f"Menu to {get_car_region_name(car)}")
            world.set_rule(entrance, Has(get_car_item_name(car)) & has_raceable_track)

    for track in world.get_enabled_tracks():
        entrance = world.get_entrance(f"Menu to {get_track_region_name(track)}")
        world.set_rule(entrance, Has(get_track_item_name(track)))

        if world.is_practice_stars_enabled() and track.folder in PRACTICE_STAR_MIN_DIFFICULTY:
            requirements = PRACTICE_STAR_MIN_DIFFICULTY[track.folder]
            enabled_cars = world.get_enabled_cars()
            eligible_car_items = [
                get_car_item_name(car) for car in enabled_cars
                if requirements[car.folder] is not None
                and requirements[car.folder] <= world.options.logic_difficulty.value
            ]
            world.set_rule(
                world.get_location(get_practice_star_location_name(track)), HasAny(*eligible_car_items),
            )

    for cup in STOCK_CUPS:
        entrance = world.get_entrance(f"Menu to {get_cup_region_name(cup)}")
        world.set_rule(entrance, Has(get_cup_item_name(cup)))

    # During generation, reaching a check represents being able to complete it.
    world.set_rule(world.get_location("Victory"), And(*(
        CanReachLocation(location.name) for location in world.get_goal_location_data()
    )))
    world.set_completion_rule(Has("Victory"))
