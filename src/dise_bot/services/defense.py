"""The confirmed defense and basic-attack tables, independent of Telegram."""

import secrets
from enum import Enum


class DefenseTier(Enum):
    LIGHT = "light"
    HEAVY = "heavy"
    SUPER = "super"
    GOD = "god"
    GOLD = "gold"


BASE_DEFENSE = {
    DefenseTier.LIGHT: 10,
    DefenseTier.HEAVY: 15,
    DefenseTier.SUPER: 20,
    DefenseTier.GOD: 25,
    DefenseTier.GOLD: 30,
}


def roll_defense() -> int:
    """Roll an independent, equally likely positive step from +1 to +9."""
    return secrets.randbelow(9) + 1


PERCENT_MAGNITUDES = (25, 50, 75, 100)


def roll_percent() -> int:
    """Return an independent negative percentage: -25, -50, -75, or -100."""
    return -secrets.choice(PERCENT_MAGNITUDES)


def show_percent_result() -> bool:
    """Randomly choose between the calculated table value and a percent result."""
    return secrets.randbelow(2) == 1


def validate_positive_roll(positive_roll: int) -> None:
    if type(positive_roll) is not int or not 1 <= positive_roll <= 9:
        raise ValueError("The defense roll must be an integer from +1 to +9.")


def calculate_defense(tier: DefenseTier, positive_roll: int) -> int:
    """Return the exact table value, with +1 as the base and +9 as the last step."""
    validate_positive_roll(positive_roll)
    if not isinstance(tier, DefenseTier):
        raise ValueError("Unknown defense tier.")
    return BASE_DEFENSE[tier] + (positive_roll - 1) * 5


def basic_attack_damage(positive_roll: int) -> int:
    """Damage for the supplied punch/kick table; this is not an energy cost."""
    validate_positive_roll(positive_roll)
    return (10, 10, 20, 20, 30, 30, 30, 35, 35)[positive_roll - 1]


CURSED_AURA_VALUES = (0, 15, 25, 35, 40)
CURSED_AURA_ENERGY_COST = 10


def roll_cursed_aura() -> int:
    """Return an independent random cursed-aura value; each costs 10 energy."""
    return secrets.choice(CURSED_AURA_VALUES)


ABSOLUTE_VALUES = (0, 15, 25, 35, 40)


def roll_absolute() -> int:
    """Return an independent random absolute value with a random sign."""
    magnitude = secrets.choice(ABSOLUTE_VALUES)
    if magnitude == 0:
        return 0
    return magnitude if secrets.randbelow(2) == 0 else -magnitude


REFLECT_VALUES = (0, 15, 25, 35, 40)


def roll_reflect() -> int:
    """Return an independent random reflect value with a random sign."""
    magnitude = secrets.choice(REFLECT_VALUES)
    if magnitude == 0:
        return 0
    return magnitude if secrets.randbelow(2) == 0 else -magnitude
