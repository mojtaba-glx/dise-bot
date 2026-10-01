"""Stateless reflect handler: one random signed value per tap."""

from telegram import Update
from telegram.ext import ContextTypes

from dise_bot import messages
from dise_bot.keyboards import defense_keyboard
from dise_bot.services.activation import can_roll, is_group
from dise_bot.services.defense import roll_reflect


async def reflect_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None or user.is_bot or not can_roll(update, context):
        return
    value = roll_reflect()
    if value > 0:
        result_line = messages.REFLECT_POS_LINE
    elif value < 0:
        result_line = messages.REFLECT_NEG_LINE
    else:
        result_line = messages.REFLECT_ZERO_LINE
    await message.reply_text(
        f"{messages.REFLECT_BUTTON}\n━━━━━━━━━━━━━━\n{result_line}",
        reply_markup=defense_keyboard(group_controls=is_group(update)),
    )
