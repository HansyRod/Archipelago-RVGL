from __future__ import annotations

from BaseClasses import CollectionState, Item, ItemClassification, Location, MultiWorld
from Options import OptionError
from worlds.AutoWorld import World

from . import car_chains, items, locations, output, regions, rules, web_world
from .cars import DC_CARS, STOCK_CARS, CarData
from .cups import STOCK_CUPS
from .options import CarDistribution, Goal, LogicDifficulty, RVGLOptions
from .tracks import DC_TRACKS, STOCK_TRACKS, TrackData

_ITEM_DATA_BY_NAME = {
    item.name: item
    for item in items.ITEM_DATA
}

_LOCATION_DATA_BY_EVENT_KEY = {
    location.event_key: location
    for location in locations.LOCATION_DATA
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
    car_chains: tuple[tuple[items.RVGLItem, ...], ...] = ()

    def generate_early(self) -> None:
        """Grant the initial cars, tracks, and cup using this world's seeded random generator."""
        # Archipelago applies start_inventory after generate_early(), so count
        # its configured cars here rather than relying on precollected items yet.
        starting_car_count = self.options.starting_cars.value + sum(
            self.options.start_inventory.value.get(items.get_car_item_name(car), 0)
            for car in self.get_enabled_cars()
        )
        if starting_car_count == 0 and self.options.logic_difficulty != LogicDifficulty.option_casual:
            raise OptionError(
                f"RVGL player {self.player} ({self.player_name}) must have at least one starting car. "
                "Increase starting_cars or add an enabled car to start_inventory."
            )
        starting_track_count = self.options.starting_tracks.value + sum(
            self.options.start_inventory.value.get(items.get_track_item_name(track), 0)
            for track in self.get_enabled_tracks()
        )
        if starting_track_count == 0:
            raise OptionError(
                f"RVGL player {self.player} ({self.player_name}) must have at least one starting track. "
                "Increase starting_tracks or add an enabled track to start_inventory."
            )
        rookie_cars = tuple(car for car in self.get_enabled_cars() if car.rating == 0)
        starting_cars = []
        if self.options.logic_difficulty == LogicDifficulty.option_casual:
            casual_cars = tuple(car for car in rookie_cars if car.folder in ("rc", "moss", "beatall", "tc6", "bigvolt"))
            has_other_starting_car = any(
                self.options.start_inventory.value.get(items.get_car_item_name(car), 0) > 0
                for car in casual_cars
            )
            if not has_other_starting_car:
                # Choose a qualifying car first when start_inventory does not provide one.
                starting_cars.append(self.random.choice(casual_cars))
        rookie_cars = tuple(car for car in rookie_cars if car not in starting_cars)
        starting_cars.extend(self.random.sample(
            rookie_cars, max(0, self.options.starting_cars.value - len(starting_cars)),
        ))
        easy_tracks = tuple(track for track in self.get_enabled_tracks() if track.difficulty == 1)
        bronze_cup = next(cup for cup in STOCK_CUPS if cup.folder == "bronze")

        starting_item_names = [
            *(items.get_car_item_name(car) for car in starting_cars),
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
            for item in self.get_enabled_item_data()
            if item.classification != ItemClassification.filler and item.name not in starting_item_names
        ]

        location_count = len(self.multiworld.get_unfilled_locations(self.player))
        if len(itempool) > location_count:
            raise OptionError(
                f"RVGL player {self.player} ({self.player_name}) has {len(itempool)} unlock items "
                f"but only {location_count} enabled locations "
                f"({len(itempool) - location_count} more locations needed). "
                "Enable more Location Pool Options to increase the number of locations, "
                "or increase the starting inventory to decrease the number of required items."
            )

        itempool.extend(self.create_filler() for _ in range(location_count - len(itempool)))
        self.multiworld.itempool.extend(itempool)

    def fill_hook(
        self,
        progitempool: list[Item],
        usefulitempool: list[Item],
        filleritempool: list[Item],
        fill_locations: list[Location],
    ) -> None:
        if self.options.car_distribution == CarDistribution.option_progressive:
            car_chains.prepare_car_chains(self, progitempool)

    def collect_item(self, state: CollectionState, item: Item, remove: bool = False) -> str | None:
        if isinstance(item, car_chains.CarChainItem):
            if remove:
                # Remove the last stage this simulated inventory owns.
                for car in reversed(item.cars):
                    if state.has(car.name, self.player):
                        return car.name
            else:
                # Grant the first stage this simulated inventory does not own yet.
                for car in item.cars:
                    if not state.has(car.name, self.player):
                        return car.name
            return None
        return super().collect_item(state, item, remove)

    @classmethod
    def stage_finalize_multiworld(cls, multiworld: MultiWorld) -> None:
        if any(world.options.car_distribution == CarDistribution.option_progressive
               for world in multiworld.get_game_worlds(cls.game)):
            car_chains.resolve_car_chains(multiworld)

    def get_enabled_item_data(self) -> tuple[items.ItemData, ...]:
        """Return the item definitions enabled by this player's item-pool options."""
        enabled_cars = self.get_enabled_cars()
        enabled_tracks = self.get_enabled_tracks()
        return tuple(
            item for item in items.ITEM_DATA
            if (item.source in enabled_cars
                or item.source in enabled_tracks
                or item.source in STOCK_CUPS
                or item.classification == ItemClassification.filler)
        )

    def get_enabled_cars(self) -> tuple[CarData, ...]:
        """Return the cars enabled by this player's item-pool options."""
        return (*STOCK_CARS, *DC_CARS) if self.options.include_dreamcast_cars else STOCK_CARS

    def get_enabled_tracks(self) -> tuple[TrackData, ...]:
        """Return the tracks enabled by this player's item-pool options."""
        return (*STOCK_TRACKS, *DC_TRACKS) if self.options.include_dreamcast_track_rooftops else STOCK_TRACKS

    def is_carsanity_enabled(self) -> bool:
        """Include car-win checks when requested by the location option or the goal."""
        return bool(self.options.carsanity) or self.options.goal == Goal.option_carsanity

    def is_single_race_wins_enabled(self) -> bool:
        """Include track-win checks when requested by the location option or the goal."""
        return bool(self.options.include_single_race_wins) or self.options.goal in (
            Goal.option_tracksanity, Goal.option_tracksanity_plus,
        )

    def is_practice_stars_enabled(self) -> bool:
        """Include Practice star checks when requested by the location option or the goal."""
        return bool(self.options.include_practice_stars) or self.options.goal == Goal.option_tracksanity_plus

    def is_normal_time_trials_enabled(self) -> bool:
        """Include Normal Time Trial checks when requested by the location option or the goal."""
        return bool(self.options.include_normal_time_trials) or self.options.goal == Goal.option_tracksanity_plus

    def get_goal_event_keys(self) -> tuple[str, ...]:
        """Return every required win key in catalogue order; all keys must be completed."""
        if self.options.goal == Goal.option_platinum_cup:
            return (locations.get_championship_event_key(self.goal_cup),)
        if self.options.goal == Goal.option_carsanity:
            return tuple(locations.get_car_race_win_event_key(car) for car in self.get_enabled_cars())
        if self.options.goal == Goal.option_tracksanity:
            return tuple(locations.get_single_race_event_key(track) for track in self.get_enabled_tracks())
        if self.options.goal == Goal.option_tracksanity_plus:
            return tuple(
                event_key
                for track in self.get_enabled_tracks()
                for event_key in (
                    locations.get_single_race_event_key(track),
                    locations.get_practice_star_event_key(track),
                    locations.get_time_trial_event_key(track),
                )
            )
        raise ValueError(f"Unsupported RVGL goal: {self.options.goal.value}.")

    def get_goal_location_data(self) -> tuple[locations.LocationData, ...]:
        """Return the registered location definitions for all required goal checks."""
        return tuple(_LOCATION_DATA_BY_EVENT_KEY[event_key] for event_key in self.get_goal_event_keys())

    def create_item(self, name: str) -> items.RVGLItem:
        try:
            item_data = _ITEM_DATA_BY_NAME[name]
        except KeyError:
            raise ValueError(f"Unknown RVGL item: {name!r}.") from None

        return items.RVGLItem(item_data.name, item_data.classification, item_data.id, self.player)

    def get_filler_item_name(self) -> str:
        return self.random.choice(items.FILLER_ITEMS).name

    def generate_output(self, output_directory: str) -> None:
        output.generate_output(self, output_directory)
