from dataclasses import dataclass


STOCK_STUNT_ARENA_STAR_COUNT = 20


@dataclass(frozen=True)
class StuntArenaData:
    display_name: str
    star_count: int


STOCK_STUNT_ARENA = StuntArenaData("Stunt Arena", STOCK_STUNT_ARENA_STAR_COUNT)
