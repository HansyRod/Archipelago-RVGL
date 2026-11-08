import unittest
from collections import Counter
from itertools import product
from unittest.mock import patch

from BaseClasses import Item, ItemClassification, Location, Region
from Fill import balance_multiworld_progression, distribute_items_restrictive
from test.general import TestWorld, setup_multiworld
from worlds.AutoWorld import call_all
from worlds.generic.Rules import locality_rules

from .. import RVGLWorld
from ..car_chains import CAR_RATINGS, CarChainItem, prepare_car_chains
from ..options import CarDistribution, option_groups
from ..output import build_randomizer_config


def progression_pool(multiworld):
    return [item for item in multiworld.itempool if item.advancement]


def sphere_locations(multiworld):
    return [frozenset((location.player, location.name) for location in sphere)
            for sphere in multiworld.get_spheres()]


class TestCarChains(unittest.TestCase):
    def test_car_distribution_defaults_and_labels(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, steps=(), seed=0)
        self.assertEqual(multiworld.worlds[1].options.car_distribution,
                         CarDistribution.option_progressive)
        self.assertEqual(CarDistribution.options, {"progressive": 0, "shuffle": 1})
        self.assertEqual(CarDistribution.from_any("progressive").current_option_name, "Progressive")
        self.assertEqual(CarDistribution.from_any("shuffle").current_option_name, "Shuffle")
        logic_group = next(group for group in option_groups if group.name == "Logic Options")
        self.assertIn(CarDistribution, logic_group.options)

    def test_random_distribution_preserves_original_placement(self) -> None:
        for dreamcast, seed in product((False, True), (0, 1)):
            with self.subTest(dreamcast=dreamcast, seed=seed):
                options = {"include_dreamcast_cars": dreamcast}
                baseline = setup_multiworld([RVGLWorld, RVGLWorld], seed=seed, options=options)
                randomized = setup_multiworld([RVGLWorld, RVGLWorld], seed=seed, options={
                    **options, "car_distribution": "shuffle",
                })
                # Disabling chain preparation recreates the original named-car fill.
                with patch("worlds.rvgl.car_chains.prepare_car_chains"):
                    distribute_items_restrictive(baseline)
                distribute_items_restrictive(randomized)
                self.assertTrue(all(not world.car_chains for world in randomized.worlds.values()))
                self.assertFalse(any(isinstance(item, CarChainItem) for item in randomized.get_items()))
                for multiworld in (baseline, randomized):
                    call_all(multiworld, "post_fill")
                    balance_multiworld_progression(multiworld)
                with patch("worlds.rvgl.car_chains.resolve_car_chains") as resolve:
                    call_all(randomized, "finalize_multiworld")
                    resolve.assert_not_called()
                expected = {(location.player, location.name): (location.item.player, location.item.name)
                            for location in baseline.get_filled_locations()}
                actual = {(location.player, location.name): (location.item.player, location.item.name)
                          for location in randomized.get_filled_locations()}
                self.assertEqual(actual, expected)
                self.assertTrue(randomized.can_beat_game())
                self.assertTrue(randomized.fulfills_accessibility())

    def test_default_chains_cover_every_tier_and_preserve_all_items(self) -> None:
        for dreamcast, starting_cars in product((False, True), (1, 3, 8)):
            with self.subTest(dreamcast=dreamcast, starting_cars=starting_cars):
                multiworld = setup_multiworld(RVGLWorld, seed=0, options={
                    "include_dreamcast_cars": dreamcast, "starting_cars": starting_cars,
                })
                world = multiworld.worlds[1]
                original = multiworld.itempool.copy()
                starting = {item.name for item in multiworld.precollected_items[1]}
                progitempool = progression_pool(multiworld)
                prepare_car_chains(world, progitempool)

                self.assertEqual(len(world.car_chains), 8 if dreamcast else 5)
                chained_cars = [car for chain in world.car_chains for car in chain]
                for chain in world.car_chains:
                    ratings = [CAR_RATINGS[car.name] for car in chain]
                    self.assertEqual(ratings, sorted(set(ratings)))
                    self.assertEqual(ratings[-4:], [1, 2, 3, 4])
                self.assertFalse(starting.intersection(car.name for car in chained_cars))
                leftovers = [item for item in multiworld.itempool
                             if not isinstance(item, CarChainItem) and item.name in CAR_RATINGS]
                self.assertTrue(all(CAR_RATINGS[item.name] < 3 for item in leftovers))
                self.assertEqual(sum(CAR_RATINGS[item.name] == 2 for item in leftovers), int(dreamcast))
                expanded = [item for item in multiworld.itempool if not isinstance(item, CarChainItem)] + chained_cars
                self.assertCountEqual(map(id, expanded), map(id, original))
                self.assertEqual(len(multiworld.itempool), len(original))
                self.assertCountEqual(map(id, progitempool),
                                      (id(item) for item in multiworld.itempool if item.advancement))
                for item in progitempool:
                    if isinstance(item, CarChainItem):
                        self.assertEqual(item.classification, ItemClassification.progression)
                        self.assertFalse(item.skip_in_prog_balancing)

    def test_collect_and_remove_reuse_each_concrete_cars_logic(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, seed=0, options={
            "goal": "carsanity", "include_dreamcast_cars": True, "include_stunt_arena_stars": True,
        })
        world = multiworld.worlds[1]
        progitempool = progression_pool(multiworld)
        prepare_car_chains(world, progitempool)
        for chain_index, chain in enumerate(world.car_chains):
            state = multiworld.state.copy()
            expected = multiworld.state.copy()
            placeholder = next(item for item in progitempool
                               if isinstance(item, CarChainItem) and item.chain_index == chain_index)
            for car in chain:
                self.assertTrue(state.collect(placeholder, prevent_sweep=True))
                expected.collect(car, prevent_sweep=True)
                self.assertEqual(state.prog_items, expected.prog_items)
                self.assertEqual([location.can_reach(state) for location in world.get_locations()],
                                 [location.can_reach(expected) for location in world.get_locations()])
            self.assertFalse(state.collect(placeholder, prevent_sweep=True))
            for car in reversed(chain):
                state.remove(placeholder)
                expected.remove(car)
                self.assertEqual(state.prog_items, expected.prog_items)
            state.remove(placeholder)
            self.assertEqual(state.prog_items, multiworld.state.prog_items)

    def test_explicit_start_inventory_can_remove_any_car_tier(self) -> None:
        starting_names = {"Car: Candy Pebbles", "Car: R6 Turbo", "Car: Zipper", "Car: Toyeca"}
        for dreamcast in (False, True):
            with self.subTest(dreamcast=dreamcast):
                multiworld = setup_multiworld(RVGLWorld, steps=("generate_early", "create_regions"), seed=0,
                                             options={"include_dreamcast_cars": dreamcast})
                world = multiworld.worlds[1]
                for name in starting_names:
                    world.push_precollected(world.create_item(name))
                world.create_items()
                world.set_rules()
                original = Counter(item.name for item in multiworld.itempool)
                distribute_items_restrictive(multiworld)
                self.assertFalse(starting_names.intersection(
                    car.name for chain in world.car_chains for car in chain
                ))
                call_all(multiworld, "post_fill")
                call_all(multiworld, "finalize_multiworld")
                self.assertEqual(Counter(item.name for item in multiworld.itempool), original)
                self.assertTrue(multiworld.can_beat_game())
                self.assertTrue(multiworld.fulfills_accessibility())

    def test_all_high_tier_cars_in_start_inventory_leave_no_chains(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, steps=("generate_early", "create_regions"), seed=0)
        world = multiworld.worlds[1]
        for name, rating in CAR_RATINGS.items():
            if rating >= 3 and name in {item.name for item in world.get_enabled_item_data()}:
                world.push_precollected(world.create_item(name))
        world.create_items()
        world.set_rules()
        distribute_items_restrictive(multiworld)
        call_all(multiworld, "post_fill")
        call_all(multiworld, "finalize_multiworld")
        self.assertFalse(world.car_chains)
        self.assertTrue(multiworld.can_beat_game())
        self.assertTrue(multiworld.fulfills_accessibility())

    def test_chain_preparation_does_not_modify_other_players_or_games(self) -> None:
        multiworld = setup_multiworld([RVGLWorld, RVGLWorld, TestWorld], steps=(), seed=0)
        world = multiworld.worlds[1]
        other_world = multiworld.worlds[2]
        other_car = other_world.create_item("Car: Toyeca")
        foreign_car = Item("Car: Toyeca", ItemClassification.progression, 1, 3)
        same_owner_foreign_car = Item("Car: Toyeca", ItemClassification.progression, 2, 1)
        progitempool = [world.create_item("Car: RC San"), other_car, world.create_item("Car: Toyeca"),
                        foreign_car, world.create_item("Car: Zipper"), same_owner_foreign_car,
                        world.create_item("Silver Cup")]
        original = progitempool.copy()
        multiworld.itempool[:] = progitempool
        prepare_car_chains(world, progitempool)
        for index in (1, 3, 5, 6):
            self.assertIs(progitempool[index], original[index])
            self.assertIs(multiworld.itempool[index], original[index])

    def test_chains_are_seeded_and_independent_of_pool_order(self) -> None:
        def chains(seed, reverse=False):
            multiworld = setup_multiworld(RVGLWorld, seed=seed)
            world = multiworld.worlds[1]
            progitempool = progression_pool(multiworld)
            if reverse:
                progitempool.reverse()
            prepare_car_chains(world, progitempool)
            return tuple(tuple(car.name for car in chain) for chain in world.car_chains)

        self.assertEqual(chains(0), chains(0, reverse=True))
        self.assertNotEqual(chains(0), chains(1))

    def test_conversion_preserves_spheres_and_normal_item_ids_for_all_goals(self) -> None:
        options = [
            {"goal": goal, "include_dreamcast_cars": dreamcast, "starting_cars": starters,
             "include_stunt_arena_stars": True, "car_distribution": distribution}
            for goal, dreamcast, starters, distribution in product(
                ("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"), (False, True), (1, 8),
                ("progressive", "shuffle")
            )
        ]
        multiworld = setup_multiworld([RVGLWorld] * len(options), seed=0, options=options)
        original_pool = Counter((item.player, item.name, item.code) for item in multiworld.itempool)
        catalogue = RVGLWorld.get_data_package_data()
        distribute_items_restrictive(multiworld)
        for world in multiworld.worlds.values():
            self.assertEqual(bool(world.car_chains),
                             world.options.car_distribution == CarDistribution.option_progressive)
            self.assertEqual(any(isinstance(item, CarChainItem) and item.player == world.player
                                 for item in multiworld.itempool), bool(world.car_chains))
        call_all(multiworld, "post_fill")
        self.assertTrue(any(isinstance(item, CarChainItem) for item in multiworld.itempool))
        balance_multiworld_progression(multiworld)
        self.assertTrue(any(isinstance(item, CarChainItem) for item in multiworld.itempool))
        before = sphere_locations(multiworld)
        unchanged = [(location, location.item) for location in multiworld.get_filled_locations()
                     if not isinstance(location.item, CarChainItem)]
        call_all(multiworld, "finalize_multiworld")
        self.assertEqual(sphere_locations(multiworld), before)
        self.assertFalse(any(isinstance(item, CarChainItem) for item in multiworld.get_items()))
        self.assertEqual(Counter((item.player, item.name, item.code) for item in multiworld.itempool), original_pool)
        self.assertEqual(RVGLWorld.get_data_package_data(), catalogue)
        for location, item in unchanged:
            self.assertIs(location.item, item)
        for location in multiworld.get_filled_locations():
            self.assertIs(location.item.location, location)
            if location.address is not None:
                self.assertEqual(location.item.code, RVGLWorld.item_name_to_id[location.item.name])
        self.assertTrue(multiworld.can_beat_game())
        self.assertTrue(multiworld.fulfills_accessibility())
        all_state = multiworld.get_all_state()
        for world in multiworld.worlds.values():
            for item in world.get_enabled_item_data():
                if item.name in CAR_RATINGS:
                    self.assertTrue(all_state.has(item.name, world.player))
            config = build_randomizer_config(world)
            self.assertFalse(any("Progressive" in name for name in config["archipelago"]["items"]))
        call_all(multiworld, "finalize_multiworld")
        self.assertFalse(any(isinstance(item, CarChainItem) for item in multiworld.get_items()))

    def test_local_and_non_local_car_constraints_stay_named(self) -> None:
        multiworld = setup_multiworld([RVGLWorld, RVGLWorld], seed=0, options=[
            {"local_items": {"Car: Toyeca"}, "non_local_items": {"Car: Humma"}}, {},
        ])
        locality_rules(multiworld)
        distribute_items_restrictive(multiworld)
        self.assertFalse({"Car: Toyeca", "Car: Humma"}.intersection(
            car.name for chain in multiworld.worlds[1].car_chains for car in chain
        ))
        call_all(multiworld, "post_fill")
        balance_multiworld_progression(multiworld)
        call_all(multiworld, "finalize_multiworld")
        self.assertEqual(multiworld.find_item("Car: Toyeca", 1).player, 1)
        self.assertEqual(multiworld.find_item("Car: Humma", 1).player, 2)
        self.assertTrue(multiworld.can_beat_game())
        self.assertTrue(multiworld.fulfills_accessibility())

    def test_named_preplaced_cars_are_preserved(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, seed=0)
        world = multiworld.worlds[1]
        car = next(item for item in multiworld.itempool if item.name == "Car: Toyeca")
        location = next(location for location in world.get_locations()
                        if location.address is not None and location.can_reach(multiworld.state))
        multiworld.itempool.remove(car)
        location.place_locked_item(car)
        distribute_items_restrictive(multiworld)
        call_all(multiworld, "post_fill")
        call_all(multiworld, "finalize_multiworld")
        self.assertIs(location.item, car)
        self.assertTrue(location.locked)
        self.assertTrue(multiworld.can_beat_game())
        self.assertTrue(multiworld.fulfills_accessibility())

    def test_a_whole_chain_in_one_sphere_can_include_a_pro_car(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, steps=(), seed=0)
        world = multiworld.worlds[1]
        region = Region("Menu", 1, multiworld)
        multiworld.regions.append(region)
        cars = tuple(world.create_item(name) for name in (
            "Car: RC San", "Car: R6 Turbo", "Car: Zipper", "Car: Toyeca",
        ))
        for index in range(len(cars)):
            location = Location(1, f"Initially available check {index}", index + 1, region)
            region.locations.append(location)
            placeholder = CarChainItem(0, cars, 1)
            location.place_locked_item(placeholder)
            multiworld.itempool.append(placeholder)

        before = sphere_locations(multiworld)
        call_all(multiworld, "post_fill")
        call_all(multiworld, "finalize_multiworld")
        self.assertEqual(sphere_locations(multiworld), before)
        first_sphere = next(multiworld.get_spheres())
        self.assertEqual({location.item.name for location in first_sphere}, {car.name for car in cars})
        self.assertTrue(any(CAR_RATINGS[location.item.name] == 4 for location in first_sphere))
