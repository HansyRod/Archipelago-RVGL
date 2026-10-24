from dataclasses import dataclass

from Options import OptionGroup, PerGameCommonOptions, Range


class StartingCars(Range):
    """Number of Rookie cars randomly granted at the start.

    To have specific starting cars, use the start_inventory option and set this to 0.
    """
    display_name = "Starting Cars"
    range_start = 0
    range_end = 8
    default = 3


@dataclass
class RVGLOptions(PerGameCommonOptions):
    """RVGL-specific options and Archipelago's common settings."""
    starting_cars: StartingCars


option_groups = [
    OptionGroup("Starting Content Options", [StartingCars]),
]
