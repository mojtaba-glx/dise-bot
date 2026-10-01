from unittest.mock import patch

import pytest

from dise_bot.services.defense import (
    ABSOLUTE_VALUES,
    CURSED_AURA_ENERGY_COST,
    CURSED_AURA_VALUES,
    REFLECT_VALUES,
    DefenseTier,
    basic_attack_damage,
    calculate_defense,
    roll_absolute,
    roll_cursed_aura,
    roll_defense,
    roll_percent,
    roll_reflect,
    show_percent_result,
)


@pytest.mark.parametrize(
    ("tier", "expected"),
    [
        (DefenseTier.LIGHT, [10, 15, 20, 25, 30, 35, 40, 45, 50]),
        (DefenseTier.HEAVY, [15, 20, 25, 30, 35, 40, 45, 50, 55]),
        (DefenseTier.SUPER, [20, 25, 30, 35, 40, 45, 50, 55, 60]),
        (DefenseTier.GOD, [25, 30, 35, 40, 45, 50, 55, 60, 65]),
        (DefenseTier.GOLD, [30, 35, 40, 45, 50, 55, 60, 65, 70]),
    ],
)
def test_all_nine_steps_match_the_supplied_defense_tables(tier, expected):
    assert [calculate_defense(tier, roll) for roll in range(1, 10)] == expected


@pytest.mark.parametrize("roll", [-1, 0, 10, 11, 1.5, True, "3", None])
def test_out_of_range_and_non_integer_rolls_are_rejected(roll):
    with pytest.raises(ValueError, match="from \\+1 to \\+9"):
        calculate_defense(DefenseTier.LIGHT, roll)


def test_unknown_tier_is_not_treated_as_a_default_tier():
    with pytest.raises(ValueError, match="Unknown defense tier"):
        calculate_defense("silver", 3)


def test_basic_attack_table_is_kept_separate_from_ranked_defense():
    assert [basic_attack_damage(roll) for roll in range(1, 10)] == [
        10,
        10,
        20,
        20,
        30,
        30,
        30,
        35,
        35,
    ]


@pytest.mark.parametrize(("sample", "expected"), [(0, 1), (8, 9)])
def test_defense_roll_boundaries(sample, expected):
    with patch("dise_bot.services.defense.secrets.randbelow", return_value=sample) as pick:
        assert roll_defense() == expected
        pick.assert_called_once_with(9)


@pytest.mark.parametrize(
    ("magnitude", "expected"),
    [(25, -25), (50, -50), (75, -75), (100, -100)],
)
def test_percent_roll_is_always_negative(magnitude, expected):
    with patch("dise_bot.services.defense.secrets.choice", return_value=magnitude):
        assert roll_percent() == expected


def test_percent_results_cover_all_negative_magnitudes():
    assert {roll_percent() for _ in range(1000)} == {-25, -50, -75, -100}


def test_value_or_percent_choice_is_random_not_fixed():
    assert {show_percent_result() for _ in range(200)} == {True, False}


def test_cursed_aura_values_cover_the_supplied_table():
    assert {roll_cursed_aura() for _ in range(1000)} == set(CURSED_AURA_VALUES)
    assert set(CURSED_AURA_VALUES) == {0, 15, 25, 35, 40}


def test_cursed_aura_choice_uses_the_supplied_table():
    with patch("dise_bot.services.defense.secrets.choice", return_value=15) as pick:
        assert roll_cursed_aura() == 15
        pick.assert_called_once_with(CURSED_AURA_VALUES)


def test_cursed_aura_energy_cost_is_ten():
    assert CURSED_AURA_ENERGY_COST == 10


def test_absolute_values_cover_the_table_with_both_signs():
    assert {roll_absolute() for _ in range(2000)} == {
        0,
        15,
        -15,
        25,
        -25,
        35,
        -35,
        40,
        -40,
    }


@pytest.mark.parametrize(
    ("magnitude", "coin", "expected"),
    [(15, 0, 15), (25, 1, -25), (40, 0, 40), (0, 1, 0)],
)
def test_absolute_roll_combines_magnitude_and_sign(magnitude, coin, expected):
    with (
        patch("dise_bot.services.defense.secrets.choice", return_value=magnitude),
        patch("dise_bot.services.defense.secrets.randbelow", return_value=coin),
    ):
        assert roll_absolute() == expected
    assert set(ABSOLUTE_VALUES) == {0, 15, 25, 35, 40}


def test_reflect_values_cover_the_table_with_both_signs():
    assert {roll_reflect() for _ in range(2000)} == {
        0,
        15,
        -15,
        25,
        -25,
        35,
        -35,
        40,
        -40,
    }
    assert set(REFLECT_VALUES) == {0, 15, 25, 35, 40}
