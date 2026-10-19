import json
import tempfile
import unittest
from pathlib import Path

from test.general import setup_multiworld

from .. import RVGLWorld
from ..cars import DC_CARS, STOCK_CARS
from ..cups import STOCK_CUPS
from ..items import get_car_item_name, get_cup_item_name, get_track_item_name
from ..output import build_randomizer_config
from ..tracks import DC_TRACKS, STOCK_TRACKS


class TestOutput(unittest.TestCase):
    def test_config_preserves_content_and_starting_unlocks(self) -> None:
        multiworld = setup_multiworld(RVGLWorld, seed=0)
        config = build_randomizer_config(multiworld.worlds[1])
        starting_names = {item.name for item in multiworld.precollected_items[1]}
        self.assertEqual(set(config), {
            "metadata", "global_options", "stockCars", "dcCars", "extraCars", "tracks", "cups",
        })
        self.assertEqual(config["metadata"]["seed"], multiworld.seed_name)
        self.assertEqual(config["metadata"]["version"], "0.2.0")
        self.assertRegex(config["metadata"]["profileName"], r"^ap_[0-9a-f]{12}$")
        self.assertFalse(any(config["global_options"].values()))
        self.assertEqual(config["extraCars"], [])
        self.assertEqual([car["folder"] for car in config["stockCars"]], [car.folder for car in STOCK_CARS])
        self.assertEqual([car["folder"] for car in config["dcCars"]], [car.folder for car in DC_CARS])
        # The runtime assigns track configs by slot, rather than looking them up by folder.
        self.assertEqual([track["folder"] for track in config["tracks"]], [
            "nhood1", "market2", "muse2", "garden1", "roof", "toylite", "wild_west1",
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

        self.assertEqual(len(entries), 60)
        for entry, obtain_key, item_name, required_item in entries:
            with self.subTest(item=item_name):
                if item_name in starting_names:
                    self.assertEqual(entry[obtain_key], 0)
                    self.assertNotIn("customUnlock", entry)
                else:
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
        self.assertEqual(config["cups"][1]["stages"][0]["trackFolder"], "roof")
        self.assertEqual(config["cups"][2]["stages"][1], {
            "trackFolder": "toylite", "numLaps": 8, "isReverse": False, "isMirror": True,
        })
        self.assertEqual(config["cups"][3]["stages"][2], {
            "trackFolder": "toylite", "numLaps": 10, "isReverse": True, "isMirror": True,
        })

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
                self.assertEqual(config["cups"][1]["obtainCondition"], 0 if player == 1 else 13)
                profiles.add(config["metadata"]["profileName"])
                world.generate_output(directory)
                self.assertEqual(path.read_bytes(), contents)
                self.assertEqual(world.random.getstate(), random_state)
            self.assertEqual(len(list(Path(directory).glob("*.rvgl.json"))), 2)
        self.assertEqual(len(profiles), 2)
