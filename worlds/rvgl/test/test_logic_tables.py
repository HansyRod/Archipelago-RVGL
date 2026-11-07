import unittest
from itertools import product

from BaseClasses import CollectionState
from Fill import distribute_items_restrictive
from test.general import setup_multiworld
from worlds.AutoWorld import call_all

from .. import RVGLWorld
from ..cars import DC_CARS, STOCK_CARS
from ..cups import STOCK_CUPS
from ..items import get_car_item_name, get_cup_item_name, get_track_item_name
from ..locations import (
    STUNT_ARENA_LOCATIONS,
    get_championship_location_name,
    get_mirror_time_trial_location_name,
    get_reverse_time_trial_location_name,
    get_single_race_location_name,
    get_time_trial_location_name,
)
from ..logic import (
    CHAMPIONSHIP_CAR_DATA,
    CHAMPIONSHIP_MIN_DIFFICULTY,
    STUNT_ARENA_CAR_DATA,
    STUNT_ARENA_MIN_DIFFICULTY,
    TIME_TRIAL_CAR_DATA,
    TIME_TRIAL_MIN_DIFFICULTY,
)
from ..options import LogicDifficulty
from ..output import TRACK_SLOTS
from ..stunt_arena import STOCK_STUNT_ARENA
from ..tracks import STOCK_TRACKS


class TestLogicTables(unittest.TestCase):
    def test_championship_and_time_trial_catalogue_coverage_and_order(self) -> None:
        car_folders = {car.folder for car in (*STOCK_CARS, *DC_CARS)}
        for columns, rows, lookup in (
            (tuple(cup.folder for cup in STOCK_CUPS), CHAMPIONSHIP_CAR_DATA, CHAMPIONSHIP_MIN_DIFFICULTY),
            (tuple(track.folder for track in TRACK_SLOTS), TIME_TRIAL_CAR_DATA, TIME_TRIAL_MIN_DIFFICULTY),
            (tuple(range(1, STOCK_STUNT_ARENA.star_count + 1)), STUNT_ARENA_CAR_DATA, STUNT_ARENA_MIN_DIFFICULTY),
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
            (tuple(range(1, STOCK_STUNT_ARENA.star_count + 1)), STUNT_ARENA_CAR_DATA, STUNT_ARENA_MIN_DIFFICULTY),
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
            for lookup in (CHAMPIONSHIP_MIN_DIFFICULTY, TIME_TRIAL_MIN_DIFFICULTY, STUNT_ARENA_MIN_DIFFICULTY):
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


    def test_every_car_matches_stunt_arena_data_at_every_tier(self) -> None:
        for difficulty, dreamcast in product(range(3), (False, True)):
            world = setup_multiworld(RVGLWorld, steps=("create_regions", "set_rules"), seed=0, options={
                "logic_difficulty": difficulty, "include_dreamcast_cars": dreamcast,
                "include_stunt_arena_stars": True,
            }).worlds[1]
            content_only = CollectionState(world.multiworld)
            for track in world.get_enabled_tracks():
                content_only.collect(world.create_item(get_track_item_name(track)), prevent_sweep=True)
            for cup in STOCK_CUPS:
                content_only.collect(world.create_item(get_cup_item_name(cup)), prevent_sweep=True)
            for location_data in STUNT_ARENA_LOCATIONS:
                self.assertFalse(world.get_location(location_data.name).can_reach(content_only))

            for car in (*STOCK_CARS, *DC_CARS):
                # Car ownership alone must suffice; Stunt Arena has no track/cup unlock item.
                state = CollectionState(world.multiworld)
                state.collect(world.create_item(get_car_item_name(car)), prevent_sweep=True)
                for column, location_data in enumerate(STUNT_ARENA_LOCATIONS):
                    minimum = STUNT_ARENA_CAR_DATA[car.folder][column]
                    expected = (car in world.get_enabled_cars() and minimum is not None and minimum <= difficulty)
                    with self.subTest(star=column + 1, car=car.folder, tier=difficulty, dreamcast=dreamcast):
                        self.assertEqual(world.get_location(location_data.name).can_reach(state), expected)

            for column, location_data in enumerate(STUNT_ARENA_LOCATIONS):
                eligible = [car for car in world.get_enabled_cars()
                            if STUNT_ARENA_CAR_DATA[car.folder][column] is not None
                            and STUNT_ARENA_CAR_DATA[car.folder][column] <= difficulty]
                ineligible = [car for car in world.get_enabled_cars() if car not in eligible]
                with self.subTest(star=column + 1, tier=difficulty, dreamcast=dreamcast, alternative=True):
                    state = CollectionState(world.multiworld)
                    if ineligible:
                        state.collect(world.create_item(get_car_item_name(ineligible[0])), prevent_sweep=True)
                        self.assertFalse(world.get_location(location_data.name).can_reach(state))
                    state.collect(world.create_item(get_car_item_name(eligible[0])), prevent_sweep=True)
                    self.assertTrue(world.get_location(location_data.name).can_reach(state))

    def test_stunt_arena_car_ownership_and_difficulty_are_player_specific(self) -> None:
        multiworld = setup_multiworld([RVGLWorld, RVGLWorld], steps=("create_regions", "set_rules"), seed=0,
                                     options=[{"logic_difficulty": "casual", "include_stunt_arena_stars": True},
                                              {"logic_difficulty": "expert", "include_dreamcast_cars": True,
                                               "include_stunt_arena_stars": True}])
        for car_owner, car in product((1, 2), (*STOCK_CARS, *DC_CARS)):
            state = CollectionState(multiworld)
            state.collect(multiworld.worlds[car_owner].create_item(get_car_item_name(car)), prevent_sweep=True)
            for player, world in multiworld.worlds.items():
                for column, location_data in enumerate(STUNT_ARENA_LOCATIONS):
                    minimum = STUNT_ARENA_CAR_DATA[car.folder][column]
                    expected = (player == car_owner and car in world.get_enabled_cars()
                                and minimum is not None and minimum <= world.options.logic_difficulty.value)
                    with self.subTest(player=player, car_owner=car_owner, car=car.folder, star=column + 1):
                        self.assertEqual(world.get_location(location_data.name).can_reach(state), expected)

    def test_stunt_arena_options_and_mixed_difficulties_fill(self) -> None:
        options = [
            {"logic_difficulty": difficulty, "include_dreamcast_cars": dreamcast,
             "include_stunt_arena_stars": True, "starting_cars": 1, "starting_tracks": 1}
            for difficulty, dreamcast in product(("casual", "standard", "expert"), (False, True))
        ]
        options.append({"include_stunt_arena_stars": False})
        for player_options in (options, list(reversed(options))):
            multiworld = setup_multiworld([RVGLWorld] * len(player_options), seed=0, options=player_options)
            for player, world in multiworld.worlds.items():
                names = {location.name for location in world.get_locations()}
                for location_data in STUNT_ARENA_LOCATIONS:
                    with self.subTest(player=player, options=player_options[player - 1], star=location_data.name):
                        self.assertEqual(location_data.name in names, bool(world.options.include_stunt_arena_stars))
                        if world.options.include_stunt_arena_stars:
                            self.assertEqual(world.get_location(location_data.name).address, location_data.id)
            distribute_items_restrictive(multiworld)
            call_all(multiworld, "post_fill")
            call_all(multiworld, "finalize_multiworld")
            self.assertFalse(multiworld.get_unfilled_locations())
            self.assertTrue(multiworld.can_beat_game())
            self.assertTrue(multiworld.fulfills_accessibility())
