from dataclasses import dataclass


# Object with relevant car information
@dataclass(frozen=True)
class CupData:
    folder: str
    display_name: str
    difficulty: int

# List of the 28 original Re-Volt cars
STOCK_CUPS: tuple[CupData, ...] = (
    CupData("bronze", "Bronze Cup", 1),
    CupData("silver", "Silver Cup", 2),
    CupData("gold", "Gold Cup", 3),
    CupData("platinum", "Platinum Cup", 4),
)
