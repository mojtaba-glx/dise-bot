"""Owner-controlled required membership with a live Telegram membership check."""

import logging
import re
import time

from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError
from telegram.ext import ApplicationHandlerStop, ContextTypes

from dise_bot import messages
from dise_bot.services.force_join import ForceJoinStore, RequiredChat
from dise_bot.services.management import ManagementStore

logger = logging.getLogger(__name__)
CHECK_CALLBACK = "force_join_check"
MEMBERSHIP_TTL_SECONDS = 30
JOIN_GUIDE = (
    "🔒 Required membership\n"
    "Public channel: /join set @channelname\n"
    "Private channel: /join set -1001234567890\n"
    "Use /join on and /join off without losing the saved link.\n"
    "Use /join status to view the setting.\n"
    "The bot must be an admin in that channel."
)
PUBLIC_USERNAME = re.compile(r"@[A-Za-z0-9_]{5,32}\Z")
PRIVATE_INVITE = re.compile(r"https://t\.me/(?:\+[A-Za-z0-9_-]+|joinchat/[A-Za-z0-9_-]+)\Z")
BOT_COMMANDS = {"start", "help", "on", "off", "status", "version", "red", "green", "defense"}
BOT_BUTTONS = {
    messages.ON_BUTTON,
    messages.OFF_BUTTON,
    messages.STATUS_BUTTON,
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


def join_keyboard(chat: RequiredChat) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Join channel", url=chat.join_url)],
            [InlineKeyboardButton("✅ Check membership", callback_data=CHECK_CALLBACK)],
        ]
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
    management: ManagementStore = context.application.bot_data["management_store"]
    return management.response_for(chat.id, text) is not None


async def verify_member(
    context: ContextTypes.DEFAULT_TYPE, chat: RequiredChat, user_id: int, *, fresh: bool = False
) -> bool | None:
    cache = membership_cache(context)
    key = (chat.chat_id, user_id)
    if not fresh and cache.get(key, 0) > time.monotonic():
        return True
    try:
        member = await context.bot.get_chat_member(chat.chat_id, user_id)
    except TelegramError as error:
        logger.warning("Required membership check failed (%s).", type(error).__name__)
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


async def force_join_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = join_store(context).required_chat
    user, message = update.effective_user, update.message
    if chat is None or user is None or message is None or user.is_bot:
        return
    management: ManagementStore = context.application.bot_data["management_store"]
    if management.is_manager(user.id):
        return
    words = (message.text or "").split(maxsplit=1)
    first_word = words[0] if words else ""
    if first_word.split("@")[0] in ("/id", "/join"):
        return
    if not is_bot_interaction(update, context):
        return
    if await verify_member(context, chat, user.id):
        return
    await message.reply_text(
        f"🔒 Join {chat.title} to use this bot, then tap Check membership.",
        reply_markup=join_keyboard(chat),
    )
    raise ApplicationHandlerStop


async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query, user = update.callback_query, update.effective_user
    if query is None or user is None:
        return
    chat = join_store(context).required_chat
    if chat is None:
        await query.answer("Membership is no longer required.", show_alert=True)
        return
    management: ManagementStore = context.application.bot_data["management_store"]
    verified = management.is_manager(user.id) or await verify_member(
        context, chat, user.id, fresh=True
    )
    if verified is None:
        await query.answer("Could not verify membership. Try again later.", show_alert=True)
    elif verified:
        await query.answer("Membership verified!", show_alert=True)
        if query.message and query.message.chat.type == Chat.PRIVATE:
            await query.edit_message_text("✅ Membership verified. You can use the bot now.")
    else:
        await query.answer("Join the channel first, then check again.", show_alert=True)


def parse_required_chat(args: list[str]) -> tuple[int | str, str | None]:
    if len(args) not in (2, 3) or args[0] != "set":
        raise ValueError(JOIN_GUIDE)
    target = args[1]
    if PUBLIC_USERNAME.fullmatch(target):
        if len(args) != 2:
            raise ValueError(JOIN_GUIDE)
        return target, None
    if target.startswith("-100") and target[1:].isascii() and target[1:].isdecimal():
        chat_id = int(target)
        if not -(2**63) < chat_id < 0:
            raise ValueError(JOIN_GUIDE)
        invite = args[2] if len(args) == 3 else None
        if invite is not None and not PRIVATE_INVITE.fullmatch(invite):
            raise ValueError("Use a valid private Telegram invite link: https://t.me/+...")
        return chat_id, invite
    raise ValueError(JOIN_GUIDE)


