"""Track known group members and mention them from a replied /tag command."""

from html import escape

from telegram import Chat, Update
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.ext import ContextTypes

from dise_bot.services.management import ManagementStore

MAX_MENTIONS_PER_MESSAGE = 30
ACTIVE_STATUSES = {
    ChatMemberStatus.OWNER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.MEMBER,
}


def member_store(context: ContextTypes.DEFAULT_TYPE) -> ManagementStore:
    return context.application.bot_data["management_store"]


def _display_name(user) -> str:
    name = " ".join(part for part in (user.first_name, user.last_name) if part).strip()
    return name or user.username or str(user.id)


def _remember_user(store: ManagementStore, chat_id: int, user, *, active: bool = True) -> None:
    if user is None or user.is_bot:
        return
    store.remember_group_member(chat_id, user.id, _display_name(user), active=active)


async def remember_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remember members the bot sees and maintain join/leave state for future /tag calls."""
    chat = update.effective_chat
    if chat is None or chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        return

    store = member_store(context)
    message = update.effective_message
    if message is not None:
        _remember_user(store, chat.id, message.from_user)
        if message.reply_to_message is not None:
            _remember_user(store, chat.id, message.reply_to_message.from_user)
        for user in message.new_chat_members:
            _remember_user(store, chat.id, user)
        if message.left_chat_member is not None:
            _remember_user(store, chat.id, message.left_chat_member, active=False)

    change = update.chat_member
    if change is not None:
        member = change.new_chat_member
        active = member.status in ACTIVE_STATUSES or (
            member.status == ChatMemberStatus.RESTRICTED and getattr(member, "is_member", False)
        )
        _remember_user(store, chat.id, member.user, active=active)


def _mention(user_id: int, display_name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{escape(display_name)}</a>'


async def tag_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, actor, chat = (
        update.effective_message,
        update.effective_user,
        update.effective_chat,
    )
    if message is None or actor is None or chat is None or actor.is_bot:
        return

    store = member_store(context)
    if chat.type not in (Chat.GROUP, Chat.SUPERGROUP):
        await message.reply_text("Use /tag inside a group.")
        return
    if not store.is_manager(actor.id):
        return
    if message.reply_to_message is None:
        await message.reply_text("Reply to a message, then send /tag.")
        return

    members = store.group_members(chat.id)
    if not members:
        await message.reply_text("No known group members are available to tag yet.")
        return

    target = message.reply_to_message
    total = len(members)
    for offset in range(0, total, MAX_MENTIONS_PER_MESSAGE):
        batch = members[offset : offset + MAX_MENTIONS_PER_MESSAGE]
        mentions = " ".join(_mention(user_id, name) for user_id, name in batch)
        part = offset // MAX_MENTIONS_PER_MESSAGE + 1
        parts = (total + MAX_MENTIONS_PER_MESSAGE - 1) // MAX_MENTIONS_PER_MESSAGE
        header = f"🔔 Members ({part}/{parts})\n" if parts > 1 else "🔔 Members\n"
        await target.reply_text(
            header + mentions,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
