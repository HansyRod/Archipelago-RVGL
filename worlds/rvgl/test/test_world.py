import unittest
from collections import Counter
from itertools import product
from unittest.mock import patch

from BaseClasses import CollectionState, ItemClassification
from Fill import distribute_items_restrictive
from Options import OptionError
from test import bases
from test.general import setup_multiworld
from worlds.AutoWorld import call_all

from .. import RVGLWorld
from ..cars import DC_CARS, STOCK_CARS, CarData
from ..cups import STOCK_CUPS, CupData
from ..items import (
    DC_CAR_ITEMS,
    FILLER_ITEM,
    ITEM_DATA,
    STOCK_CAR_ITEMS,
    get_car_item_name,
    get_cup_item_name,
    get_track_item_name,
)
from ..locations import (
    DC_CAR_LOCATIONS,
    EVENT_KEY_TO_LOCATION_ID,
    LOCATION_DATA,
    STOCK_CAR_LOCATIONS,
    STUNT_ARENA_LOCATIONS,
    get_car_race_win_location_name,
)
from ..options import Goal, option_groups
from ..regions import get_car_region_name, get_cup_region_name, get_track_region_name
from ..stunt_arena import STOCK_STUNT_ARENA_STAR_COUNT
from ..tracks import DC_TRACKS, STOCK_TRACKS, TrackData


class TestRVGL(bases.WorldTestBase):
    game = "RVGL"
    world: RVGLWorld

    def world_setup(self, seed: int | None = 0) -> None:
        # A fixed seed makes failures reproducible and enables the inherited world tests.
        super().world_setup(seed)

    def test_starting_inventory(self) -> None:
        starting_items = self.multiworld.precollected_items[self.player]
        starting_names = {item.name for item in starting_items}
        starting_data = [item for item in ITEM_DATA if item.name in starting_names]
        cars = [item.source for item in starting_data if isinstance(item.source, CarData)]
        tracks = [item.source for item in starting_data if isinstance(item.source, TrackData)]
        cups = [item.source for item in starting_data if isinstance(item.source, CupData)]

        self.assertEqual(len(starting_items), 5)
        self.assertEqual(len(starting_names), 5)
        self.assertTrue(all(item.player == self.player for item in starting_items))
        self.assertEqual(len(cars), 3)
        self.assertTrue(all(car in STOCK_CARS and car.rating == 0 for car in cars))
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].difficulty, 1)
        self.assertEqual(len(cups), 1)
        self.assertEqual(cups[0].folder, "bronze")

    def test_item_pool_contains_each_remaining_unlock_once(self) -> None:
        starting_names = {item.name for item in self.multiworld.precollected_items[self.player]}
        unlock_names = {
            item.name for item in ITEM_DATA
            if item.source is not None and item.source not in DC_CARS and item.source not in DC_TRACKS
        }
        pool = [item for item in self.multiworld.itempool if item.player == self.player]
        pool_counts = Counter(item.name for item in pool)

        self.assertEqual(len(pool), len(self.multiworld.get_unfilled_locations(self.player)))
        self.assertFalse(starting_names.intersection(pool_counts))
        self.assertEqual(set(pool_counts) - {FILLER_ITEM.name}, unlock_names - starting_names)
        for item_name in unlock_names - starting_names:
            with self.subTest(item=item_name):
                self.assertEqual(pool_counts[item_name], 1)


class TestRVGLWithCarsanity(TestRVGL):
    options = {"carsanity": "enabled"}


