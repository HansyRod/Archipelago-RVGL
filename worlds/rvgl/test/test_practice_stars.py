import unittest
from itertools import product

from BaseClasses import CollectionState
from Fill import distribute_items_restrictive
from Options import OptionError
from test.general import setup_multiworld
from worlds.AutoWorld import call_all

from .. import RVGLWorld
from ..cars import DC_CARS, STOCK_CARS
from ..items import get_car_item_name, get_track_item_name
from ..locations import get_practice_star_location_name, get_single_race_location_name, get_time_trial_location_name
from ..logic import (
    PRACTICE_STAR_CAR_DATA,
    PRACTICE_STAR_MIN_DIFFICULTY,
    PRACTICE_STAR_RESTRICTED_TRACKS,
    PRACTICE_STAR_UNRESTRICTED_TRACKS,
)
from ..options import LogicDifficulty, option_groups
from ..tracks import DC_TRACKS, STOCK_TRACKS


class TestPracticeStarRules(unittest.TestCase):
    def test_option_defaults_and_reference_table_coverage(self) -> None:
        world = setup_multiworld(RVGLWorld, steps=(), seed=0).worlds[1]
        self.assertEqual(LogicDifficulty.options, {"casual": 0, "standard": 1, "expert": 2})
        self.assertEqual(world.options.logic_difficulty.current_key, "standard")
        self.assertTrue(any(LogicDifficulty in group.options for group in option_groups))
        self.assertEqual(tuple(PRACTICE_STAR_MIN_DIFFICULTY), PRACTICE_STAR_RESTRICTED_TRACKS)
        self.assertFalse(set(PRACTICE_STAR_RESTRICTED_TRACKS) & PRACTICE_STAR_UNRESTRICTED_TRACKS)
        self.assertEqual(
            set(PRACTICE_STAR_RESTRICTED_TRACKS) | PRACTICE_STAR_UNRESTRICTED_TRACKS,
            {track.folder for track in (*STOCK_TRACKS, *DC_TRACKS)},
        )
        self.assertEqual(
            PRACTICE_STAR_RESTRICTED_TRACKS,
            tuple(track.folder for track in (*STOCK_TRACKS, *DC_TRACKS)
                  if track.folder in PRACTICE_STAR_RESTRICTED_TRACKS),
        )
        self.assertEqual(set(PRACTICE_STAR_CAR_DATA), {car.folder for car in (*STOCK_CARS, *DC_CARS)})
        for car, difficulties in PRACTICE_STAR_CAR_DATA.items():
            with self.subTest(car=car):
                self.assertEqual(len(difficulties), len(PRACTICE_STAR_RESTRICTED_TRACKS))
                self.assertTrue(all(level in (None, 0, 1, 2) for level in difficulties))
        for requirements in PRACTICE_STAR_MIN_DIFFICULTY.values():
            self.assertEqual(set(requirements), {car.folder for car in (*STOCK_CARS, *DC_CARS)})

    def test_every_car_matches_the_supplied_table_at_every_tier(self) -> None:
        for difficulty, dreamcast in product(range(3), (False, True)):
            world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
                "logic_difficulty": difficulty, "include_dreamcast_cars": dreamcast,
            }).worlds[1]
            for track in STOCK_TRACKS:
                if track.folder not in PRACTICE_STAR_MIN_DIFFICULTY:
                    continue
                location = world.get_location(get_practice_star_location_name(track))
                track_state = CollectionState(world.multiworld)
                track_state.collect(world.create_item(get_track_item_name(track)), prevent_sweep=True)
                self.assertFalse(location.can_reach(track_state))
                self.assertTrue(world.get_location(get_single_race_location_name(track)).can_reach(track_state))
                self.assertTrue(world.get_location(get_time_trial_location_name(track)).can_reach(track_state))

                column = PRACTICE_STAR_RESTRICTED_TRACKS.index(track.folder)
                eligible_cars = []
                ineligible_cars = []
                for car in (*STOCK_CARS, *DC_CARS):
                    # Read the canonical car rows, independently of the lookup used by rules.py.
                    minimum_difficulty = PRACTICE_STAR_CAR_DATA[car.folder][column]
                    expected = (minimum_difficulty is not None and minimum_difficulty <= difficulty
                                and car in world.get_enabled_cars())
                    if expected:
                        eligible_cars.append(car)
                    elif car in world.get_enabled_cars():
                        ineligible_cars.append(car)
                    with self.subTest(track=track.folder, car=car.display_name, tier=difficulty, dreamcast=dreamcast):
                        car_state = CollectionState(world.multiworld)
                        car_state.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
                        self.assertFalse(location.can_reach(car_state), "The car must not bypass track ownership")
                        state = track_state.copy()
                        state.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
                        self.assertEqual(location.can_reach(state), expected)

                # An unsuitable owned car must not invalidate a suitable alternative.
                if ineligible_cars:
                    track_state.collect(world.create_item(get_car_item_name(ineligible_cars[0])), prevent_sweep=True)
                    self.assertFalse(location.can_reach(track_state))
                track_state.collect(world.create_item(get_car_item_name(eligible_cars[0])), prevent_sweep=True)
                self.assertTrue(location.can_reach(track_state))

    def test_unrestricted_tracks_keep_their_track_only_rules(self) -> None:
        for difficulty in range(3):
            world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
                "logic_difficulty": difficulty, "include_dreamcast_track_rooftops": True,
            }).worlds[1]
            for track in world.get_enabled_tracks():
                if track.folder in PRACTICE_STAR_MIN_DIFFICULTY:
                    continue
                with self.subTest(track=track.folder, tier=difficulty):
                    state = CollectionState(world.multiworld)
                    location = world.get_location(get_practice_star_location_name(track))
                    self.assertFalse(location.can_reach(state))
                    state.collect(world.create_item(get_track_item_name(track)), prevent_sweep=True)
                    self.assertTrue(location.can_reach(state))

    def test_car_and_track_ownership_and_difficulty_are_player_specific(self) -> None:
        multiworld = setup_multiworld([RVGLWorld, RVGLWorld], steps=("create_regions", "set_rules"), seed=0,
                                     options=[{"logic_difficulty": "casual"}, {"logic_difficulty": "expert"}])
        track = next(track for track in STOCK_TRACKS if track.folder in PRACTICE_STAR_MIN_DIFFICULTY)
        for car_owner, track_owner, car in product((1, 2), (1, 2), STOCK_CARS):
            state = CollectionState(multiworld)
            state.collect(multiworld.worlds[car_owner].create_item(get_car_item_name(car)), prevent_sweep=True)
            state.collect(multiworld.worlds[track_owner].create_item(get_track_item_name(track)), prevent_sweep=True)
            for player, world in multiworld.worlds.items():
                with self.subTest(car_owner=car_owner, track_owner=track_owner, car=car.folder, player=player):
                    minimum_difficulty = PRACTICE_STAR_MIN_DIFFICULTY[track.folder][car.folder]
                    expected = (player == car_owner == track_owner and minimum_difficulty is not None
                                and minimum_difficulty <= world.options.logic_difficulty.value)
                    self.assertEqual(
                        world.get_location(get_practice_star_location_name(track)).can_reach(state), expected,
                    )

    def test_disabled_stars_skip_rules_but_tracksanity_plus_forces_them(self) -> None:
        for goal in ("platinum_cup", "tracksanity_plus"):
            world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
                "include_practice_stars": False, "goal": goal,
            }).worlds[1]
            location_names = {location.name for location in world.get_locations()}
            for track in world.get_enabled_tracks():
                name = get_practice_star_location_name(track)
                with self.subTest(goal=goal, track=track.folder):
                    if goal != "tracksanity_plus":
                        self.assertNotIn(name, location_names)
                        continue
                    self.assertIn(name, location_names)
                    if track.folder not in PRACTICE_STAR_MIN_DIFFICULTY:
                        continue
                    state = CollectionState(world.multiworld)
                    state.collect(world.create_item(get_track_item_name(track)), prevent_sweep=True)
                    self.assertFalse(world.get_location(name).can_reach(state))
                    requirements = PRACTICE_STAR_MIN_DIFFICULTY[track.folder]
                    car = next(car for car in world.get_enabled_cars()
                               if requirements[car.folder] is not None
                               and requirements[car.folder] <= world.options.logic_difficulty.value)
                    state.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
                    self.assertTrue(world.get_location(name).can_reach(state))

    def test_every_restricted_star_has_a_qualifying_enabled_car(self) -> None:
        for difficulty, dreamcast in product(range(3), (False, True)):
            world = setup_multiworld(RVGLWorld, steps=(), seed=0, options={
                "logic_difficulty": difficulty, "include_dreamcast_cars": dreamcast,
            }).worlds[1]
            for track, requirements in PRACTICE_STAR_MIN_DIFFICULTY.items():
                with self.subTest(track=track, tier=difficulty, dreamcast=dreamcast):
                    self.assertTrue(any(
                        requirements[car.folder] is not None and requirements[car.folder] <= difficulty
                        for car in world.get_enabled_cars()
                    ))

    def test_mixed_difficulties_fill_and_reach_tracksanity_plus_victory(self) -> None:
        options = [
            {"logic_difficulty": difficulty, "include_dreamcast_cars": dreamcast,
             "include_dreamcast_track_rooftops": dreamcast, "starting_cars": 1,
             "starting_tracks": 0 if dreamcast else 1, "goal": "tracksanity_plus"}
            for difficulty, dreamcast in product(("casual", "standard", "expert"), (False, True))
        ]
        multiworld = setup_multiworld([RVGLWorld] * len(options), seed=0, options=options)
        distribute_items_restrictive(multiworld)
        call_all(multiworld, "post_fill")
        call_all(multiworld, "finalize_multiworld")
        self.assertFalse(multiworld.get_unfilled_locations())
        self.assertTrue(multiworld.can_beat_game())
        self.assertTrue(multiworld.fulfills_accessibility())


