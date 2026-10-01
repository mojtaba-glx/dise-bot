"""Owner/admin menu, moderation commands, and exact group replies."""

from telegram import Chat, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from dise_bot import messages
from dise_bot.keyboards import panel_keyboard
from dise_bot.services.management import ManagementStore

ACTION_BUTTONS = {
    messages.BAN_BUTTON: "ban",
    messages.UNBAN_BUTTON: "unban",
    messages.ADD_ADMIN_BUTTON: "admin",
    messages.REMOVE_ADMIN_BUTTON: "unadmin",
}
REPLY_GUIDE = (
    "In the target group, use:\n"
    "/reply add سلام | سلام!\n"
    "/reply remove سلام\n"
    "/reply list\n\n"
    "Triggers match whole messages. Persian ی/ي and ک/ك are treated alike."
)


def manager_store(context: ContextTypes.DEFAULT_TYPE) -> ManagementStore:
    return context.application.bot_data["management_store"]


async def ban_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is not None and manager_store(context).is_banned(user.id):
        raise ApplicationHandlerStop


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user = update.effective_message, update.effective_user
    if message is not None and user is not None and not user.is_bot:
        await message.reply_text(f"Your Telegram user ID: {user.id}")


async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user, chat = (
        update.effective_message,
        update.effective_user,
        update.effective_chat,
    )
    if message is None or user is None or chat is None or user.is_bot:
        return
    if not manager_store(context).is_manager(user.id):
        if chat.type == Chat.PRIVATE:
            await message.reply_text("Access denied.")
        return
    if chat.type != Chat.PRIVATE:
        await message.reply_text("Open /panel in a private chat with this bot.")
        return
    context.user_data.pop("pending_panel_action", None)
    await message.reply_text(
        "👑 Control panel\nChoose an action. User moderation applies across this bot; "
        "auto replies are configured separately in each group.",
        reply_markup=panel_keyboard(owner=manager_store(context).is_owner(user.id)),
    )


async def panel_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user, chat = (
        update.effective_message,
        update.effective_user,
        update.effective_chat,
    )
    if message is None or user is None or chat is None or chat.type != Chat.PRIVATE:
        return
    store = manager_store(context)
    if not store.is_manager(user.id):
        await message.reply_text("Access denied.")
        return
    if message.text == messages.PANEL_BUTTON:
        await panel_command(update, context)
        return
    if message.text == messages.AUTO_REPLIES_BUTTON:
        context.user_data.pop("pending_panel_action", None)
        await message.reply_text(
            REPLY_GUIDE, reply_markup=panel_keyboard(owner=store.is_owner(user.id))
        )
        return
    action = ACTION_BUTTONS.get(message.text or "")
    if action is None:
        return
    if action in {"admin", "unadmin"} and not store.is_owner(user.id):
        await message.reply_text("Only the owner can change admin roles.")
        return
    context.user_data["pending_panel_action"] = action
    await message.reply_text(
        "Send the numeric Telegram user ID now. Use /id to find your own ID, "
        "or reply to a person's message in a group with a moderation command.",
        reply_markup=panel_keyboard(owner=store.is_owner(user.id)),
    )


def parse_target(update: Update, args: list[str]) -> int:
    message = update.effective_message
    if len(args) == 1 and args[0].isascii() and args[0].isdecimal():
        target = int(args[0])
    elif not args and message is not None and message.reply_to_message:
        user = message.reply_to_message.from_user
        if user is None or user.is_bot:
            raise ValueError("Reply to a person's message or send their numeric ID.")
        target = user.id
    else:
        raise ValueError("Send one numeric user ID or reply to a person's message.")
    if not 0 < target < 2**63:
        raise ValueError("Use a valid positive Telegram user ID.")
    return target


async def change_target(
    update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, args: list[str]
) -> None:
    message, actor = update.effective_message, update.effective_user
    if message is None or actor is None or actor.is_bot:
        return
    store = manager_store(context)
    if not store.is_manager(actor.id):
        if update.effective_chat and update.effective_chat.type == Chat.PRIVATE:
            await message.reply_text("Access denied.")
        return
    if action in {"admin", "unadmin"} and not store.is_owner(actor.id):
        await message.reply_text("Only the owner can change admin roles.")
        return
    try:
        target = parse_target(update, args)
        if action == "ban":
            store.set_banned(target, enabled=True)
            result = f"User {target} banned from this bot."
        elif action == "unban":
            store.set_banned(target, enabled=False)
            result = f"User {target} unbanned."
        elif action == "admin":
            store.set_admin(target, enabled=True)
            result = f"User {target} is now a bot admin."
        elif action == "unadmin":
            store.set_admin(target, enabled=False)
            result = f"User {target} is no longer a bot admin."
        else:
            raise ValueError("Unknown moderation action.")
    except ValueError as error:
        await message.reply_text(str(error))
        return
    context.user_data.pop("pending_panel_action", None)
    await message.reply_text(result)


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await change_target(update, context, "ban", context.args or [])


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await change_target(update, context, "unban", context.args or [])


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await change_target(update, context, "admin", context.args or [])


async def unadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await change_target(update, context, "unadmin", context.args or [])


async def pending_panel_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if user is None or not manager_store(context).is_manager(user.id):
        context.user_data.pop("pending_panel_action", None)
        return False
    action = context.user_data.get("pending_panel_action")
    if action is None:
        return False
    text = update.effective_message.text or ""
    await change_target(update, context, action, [text.strip()])
    return True


async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user, chat = (
        update.effective_message,
        update.effective_user,
        update.effective_chat,
    )
    if message is None or user is None or chat is None or user.is_bot:
        return
    store = manager_store(context)
    if not store.is_manager(user.id):
        if chat.type == Chat.PRIVATE:
            await message.reply_text("Access denied.")
        return
    if chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        await message.reply_text(REPLY_GUIDE)
        return
    payload = (message.text or "").partition(" ")[2].strip()
    action, _, rest = payload.partition(" ")
    if action == "list" and not rest.strip():
        triggers = store.replies_for_chat(chat.id)
        if not triggers:
            await message.reply_text("No auto replies in this group yet.")
            return
        preview = triggers[:30]
        remaining = len(triggers) - len(preview)
        suffix = f"\n… and {remaining} more." if remaining else ""
        await message.reply_text("Group triggers:\n" + "\n".join(preview) + suffix)
        return
    if action == "add" and "|" in rest:
        trigger, _, response = rest.partition("|")
        try:
            store.add_reply(chat.id, trigger, response)
        except ValueError as error:
            await message.reply_text(str(error))
            return
        await message.reply_text(f"Auto reply saved for: {trigger.strip()}")
        return
    if action == "remove" and rest.strip():
        removed = store.remove_reply(chat.id, rest)
        await message.reply_text("Auto reply removed." if removed else "No matching trigger found.")
        return
    await message.reply_text(REPLY_GUIDE)


async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user, chat = (
        update.effective_message,
        update.effective_user,
        update.effective_chat,
    )
    if message is None or user is None or chat is None or user.is_bot or not message.text:
        return
    response = manager_store(context).response_for(chat.id, message.text)
    if response is not None:
        await message.reply_text(response)
