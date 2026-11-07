from __future__ import annotations

from typing import TYPE_CHECKING

from rule_builder.rules import And, CanReachLocation, Has, HasAny

from .cups import STOCK_CUPS
from .items import get_car_item_name, get_cup_item_name, get_track_item_name
from .locations import (
    get_championship_location_name,
    get_mirror_time_trial_location_name,
    get_practice_star_location_name,
    get_reverse_time_trial_location_name,
    get_stunt_arena_star_location_name,
    get_time_trial_location_name,
)
from .logic import (
    CHAMPIONSHIP_MIN_DIFFICULTY,
    PRACTICE_STAR_MIN_DIFFICULTY,
    STUNT_ARENA_MIN_DIFFICULTY,
    TIME_TRIAL_MIN_DIFFICULTY,
)
from .regions import get_car_region_name, get_cup_region_name, get_track_region_name
from .stunt_arena import STOCK_STUNT_ARENA

if TYPE_CHECKING:
    from .world import RVGLWorld


def set_rules(world: RVGLWorld) -> None:
    """Model which RVGL activities the player's unlock items make available.

    A track item opens that track's Single Race, Practice, and Time Trial checks.
    A cup item opens its championship, including stages on otherwise locked tracks.
    Carsanity checks need the specific car and any unlocked track to race on.
    Generation guarantees a starting car, so region access does not need an
    additional car requirement.

    Championship, Time Trial, Stunt Arena and restricted Practice
    star locations require a suitable car according to the selected logic difficulty.
    All Time Trial variants on a track share that track's car requirement.
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
            world.set_rule(
                world.get_location(get_practice_star_location_name(track)), get_car_rule(world, requirements),
            )

        time_trial_rule = get_car_rule(world, TIME_TRIAL_MIN_DIFFICULTY[track.folder])
        for enabled, location_name in (
            (world.is_normal_time_trials_enabled(), get_time_trial_location_name(track)),
            (world.options.include_reverse_time_trials and track.has_reverse,
             get_reverse_time_trial_location_name(track)),
            (world.options.include_mirror_time_trials, get_mirror_time_trial_location_name(track)),
        ):
            if enabled:
                world.set_rule(world.get_location(location_name), time_trial_rule)

    for cup in STOCK_CUPS:
        entrance = world.get_entrance(f"Menu to {get_cup_region_name(cup)}")
        world.set_rule(entrance, Has(get_cup_item_name(cup)))
        world.set_rule(
            world.get_location(get_championship_location_name(cup)),
            get_car_rule(world, CHAMPIONSHIP_MIN_DIFFICULTY[cup.folder]),
        )

    if world.options.include_stunt_arena_stars:
        for star_number, requirements in STUNT_ARENA_MIN_DIFFICULTY.items():
            world.set_rule(
                world.get_location(get_stunt_arena_star_location_name(STOCK_STUNT_ARENA, star_number)),
                get_car_rule(world, requirements),
            )

    # During generation, reaching a check represents being able to complete it.
    world.set_rule(world.get_location("Victory"), And(*(
        CanReachLocation(location.name) for location in world.get_goal_location_data()
    )))
    world.set_completion_rule(Has("Victory"))


def get_car_rule(world: RVGLWorld, requirements: dict[str, int | None]) -> HasAny[RVGLWorld]:
    """Require any enabled car that qualifies at the selected logic difficulty."""
    return HasAny(*(
        get_car_item_name(car) for car in world.get_enabled_cars()
        if requirements[car.folder] is not None
        and requirements[car.folder] <= world.options.logic_difficulty.value
    ))
