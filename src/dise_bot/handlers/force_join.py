"""Multi-channel required membership with bilingual admin controls."""

import logging
import re
import time

from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import ApplicationHandlerStop, ContextTypes

from dise_bot import admin_i18n, messages
from dise_bot.handlers.management import button_action, manager_store, panel_command
from dise_bot.keyboards import force_join_keyboard
from dise_bot.services.force_join import ForceJoinStore, RequiredChat

logger = logging.getLogger(__name__)
CHECK_CALLBACK = "force_join_check"
MEMBERSHIP_TTL_SECONDS = 30
PUBLIC_USERNAME = re.compile(r"@[A-Za-z0-9_]{5,32}\Z")
PRIVATE_INVITE = re.compile(r"https://t\.me/(?:\+[A-Za-z0-9_-]+|joinchat/[A-Za-z0-9_-]+)\Z")
BOT_COMMANDS = {
    "start",
    "help",
    "on",
    "off",
    "status",
    "version",
    "red",
    "green",
    "defense",
    "tag",
}
BOT_BUTTONS = {
    messages.RED_BUTTON,
    messages.GREEN_BUTTON,
    messages.DEFENSE_BUTTON,
    messages.ABLITY_BUTTON,
    messages.LIGHT_BUTTON,
    messages.HEAVY_BUTTON,
    messages.SUPER_BUTTON,
    messages.GOD_BUTTON,
    messages.GOLD_BUTTON,
    messages.CURSED_AURA_BUTTON,
    messages.ABSOLUTE_BUTTON,
    messages.REFLECT_BUTTON,
    messages.BACK_BUTTON,
}


def join_store(context: ContextTypes.DEFAULT_TYPE) -> ForceJoinStore:
    return context.application.bot_data["force_join_store"]


def membership_cache(context: ContextTypes.DEFAULT_TYPE) -> dict[tuple[int, int], float]:
    return context.application.bot_data["membership_cache"]


def admin_language(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
    return manager_store(context).language_for(user_id)


def join_keyboard(chats: list[RequiredChat]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(f"📢 {chat.title}", url=chat.join_url)]
        for chat in chats
    ]
    rows.append([InlineKeyboardButton("✅ Check membership", callback_data=CHECK_CALLBACK)])
    return InlineKeyboardMarkup(rows)


def user_join_prompt(chats: list[RequiredChat]) -> str:
    names = "\n".join(f"• {chat.title}" for chat in chats)
    return (
        "🔒 Join all required channels to use this bot:\n"
        f"{names}\n\n"
        "Then tap Check membership."
    )


def is_bot_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    message, chat = update.effective_message, update.effective_chat
    if message is None or chat is None or not message.text:
        return False
    if chat.type == Chat.PRIVATE:
        return True
    if chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        return False
    text = message.text
    if text in BOT_BUTTONS:
        return True
    if text.startswith("/"):
        command = text.split(maxsplit=1)[0][1:]
        name, separator, recipient = command.partition("@")
        if separator and recipient.casefold() != (context.bot.username or "").casefold():
            return False
        return name.casefold() in BOT_COMMANDS
    management = manager_store(context)
    return management.response_for(chat.id, text) is not None


async def verify_member(
    context: ContextTypes.DEFAULT_TYPE,
    chat: RequiredChat,
    user_id: int,
    *,
    fresh: bool = False,
) -> bool | None:
    cache = membership_cache(context)
    key = (chat.chat_id, user_id)
    if not fresh and cache.get(key, 0) > time.monotonic():
        return True
    try:
        member = await context.bot.get_chat_member(chat.chat_id, user_id)
    except TelegramError as error:
        logger.warning(
            "Required membership check failed for %s (%s)",
            chat.chat_id,
            type(error).__name__,
        )
        return None
    active = member.status in (
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.MEMBER,
    ) or (member.status == ChatMemberStatus.RESTRICTED and member.is_member)
    if active:
        cache[key] = time.monotonic() + MEMBERSHIP_TTL_SECONDS
    else:
        cache.pop(key, None)
    return active


