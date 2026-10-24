import unittest
from collections import Counter

from BaseClasses import CollectionState
from test import bases
from test.general import setup_multiworld

from .. import RVGLWorld
from ..cars import STOCK_CARS, CarData
from ..cups import STOCK_CUPS, CupData
from ..items import FILLER_ITEM, ITEM_DATA, get_cup_item_name, get_track_item_name
from ..regions import get_cup_region_name, get_track_region_name
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
        unlock_names = {item.name for item in ITEM_DATA if item.source is not None}
        pool = [item for item in self.multiworld.itempool if item.player == self.player]
        pool_counts = Counter(item.name for item in pool)

        self.assertEqual(len(pool), len(self.multiworld.get_unfilled_locations(self.player)))
        self.assertFalse(starting_names.intersection(pool_counts))
        self.assertEqual(set(pool_counts) - {FILLER_ITEM.name}, unlock_names - starting_names)
        for item_name in unlock_names - starting_names:
            with self.subTest(item=item_name):
                self.assertEqual(pool_counts[item_name], 1)


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


class TestRegionAccess(unittest.TestCase):
    def test_regions_require_their_own_players_item(self) -> None:
        # Omit starting inventory so every region's requirement can be tested independently.
        multiworld = setup_multiworld(
            [RVGLWorld, RVGLWorld], steps=("create_regions", "set_rules"), seed=0,
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