class TestGoals(unittest.TestCase):
    def test_goal_choices_and_existing_defaults(self) -> None:
        world = setup_multiworld(RVGLWorld, steps=(), seed=0).worlds[1]
        self.assertEqual(Goal.options, {"platinum_cup": 0, "carsanity": 1, "tracksanity": 2, "tracksanity_plus": 3})
        self.assertEqual(world.options.goal.current_key, "platinum_cup")
        self.assertTrue(any(Goal in group.options for group in option_groups))
        self.assertEqual(world.options.carsanity.current_key, "disabled")
        self.assertTrue(world.options.include_single_race_wins)
        self.assertFalse(world.is_carsanity_enabled())
        self.assertTrue(world.is_single_race_wins_enabled())
        self.assertTrue(world.is_practice_stars_enabled())
        self.assertTrue(world.is_normal_time_trials_enabled())
        self.assertEqual(world.get_goal_event_keys(), ("championship_win:4",))

    def test_effective_check_settings_preserve_configured_options(self) -> None:
        for goal, carsanity, race_wins in product(
            ("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"), ("disabled", "enabled"), (False, True),
        ):
            with self.subTest(goal=goal, carsanity=carsanity, race_wins=race_wins):
                world = setup_multiworld(RVGLWorld, steps=(), seed=0, options={
                    "goal": goal, "carsanity": carsanity, "include_single_race_wins": race_wins,
                }).worlds[1]
                self.assertIs(world.is_carsanity_enabled(), carsanity == "enabled" or goal == "carsanity")
                self.assertIs(world.is_single_race_wins_enabled(), race_wins or goal in ("tracksanity", "tracksanity_plus"))
                self.assertEqual(world.options.carsanity.current_key, carsanity)
                self.assertEqual(bool(world.options.include_single_race_wins), race_wins)
                self.assertEqual(world.options.goal.current_key, goal)

    def test_effective_practice_and_normal_time_trial_settings_preserve_configured_options(self) -> None:
        for goal, practice_stars, normal_trials in product(
            ("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"), (False, True), (False, True),
        ):
            with self.subTest(goal=goal, practice_stars=practice_stars, normal_trials=normal_trials):
                world = setup_multiworld(RVGLWorld, steps=(), seed=0, options={
                    "goal": goal, "include_practice_stars": practice_stars, "include_normal_time_trials": normal_trials,
                }).worlds[1]
                self.assertIs(world.is_practice_stars_enabled(), practice_stars or goal == "tracksanity_plus")
                self.assertIs(world.is_normal_time_trials_enabled(), normal_trials or goal == "tracksanity_plus")
                self.assertEqual(bool(world.options.include_practice_stars), practice_stars)
                self.assertEqual(bool(world.options.include_normal_time_trials), normal_trials)

    def test_goal_requirements_match_each_players_enabled_content(self) -> None:
        options = [
            {"goal": goal, "include_dreamcast_cars": cars, "include_dreamcast_track_rooftops": rooftops,
             "carsanity": "disabled", "include_single_race_wins": False, "include_practice_stars": False,
             "include_normal_time_trials": False, "include_stunt_arena_stars": True}
            for goal, cars, rooftops in product(
                ("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"), (False, True), (False, True),
            )
        ]
        catalogue = {location.event_key: location for location in LOCATION_DATA}
        multiworld = setup_multiworld([RVGLWorld] * len(options), steps=(), seed=0, options=options)
        for player, world in multiworld.worlds.items():
            settings = options[player - 1]
            with self.subTest(player=player, options=settings):
                if settings["goal"] == "carsanity":
                    cars = (*STOCK_CARS, *DC_CARS) if settings["include_dreamcast_cars"] else STOCK_CARS
                    expected_keys = tuple(f"car_race_win:{car.folder}" for car in cars)
                    expected_count = 42 if settings["include_dreamcast_cars"] else 28
                elif settings["goal"] in ("tracksanity", "tracksanity_plus"):
                    tracks = (*STOCK_TRACKS, *DC_TRACKS) if settings["include_dreamcast_track_rooftops"] else STOCK_TRACKS
                    if settings["goal"] == "tracksanity_plus":
                        event_types = ("single_race_win", "practice_star", "time_trial_normal")
                        expected_count = 42 if settings["include_dreamcast_track_rooftops"] else 39
                    else:
                        event_types = ("single_race_win",)
                        expected_count = 14 if settings["include_dreamcast_track_rooftops"] else 13
                    expected_keys = tuple(f"{event_type}:{track.folder}" for track in tracks for event_type in event_types)
                else:
                    expected_keys = ("championship_win:4",)
                    expected_count = 1
                self.assertEqual(world.get_goal_event_keys(), expected_keys)
                self.assertEqual(len(expected_keys), expected_count)
                self.assertEqual(len(set(expected_keys)), expected_count)
                self.assertEqual(world.get_goal_location_data(), tuple(catalogue[key] for key in expected_keys))
                for location in world.get_goal_location_data():
                    self.assertIs(location, catalogue[location.event_key])
                    self.assertEqual(world.location_name_to_id[location.name], location.id)
                    self.assertEqual(EVENT_KEY_TO_LOCATION_ID[location.event_key], location.id)

    def test_starting_inventory_and_seed_do_not_remove_or_reorder_goal_checks(self) -> None:
        for goal, starting_cars, starting_tracks in product(
            ("carsanity", "tracksanity", "tracksanity_plus"), (1, 3, 8), (0, 1, 4),
        ):
            with self.subTest(goal=goal, starting_cars=starting_cars, starting_tracks=starting_tracks):
                expected_sources = STOCK_CARS if goal == "carsanity" else STOCK_TRACKS
                if goal == "tracksanity_plus":
                    expected_sources = tuple(track for track in STOCK_TRACKS for _ in range(3))
                for seed in (0, 1):
                    multiworld = setup_multiworld(RVGLWorld, steps=("generate_early",), seed=seed, options={
                        "goal": goal, "starting_cars": starting_cars, "starting_tracks": starting_tracks,
                    })
                    world = multiworld.worlds[1]
                    requirements = world.get_goal_location_data()
                    self.assertEqual(tuple(location.source for location in requirements), expected_sources)
                    self.assertEqual(len(multiworld.precollected_items[1]), starting_cars + starting_tracks + 1)


