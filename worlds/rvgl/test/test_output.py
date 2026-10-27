import json
import tempfile
import unittest
from itertools import product
from pathlib import Path

from test.general import setup_multiworld

from .. import RVGLWorld
from ..cars import DC_CARS, STOCK_CARS
from ..cups import STOCK_CUPS
from ..items import FILLER_ITEM, STUNT_ARENA_ID_OFFSET, get_car_item_name, get_cup_item_name, get_track_item_name
from ..locations import LOCATION_DATA, STUNT_ARENA_LOCATIONS
from ..output import build_randomizer_config
from ..stunt_arena import STOCK_STUNT_ARENA_STAR_COUNT
from ..tracks import DC_TRACKS, STOCK_TRACKS


class TestOutput(unittest.TestCase):
    def test_config_preserves_content_and_starting_unlocks(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, seed=0)
        config = build_randomizer_config(multiworld.worlds[1])
        self.assertEqual(set(config), {
            "metadata", "global_options", "stockCars", "dcCars", "extraCars", "tracks", "cups", "archipelago",
        })
        self.assertEqual(config["metadata"]["seed"], multiworld.seed_name)
        self.assertEqual(config["metadata"]["version"], "0.2.0")
        self.assertRegex(config["metadata"]["profileName"], r"^ap_[0-9a-f]{12}$")
        self.assertTrue(config["global_options"]["is_stock_cars"])
        self.assertTrue(config["global_options"]["is_stock_tracks"])
        self.assertFalse(any(
            value for key, value in config["global_options"].items()
            if key not in {"is_stock_cars", "is_stock_tracks"}
        ))
        self.assertEqual(config["extraCars"], [])
        self.assertEqual([car["folder"] for car in config["stockCars"]], [car.folder for car in STOCK_CARS])
        self.assertEqual([car["folder"] for car in config["dcCars"]], [car.folder for car in DC_CARS])
        # The runtime assigns track configs by slot, rather than looking them up by folder.
        self.assertEqual([track["folder"] for track in config["tracks"]], [
            "nhood1", "market2", "muse2", "garden1", "toylite", "wild_west1",
            "toy2", "nhood2", "ship1", "muse1", "market1", "wild_west2", "ship2",
        ])

        entries = []
        for car, data in zip(config["stockCars"] + config["dcCars"], (*STOCK_CARS, *DC_CARS)):
            self.assertEqual(car["rating"], data.rating)
            self.assertTrue(car["selectable_player"] and car["selectable_cpu"])
            entries.append((car, "obtain", get_car_item_name(data), f"car:{data.folder}"))
        tracks_by_folder = {track.folder: track for track in (*STOCK_TRACKS, *DC_TRACKS)}
        for track in config["tracks"]:
            data = tracks_by_folder[track["folder"]]
            self.assertEqual(track["difficulty"], data.difficulty)
            entries.append((track, "obtain", get_track_item_name(data), f"track:{data.folder}"))
        for cup, data in zip(config["cups"], STOCK_CUPS):
            self.assertEqual((cup["name"], cup["difficulty"]), (data.display_name, data.difficulty))
            entries.append((cup, "obtainCondition", get_cup_item_name(data), f"cup:{data.difficulty}"))

        self.assertEqual(len(entries), len(STOCK_CARS) + len(DC_CARS) + len(STOCK_TRACKS) + len(STOCK_CUPS))
        for entry, obtain_key, item_name, required_item in entries:
            with self.subTest(item=item_name):
                self.assertEqual(entry[obtain_key], 13)
                self.assertEqual(entry["customUnlock"], {
                    "trackFolder": [], "requiredCount": 0, "archipelagoItem": required_item,
                })

    def test_cups_have_valid_defaults_and_stage_variants(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, seed=0)
        config = build_randomizer_config(multiworld.worlds[1])
        track_folders = {track["folder"] for track in config["tracks"]}
        for cup in config["cups"]:
            with self.subTest(cup=cup["name"]):
                self.assertEqual(cup["numCars"], 8)
                self.assertEqual(cup["numTries"], 3)
                self.assertEqual(cup["perRaceRequiredPlace"], 3)
                self.assertEqual(cup["overallRequiredPlace"], 1)
                self.assertEqual(len(cup["carsPerClass"]), 6)
                self.assertEqual(sum(cup["carsPerClass"]), cup["numCars"] - 1)
                self.assertEqual(cup["pointsTable"], [10, 6, 4, 3, 2, 1] + [0] * 24)
                self.assertGreater(len(cup["stages"]), 0)
                self.assertLessEqual(len(cup["stages"]), 16)
                for stage in cup["stages"]:
                    self.assertIn(stage["trackFolder"], track_folders)
                    self.assertGreaterEqual(stage["numLaps"], 1)
                    self.assertIsInstance(stage["isReverse"], bool)
                    self.assertIsInstance(stage["isMirror"], bool)
        self.assertEqual([len(cup["stages"]) for cup in config["cups"]], [4, 4, 4, 5])
        self.assertEqual(config["cups"][2]["stages"][1], {
            "trackFolder": "toylite", "numLaps": 8, "isReverse": False, "isMirror": True,
        })
        self.assertEqual(config["cups"][3]["stages"][2], {
            "trackFolder": "toylite", "numLaps": 10, "isReverse": True, "isMirror": True,
        })

    def test_archipelago_metadata_matches_registered_ids_and_unlock_conditions(self) -> None:
        multiworld = setup_multiworld(
            [RVGLWorld, RVGLWorld], seed=0,
            options=[{"include_stunt_arena_stars": True}, {"include_stunt_arena_stars": False}],
        )
        multiworld.player_name[2] = "Player Two \u00c9"
        for player, world in multiworld.worlds.items():
            with self.subTest(player=player):
                config = build_randomizer_config(world)
                archipelago = config["archipelago"]
                self.assertEqual(set(archipelago), {
                    "schemaVersion", "slotNumber", "slotName", "locations", "items", "goalEventKey",
                })
                self.assertEqual(archipelago["schemaVersion"], 1)
                self.assertEqual(archipelago["slotNumber"], player)
                self.assertEqual(archipelago["slotName"], world.player_name)
                self.assertEqual(archipelago["goalEventKey"], "championship_win:4")
                self.assertIn(archipelago["goalEventKey"], archipelago["locations"])
                self.assertEqual(archipelago["items"][""], FILLER_ITEM.id)

                stunt_locations = {
                    event_key: location_id
                    for event_key, location_id in archipelago["locations"].items()
                    if event_key.startswith("stunt_star:")
                }
                if world.options.include_stunt_arena_stars:
                    self.assertEqual(stunt_locations, {
                        f"stunt_star:{number}": STUNT_ARENA_ID_OFFSET + number
                        for number in range(1, STOCK_STUNT_ARENA_STAR_COUNT + 1)
                    })
                else:
                    self.assertEqual(stunt_locations, {})

                active_locations = {
                    location.name: location.id
                    for location in LOCATION_DATA
                    if location.source not in DC_TRACKS
                    and (location not in STUNT_ARENA_LOCATIONS or world.options.include_stunt_arena_stars)
                }
                for mapping, registered_ids in (
                    (archipelago["items"], world.item_name_to_id),
                    (archipelago["locations"], active_locations),
                ):
                    self.assertEqual(len(mapping), len(registered_ids))
                    self.assertEqual(set(mapping.values()), set(registered_ids.values()))
                    self.assertTrue(all(isinstance(key, str) for key in mapping))
                    self.assertTrue(all(type(value) is int for value in mapping.values()))
                for location in LOCATION_DATA:
                    if location.name in active_locations:
                        self.assertEqual(archipelago["locations"][location.event_key], location.id)
                    else:
                        self.assertNotIn(location.event_key, archipelago["locations"])

                for entry in config["stockCars"] + config["dcCars"] + config["tracks"] + config["cups"]:
                    if "customUnlock" in entry:
                        self.assertIn(entry["customUnlock"]["archipelagoItem"], archipelago["items"])

                # Precollected unlocks must remain in the ID map for initial server delivery.
                starting_ids = {item.code for item in multiworld.precollected_items[player]}
                self.assertTrue(starting_ids.issubset(archipelago["items"].values()))
                self.assertNotIn("Victory", archipelago["items"])
                self.assertNotIn("Victory", archipelago["locations"])
                self.assertEqual(json.loads(json.dumps(archipelago)), archipelago)

    def test_track_check_options_filter_each_players_output(self) -> None:
        location_options = {
            "include_single_race_wins": "single_race_win:",
            "include_practice_stars": "practice_star:",
            "include_normal_time_trials": "time_trial_normal:",
            "include_reverse_time_trials": "time_trial_reverse:",
            "include_mirror_time_trials": "time_trial_mirror:",
        }
        for option, prefix in location_options.items():
            with self.subTest(option=option):
                multiworld = setup_multiworld(
                    [RVGLWorld, RVGLWorld], seed=0, options=[{option: False}, {option: True}],
                )
                for player, world in multiworld.worlds.items():
                    with self.subTest(player=player):
                        mappings = build_randomizer_config(world)["archipelago"]["locations"]
                        expected_mappings = {
                            location.event_key: location.id for location in LOCATION_DATA
                            if location not in STUNT_ARENA_LOCATIONS
                            and location.source not in DC_TRACKS
                            and (getattr(world.options, option) or not location.event_key.startswith(prefix))
                        }
                        self.assertEqual(mappings, expected_mappings)

    def test_dreamcast_options_update_track_slots_and_silver_cup(self) -> None:
        # Keep expected layouts independent of CUP_STAGES to catch incorrect definitions.
        expected_stages = {
            False: [
                ("toylite", 6, False, False),
                ("nhood1", 4, False, True),
                ("wild_west1", 4, False, False),
                ("toy2", 4, False, False),
            ],
            True: [
                ("roof", 4, False, False),
                ("toylite", 6, False, False),
                ("wild_west1", 4, False, False),
                ("toy2", 4, False, False),
            ],
        }
        options = [
            {"include_dreamcast_cars": cars, "include_dreamcast_track_rooftops": rooftops}
            for cars, rooftops in product((False, True), repeat=2)
        ]
        multiworld = setup_multiworld([RVGLWorld] * len(options), seed=0, options=options)
        for player, world in multiworld.worlds.items():
            with self.subTest(player=player, options=options[player - 1]):
                config = build_randomizer_config(world)
                self.assertEqual(config["global_options"]["is_stock_cars"], not world.options.include_dreamcast_cars)
                self.assertEqual(config["global_options"]["is_stock_tracks"], not world.options.include_dreamcast_track_rooftops)
                expected_tracks = [track.folder for track in STOCK_TRACKS]
                if world.options.include_dreamcast_track_rooftops:
                    expected_tracks.insert(4, "roof")
                self.assertEqual([track["folder"] for track in config["tracks"]], expected_tracks)
                self.assertEqual([
                    (stage["trackFolder"], stage["numLaps"], stage["isReverse"], stage["isMirror"])
                    for stage in config["cups"][1]["stages"]
                ], expected_stages[bool(world.options.include_dreamcast_track_rooftops)])
                self.assertEqual(
                    {key: value for key, value in config["archipelago"]["locations"].items() if key.endswith(":roof")},
                    {location.event_key: location.id for location in LOCATION_DATA if location.source in DC_TRACKS}
                    if world.options.include_dreamcast_track_rooftops else {},
                )
                self.assertEqual([car["folder"] for car in config["dcCars"]], [car.folder for car in DC_CARS])
                for car, data in zip(config["dcCars"], DC_CARS):
                    self.assertEqual(car["obtain"], 13)
                    self.assertEqual(car["customUnlock"]["archipelagoItem"], f"car:{data.folder}")

    def test_output_is_reproducible_and_scoped_to_each_player(self) -> None:
        multiworld = setup_multiworld([RVGLWorld, RVGLWorld], seed=0)
        multiworld.worlds[1].push_precollected(multiworld.worlds[1].create_item("Silver Cup"))
        profiles = set()
        with tempfile.TemporaryDirectory() as directory:
            for player, world in multiworld.worlds.items():
                random_state = world.random.getstate()
                world.generate_output(directory)
                path = Path(directory) / (multiworld.get_out_file_name_base(player) + ".rvgl.json")
                contents = path.read_bytes()
                config = json.loads(contents)
                self.assertEqual(config, build_randomizer_config(world))
                self.assertEqual(config["cups"][1]["obtainCondition"], 13)
                profiles.add(config["metadata"]["profileName"])
                world.generate_output(directory)
                self.assertEqual(path.read_bytes(), contents)
                self.assertEqual(world.random.getstate(), random_state)
            self.assertEqual(len(list(Path(directory).glob("*.rvgl.json"))), 2)
        self.assertEqual(len(profiles), 2)
