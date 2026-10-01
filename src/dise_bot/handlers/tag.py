"""Fetch all current group members over MTProto and mention them from /tag."""

import asyncio
import logging

from telegram import Chat, MessageEntity, Update, User
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from dise_bot.config import Settings
from dise_bot.services.management import ManagementStore

MENTIONS_PER_MESSAGE = 3
SEND_DELAY_SECONDS = 1.0
SEPARATOR_TEXT = "⏳ ادامه تگ اعضا..."
MTProto_SETUP_MESSAGE = (
    "Full /tag sync needs TELEGRAM_API_ID and TELEGRAM_API_HASH in .env. "
    "Get them from my.telegram.org, add both values, then restart the bot."
)
ACTIVE_STATUSES = {
    ChatMemberStatus.OWNER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.MEMBER,
}

logger = logging.getLogger(__name__)


def member_store(context: ContextTypes.DEFAULT_TYPE) -> ManagementStore:
    return context.application.bot_data["management_store"]


def bot_settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.application.bot_data["settings"]


def _display_name(user) -> str:
    name = " ".join(part for part in (user.first_name, user.last_name) if part).strip()
    return name or user.username or str(user.id)


def _remember_user(store: ManagementStore, chat_id: int, user, *, active: bool = True) -> None:
    if user is None or user.is_bot:
        return
    store.remember_group_member(chat_id, user.id, _display_name(user), active=active)


async def remember_group_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Keep the local registry useful between full MTProto syncs."""
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


async def fetch_all_members_mtproto(
    context: ContextTypes.DEFAULT_TYPE, chat_id: int
) -> list[tuple[int, str]] | None:
    """Return every current non-bot member, or None when MTProto is not configured."""
    settings = bot_settings(context)
    if settings.telegram_api_id is None or settings.telegram_api_hash is None:
        return None

    try:
        from telethon import TelegramClient, functions, types, utils
        from telethon.sessions import MemorySession
    except ImportError:
        logger.error("Telethon is not installed; full /tag sync is unavailable.")
        return None

    def member_tuple(member) -> tuple[int, str] | None:
        if getattr(member, "bot", False) or getattr(member, "deleted", False):
            return None
        name = " ".join(
            part
            for part in (
                getattr(member, "first_name", None),
                getattr(member, "last_name", None),
            )
            if part
        ).strip()
        name = name or getattr(member, "username", None) or str(member.id)
        return member.id, name

    client = TelegramClient(
        MemorySession(),
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )
    try:
        await client.start(bot_token=settings.token)
        real_id, peer_type = utils.resolve_id(chat_id)
        found: dict[int, str] = {}

        if peer_type is types.PeerChannel:
            channel = types.InputChannel(real_id, 0)
            offset = 0
            limit = 200
            while True:
                result = await client(
                    functions.channels.GetParticipantsRequest(
                        channel=channel,
                        filter=types.ChannelParticipantsRecent(),
                        offset=offset,
                        limit=limit,
                        hash=0,
                    )
                )
                for member in result.users:
                    item = member_tuple(member)
                    if item is not None:
                        found[item[0]] = item[1]
                received = len(result.participants)
                offset += received
                if received == 0 or offset >= result.count:
                    break

        elif peer_type is types.PeerChat:
            result = await client(functions.messages.GetFullChatRequest(chat_id=real_id))
            users = {user.id: user for user in result.users}
            participants = getattr(result.full_chat, "participants", None)
            participant_rows = getattr(participants, "participants", [])
            for participant in participant_rows:
                member = users.get(participant.user_id)
                if member is None:
                    continue
                item = member_tuple(member)
                if item is not None:
                    found[item[0]] = item[1]
        else:
            raise RuntimeError("Unsupported Telegram chat type for full member sync.")

        return sorted(found.items())
    except Exception as error:
        logger.warning("Full MTProto member sync failed (%s).", type(error).__name__)
        raise RuntimeError("Could not load the full member list from Telegram.") from None
    finally:
        await client.disconnect()


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

    try:
        members = await fetch_all_members_mtproto(context, chat.id)
    except RuntimeError as error:
        await message.reply_text(str(error))
        return
    if members is None:
        await message.reply_text(MTProto_SETUP_MESSAGE)
        return
    if not members:
        await message.reply_text("Telegram returned no current group members to tag.")
        return

    for user_id, display_name in members:
        store.remember_group_member(chat.id, user_id, display_name, active=True)

    target = message.reply_to_message
    batches = [
        members[offset : offset + MENTIONS_PER_MESSAGE]
        for offset in range(0, len(members), MENTIONS_PER_MESSAGE)
    ]
    for index, batch in enumerate(batches):
        text, entities = _mention_payload(batch)
        await target.reply_text(text, entities=entities, do_quote=True)

        if index < len(batches) - 1:
            await asyncio.sleep(SEND_DELAY_SECONDS)
            await target.reply_text(SEPARATOR_TEXT, do_quote=True)
            await asyncio.sleep(SEND_DELAY_SECONDS)
