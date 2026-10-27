import unittest
from collections import Counter
from itertools import product

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


class TestStartingCars(unittest.TestCase):
    def test_starting_car_counts_and_item_pool(self) -> None:
        rookie_names = {f"Car: {car.display_name}" for car in STOCK_CARS if car.rating == 0}
        for count in range(9):
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
            self.assertTrue(multiworld.get_region("Menu", player).can_reach(empty_state))
            for region_name, _ in requirements:
                with self.subTest(player=player, region=region_name, inventory="empty"):
                    self.assertFalse(multiworld.get_region(region_name, player).can_reach(empty_state))

        for recipient in multiworld.player_ids:
            for unlocked_region, item_name in requirements:
                state = CollectionState(multiworld)
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
        for dreamcast, starting_cars in product((False, True), (0, 3, 8)):
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

    def test_platinum_cup_remains_the_only_goal(self) -> None:
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
        state.collect(world.create_item("Platinum Cup"))
        state.sweep_for_advancements()
        self.assertTrue(multiworld.completion_condition[1](state))
        self.assertFalse(any(world.get_location(get_car_race_win_location_name(car)).can_reach(state) for car in STOCK_CARS))
