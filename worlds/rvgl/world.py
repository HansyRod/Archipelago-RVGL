from __future__ import annotations

from worlds.AutoWorld import World

from . import items, locations, output, regions, rules, web_world
from .cars import STOCK_CARS
from .cups import STOCK_CUPS
from .options import RVGLOptions
from .tracks import DC_TRACKS, STOCK_TRACKS

_ITEM_DATA_BY_NAME = {
    item.name: item
    for item in items.ITEM_DATA
}


class RVGLWorld(World):
    """
    Archipelago world for RVGL, a community-made OpenGL port of the RC car racing game Re-Volt.
    Control and race toy RC cars in everyday scenarios like a neighbourhood, supermarkets and gardens!
    """
    game = "RVGL"

    web = web_world.RVGLWebWorld()

    options_dataclass = RVGLOptions
    options: RVGLOptions

    item_name_to_id = items.ITEM_NAME_TO_ID
    location_name_to_id = locations.LOCATION_NAME_TO_ID

    goal_cup = next(cup for cup in STOCK_CUPS if cup.folder == "platinum")

    def generate_early(self) -> None:
        """Grant the initial cars, tracks, and cup using this world's seeded random generator."""
        rookie_cars = tuple(car for car in STOCK_CARS if car.rating == 0)
        easy_tracks = tuple(track for track in (*STOCK_TRACKS, *DC_TRACKS) if track.difficulty == 1)
        bronze_cup = next(cup for cup in STOCK_CUPS if cup.folder == "bronze")

        starting_item_names = [
            *(items.get_car_item_name(car)
              for car in self.random.sample(rookie_cars, self.options.starting_cars.value)),
            *(items.get_track_item_name(track)
              for track in self.random.sample(easy_tracks, self.options.starting_tracks.value)),
            items.get_cup_item_name(bronze_cup),
        ]

        for item_name in starting_item_names:
            self.push_precollected(self.create_item(item_name))

    def create_regions(self) -> None:
        regions.create_regions(self)

    def set_rules(self) -> None:
        rules.set_rules(self)

    def create_items(self) -> None:
        """Create each remaining unlock once and fill the unused reward slots with filler."""
        starting_item_names = {item.name for item in self.multiworld.precollected_items[self.player]}
        itempool = [
            self.create_item(item.name)
            for item in items.ITEM_DATA
            if item.name != items.FILLER_ITEM.name and item.name not in starting_item_names
        ]

        location_count = len(self.multiworld.get_unfilled_locations(self.player))
        if len(itempool) > location_count:
            raise ValueError(
                f"RVGL player {self.player} has {len(itempool)} unlock items "
                f"but only {location_count} reward locations."
            )

        itempool.extend(self.create_filler() for _ in range(location_count - len(itempool)))
        self.multiworld.itempool.extend(itempool)

    def create_item(self, name: str) -> items.RVGLItem:
        try:
            item_data = _ITEM_DATA_BY_NAME[name]
        except KeyError:
            raise ValueError(f"Unknown RVGL item: {name!r}.") from None

        return items.RVGLItem(item_data.name, item_data.classification, item_data.id, self.player)

    def get_filler_item_name(self) -> str:
        return items.FILLER_ITEM.name

    def generate_output(self, output_directory: str) -> None:
        output.generate_output(self, output_directory)

    def fill_slot_data(self) -> dict[str, str]:
        return {"goalEventKey": locations.get_championship_event_key(self.goal_cup)}
