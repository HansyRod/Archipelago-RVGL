from dataclasses import dataclass


# Object with relevant track information
@dataclass(frozen=True)
class TrackData:
    folder: str
    display_name: str
    difficulty: int
    has_reverse: bool

# List of the 13 original Re-Volt tracks
STOCK_TRACKS: tuple[TrackData, ...] = (
    TrackData("nhood1", "Toys in the Hood 1", 1, True),
    TrackData("market2", "Supermarket 2", 1, True),
    TrackData("muse2", "Museum 2", 1, True),
    TrackData("garden1", "Botanical Garden", 1, True),
    TrackData("toylite", "Toy World 1", 2, True),
    TrackData("wild_west1", "Ghost Town 1", 2, True),
    TrackData("toy2", "Toy World 2", 2, True),
    TrackData("nhood2", "Toys in the Hood 2", 3, True),
    TrackData("ship1", "Toytanic 1", 3, True),
    TrackData("muse1", "Museum 1", 3, True),
    TrackData("market1", "Supermarket 1", 4, True),
    TrackData("wild_west2", "Ghost Town 2", 4, True),
    TrackData("ship2", "Toytanic 2", 4, True),
)

# Rooftops was the only track released exclusively on the Dreamcast version
DC_TRACKS: tuple[TrackData, ...] = (
    TrackData("roof", "Rooftops", 2, True),
)
