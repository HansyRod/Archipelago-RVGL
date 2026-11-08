"""Temporary progressive car items used during fill, then resolved to normal unlocks."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from BaseClasses import Item, Location, MultiWorld
from Fill import FillError

from .cars import CarData
from .items import ITEM_DATA, RVGLItem

if TYPE_CHECKING:
    from .world import RVGLWorld


CAR_RATINGS = {
    item.name: item.source.rating
    for item in ITEM_DATA
    if isinstance(item.source, CarData)
}


class CarChainItem(RVGLItem):
    def __init__(self, chain_index: int, cars: tuple[RVGLItem, ...], player: int) -> None:
        # This code is temporary: finalize_multiworld restores the concrete car items before output.
        super().__init__(f"Progressive Car (chain {chain_index + 1})",
                         cars[0].classification, cars[0].code, player)
        self.chain_index = chain_index
        self.cars = cars


def prepare_car_chains(world: RVGLWorld, progitempool: list[Item]) -> None:
    """Replace this player's remaining car items with seeded progressive chains."""
    if world.car_chains:
        return

    # Named placement constraints take precedence over the chain arrangement.
    restricted_items = world.options.local_items.value | world.options.non_local_items.value
    cars_by_rating: list[list[RVGLItem]] = [[] for _ in range(5)]
    for item in progitempool:
        if (item.player == world.player and item.game == world.game
                and item.name in CAR_RATINGS and item.name not in restricted_items):
            cars_by_rating[CAR_RATINGS[item.name]].append(item)

    for cars in cars_by_rating:
        # Start with a canonical order so other players' pool ordering does not affect the chains.
        cars.sort(key=lambda item: item.name)
        world.random.shuffle(cars)

    chain_count = max(len(cars_by_rating[3]), len(cars_by_rating[4]))
    world.car_chains = tuple(
        tuple(cars.pop() for cars in cars_by_rating if cars)
        for _ in range(chain_count)
    )
    replacements = {
        id(car): CarChainItem(chain_index, chain, world.player)
        for chain_index, chain in enumerate(world.car_chains)
        for car in chain
    }
    # Use identity: copies of the same progressive item compare equal in Archipelago.
    progitempool[:] = [replacements.get(id(item), item) for item in progitempool]
    world.multiworld.itempool[:] = [
        replacements.get(id(item), item) for item in world.multiworld.itempool
    ]


def resolve_car_chains(multiworld: MultiWorld) -> None:
    """Materialize every RVGL player's chains using one snapshot of logical spheres."""
    # Track the next stage separately for each receiving player and chain.
    stages: Counter[tuple[int, int]] = Counter()
    replacements: dict[int, RVGLItem] = {}
    placements: list[tuple[Location, CarChainItem, RVGLItem]] = []

    # Do not change items while iterating: the sphere calculation must collect the
    # original progressive copies, including all RVGL players' chains together.
    # Visit spheres from earliest to latest.
    for sphere in multiworld.get_spheres():
        chain_locations: dict[tuple[int, int], list[Location]] = defaultdict(list)
        # Group locations by recipient and chain, starting from a deterministic order.
        for location in sorted(sphere):
            if isinstance(location.item, CarChainItem):
                chain_locations[location.item.player, location.item.chain_index].append(location)
        # Randomize stage assignments only within the same chain and sphere.
        for key, locations in sorted(chain_locations.items()):
            multiworld.worlds[key[0]].random.shuffle(locations)
            # Assign each copy its next car and record the replacement without applying it yet.
            for location in locations:
                placeholder = location.item
                if stages[key] >= len(placeholder.cars):
                    raise FillError(f"RVGL car chain {placeholder} has too many placed copies.")
                car = placeholder.cars[stages[key]]
                if not location.item_rule(car):
                    raise FillError(f"RVGL car chain cannot place {car} at {location}.")
                stages[key] += 1
                replacements[id(placeholder)] = car
                placements.append((location, placeholder, car))

    # Check that every placeholder is placed and each chain has its expected number of copies.
    if any(isinstance(item, CarChainItem)
           and (id(item) not in replacements or stages[item.player, item.chain_index] != len(item.cars))
           for item in multiworld.itempool):
        raise FillError("RVGL car chain has missing or unplaced items after fill.")

    # Apply the planned location replacements after the original sphere traversal has finished.
    for location, placeholder, car in placements:
        location.item = car
        car.location = location
        placeholder.location = None
    # Update the global item pool to match the resolved location contents.
    multiworld.itempool[:] = [
        replacements.get(id(item), item) for item in multiworld.itempool
    ]