async def verify_all_required(
    context: ContextTypes.DEFAULT_TYPE,
    chats: list[RequiredChat],
    user_id: int,
    *,
    fresh: bool = False,
) -> tuple[bool | None, list[RequiredChat]]:
    missing: list[RequiredChat] = []
    for chat in chats:
        verified = await verify_member(context, chat, user_id, fresh=fresh)
        if verified is None:
            return None, []
        if not verified:
            missing.append(chat)
    return not missing, missing


async def force_join_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chats = join_store(context).required_chats
    user, message = update.effective_user, update.message
    if not chats or user is None or message is None or user.is_bot:
        return
    management = manager_store(context)
    if management.is_manager(user.id):
        return
    words = (message.text or "").split(maxsplit=1)
    first_word = words[0] if words else ""
    if first_word.split("@")[0] == "/id":
        return
    if not is_bot_interaction(update, context):
        return
    verified, _ = await verify_all_required(context, chats, user.id)
    if verified:
        return
    await message.reply_text(
        user_join_prompt(chats),
        reply_markup=join_keyboard(chats),
    )
    raise ApplicationHandlerStop


async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query, user = update.callback_query, update.effective_user
    if query is None or user is None:
        return
    chats = join_store(context).required_chats
    if not chats:
        await query.answer("Membership is no longer required.", show_alert=True)
        return
    management = manager_store(context)
    if management.is_manager(user.id):
        verified, missing = True, []
    else:
        verified, missing = await verify_all_required(
            context,
            chats,
            user.id,
            fresh=True,
        )
    if verified is None:
        await query.answer("Could not verify membership. Try again later.", show_alert=True)
    elif verified:
        await query.answer("Membership verified!", show_alert=True)
        if query.message and query.message.chat.type == Chat.PRIVATE:
            await query.edit_message_text("✅ Membership verified. You can use the bot now.")
    else:
        titles = ", ".join(chat.title for chat in missing[:3])
        suffix = "…" if len(missing) > 3 else ""
        await query.answer(
            f"Join all required channels first: {titles}{suffix}",
            show_alert=True,
        )


def parse_add_spec(tokens: list[str], *, language: str) -> tuple[int | str, str | None]:
    if len(tokens) not in (1, 2):
        raise ValueError(admin_i18n.text(language, "join_add_help"))
    target = tokens[0]
    if PUBLIC_USERNAME.fullmatch(target):
        if len(tokens) != 1:
            raise ValueError(admin_i18n.text(language, "join_add_help"))
        return target, None
    if target.startswith("-100") and target[1:].isascii() and target[1:].isdecimal():
        chat_id = int(target)
        if not -(2**63) < chat_id < 0:
            raise ValueError(admin_i18n.text(language, "join_add_help"))
        invite = tokens[1] if len(tokens) == 2 else None
        if invite is not None and not PRIVATE_INVITE.fullmatch(invite):
            raise ValueError(admin_i18n.text(language, "join_invalid_private_link"))
        return chat_id, invite
    raise ValueError(admin_i18n.text(language, "join_add_help"))


async def prepare_required_chat(
    context: ContextTypes.DEFAULT_TYPE,
    target: int | str,
    private_invite: str | None,
    *,
    language: str,
    refresh_private: bool = False,
) -> RequiredChat:
    channel = await context.bot.get_chat(target)
    if channel.type not in (Chat.CHANNEL, Chat.SUPERGROUP):
        raise ValueError(admin_i18n.text(language, "join_bad_chat"))
    bot_member = await context.bot.get_chat_member(channel.id, context.bot.id)
    if bot_member.status not in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
        raise ValueError(admin_i18n.text(language, "join_make_admin"))
    can_invite = bot_member.status == ChatMemberStatus.OWNER or bot_member.can_invite_users
    if channel.username:
        join_url = f"https://t.me/{channel.username}"
    elif can_invite and (private_invite is None or refresh_private):
        invite = await context.bot.create_chat_invite_link(channel.id, name="dise-bot")
        join_url = invite.invite_link
    elif private_invite:
        join_url = private_invite
    else:
        raise ValueError(admin_i18n.text(language, "join_private_link"))
    return RequiredChat(channel.id, channel.title or str(channel.id), join_url)


