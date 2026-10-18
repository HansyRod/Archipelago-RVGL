from dataclasses import dataclass


# Object with relevant car information
@dataclass(frozen=True)
class CarData:
    folder: str
    display_name: str
    rating: int

# List of the 28 original Re-Volt cars
STOCK_CARS: tuple[CarData, ...] = (
    CarData("rc", "RC Bandit", 0),
    CarData("mite", "Dust Mite", 0),
    CarData("phat", "Phat Slug", 0),
    CarData("moss", "Col. Moss", 0),
    CarData("mud", "Harvester", 0),
    CarData("beatall", "Dr. Grudge", 0),
    CarData("volken", "Volken Turbo", 0),
    CarData("tc6", "Sprinter XL", 0),
    CarData("dino", "RC San", 1),
    CarData("candy", "Candy Pebbles", 1),
    CarData("gencar", "Genghis Kar", 1),
    CarData("tc4", "Aquasonic", 1),
    CarData("mouse", "Mouse", 1),
    CarData("flag", "Evil Weasel", 2),
    CarData("tc2", "Panga TC", 2),
    CarData("r5", "R6 Turbo", 2),
    CarData("tc5", "NY 54", 2),
    CarData("sgt", "Bertha Ballistics", 2),
    CarData("tc3", "Pest Control", 3),
    CarData("adeon", "Adeon", 3),
    CarData("fone", "Pole Poz", 3),
    CarData("tc1", "Zipper", 3),
    CarData("rotor", "Rotor", 3),
    CarData("cougar", "Cougar", 4),
    CarData("sugo", "Humma", 4),
    CarData("toyeca", "Toyeca", 4),
    CarData("amw", "AMW", 4),
    CarData("panga", "Panga", 4),
)

# List of the 14 cars released on the Dreamcast version
DC_CARS: tuple[CarData, ...] = (
    CarData("bigvolt", "BigVolt", 0),
    CarData("bossvolt", "BossVolt", 2),
    CarData("jg6rc", "RC Phink", 1),
    CarData("tc12", "LA 54", 1),
    CarData("tc10", "Matra XL", 1),
    CarData("tc8", "Shocker", 2),
    CarData("tc11", "Splat", 2),
    CarData("tc9", "Groovster", 2),
    CarData("jg1jg7", "JG-7", 3),
    CarData("tc7", "RG1", 3),
    CarData("jg3loco", "RV Loco", 3),
    CarData("jg4snw35", "SNW 35", 4),
    CarData("jg5purpxl", "Purp XL", 4),
    CarData("jg2fulonx", "Fulon X", 4),
)
