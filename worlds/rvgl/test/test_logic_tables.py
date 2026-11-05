import unittest
from itertools import product

from BaseClasses import CollectionState
from test.general import setup_multiworld

from .. import RVGLWorld
from ..cars import DC_CARS, STOCK_CARS
from ..cups import STOCK_CUPS
from ..items import get_car_item_name, get_cup_item_name, get_track_item_name
from ..locations import (
    get_championship_location_name,
    get_mirror_time_trial_location_name,
    get_reverse_time_trial_location_name,
    get_single_race_location_name,
    get_time_trial_location_name,
)
from ..logic import (
    CHAMPIONSHIP_CAR_DATA,
    CHAMPIONSHIP_MIN_DIFFICULTY,
    TIME_TRIAL_CAR_DATA,
    TIME_TRIAL_MIN_DIFFICULTY,
)
from ..options import LogicDifficulty
from ..output import TRACK_SLOTS
from ..tracks import STOCK_TRACKS


class TestLogicTables(unittest.TestCase):
    def test_championship_and_time_trial_catalogue_coverage_and_order(self) -> None:
        car_folders = {car.folder for car in (*STOCK_CARS, *DC_CARS)}
        for columns, rows, lookup in (
            (tuple(cup.folder for cup in STOCK_CUPS), CHAMPIONSHIP_CAR_DATA, CHAMPIONSHIP_MIN_DIFFICULTY),
            (tuple(track.folder for track in TRACK_SLOTS), TIME_TRIAL_CAR_DATA, TIME_TRIAL_MIN_DIFFICULTY),
        ):
            self.assertEqual(set(rows), car_folders)
            self.assertEqual(tuple(lookup), columns)
            self.assertEqual(len(columns), len(set(columns)))
            for requirements in lookup.values():
                self.assertEqual(set(requirements), car_folders)

    def test_car_rows_have_valid_difficulties_and_matching_indexed_values(self) -> None:
        valid_difficulties = {None, *LogicDifficulty.options.values()}
        for columns, rows, lookup in (
            (tuple(cup.folder for cup in STOCK_CUPS), CHAMPIONSHIP_CAR_DATA, CHAMPIONSHIP_MIN_DIFFICULTY),
            (tuple(track.folder for track in TRACK_SLOTS), TIME_TRIAL_CAR_DATA, TIME_TRIAL_MIN_DIFFICULTY),
        ):
            for car, difficulties in rows.items():
                with self.subTest(car=car, columns=columns):
                    self.assertEqual(len(difficulties), len(columns))
                    self.assertTrue(all(difficulty in valid_difficulties for difficulty in difficulties))
                    for column, check in enumerate(columns):
                        self.assertEqual(lookup[check][car], difficulties[column])

    def test_every_check_has_a_qualifying_enabled_car_at_every_difficulty(self) -> None:
        for difficulty, dreamcast in product(LogicDifficulty.options.values(), (False, True)):
            world = setup_multiworld(RVGLWorld, steps=(), seed=0, options={
                "logic_difficulty": difficulty, "include_dreamcast_cars": dreamcast,
            }).worlds[1]
            for lookup in (CHAMPIONSHIP_MIN_DIFFICULTY, TIME_TRIAL_MIN_DIFFICULTY):
                for check, requirements in lookup.items():
                    with self.subTest(check=check, difficulty=difficulty, dreamcast=dreamcast):
                        self.assertTrue(any(
                            requirements[car.folder] is not None and requirements[car.folder] <= difficulty
                            for car in world.get_enabled_cars()
                        ))


