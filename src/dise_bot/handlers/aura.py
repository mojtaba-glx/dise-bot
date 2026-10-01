"""Stateless cursed-aura handler: one random value per tap, costing 10 energy."""

from telegram import Update
from telegram.ext import ContextTypes

from dise_bot import messages
from dise_bot.keyboards import defense_keyboard
from dise_bot.services.activation import can_roll, is_group
from dise_bot.services.defense import CURSED_AURA_ENERGY_COST, roll_cursed_aura


async def aura_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None or user.is_bot or not can_roll(update, context):
        return
    value = roll_cursed_aura()
    await message.reply_text(
        f"{messages.CURSED_AURA_BUTTON}\n"
        "━━━━━━━━━━━━━━\n"
        f"{messages.AURA_VALUE_LINE.format(value)}\n"
        f"⚡ Energy cost: {CURSED_AURA_ENERGY_COST}",
        reply_markup=defense_keyboard(group_controls=is_group(update)),
    )