class TestCasualStartingCars(unittest.TestCase):
    def test_random_starters_guarantee_a_non_phat_car_without_reducing_counts(self) -> None:
        for seed, count, dreamcast in product(range(24), (1, 2, 8), (False, True)):
            with self.subTest(seed=seed, count=count, dreamcast=dreamcast):
                multiworld = setup_multiworld(RVGLWorld, steps=("generate_early",), seed=seed, options={
                    "logic_difficulty": "casual", "starting_cars": count, "include_dreamcast_cars": dreamcast,
                })
                starters = {item.name for item in multiworld.precollected_items[1] if item.name.startswith("Car: ")}
                self.assertEqual(len(starters), count)
                self.assertTrue(starters - {"Car: Phat Slug"})

    def test_phat_only_explicit_starts_require_standard_or_expert(self) -> None:
        for inventory in ({"Car: Phat Slug": 1}, {"Car: Phat Slug": 2},
                          {"Car: Phat Slug": 1, "Car: RC Bandit": 0},
                          {"Car: Phat Slug": 1, "Car: BigVolt": 1}):
            with self.subTest(inventory=inventory):
                with self.assertRaisesRegex(OptionError, "Casual logic.*other than Phat Slug.*starting_cars"):
                    setup_multiworld(RVGLWorld, steps=("generate_early",), seed=0, options={
                        "logic_difficulty": "casual", "starting_cars": 0, "start_inventory": inventory,
                    })
        for difficulty in ("standard", "expert"):
            setup_multiworld(RVGLWorld, steps=("generate_early",), seed=0, options={
                "logic_difficulty": difficulty, "starting_cars": 0, "start_inventory": {"Car: Phat Slug": 1},
            })

    def test_explicit_alternatives_and_random_supplements_are_supported(self) -> None:
        for count, inventory, dreamcast in (
            (0, {"Car: Phat Slug": 1, "Car: RC Bandit": 1}, False),
            (0, {"Car: Toyeca": 1}, False),
            (0, {"Car: Phat Slug": 1, "Car: BigVolt": 1}, True),
            (1, {"Car: Phat Slug": 1}, False),
        ):
            with self.subTest(count=count, inventory=inventory, dreamcast=dreamcast):
                multiworld = setup_multiworld(RVGLWorld, steps=("generate_early", "create_regions"), seed=0, options={
                    "logic_difficulty": "casual", "starting_cars": count, "start_inventory": inventory,
                    "include_dreamcast_cars": dreamcast, "goal": "tracksanity_plus",
                })
                world = multiworld.worlds[1]
                # Match Main.py's timing for the explicit starting inventory.
                for name, quantity in inventory.items():
                    for _ in range(quantity):
                        world.push_precollected(world.create_item(name))
                world.create_items()
                world.set_rules()
                starters = {item.name for item in multiworld.precollected_items[1] if item.name.startswith("Car: ")}
                self.assertTrue(starters - {"Car: Phat Slug"})
                pool_names = {item.name for item in multiworld.itempool}
                self.assertFalse(starters & pool_names)
                distribute_items_restrictive(multiworld)
                self.assertTrue(multiworld.can_beat_game())
                self.assertTrue(multiworld.fulfills_accessibility())