class TestGoalRules(unittest.TestCase):
    def _goal_item_names(self, world: RVGLWorld) -> tuple[str, ...]:
        """Return goal items needed in addition to the guaranteed starting RC Bandit."""
        if world.options.goal == "platinum_cup":
            return ("Platinum Cup",)
        if world.options.goal == "carsanity":
            return (*(get_car_item_name(car) for car in world.get_enabled_cars() if car != STOCK_CARS[0]),
                    "Track: Toys in the Hood 1")
        return tuple(get_track_item_name(track) for track in world.get_enabled_tracks())

    def _state_with_items(self, world: RVGLWorld, item_names: tuple[str, ...]) -> CollectionState:
        state = CollectionState(world.multiworld)
        state.collect(world.create_item("Car: RC Bandit"), prevent_sweep=True)
        for item_name in item_names:
            state.collect(world.create_item(item_name), prevent_sweep=True)
        return state

    def test_goals_include_their_checks_when_location_options_are_disabled(self) -> None:
        disabled_options = {
            "carsanity": "disabled", "include_single_race_wins": False, "include_practice_stars": False,
            "include_normal_time_trials": False, "include_reverse_time_trials": False,
            "include_mirror_time_trials": False,
        }
        for goal, cars, rooftops in product(
            ("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"), (False, True), (False, True),
        ):
            with self.subTest(goal=goal, cars=cars, rooftops=rooftops):
                world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
                    **disabled_options, "goal": goal, "include_dreamcast_cars": cars,
                    "include_dreamcast_track_rooftops": rooftops,
                }).worlds[1]
                required_ids = {location.id for location in world.get_goal_location_data()}
                cup_ids = {location.id for location in LOCATION_DATA if isinstance(location.source, CupData)}
                active_ids = {location.address for location in world.get_locations() if location.address is not None}
                self.assertEqual(active_ids, required_ids | cup_ids)
                self.assertEqual(
                    sum(region.name.startswith("Car: ") for region in world.get_regions()),
                    len(world.get_enabled_cars()) if goal == "carsanity" else 0,
                )
                for option_name, configured_value in disabled_options.items():
                    expected = "disabled" if option_name == "carsanity" else configured_value
                    actual = getattr(world.options, option_name)
                    self.assertEqual(actual.current_key if option_name == "carsanity" else bool(actual), expected)
                victory = world.get_location("Victory")
                self.assertEqual(victory.parent_region.name, "Menu")
                self.assertIsNone(victory.address)
                self.assertIsNone(victory.item.code)

    def test_goal_requires_each_needed_item_and_accepts_the_last_missing_item(self) -> None:
        for goal, dreamcast in product(("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"), (False, True)):
            world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
                "goal": goal, "include_dreamcast_cars": dreamcast, "include_dreamcast_track_rooftops": dreamcast,
            }).worlds[1]
            item_names = self._goal_item_names(world)
            for missing_item in item_names:
                with self.subTest(goal=goal, dreamcast=dreamcast, missing_item=missing_item):
                    state = self._state_with_items(world, tuple(name for name in item_names if name != missing_item))
                    self.assertFalse(world.get_location("Victory").can_reach(state))
                    state.sweep_for_advancements()
                    self.assertFalse(world.multiworld.completion_condition[world.player](state))
                    state.collect(world.create_item(missing_item), prevent_sweep=True)
                    self.assertTrue(world.get_location("Victory").can_reach(state))
                    state.sweep_for_advancements()
                    self.assertTrue(world.multiworld.completion_condition[world.player](state))

    def test_victory_requires_every_goal_location_including_each_plus_check_type(self) -> None:
        for goal in ("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"):
            world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
                "goal": goal, "include_dreamcast_cars": True, "include_dreamcast_track_rooftops": True,
            }).worlds[1]
            for requirement in world.get_goal_location_data():
                with self.subTest(goal=goal, blocked_location=requirement.name):
                    state = self._state_with_items(world, self._goal_item_names(world))
                    with patch.object(world.get_location(requirement.name), "access_rule", return_value=False):
                        self.assertFalse(world.get_location("Victory").can_reach(state))
                        state.sweep_for_advancements()
                        self.assertFalse(world.multiworld.completion_condition[world.player](state))

    def test_optional_checks_and_cups_do_not_gate_other_goals(self) -> None:
        for goal in ("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"):
            with self.subTest(goal=goal):
                world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
                    "goal": goal, "carsanity": "enabled", "include_stunt_arena_stars": True,
                }).worlds[1]
                state = self._state_with_items(world, self._goal_item_names(world))
                self.assertTrue(world.get_location("Victory").can_reach(state))
                state.sweep_for_advancements()
                self.assertTrue(world.multiworld.completion_condition[world.player](state))

    def test_mixed_goals_generate_and_fill_with_independent_content_and_starting_items(self) -> None:
        options = [
            {"goal": goal, "include_dreamcast_cars": cars, "include_dreamcast_track_rooftops": rooftops,
             "carsanity": "disabled", "include_single_race_wins": False,
             "starting_cars": 1 if cars else 3, "starting_tracks": 4 if cars else 0}
            for goal, cars, rooftops in product(
                ("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"), (False, True), (False, True),
            )
        ]
        catalogue = dict(RVGLWorld.location_name_to_id)
        for player_options in (options, list(reversed(options))):
            multiworld = setup_multiworld([RVGLWorld] * len(player_options), seed=0, options=player_options)
            for player, world in multiworld.worlds.items():
                with self.subTest(player=player, options=player_options[player - 1]):
                    self.assertEqual(world.options.goal.current_key, player_options[player - 1]["goal"])
                    pool = [item for item in multiworld.itempool if item.player == player]
                    self.assertEqual(len(pool), len(multiworld.get_unfilled_locations(player)))
                    self.assertTrue(all(world.get_location(location.name).address == location.id
                                        for location in world.get_goal_location_data()))
            distribute_items_restrictive(multiworld)
            call_all(multiworld, "post_fill")
            call_all(multiworld, "finalize_multiworld")
            self.assertFalse(multiworld.get_unfilled_locations())
            self.assertTrue(multiworld.can_beat_game())
            self.assertTrue(multiworld.fulfills_accessibility())
            self.assertEqual(RVGLWorld.location_name_to_id, catalogue)


