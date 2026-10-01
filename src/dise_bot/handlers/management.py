"""Bilingual owner/admin panel, moderation commands, and exact group replies."""

from telegram import Chat, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from dise_bot import admin_i18n
from dise_bot.keyboards import admin_settings_keyboard, panel_keyboard
from dise_bot.services.management import ManagementStore


def manager_store(context: ContextTypes.DEFAULT_TYPE) -> ManagementStore:
    return context.application.bot_data["management_store"]


def admin_language(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
    return manager_store(context).language_for(user_id)


def admin_text(context: ContextTypes.DEFAULT_TYPE, user_id: int, key: str, **kwargs) -> str:
    return admin_i18n.text(admin_language(context, user_id), key, **kwargs)


def button_action(label: str) -> str | None:
    for language in admin_i18n.SUPPORTED_LANGUAGES:
        for key, value in admin_i18n.BUTTONS[language].items():
            if label == value:
                return key
    if label == admin_i18n.LANGUAGE_BUTTONS[admin_i18n.LANG_FA]:
        return "lang_fa"
    if label == admin_i18n.LANGUAGE_BUTTONS[admin_i18n.LANG_EN]:
        return "lang_en"
    return None


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
    store = manager_store(context)
    if not store.is_manager(user.id):
        if chat.type == Chat.PRIVATE:
            await message.reply_text(admin_i18n.text("en", "access_denied"))
        return
    language = store.language_for(user.id)
    if chat.type != Chat.PRIVATE:
        await message.reply_text(admin_i18n.text(language, "panel_private"))
        return
    context.user_data.pop("pending_panel_action", None)
    context.user_data.pop("pending_force_join_action", None)
    await message.reply_text(
        admin_i18n.text(language, "panel_title"),
        reply_markup=panel_keyboard(owner=store.is_owner(user.id), language=language),
    )


async def settings_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None:
        return
    store = manager_store(context)
    if not store.is_manager(user.id):
        return
    language = store.language_for(user.id)
    context.user_data.pop("pending_panel_action", None)
    context.user_data.pop("pending_force_join_action", None)
    await message.reply_text(
        admin_i18n.text(
            language,
            "settings_title",
            language_name=admin_i18n.language_name(language),
        ),
        reply_markup=admin_settings_keyboard(language=language),
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
        await message.reply_text(admin_i18n.text("en", "access_denied"))
        return

    action = button_action(message.text or "")
    if action is None:
        return
    if action == "panel" or action == "back":
        await panel_command(update, context)
        return
    if action == "settings" or action == "language":
        await settings_panel(update, context)
        return
    if action in {"lang_fa", "lang_en"}:
        language = admin_i18n.LANG_FA if action == "lang_fa" else admin_i18n.LANG_EN
        store.set_language(user.id, language)
        await message.reply_text(admin_i18n.text(language, "language_changed"))
        await settings_panel(update, context)
        return
    if action == "auto_replies":
        language = store.language_for(user.id)
        context.user_data.pop("pending_panel_action", None)
        await message.reply_text(
            admin_i18n.text(language, "reply_guide"),
            reply_markup=panel_keyboard(owner=store.is_owner(user.id), language=language),
        )
        return
    if action == "force_join":
        # Routed by the dedicated force-join handler before this handler.
        return
    moderation = {
        "ban": "ban",
        "unban": "unban",
        "add_admin": "admin",
        "remove_admin": "unadmin",
    }.get(action)
    if moderation is None:
        return
    language = store.language_for(user.id)
    if moderation in {"admin", "unadmin"} and not store.is_owner(user.id):
        await message.reply_text(admin_i18n.text(language, "only_owner_roles"))
        return
    context.user_data["pending_panel_action"] = moderation
    await message.reply_text(
        admin_i18n.text(language, "target_prompt"),
        reply_markup=panel_keyboard(owner=store.is_owner(user.id), language=language),
    )


def parse_target(
    update: Update,
    args: list[str],
    *,
    language: str,
) -> int:
    message = update.effective_message
    if len(args) == 1 and args[0].isascii() and args[0].isdecimal():
        target = int(args[0])
    elif not args and message is not None and message.reply_to_message:
        user = message.reply_to_message.from_user
        if user is None or user.is_bot:
            raise ValueError(admin_i18n.text(language, "target_bot_error"))
        target = user.id
    else:
        raise ValueError(admin_i18n.text(language, "target_error"))
    if not 0 < target < 2**63:
        raise ValueError(admin_i18n.text(language, "target_id_error"))
    return target


async def change_target(
    update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, args: list[str]
) -> None:
    message, actor = update.effective_message, update.effective_user
    if message is None or actor is None or actor.is_bot:
        return
    store = manager_store(context)
    language = store.language_for(actor.id)
    if not store.is_manager(actor.id):
        if update.effective_chat and update.effective_chat.type == Chat.PRIVATE:
            await message.reply_text(admin_i18n.text("en", "access_denied"))
        return
    if action in {"admin", "unadmin"} and not store.is_owner(actor.id):
        await message.reply_text(admin_i18n.text(language, "only_owner_roles"))
        return
    try:
        target = parse_target(update, args, language=language)
        if action == "ban":
            store.set_banned(target, enabled=True)
            result = admin_i18n.text(language, "ban_done", user_id=target)
        elif action == "unban":
            store.set_banned(target, enabled=False)
            result = admin_i18n.text(language, "unban_done", user_id=target)
        elif action == "admin":
            store.set_admin(target, enabled=True)
            result = admin_i18n.text(language, "admin_done", user_id=target)
        elif action == "unadmin":
            store.set_admin(target, enabled=False)
            result = admin_i18n.text(language, "unadmin_done", user_id=target)
        else:
            raise ValueError(admin_i18n.text(language, "unknown_action"))
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
    language = store.language_for(user.id)
    if not store.is_manager(user.id):
        if chat.type == Chat.PRIVATE:
            await message.reply_text(admin_i18n.text("en", "access_denied"))
        return
    if chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        await message.reply_text(admin_i18n.text(language, "reply_guide"))
        return
    payload = (message.text or "").partition(" ")[2].strip()
    action, _, rest = payload.partition(" ")
    if action == "list" and not rest.strip():
        triggers = store.replies_for_chat(chat.id)
        if not triggers:
            await message.reply_text(admin_i18n.text(language, "no_replies"))
            return
        preview = triggers[:30]
        remaining = len(triggers) - len(preview)
        suffix = f"\n… +{remaining}" if remaining else ""
        await message.reply_text(
            admin_i18n.text(
                language,
                "triggers",
                items="\n".join(preview),
                suffix=suffix,
            )
        )
        return
    if action == "add" and "|" in rest:
        trigger, _, response = rest.partition("|")
        try:
            store.add_reply(chat.id, trigger, response)
        except ValueError as error:
            await message.reply_text(str(error))
            return
        await message.reply_text(
            admin_i18n.text(language, "reply_saved", trigger=trigger.strip())
        )
        return
    if action == "remove" and rest.strip():
        removed = store.remove_reply(chat.id, rest)
        key = "reply_removed" if removed else "reply_missing"
        await message.reply_text(admin_i18n.text(language, key))
        return
    await message.reply_text(admin_i18n.text(language, "reply_guide"))


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
