"""Preserve the original weighted pools, including their intentional duplicates."""

import secrets
from enum import Enum


class DiceColor(Enum):
    RED = "red"
    GREEN = "green"


# Do not turn these into sets: repeated entries are the intended weights.
RED_DICE = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 3, 2, 1, 4)
GREEN_DICE = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 7, 8, 9, 10)


def roll(color: DiceColor) -> int:
    """Select a uniform pool entry and return its signed result."""
    if color is DiceColor.RED:
        return -secrets.choice(RED_DICE)
    if color is DiceColor.GREEN:
        return secrets.choice(GREEN_DICE)
    raise ValueError("Unknown dice color.")
