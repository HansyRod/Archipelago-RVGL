from dataclasses import dataclass

from Options import OptionGroup, PerGameCommonOptions, Range, Toggle


class StartingCars(Range):
    """Number of Rookie cars randomly granted at the start.

    To have specific starting cars, use the start_inventory option and set this to 0.
    """
    display_name = "Starting Cars"
    range_start = 0
    range_end = 8
    default = 3


class StartingTracks(Range):
    """Number of Easy tracks accessible from the start.

    To have specific starting tracks, use the start_inventory option and set this to 0.
    """
    display_name = "Starting Tracks"
    range_start = 0
    range_end = 4
    default = 1


class IncludeStuntArenaStars(Toggle):
    """Include the Stunt Arena's 20 stars as location checks."""
    display_name = "Include Stunt Arena Stars"


@dataclass
class RVGLOptions(PerGameCommonOptions):
    """RVGL-specific options and Archipelago's common settings."""
    starting_cars: StartingCars
    starting_tracks: StartingTracks
    include_stunt_arena_stars: IncludeStuntArenaStars


option_groups = [
    OptionGroup("Starting Content Options", [StartingCars, StartingTracks]),
    OptionGroup("Location Pool Options", [IncludeStuntArenaStars]),
]