class TestStartingCars(unittest.TestCase):
    def test_zero_starting_cars_raises_option_error(self) -> None:
        for goal, starting_inventory in product(
            ("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"),
            ({}, {"Car: RC Bandit": 0}, {"Track: Toys in the Hood 1": 1}, {"Car: BigVolt": 1}),
        ):
            with self.subTest(goal=goal, start_inventory=starting_inventory):
                with self.assertRaisesRegex(OptionError, "at least one starting car.*starting_cars"):
                    setup_multiworld(RVGLWorld, seed=0, options={
                        "goal": goal, "starting_cars": 0, "start_inventory": starting_inventory,
                    })
        with self.assertRaisesRegex(OptionError, r"RVGL player 2 \(Tester2\).*at least one starting car"):
            setup_multiworld([RVGLWorld, RVGLWorld], seed=0, options=[{}, {"starting_cars": 0}])

    def test_zero_random_starting_cars_accepts_enabled_start_inventory_cars(self) -> None:
        for goal, (car_name, dreamcast) in product(
            ("platinum_cup", "carsanity", "tracksanity", "tracksanity_plus"),
            (("Car: RC Bandit", False), ("Car: Toyeca", False), ("Car: BigVolt", True)),
        ):
            with self.subTest(goal=goal, car=car_name, dreamcast=dreamcast):
                multiworld = setup_multiworld(RVGLWorld, steps=("generate_early", "create_regions"), seed=0, options={
                    "goal": goal, "starting_cars": 0, "start_inventory": {car_name: 1},
                    "include_dreamcast_cars": dreamcast,
                })
                world = multiworld.worlds[1]
                # Match Main.py: apply the common start_inventory after generate_early.
                for item_name, count in world.options.start_inventory.value.items():
                    for _ in range(count):
                        world.push_precollected(world.create_item(item_name))
                world.create_items()
                world.set_rules()
                self.assertEqual(
                    [item.name for item in multiworld.precollected_items[1] if item.name.startswith("Car: ")],
                    [car_name],
                )
                self.assertNotIn(car_name, [item.name for item in multiworld.itempool])
                self.assertEqual(len(multiworld.itempool), len(multiworld.get_unfilled_locations(1)))
                distribute_items_restrictive(multiworld)
                self.assertFalse(multiworld.get_unfilled_locations())
                self.assertTrue(multiworld.can_beat_game())
                self.assertTrue(multiworld.fulfills_accessibility())

    def test_starting_car_counts_and_item_pool(self) -> None:
        rookie_names = {f"Car: {car.display_name}" for car in STOCK_CARS if car.rating == 0}
        for count in range(1, 9):
            with self.subTest(starting_cars=count):
                multiworld = setup_multiworld(RVGLWorld, seed=0, options={"starting_cars": count})
                starting_items = multiworld.precollected_items[1]
                starting_names = {item.name for item in starting_items}
                starting_cars = {name for name in starting_names if name.startswith("Car: ")}
                pool_names = [item.name for item in multiworld.itempool]

                self.assertEqual(len(starting_cars), count)
                self.assertTrue(starting_cars.issubset(rookie_names))
                self.assertEqual(len(starting_items), count + 2)
                self.assertEqual(len(starting_names), count + 2)
                self.assertIn("Bronze Cup", starting_names)
                self.assertEqual(sum(name.startswith("Track: ") for name in starting_names), 1)
                self.assertFalse(starting_names.intersection(pool_names))
                self.assertEqual(len(pool_names), len(multiworld.get_unfilled_locations(1)))
                self.assertTrue((rookie_names - starting_cars).issubset(pool_names))


class TestStartingTracks(unittest.TestCase):
    def test_starting_track_counts_and_item_pool(self) -> None:
        easy_names = {
            get_track_item_name(track) for track in (*STOCK_TRACKS, *DC_TRACKS) if track.difficulty == 1
        }
        for count in range(5):
            with self.subTest(starting_tracks=count):
                multiworld = setup_multiworld(RVGLWorld, seed=0, options={"starting_tracks": count})
                starting_items = multiworld.precollected_items[1]
                starting_names = {item.name for item in starting_items}
                starting_tracks = {name for name in starting_names if name.startswith("Track: ")}
                pool_counts = Counter(item.name for item in multiworld.itempool)

                self.assertEqual(len(starting_tracks), count)
                self.assertTrue(starting_tracks.issubset(easy_names))
                self.assertEqual(len(starting_items), count + 4)
                self.assertEqual(len(starting_names), count + 4)
                self.assertIn("Bronze Cup", starting_names)
                self.assertEqual(sum(name.startswith("Car: ") for name in starting_names), 3)
                self.assertFalse(starting_names.intersection(pool_counts))
                self.assertEqual(len(multiworld.itempool), len(multiworld.get_unfilled_locations(1)))
                for item_name in easy_names - starting_tracks:
                    self.assertEqual(pool_counts[item_name], 1)


class TestItemPoolOptions(unittest.TestCase):
    def test_dreamcast_content_is_selected_independently_for_each_player(self) -> None:
        options = [
            {"include_dreamcast_cars": cars, "include_dreamcast_track_rooftops": rooftops}
            for cars, rooftops in product((False, True), repeat=2)
        ]
        catalogue = dict(RVGLWorld.location_name_to_id)
        item_catalogue = dict(RVGLWorld.item_name_to_id)
        multiworld = setup_multiworld([RVGLWorld] * len(options), seed=0, options=options)
        for player, world in multiworld.worlds.items():
            with self.subTest(player=player, options=options[player - 1]):
                starting_names = {item.name for item in multiworld.precollected_items[player]}
                unlock_names = {
                    item.name for item in ITEM_DATA
                    if item.source is not None
                    and (world.options.include_dreamcast_cars or item.source not in DC_CARS)
                    and (world.options.include_dreamcast_track_rooftops or item.source not in DC_TRACKS)
                } - starting_names
                pool = [item for item in multiworld.itempool if item.player == player]
                self.assertEqual(
                    Counter(item.name for item in pool if item.name != FILLER_ITEM.name), Counter(unlock_names),
                )
                self.assertEqual(len(pool), len(multiworld.get_unfilled_locations(player)))
                self.assertEqual(
                    {location.address for location in world.get_locations() if location.address is not None},
                    {location.id for location in LOCATION_DATA
                     if location not in STUNT_ARENA_LOCATIONS
                     and not isinstance(location.source, CarData)
                     and (world.options.include_dreamcast_track_rooftops or location.source not in DC_TRACKS)},
                )
                self.assertEqual(world.location_name_to_id, catalogue)
                self.assertEqual(world.item_name_to_id, item_catalogue)
        distribute_items_restrictive(multiworld)
        call_all(multiworld, "post_fill")
        call_all(multiworld, "finalize_multiworld")
        self.assertFalse(multiworld.get_unfilled_locations())
        self.assertTrue(multiworld.can_beat_game())
        self.assertTrue(multiworld.fulfills_accessibility())


