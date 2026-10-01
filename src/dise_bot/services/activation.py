"""Persistent per-user, per-group activation state."""

import sqlite3
from contextlib import closing
from pathlib import Path

from telegram import Chat, Update
from telegram.ext import ContextTypes


class ActivationStore:
    """Keep group choices across restarts while making roll checks inexpensive."""

    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path, timeout=5)) as connection:
            with connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS enabled_users ("
                    "chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, "
                    "PRIMARY KEY (chat_id, user_id))"
                )
            self._enabled = set(
                connection.execute("SELECT chat_id, user_id FROM enabled_users").fetchall()
            )

    def is_enabled(self, chat_id: int, user_id: int) -> bool:
        return (chat_id, user_id) in self._enabled

    def set_enabled(self, chat_id: int, user_id: int, *, enabled: bool) -> None:
        key = (chat_id, user_id)
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            if enabled:
                connection.execute(
                    "INSERT OR IGNORE INTO enabled_users (chat_id, user_id) VALUES (?, ?)",
                    key,
                )
            else:
                connection.execute(
                    "DELETE FROM enabled_users WHERE chat_id = ? AND user_id = ?", key
                )
        if enabled:
            self._enabled.add(key)
        else:
            self._enabled.discard(key)


def is_group(update: Update) -> bool:
    chat = update.effective_chat
    return chat is not None and chat.type in (Chat.GROUP, Chat.SUPERGROUP)


def can_roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Private chats retain their existing behavior; group rolls need /on."""
    if not is_group(update):
        return True
    chat, user = update.effective_chat, update.effective_user
    if chat is None or user is None or user.is_bot:
        return False
    store: ActivationStore = context.application.bot_data["activation_store"]
    return store.is_enabled(chat.id, user.id)
