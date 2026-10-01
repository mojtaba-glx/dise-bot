"""Track known group members and mention them from a replied /tag command."""

import asyncio

from telegram import Chat, MessageEntity, Update, User
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from dise_bot.services.management import ManagementStore

MENTIONS_PER_MESSAGE = 3
SEND_DELAY_SECONDS = 1.0
SEPARATOR_TEXT = "⏳ ادامه تگ اعضا..."
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


def _mention_payload(batch: list[tuple[int, str]]) -> tuple[str, list[MessageEntity]]:
    prefix = "🔔 "
    parts: list[str] = []
    entities: list[MessageEntity] = []
    cursor = len(prefix)

    for index, (user_id, display_name) in enumerate(batch):
        if index:
            separator = " · "
            parts.append(separator)
            cursor += len(separator)
        label = display_name or str(user_id)
        parts.append(label)
        entities.append(
            MessageEntity(
                type=MessageEntity.TEXT_MENTION,
                offset=cursor,
                length=len(label),
                user=User(id=user_id, is_bot=False, first_name=label),
            )
        )
        cursor += len(label)

    text = prefix + "".join(parts)
    return text, list(MessageEntity.adjust_message_entities_to_utf_16(text, entities))


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
    batches = [
        members[offset : offset + MENTIONS_PER_MESSAGE]
        for offset in range(0, total, MENTIONS_PER_MESSAGE)
    ]

    for index, batch in enumerate(batches):
        text, entities = _mention_payload(batch)
        await target.reply_text(
            text,
            entities=entities,
            do_quote=True,
        )

        if index < len(batches) - 1:
            await asyncio.sleep(SEND_DELAY_SECONDS)
            await target.reply_text(SEPARATOR_TEXT, do_quote=True)
            await asyncio.sleep(SEND_DELAY_SECONDS)