class TestStuntArena(unittest.TestCase):
    def test_stunt_star_catalogue_matches_dll_events(self) -> None:
        self.assertEqual(len(STUNT_ARENA_LOCATIONS), STOCK_STUNT_ARENA_STAR_COUNT)
        self.assertEqual(
            [location.id for location in STUNT_ARENA_LOCATIONS],
            list(range(4000001, 4000001 + STOCK_STUNT_ARENA_STAR_COUNT)),
        )
        self.assertEqual(
            [location.name for location in STUNT_ARENA_LOCATIONS],
            [f"Find Stunt Arena Star: {number}" for number in range(1, STOCK_STUNT_ARENA_STAR_COUNT + 1)],
        )
        self.assertEqual(
            [location.event_key for location in STUNT_ARENA_LOCATIONS],
            [f"stunt_star:{number}" for number in range(1, STOCK_STUNT_ARENA_STAR_COUNT + 1)],
        )
        self.assertEqual(len(LOCATION_DATA), len({location.id for location in LOCATION_DATA}))
        self.assertEqual(len(LOCATION_DATA), len(RVGLWorld.location_name_to_id))
        self.assertEqual(len(LOCATION_DATA), len(EVENT_KEY_TO_LOCATION_ID))

    def test_mixed_stunt_star_options_generate_independently(self) -> None:
        catalogue = dict(RVGLWorld.location_name_to_id)
        data_package = RVGLWorld.get_data_package_data()
        stunt_ids = {location.id for location in STUNT_ARENA_LOCATIONS}
        for enabled_player in (1, 2):
            with self.subTest(enabled_player=enabled_player):
                multiworld = setup_multiworld(
                    [RVGLWorld, RVGLWorld], seed=0,
                    options=[{"include_stunt_arena_stars": player == enabled_player} for player in (1, 2)],
                )
                filler_counts = {}
                for player, world in multiworld.worlds.items():
                    active_ids = {
                        location.address for location in world.get_locations() if location.address is not None
                    }
                    expected_ids = set(catalogue.values())
                    expected_ids -= {location.id for location in LOCATION_DATA if isinstance(location.source, CarData)}
                    expected_ids -= {location.id for location in LOCATION_DATA if location.source in DC_TRACKS}
                    if player != enabled_player:
                        expected_ids -= stunt_ids
                    self.assertEqual(active_ids, expected_ids)
                    self.assertEqual(world.location_name_to_id, catalogue)

                    pool = [item for item in multiworld.itempool if item.player == player]
                    self.assertEqual(len(pool), len(multiworld.get_unfilled_locations(player)))
                    filler_counts[player] = sum(item.name == FILLER_ITEM.name for item in pool)
                    if player == enabled_player:
                        state = CollectionState(multiworld)
                        for location in STUNT_ARENA_LOCATIONS:
                            self.assertTrue(world.get_location(location.name).can_reach(state))

                self.assertEqual(
                    filler_counts[enabled_player] - filler_counts[3 - enabled_player], STOCK_STUNT_ARENA_STAR_COUNT,
                )
                distribute_items_restrictive(multiworld)
                call_all(multiworld, "post_fill")
                call_all(multiworld, "finalize_multiworld")
                self.assertFalse(multiworld.get_unfilled_locations())
                self.assertTrue(multiworld.can_beat_game())
                self.assertTrue(multiworld.fulfills_accessibility())
                self.assertEqual(RVGLWorld.location_name_to_id, catalogue)
                self.assertEqual(RVGLWorld.get_data_package_data(), data_package)


