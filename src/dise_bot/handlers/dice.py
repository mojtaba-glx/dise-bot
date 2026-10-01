from telegram import Update
from telegram.ext import ContextTypes

from dise_bot import messages
from dise_bot.handlers.management import manager_store
from dise_bot.keyboards import dice_keyboard
from dise_bot.services.activation import can_roll, is_group
from dise_bot.services.dice import DiceColor, roll

BUTTON_COLORS = {
    messages.RED_BUTTON: DiceColor.RED,
    messages.GREEN_BUTTON: DiceColor.GREEN,
}


async def _roll(update: Update, context: ContextTypes.DEFAULT_TYPE, color: DiceColor) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None or user.is_bot or not can_roll(update, context):
        return

    # Generate exactly one result; do not reroll or resend on uncertain network failures.
    result = roll(color)
    await message.reply_text(
        f"{result:+d}",
        reply_markup=dice_keyboard(
            group_controls=is_group(update),
            manager=manager_store(context).is_manager(user.id),
        ),
        do_quote=is_group(update),
    )


async def dice_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is not None and (color := BUTTON_COLORS.get(message.text or "")) is not None:
        await _roll(update, context, color)


async def red_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _roll(update, context, DiceColor.RED)


async def green_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _roll(update, context, DiceColor.GREEN)