def configured_channels_text(store: ForceJoinStore, language: str) -> str:
    if not store.configured_chats:
        return admin_i18n.text(language, "join_none")
    lines = [
        f"• {chat.title} — {chat.chat_id}\n  {chat.join_url}"
        for chat in store.configured_chats
    ]
    return admin_i18n.text(language, "join_channels", items="\n".join(lines))


async def show_force_join_panel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None:
        return
    store = join_store(context)
    language = admin_language(context, user.id)
    status = admin_i18n.text(language, "on" if store.enabled else "off")
    body = (
        admin_i18n.text(language, "join_title")
        + "\n"
        + admin_i18n.text(
            language,
            "join_status",
            status=status,
            count=len(store.configured_chats),
        )
        + "\n\n"
        + configured_channels_text(store, language)
    )
    await message.reply_text(
        body,
        reply_markup=force_join_keyboard(language=language, enabled=store.enabled),
    )


async def add_required_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tokens: list[str],
    *,
    enable_after: bool = False,
) -> bool:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None:
        return False
    language = admin_language(context, user.id)
    try:
        target, private_invite = parse_add_spec(tokens, language=language)
        required = await prepare_required_chat(
            context,
            target,
            private_invite,
            language=language,
        )
    except ValueError as error:
        await message.reply_text(str(error))
        return False
    except TelegramError as error:
        logger.warning("Could not add required channel (%s).", type(error).__name__)
        await message.reply_text(admin_i18n.text(language, "join_access_error"))
        return False
    store = join_store(context)
    store.add_chat(required, enable=False)
    if enable_after:
        store.enable()
    membership_cache(context).clear()
    await message.reply_text(
        admin_i18n.text(
            language,
            "join_added",
            title=required.title,
            chat_id=required.chat_id,
        )
    )
    return True


async def remove_required_channel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    raw_id: str,
) -> bool:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None:
        return False
    language = admin_language(context, user.id)
    if not (
        raw_id.startswith("-100")
        and raw_id[1:].isascii()
        and raw_id[1:].isdecimal()
    ):
        await message.reply_text(admin_i18n.text(language, "join_remove_prompt"))
        return False
    chat_id = int(raw_id)
    removed = join_store(context).remove_chat(chat_id)
    membership_cache(context).clear()
    key = "join_removed" if removed else "join_remove_missing"
    await message.reply_text(admin_i18n.text(language, key, chat_id=chat_id))
    return removed


