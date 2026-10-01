"""Stateless ranked-defense handlers, safe for concurrent button presses."""

from telegram import Update
from telegram.ext import ContextTypes

from dise_bot import messages
from dise_bot.keyboards import defense_keyboard
from dise_bot.services.activation import can_roll, is_group
from dise_bot.services.defense import (
    DefenseTier,
    calculate_defense,
    roll_defense,
    roll_percent,
    show_percent_result,
)

TIER_BUTTONS = {
    messages.LIGHT_BUTTON: DefenseTier.LIGHT,
    messages.HEAVY_BUTTON: DefenseTier.HEAVY,
    messages.SUPER_BUTTON: DefenseTier.SUPER,
    messages.GOD_BUTTON: DefenseTier.GOD,
    messages.GOLD_BUTTON: DefenseTier.GOLD,
}
TIER_TITLES = {tier: button for button, tier in TIER_BUTTONS.items()}
USAGE = (
    "Use /defense to open the menu, or /defense light 3 to calculate a roll.\n"
    "Tiers: light, heavy, super, god, gold. Rolls: +1 to +9."
)


async def show_defense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            messages.GROUP_DEFENSE_MENU if is_group(update) else messages.DEFENSE_MENU,
            reply_markup=defense_keyboard(group_controls=is_group(update)),
        )


async def _send_result(
    update: Update, tier: DefenseTier, positive_roll: int, *, allow_percent: bool
) -> None:
    if update.effective_message:
        if allow_percent and show_percent_result():
            result_line = messages.DEFENSE_PERCENT_LINE.format(roll_percent())
        else:
            amount = calculate_defense(tier, positive_roll)
            result_line = messages.DEFENSE_VALUE_LINE.format(amount)
        await update.effective_message.reply_text(
            f"{TIER_TITLES[tier]} · DEFENSE\n"
            "━━━━━━━━━━━━━━\n"
            f"🎲 Roll: +{positive_roll}\n"
            f"{result_line}",
            reply_markup=defense_keyboard(group_controls=is_group(update)),
        )


async def defense_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None or user.is_bot or not can_roll(update, context):
        return
    tier = TIER_BUTTONS.get(message.text or "")
    if tier is not None:
        await _send_result(update, tier, roll_defense(), allow_percent=True)


async def defense_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None or user.is_bot:
        return
    args = context.args or []
    if not args:
        await show_defense(update, context)
        return
    if not can_roll(update, context):
        return
    try:
        if len(args) != 2:
            raise ValueError("Expected tier and roll.")
        tier = DefenseTier(args[0].lower())
        positive_roll = int(args[1])
        calculate_defense(tier, positive_roll)
    except ValueError:
        await message.reply_text(
            USAGE, reply_markup=defense_keyboard(group_controls=is_group(update))
        )
        return
    await _send_result(update, tier, positive_roll, allow_percent=False)
