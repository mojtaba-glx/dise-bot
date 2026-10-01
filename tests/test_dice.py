from collections import Counter
from unittest.mock import patch

import pytest

from dise_bot.services.dice import DiceColor, roll


@pytest.mark.parametrize(
    ("color", "expected"),
    [
        (DiceColor.RED, Counter({-1: 2, -2: 2, -3: 2, -4: 2, **{-n: 1 for n in range(5, 11)}})),
        (DiceColor.GREEN, Counter({**{n: 1 for n in range(1, 7)}, 7: 2, 8: 2, 9: 2, 10: 2})),
    ],
)
def test_every_pool_position_preserves_original_odds_and_sign(color, expected):
    # Enumerate every selectable entry instead of using a flaky statistical test.
    results = []
    for index in range(14):
        with patch(
            "dise_bot.services.dice.secrets.choice",
            side_effect=lambda pool, index=index: pool[index],
        ) as pick:
            results.append(roll(color))
            pick.assert_called_once()
            assert len(pick.call_args.args[0]) == 14
    assert Counter(results) == expected
    assert all(1 <= abs(value) <= 10 for value in results)


def test_invalid_color_does_not_silently_roll_green():
    with pytest.raises(ValueError, match="Unknown dice color"):
        roll("blue")