async def prepare_required_chat(
    context: ContextTypes.DEFAULT_TYPE,
    target: int | str,
    private_invite: str | None,
    *,
    refresh_private: bool = False,
) -> RequiredChat:
    channel = await context.bot.get_chat(target)
    if channel.type not in (Chat.CHANNEL, Chat.SUPERGROUP):
        raise ValueError("Choose a channel or supergroup.")
    bot_member = await context.bot.get_chat_member(channel.id, context.bot.id)
    if bot_member.status not in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
        raise ValueError("Make this bot an admin in that chat, then retry.")
    can_invite = bot_member.status == ChatMemberStatus.OWNER or bot_member.can_invite_users
    if channel.username:
        join_url = f"https://t.me/{channel.username}"
    elif can_invite and (private_invite is None or refresh_private):
        invite = await context.bot.create_chat_invite_link(channel.id, name="dise-bot")
        join_url = invite.invite_link
    elif private_invite:
        join_url = private_invite
    else:
        raise ValueError(
            "Give this bot permission to invite users, or provide a private "
            "https://t.me/+... link after the channel ID."
        )
    return RequiredChat(channel.id, channel.title or str(channel.id), join_url)


async def join_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user, source = (
        update.effective_message,
        update.effective_user,
        update.effective_chat,
    )
    if message is None or user is None or source is None:
        return
    management: ManagementStore = context.application.bot_data["management_store"]
    if not management.is_owner(user.id):
        if source.type == Chat.PRIVATE:
            await message.reply_text("Only the owner can manage required membership.")
        return
    if source.type != Chat.PRIVATE:
        await message.reply_text("Use /join in a private chat with this bot.")
        return
    args = context.args or []
    store = join_store(context)
    if args == ["status"]:
        chat = store.configured_chat
        status = (
            f"Required membership is {'on' if store.enabled else 'off'}: "
            f"{chat.title} ({chat.chat_id})\nJoin link: {chat.join_url}"
            if chat
            else "Required membership is off. No channel is configured."
        )
        await message.reply_text(status)
        return
    if args == ["off"]:
        store.disable()
        membership_cache(context).clear()
        await message.reply_text("Required membership is off.")
        return
    if args == ["on"]:
        configured = store.configured_chat
        if configured is None:
            await message.reply_text("Set a channel first.\n" + JOIN_GUIDE)
            return
        try:
            required = await prepare_required_chat(
                context,
                configured.chat_id,
                configured.join_url,
                refresh_private=True,
            )
        except ValueError as error:
            await message.reply_text(str(error))
            return
        except TelegramError as error:
            logger.warning("Could not enable required membership (%s).", type(error).__name__)
            await message.reply_text("Could not verify the channel or link. Check bot permissions.")
            return
        if required == configured:
            store.enable()
        else:
            store.set_required_chat(required)
        membership_cache(context).clear()
        await message.reply_text(
            f"Required membership is on for {required.title} ({required.chat_id}).",
            reply_markup=join_keyboard(required),
        )
        return
    try:
        target, private_invite = parse_required_chat(args)
    except ValueError as error:
        await message.reply_text(str(error))
        return
    try:
        required = await prepare_required_chat(context, target, private_invite)
    except ValueError as error:
        await message.reply_text(str(error))
        return
    except TelegramError as error:
        logger.warning("Could not configure required membership (%s).", type(error).__name__)
        await message.reply_text(
            "Could not access that chat. Add this bot as an admin, then retry."
        )
        return
    store.set_required_chat(required)
    membership_cache(context).clear()
    await message.reply_text(
        f"Required membership is on for {required.title} ({required.chat_id}).",
        reply_markup=join_keyboard(required),
    )


async def join_panel_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None:
        return
    management: ManagementStore = context.application.bot_data["management_store"]
    if not management.is_owner(user.id):
        await message.reply_text("Only the owner can manage required membership.")
        return
    store = join_store(context)
    chat = store.configured_chat
    status = (
        f"\nCurrent: {'on' if store.enabled else 'off'} · {chat.title} ({chat.chat_id})"
        if chat
        else "\nCurrent: off"
    )
    await message.reply_text(JOIN_GUIDE + status)