class TestCarLogicRules(unittest.TestCase):
    def test_every_car_matches_championship_and_trial_data_at_every_tier(self) -> None:
        for difficulty, dreamcast, rooftops in product(range(3), (False, True), (False, True)):
            world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
                "logic_difficulty": difficulty, "include_dreamcast_cars": dreamcast,
                "include_dreamcast_track_rooftops": rooftops,
            }).worlds[1]
            unlocked = CollectionState(world.multiworld)
            cases = []
            for column, cup in enumerate(STOCK_CUPS):
                unlocked.collect(world.create_item(get_cup_item_name(cup)), prevent_sweep=True)
                cases.append((world.get_location(get_championship_location_name(cup)), CHAMPIONSHIP_CAR_DATA, column))
            for track in world.get_enabled_tracks():
                unlocked.collect(world.create_item(get_track_item_name(track)), prevent_sweep=True)
                column = TRACK_SLOTS.index(track)
                names = [get_time_trial_location_name(track), get_mirror_time_trial_location_name(track)]
                if track.has_reverse:
                    names.append(get_reverse_time_trial_location_name(track))
                for name in names:
                    cases.append((world.get_location(name), TIME_TRIAL_CAR_DATA, column))
            for location, _, _ in cases:
                self.assertFalse(location.can_reach(unlocked), location.name)
            for track in world.get_enabled_tracks():
                self.assertTrue(world.get_location(get_single_race_location_name(track)).can_reach(unlocked))

            for car in (*STOCK_CARS, *DC_CARS):
                state = unlocked.copy()
                state.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
                car_only = CollectionState(world.multiworld)
                car_only.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
                for location, rows, column in cases:
                    minimum = rows[car.folder][column]
                    expected = (car in world.get_enabled_cars() and minimum is not None and minimum <= difficulty)
                    with self.subTest(check=location.name, car=car.folder, tier=difficulty,
                                      dreamcast=dreamcast, rooftops=rooftops):
                        self.assertEqual(location.can_reach(state), expected)
                        self.assertFalse(location.can_reach(car_only), "A car does not replace the cup or track item")

    def test_time_trial_variants_respect_location_options_and_goal_forced_checks(self) -> None:
        for normal, reverse, mirror, goal in product((False, True), (False, True), (False, True),
                                                    ("platinum_cup", "tracksanity_plus")):
            world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
                "include_normal_time_trials": normal, "include_reverse_time_trials": reverse,
                "include_mirror_time_trials": mirror, "include_practice_stars": False,
                "include_dreamcast_track_rooftops": True, "goal": goal,
            }).worlds[1]
            names = {location.name for location in world.get_locations()}
            state = CollectionState(world.multiworld)
            for car in world.get_enabled_cars():
                state.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
            for track in world.get_enabled_tracks():
                state.collect(world.create_item(get_track_item_name(track)), prevent_sweep=True)
                for enabled, name in (
                    (normal or goal == "tracksanity_plus", get_time_trial_location_name(track)),
                    (reverse and track.has_reverse, get_reverse_time_trial_location_name(track)),
                    (mirror, get_mirror_time_trial_location_name(track)),
                ):
                    with self.subTest(check=name, normal=normal, reverse=reverse, mirror=mirror, goal=goal):
                        self.assertEqual(name in names, enabled)
                        if enabled:
                            self.assertTrue(world.get_location(name).can_reach(state))

    def test_car_and_content_ownership_and_difficulty_are_player_specific(self) -> None:
        multiworld = setup_multiworld([RVGLWorld, RVGLWorld], steps=("create_regions", "set_rules"), seed=0,
                                     options=[{"logic_difficulty": "casual"},
                                              {"logic_difficulty": "expert", "include_dreamcast_cars": True}])
        cup = STOCK_CUPS[-1]
        track = STOCK_TRACKS[-1]
        checks = (
            (get_cup_item_name(cup), (get_championship_location_name(cup),), CHAMPIONSHIP_MIN_DIFFICULTY[cup.folder]),
            (get_track_item_name(track),
             (get_time_trial_location_name(track), get_reverse_time_trial_location_name(track),
              get_mirror_time_trial_location_name(track)), TIME_TRIAL_MIN_DIFFICULTY[track.folder]),
        )
        for car_owner, content_owner, car in product((1, 2), (1, 2), (*STOCK_CARS, *DC_CARS)):
            for item_name, location_names, requirements in checks:
                state = CollectionState(multiworld)
                state.collect(multiworld.worlds[car_owner].create_item(get_car_item_name(car)), prevent_sweep=True)
                state.collect(multiworld.worlds[content_owner].create_item(item_name), prevent_sweep=True)
                for player, world in multiworld.worlds.items():
                    minimum = requirements[car.folder]
                    expected = (player == car_owner == content_owner and car in world.get_enabled_cars()
                                and minimum is not None and minimum <= world.options.logic_difficulty.value)
                    for name in location_names:
                        with self.subTest(player=player, car_owner=car_owner, content_owner=content_owner,
                                          car=car.folder, check=name):
                            self.assertEqual(world.get_location(name).can_reach(state), expected)

    def test_cup_checks_require_a_suitable_car_but_no_separate_stage_track_items(self) -> None:
        for difficulty in range(3):
            world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0,
                                     options={"logic_difficulty": difficulty}).worlds[1]
            for cup in STOCK_CUPS:
                requirements = CHAMPIONSHIP_MIN_DIFFICULTY[cup.folder]
                car = next(car for car in world.get_enabled_cars()
                           if requirements[car.folder] is not None and requirements[car.folder] <= difficulty)
                state = CollectionState(world.multiworld)
                state.collect(world.create_item(get_cup_item_name(cup)), prevent_sweep=True)
                location = world.get_location(get_championship_location_name(cup))
                self.assertFalse(location.can_reach(state))
                state.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
                self.assertTrue(location.can_reach(state))
                for track in world.get_enabled_tracks():
                    self.assertFalse(world.get_location(get_time_trial_location_name(track)).can_reach(state))
