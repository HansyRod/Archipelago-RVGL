from dataclasses import dataclass

from Options import Choice, DefaultOnToggle, OptionGroup, PerGameCommonOptions, Range, Toggle


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


class IncludeDreamcastCars(Toggle):
    """Include the 14 Dreamcast cars as unlock items in the item pool."""
    display_name = "Include Dreamcast Cars"


class IncludeDreamcastTrackRooftops(Toggle):
    """Include the Dreamcast track Rooftops as an unlock item and enable its location checks."""
    display_name = "Include Dreamcast Track Rooftops"


class IncludeSingleRaceWins(DefaultOnToggle):
    """Include Single Race wins on each track as location checks.

    Removing too many locations from the location pool can cause generation to fail
    if the world has more required items than available locations.
    """
    display_name = "Include Single Race Wins"


class IncludePracticeStars(DefaultOnToggle):
    """Include Practice stars on each track as location checks."""
    display_name = "Include Practice Stars"


class IncludeNormalTimeTrials(DefaultOnToggle):
    """Include Normal Time Trial records on each track as location checks."""
    display_name = "Include Normal Time Trials"


class IncludeReverseTimeTrials(DefaultOnToggle):
    """Include Reverse Time Trial records on tracks with reverse version as location checks."""
    display_name = "Include Reverse Time Trials"


class IncludeMirrorTimeTrials(DefaultOnToggle):
    """Include Mirror Time Trial records on each track as location checks."""
    display_name = "Include Mirror Time Trials"


class IncludeStuntArenaStars(Toggle):
    """Include the Stunt Arena's 20 stars as location checks."""
    display_name = "Include Stunt Arena Stars"


class Carsanity(Choice):
    """Include a Single Race win with each enabled car as a location check.

    Disabled: No location checks for winning races with individual cars.
    Enabled: Each enabled car has a location check for winning a Single Race with it.

    Dreamcast car checks are included only when Include Dreamcast Cars is enabled.
    """
    display_name = "Carsanity"
    option_disabled = 0
    option_enabled = 1
    default = option_disabled


@dataclass
class RVGLOptions(PerGameCommonOptions):
    """RVGL-specific options and Archipelago's common settings."""
    starting_cars: StartingCars
    starting_tracks: StartingTracks
    include_dreamcast_cars: IncludeDreamcastCars
    include_dreamcast_track_rooftops: IncludeDreamcastTrackRooftops
    include_single_race_wins: IncludeSingleRaceWins
    include_practice_stars: IncludePracticeStars
    include_normal_time_trials: IncludeNormalTimeTrials
    include_reverse_time_trials: IncludeReverseTimeTrials
    include_mirror_time_trials: IncludeMirrorTimeTrials
    include_stunt_arena_stars: IncludeStuntArenaStars
    carsanity: Carsanity


option_groups = [
    OptionGroup("Starting Content Options", [StartingCars, StartingTracks]),
    OptionGroup("Item Pool Options", [IncludeDreamcastCars, IncludeDreamcastTrackRooftops]),
    OptionGroup("Location Pool Options", [
        IncludeSingleRaceWins,
        IncludePracticeStars,
        IncludeNormalTimeTrials,
        IncludeReverseTimeTrials,
        IncludeMirrorTimeTrials,
        IncludeStuntArenaStars,
        Carsanity,
    ]),
]