async def enable_required_membership(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None:
        return False
    language = admin_language(context, user.id)
    store = join_store(context)
    if not store.configured_chats:
        await message.reply_text(admin_i18n.text(language, "join_need_channel"))
        return False

    refreshed: list[RequiredChat] = []
    try:
        for configured in store.configured_chats:
            refreshed.append(
                await prepare_required_chat(
                    context,
                    configured.chat_id,
                    configured.join_url,
                    language=language,
                    refresh_private=True,
                )
            )
    except (ValueError, TelegramError) as error:
        logger.warning("Could not enable required membership (%s).", type(error).__name__)
        await message.reply_text(admin_i18n.text(language, "join_verify_error"))
        return False

    for chat in refreshed:
        store.update_chat(chat)
    store.enable()
    membership_cache(context).clear()
    await message.reply_text(
        admin_i18n.text(language, "join_enabled", count=len(refreshed)),
        reply_markup=join_keyboard(refreshed),
    )
    return True


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user, source = (
        update.effective_message,
        update.effective_user,
        update.effective_chat,
    )
    if message is None or user is None or source is None:
        return
    management = manager_store(context)
    if not management.is_manager(user.id):
        if source.type == Chat.PRIVATE:
            await message.reply_text(admin_i18n.text("en", "access_denied"))
        return
    language = management.language_for(user.id)
    if source.type != Chat.PRIVATE:
        await message.reply_text(admin_i18n.text(language, "join_only_private"))
        return

    args = context.args or []
    store = join_store(context)
    if not args:
        await show_force_join_panel(update, context)
        return
    action = args[0].casefold()

    if action in {"status", "list"} and len(args) == 1:
        await show_force_join_panel(update, context)
        return
    if action == "off" and len(args) == 1:
        store.disable()
        membership_cache(context).clear()
        await message.reply_text(admin_i18n.text(language, "join_disabled"))
        await show_force_join_panel(update, context)
        return
    if action == "on" and len(args) == 1:
        if await enable_required_membership(update, context):
            await show_force_join_panel(update, context)
        return
    if action in {"add", "set"}:
        added = await add_required_channel(
            update,
            context,
            args[1:],
            enable_after=action == "set",
        )
        if added:
            await show_force_join_panel(update, context)
        return
    if action == "remove" and len(args) == 2:
        await remove_required_channel(update, context, args[1])
        await show_force_join_panel(update, context)
        return
    await message.reply_text(admin_i18n.text(language, "join_guide"))


async def join_panel_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user, source = (
        update.effective_message,
        update.effective_user,
        update.effective_chat,
    )
    if message is None or user is None or source is None or source.type != Chat.PRIVATE:
        return
    management = manager_store(context)
    if not management.is_manager(user.id):
        await message.reply_text(admin_i18n.text("en", "access_denied"))
        return
    language = management.language_for(user.id)
    action = button_action(message.text or "")

    if action == "force_join":
        context.user_data.pop("pending_force_join_action", None)
        await show_force_join_panel(update, context)
        return
    if action == "join_on":
        context.user_data.pop("pending_force_join_action", None)
        if await enable_required_membership(update, context):
            await show_force_join_panel(update, context)
        return
    if action == "join_off":
        context.user_data.pop("pending_force_join_action", None)
        join_store(context).disable()
        membership_cache(context).clear()
        await message.reply_text(admin_i18n.text(language, "join_disabled"))
        await show_force_join_panel(update, context)
        return
    if action == "join_add":
        context.user_data["pending_force_join_action"] = "add"
        await message.reply_text(
            admin_i18n.text(language, "join_add_prompt"),
            reply_markup=force_join_keyboard(
                language=language,
                enabled=join_store(context).enabled,
            ),
        )
        return
    if action == "join_remove":
        context.user_data["pending_force_join_action"] = "remove"
        await message.reply_text(
            admin_i18n.text(language, "join_remove_prompt"),
            reply_markup=force_join_keyboard(
                language=language,
                enabled=join_store(context).enabled,
            ),
        )
        return
    if action == "join_list":
        context.user_data.pop("pending_force_join_action", None)
        await show_force_join_panel(update, context)
        return
    if action == "back":
        context.user_data.pop("pending_force_join_action", None)
        await panel_command(update, context)


async def pending_force_join_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    message, user, source = (
        update.effective_message,
        update.effective_user,
        update.effective_chat,
    )
    if (
        message is None
        or user is None
        or source is None
        or source.type != Chat.PRIVATE
        or not manager_store(context).is_manager(user.id)
    ):
        context.user_data.pop("pending_force_join_action", None)
        return False

    action = context.user_data.get("pending_force_join_action")
    if action is None:
        return False
    raw = (message.text or "").strip()
    if not raw:
        return True

    if action == "add":
        success = await add_required_channel(update, context, raw.split())
    elif action == "remove":
        success = await remove_required_channel(update, context, raw)
    else:
        context.user_data.pop("pending_force_join_action", None)
        return False

    if success:
        context.user_data.pop("pending_force_join_action", None)
        await show_force_join_panel(update, context)
    return True
