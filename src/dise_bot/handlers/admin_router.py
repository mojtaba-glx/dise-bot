"""Single router for all private admin reply-keyboard buttons."""

from telegram import Chat, Update
from telegram.ext import ContextTypes

from dise_bot.handlers.force_join import join_panel_button
from dise_bot.handlers.management import button_action, manager_store, panel_button

FORCE_JOIN_ACTIONS = {
    "force_join",
    "join_on",
    "join_off",
    "join_add",
    "join_remove",
    "join_list",
}


async def admin_private_button_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message, user, chat = (
        update.effective_message,
        update.effective_user,
        update.effective_chat,
    )
    if (
        message is None
        or user is None
        or chat is None
        or chat.type != Chat.PRIVATE
        or user.is_bot
        or not manager_store(context).is_manager(user.id)
    ):
        return

    action = button_action(message.text or "")
    if action in FORCE_JOIN_ACTIONS:
        await join_panel_button(update, context)
        return
    await panel_button(update, context)
