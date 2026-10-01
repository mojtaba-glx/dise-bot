"""Group-only commands that affect only the sending user's dice."""

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from dise_bot import messages
from dise_bot.keyboards import dice_keyboard
from dise_bot.services.activation import ActivationStore, is_group


async def _set_activation(
    update: Update, context: ContextTypes.DEFAULT_TYPE, *, enabled: bool
) -> None:
    message, chat, user = (
        update.effective_message,
        update.effective_chat,
        update.effective_user,
    )
    if message is None or chat is None or user is None or user.is_bot:
        return
    if not is_group(update):
        await message.reply_text(messages.GROUP_ONLY_MESSAGE)
        return

    store: ActivationStore = context.application.bot_data["activation_store"]
    store.set_enabled(chat.id, user.id, enabled=enabled)
    await message.reply_text(
        messages.ON_MESSAGE if enabled else messages.OFF_MESSAGE,
        reply_markup=dice_keyboard(group_controls=True),
    )


async def on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_activation(update, context, enabled=True)


async def off_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _set_activation(update, context, enabled=False)


async def activation_button_gate(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the persistent ON/OFF buttons before normal message routing."""
    message = update.effective_message
    if message is None or not is_group(update) or not message.text:
        return

    text = " ".join(message.text.split()).casefold()
    if text == messages.ON_BUTTON.casefold():
        await _set_activation(update, context, enabled=True)
    elif text == messages.OFF_BUTTON.casefold():
        await _set_activation(update, context, enabled=False)
    else:
        return

    # Do not let the same keyboard click fall through to later text handlers.
    raise ApplicationHandlerStop