class TestLocationPoolOptions(unittest.TestCase):
    def test_location_option_combinations_preserve_catalogue_and_balance(self) -> None:
        location_options = {
            "include_single_race_wins": "single_race_win:",
            "include_practice_stars": "practice_star:",
            "include_normal_time_trials": "time_trial_normal:",
            "include_reverse_time_trials": "time_trial_reverse:",
            "include_mirror_time_trials": "time_trial_mirror:",
            "include_stunt_arena_stars": "stunt_star:",
            "carsanity": "car_race_win:",
        }
        catalogue = dict(RVGLWorld.location_name_to_id)
        data_package = RVGLWorld.get_data_package_data()
        item_options = ("include_dreamcast_cars", "include_dreamcast_track_rooftops")
        for enabled in product((False, True), repeat=len(location_options) + len(item_options)):
            options = dict(zip((*location_options, *item_options), enabled))
            # Carsanity is a Choice accepting 0/1 rather than Toggle's boolean values.
            options["carsanity"] = int(options["carsanity"])
            with self.subTest(options=options):
                multiworld = setup_multiworld(
                    RVGLWorld, steps=("generate_early", "create_regions"), seed=0, options=options,
                )
                world = multiworld.worlds[1]
                expected_ids = {
                    location.id for location in LOCATION_DATA
                    if (options["include_dreamcast_track_rooftops"] or location.source not in DC_TRACKS)
                    and (options["include_dreamcast_cars"] or location.source not in DC_CARS)
                    and (location.event_key.startswith("championship_win:")
                         or any(options[key] and location.event_key.startswith(prefix)
                                for key, prefix in location_options.items()))
                }
                self.assertEqual(
                    {location.address for location in world.get_locations() if location.address is not None},
                    expected_ids,
                )
                starting_names = {item.name for item in multiworld.precollected_items[1]}
                unlock_names = {
                    item.name for item in ITEM_DATA
                    if item.source is not None
                    and (options["include_dreamcast_cars"] or item.source not in DC_CARS)
                    and (options["include_dreamcast_track_rooftops"] or item.source not in DC_TRACKS)
                } - starting_names
                if len(unlock_names) > len(expected_ids):
                    with self.assertRaisesRegex(
                        OptionError,
                        f"{len(unlock_names)} unlock items.*only {len(expected_ids)} enabled locations.*"
                        "Enable more Location Pool Options",
                    ):
                        world.create_items()
                    self.assertFalse(multiworld.itempool)
                else:
                    world.create_items()
                    world.set_rules()
                    self.assertEqual(len(multiworld.itempool), len(expected_ids))
                    self.assertEqual(
                        Counter(item.name for item in multiworld.itempool if item.name != FILLER_ITEM.name),
                        Counter(unlock_names),
                    )
                    distribute_items_restrictive(multiworld)
                    call_all(multiworld, "post_fill")
                    call_all(multiworld, "finalize_multiworld")
                    self.assertFalse(multiworld.get_unfilled_locations())
                    self.assertTrue(multiworld.can_beat_game())
                    self.assertTrue(multiworld.fulfills_accessibility())
                self.assertEqual({key: getattr(world.options, key).value for key in options}, options)
                self.assertEqual({item.name for item in multiworld.precollected_items[1]}, starting_names)
                self.assertEqual(RVGLWorld.location_name_to_id, catalogue)
                self.assertEqual(RVGLWorld.get_data_package_data(), data_package)

    def test_starting_inventory_can_make_exactly_enough_room(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, seed=0, options={
            "include_dreamcast_cars": True,
            "include_dreamcast_track_rooftops": True,
            "include_normal_time_trials": False,
            "include_reverse_time_trials": False,
            "include_mirror_time_trials": False,
            "include_stunt_arena_stars": True,
            "starting_cars": 5,
            "starting_tracks": 2,
        })
        self.assertEqual(len(multiworld.itempool), len(multiworld.get_unfilled_locations(1)))
        self.assertTrue(all(item.name != FILLER_ITEM.name for item in multiworld.itempool))
        distribute_items_restrictive(multiworld)
        self.assertFalse(multiworld.get_unfilled_locations())
        self.assertTrue(multiworld.can_beat_game())
        self.assertTrue(multiworld.fulfills_accessibility())


class TestRegionAccess(unittest.TestCase):
    def test_regions_require_their_own_players_item(self) -> None:
        # Omit starting inventory so every region's requirement can be tested independently.
        multiworld = setup_multiworld(
            [RVGLWorld, RVGLWorld], steps=("create_regions", "set_rules"), seed=0,
            options={"include_dreamcast_track_rooftops": True},
        )
        requirements = [
            (get_track_region_name(track), get_track_item_name(track))
            for track in (*STOCK_TRACKS, *DC_TRACKS)
        ] + [
            (get_cup_region_name(cup), get_cup_item_name(cup))
            for cup in STOCK_CUPS
        ]

        empty_state = CollectionState(multiworld)
        for player in multiworld.player_ids:
            empty_state.collect(multiworld.worlds[player].create_item("Car: RC Bandit"), prevent_sweep=True)
            self.assertTrue(multiworld.get_region("Menu", player).can_reach(empty_state))
            for region_name, _ in requirements:
                with self.subTest(player=player, region=region_name, inventory="empty"):
                    self.assertFalse(multiworld.get_region(region_name, player).can_reach(empty_state))

        for recipient in multiworld.player_ids:
            for unlocked_region, item_name in requirements:
                state = empty_state.copy()
                state.collect(multiworld.worlds[recipient].create_item(item_name), prevent_sweep=True)

                for player in multiworld.player_ids:
                    for region_name, _ in requirements:
                        with self.subTest(recipient=recipient, item=item_name, player=player, region=region_name):
                            expected = player == recipient and region_name == unlocked_region
                            region = multiworld.get_region(region_name, player)
                            self.assertEqual(region.can_reach(state), expected)
                            for location in region.locations:
                                self.assertEqual(location.can_reach(state), expected, location.name)


class TestCarsanity(unittest.TestCase):
    def test_car_catalogue_matches_dll_events_and_stable_ids(self) -> None:
        for locations, cars, first_id, count in (
            (STOCK_CAR_LOCATIONS, STOCK_CARS, 1000001, 28),
            (DC_CAR_LOCATIONS, DC_CARS, 1005001, 14),
        ):
            self.assertEqual(len(locations), count)
            self.assertEqual([location.id for location in locations],
                             [first_id + index * 100 for index in range(count)])
            self.assertEqual([location.name for location in locations],
                             [f"Win Race with Car: {car.display_name}" for car in cars])
            self.assertEqual([location.event_key for location in locations],
                             [f"car_race_win:{car.folder}" for car in cars])
            self.assertEqual([location.source for location in locations], list(cars))
        self.assertEqual(len(LOCATION_DATA), len({location.id for location in LOCATION_DATA}))
        self.assertEqual(len(LOCATION_DATA), len(RVGLWorld.location_name_to_id))
        self.assertEqual(len(LOCATION_DATA), len(EVENT_KEY_TO_LOCATION_ID))

    def test_car_items_are_progression_with_carsanity_disabled_or_enabled(self) -> None:
        options = [{}, {"carsanity": "enabled"}, {"include_dreamcast_cars": True},
                   {"carsanity": "enabled", "include_dreamcast_cars": True}]
        multiworld = setup_multiworld([RVGLWorld] * len(options), seed=0, options=options)
        self.assertEqual(multiworld.worlds[1].options.carsanity.current_key, "disabled")
        for player, world in multiworld.worlds.items():
            expected_cars = (*STOCK_CARS, *DC_CARS) if options[player - 1].get("include_dreamcast_cars") else STOCK_CARS
            self.assertEqual(world.get_enabled_cars(), expected_cars)
            enabled_car_items = tuple(item for item in world.get_enabled_item_data() if isinstance(item.source, CarData))
            self.assertEqual({item.source for item in enabled_car_items}, set(expected_cars))
            for item in (*STOCK_CAR_ITEMS, *DC_CAR_ITEMS):
                with self.subTest(player=player, item=item.name):
                    self.assertEqual(item.classification, ItemClassification.progression)
                    self.assertEqual(world.create_item(item.name).classification, ItemClassification.progression)

    def test_starting_cars_retain_their_win_checks(self) -> None:
        for dreamcast, starting_cars in product((False, True), (1, 3, 8)):
            with self.subTest(dreamcast=dreamcast, starting_cars=starting_cars):
                multiworld = setup_multiworld(RVGLWorld, seed=0, options={
                    "carsanity": "enabled", "include_dreamcast_cars": dreamcast,
                    "starting_cars": starting_cars,
                })
                world = multiworld.worlds[1]
                starting_names = {item.name for item in multiworld.precollected_items[1]}
                cars = (*STOCK_CARS, *DC_CARS) if dreamcast else STOCK_CARS
                self.assertEqual(sum(get_car_item_name(car) in starting_names for car in cars), starting_cars)
                for car in cars:
                    location = world.get_location(get_car_race_win_location_name(car))
                    self.assertEqual(location.can_reach(multiworld.state), get_car_item_name(car) in starting_names)
                    self.assertEqual(location.parent_region.name, get_car_region_name(car))
                self.assertFalse(starting_names.intersection(item.name for item in multiworld.itempool))

    def test_mixed_options_generate_and_fill_in_both_player_orders(self) -> None:
        options = [
            {"carsanity": carsanity, "include_dreamcast_cars": cars, "include_dreamcast_track_rooftops": rooftops,
             "include_single_race_wins": False, "include_stunt_arena_stars": True, "starting_tracks": 0}
            for carsanity, cars, rooftops in product(("disabled", "enabled"), (False, True), (False, True))
        ]
        catalogue = dict(RVGLWorld.location_name_to_id)
        data_package = RVGLWorld.get_data_package_data()
        for player_options in (options, list(reversed(options))):
            multiworld = setup_multiworld([RVGLWorld] * len(player_options), seed=0, options=player_options)
            filler_counts = {}
            for player, world in multiworld.worlds.items():
                with self.subTest(player=player, options=player_options[player - 1]):
                    carsanity = player_options[player - 1]["carsanity"] == "enabled"
                    dreamcast = player_options[player - 1]["include_dreamcast_cars"]
                    rooftops = player_options[player - 1]["include_dreamcast_track_rooftops"]
                    cars = (*STOCK_CARS, *DC_CARS) if dreamcast else STOCK_CARS
                    expected_cars = cars if carsanity else ()
                    car_locations = [location for location in world.get_locations()
                                     if location.name.startswith("Win Race with Car:")]
                    self.assertEqual({location.name for location in car_locations},
                                     {get_car_race_win_location_name(car) for car in expected_cars})
                    self.assertEqual({region.name for region in multiworld.get_regions(player)
                                      if region.name.startswith("Car:")},
                                     {get_car_region_name(car) for car in expected_cars})
                    location_count = (14 if rooftops else 13) * 4 + 4 + 20 + len(expected_cars)
                    self.assertEqual(len(multiworld.get_unfilled_locations(player)), location_count)
                    pool = [item for item in multiworld.itempool if item.player == player]
                    self.assertEqual(len(pool), location_count)
                    filler_counts[carsanity, dreamcast, rooftops] = sum(item.name == FILLER_ITEM.name for item in pool)
                    self.assertEqual(world.location_name_to_id, catalogue)
            for dreamcast, rooftops in product((False, True), repeat=2):
                self.assertEqual(filler_counts[True, dreamcast, rooftops] - filler_counts[False, dreamcast, rooftops],
                                 42 if dreamcast else 28)
            distribute_items_restrictive(multiworld)
            call_all(multiworld, "post_fill")
            call_all(multiworld, "finalize_multiworld")
            self.assertFalse(multiworld.get_unfilled_locations())
            self.assertTrue(multiworld.can_beat_game())
            self.assertTrue(multiworld.fulfills_accessibility())
            self.assertEqual(RVGLWorld.location_name_to_id, catalogue)
            self.assertEqual(RVGLWorld.get_data_package_data(), data_package)

    def test_car_checks_require_the_matching_car_and_any_raceable_track(self) -> None:
        # No starting inventory; disable track-win checks to test track ownership independently.
        multiworld = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
            "carsanity": "enabled", "include_dreamcast_cars": True,
            "include_dreamcast_track_rooftops": True, "include_single_race_wins": False,
            "include_stunt_arena_stars": True,
        })
        world = multiworld.worlds[1]
        for car in (*STOCK_CARS, *DC_CARS):
            location = world.get_location(get_car_race_win_location_name(car))
            state = CollectionState(multiworld)
            self.assertFalse(location.can_reach(state))
            state.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
            for cup in STOCK_CUPS:
                state.collect(world.create_item(get_cup_item_name(cup)), prevent_sweep=True)
            self.assertTrue(world.get_region("Stunt Arena").can_reach(state))
            self.assertFalse(location.can_reach(state), "Cups and Stunt Arena must not substitute for a track")
            for track in (*STOCK_TRACKS, *DC_TRACKS):
                with self.subTest(car=car.folder, track=track.folder):
                    state = CollectionState(multiworld)
                    state.collect(world.create_item(get_track_item_name(track)), prevent_sweep=True)
                    self.assertFalse(location.can_reach(state))
                    wrong_car = STOCK_CARS[1] if car == STOCK_CARS[0] else STOCK_CARS[0]
                    state.collect(world.create_item(get_car_item_name(wrong_car)), prevent_sweep=True)
                    self.assertFalse(location.can_reach(state))
                    state.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
                    self.assertTrue(location.can_reach(state))

    def test_car_and_track_items_must_belong_to_the_location_owner(self) -> None:
        multiworld = setup_multiworld(
            [RVGLWorld, RVGLWorld], steps=("create_regions", "set_rules"), seed=0,
            options=[{"carsanity": "enabled"}, {"carsanity": "enabled", "include_dreamcast_track_rooftops": True}],
        )
        for car_owner, track_owner in product((1, 2), repeat=2):
            state = CollectionState(multiworld)
            state.collect(multiworld.worlds[car_owner].create_item("Car: RC Bandit"), prevent_sweep=True)
            state.collect(multiworld.worlds[track_owner].create_item("Track: Toys in the Hood 1"), prevent_sweep=True)
            for player, world in multiworld.worlds.items():
                with self.subTest(car_owner=car_owner, track_owner=track_owner, player=player):
                    location = world.get_location("Win Race with Car: RC Bandit")
                    self.assertEqual(location.can_reach(state), player == car_owner == track_owner)
        for player, world in multiworld.worlds.items():
            state = CollectionState(multiworld)
            state.collect(world.create_item("Car: RC Bandit"), prevent_sweep=True)
            state.collect(world.create_item("Track: Rooftops"), prevent_sweep=True)
            self.assertEqual(world.get_location("Win Race with Car: RC Bandit").can_reach(state), player == 2)

    def test_zero_starting_tracks_blocks_starting_car_checks_until_a_track_is_received(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, seed=0, options={
            "carsanity": "enabled", "starting_tracks": 0, "include_single_race_wins": False,
        })
        world = multiworld.worlds[1]
        starting_names = {item.name for item in multiworld.precollected_items[1]}
        self.assertFalse(any(name.startswith("Track:") for name in starting_names))
        state = multiworld.state.copy()
        state.collect(world.create_item("Track: Ghost Town 2"), prevent_sweep=True)
        for car in STOCK_CARS:
            location = world.get_location(get_car_race_win_location_name(car))
            self.assertFalse(location.can_reach(multiworld.state))
            self.assertEqual(location.can_reach(state), get_car_item_name(car) in starting_names)

    def test_carsanity_only_pool_reports_shortfall_and_supports_exact_capacity(self) -> None:
        options = {"carsanity": "enabled", "include_single_race_wins": False, "include_practice_stars": False,
                   "include_normal_time_trials": False, "include_reverse_time_trials": False,
                   "include_mirror_time_trials": False}
        with self.assertRaisesRegex(OptionError, "40 unlock items.*only 32 enabled locations.*8 more locations needed"):
            setup_multiworld(RVGLWorld, seed=0, options=options)
        multiworld = setup_multiworld(RVGLWorld, seed=0, options={**options, "starting_cars": 8, "starting_tracks": 4})
        self.assertEqual(len(multiworld.itempool), 32)
        self.assertTrue(all(item.name != FILLER_ITEM.name for item in multiworld.itempool))
        distribute_items_restrictive(multiworld)
        self.assertFalse(multiworld.get_unfilled_locations())
        self.assertTrue(multiworld.can_beat_game())
        self.assertTrue(multiworld.fulfills_accessibility())

    def test_carsanity_checks_do_not_change_default_platinum_goal(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0,
                                     options={"carsanity": "enabled"})
        world = multiworld.worlds[1]
        state = CollectionState(multiworld)
        for car in STOCK_CARS:
            state.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
        state.collect(world.create_item("Track: Toys in the Hood 1"), prevent_sweep=True)
        state.sweep_for_advancements()
        self.assertTrue(all(world.get_location(get_car_race_win_location_name(car)).can_reach(state) for car in STOCK_CARS))
        self.assertFalse(multiworld.completion_condition[1](state))

        state = CollectionState(multiworld)
        state.collect(world.create_item("Car: RC Bandit"))
        state.collect(world.create_item("Platinum Cup"))
        state.sweep_for_advancements()
        self.assertTrue(multiworld.completion_condition[1](state))
        self.assertFalse(any(world.get_location(get_car_race_win_location_name(car)).can_reach(state) for car in STOCK_CARS))
