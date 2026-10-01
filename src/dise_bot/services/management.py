"""Persistent moderation roles, bans, and group-specific text replies."""

import re
import sqlite3
import unicodedata
from contextlib import closing
from pathlib import Path


def normalize_trigger(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"\s+", " ", normalized).strip().casefold()


class ManagementStore:
    def __init__(self, path: Path, owner_user_id: int | None) -> None:
        self._path = path
        self.owner_user_id = owner_user_id
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path, timeout=5)) as connection:
            with connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS bot_admins (user_id INTEGER PRIMARY KEY)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS auto_replies ("
                    "chat_id INTEGER NOT NULL, trigger TEXT NOT NULL, "
                    "response TEXT NOT NULL, PRIMARY KEY (chat_id, trigger))"
                )
            self._banned = {
                row[0] for row in connection.execute("SELECT user_id FROM banned_users")
            }
            self._admins = {row[0] for row in connection.execute("SELECT user_id FROM bot_admins")}
            self._replies = {
                (chat_id, trigger): response
                for chat_id, trigger, response in connection.execute(
                    "SELECT chat_id, trigger, response FROM auto_replies"
                )
            }

    def is_owner(self, user_id: int) -> bool:
        return self.owner_user_id is not None and user_id == self.owner_user_id

    def is_admin(self, user_id: int) -> bool:
        return (
            self.owner_user_id is not None
            and user_id in self._admins
            and not self.is_banned(user_id)
        )

    def is_manager(self, user_id: int) -> bool:
        return self.is_owner(user_id) or self.is_admin(user_id)

    def is_banned(self, user_id: int) -> bool:
        return user_id in self._banned and not self.is_owner(user_id)

    def set_admin(self, user_id: int, *, enabled: bool) -> None:
        if self.is_owner(user_id):
            raise ValueError("The owner already has full access.")
        if enabled and self.is_banned(user_id):
            raise ValueError("Unban this user before making them an admin.")
        self._set_user_row("bot_admins", user_id, enabled=enabled)
        if enabled:
            self._admins.add(user_id)
        else:
            self._admins.discard(user_id)

    def set_banned(self, user_id: int, *, enabled: bool) -> None:
        if self.is_owner(user_id):
            raise ValueError("The owner cannot be banned.")
        if enabled and user_id in self._admins:
            raise ValueError("Remove the admin role before banning this user.")
        self._set_user_row("banned_users", user_id, enabled=enabled)
        if enabled:
            self._banned.add(user_id)
        else:
            self._banned.discard(user_id)

    def _set_user_row(self, table: str, user_id: int, *, enabled: bool) -> None:
        if not 0 < user_id < 2**63:
            raise ValueError("Use a positive numeric Telegram user ID.")
        # The table name is selected only by methods above, never by user input.
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            if enabled:
                connection.execute(
                    f"INSERT OR IGNORE INTO {table} (user_id) VALUES (?)", (user_id,)
                )
            else:
                connection.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))

    def add_reply(self, chat_id: int, trigger: str, response: str) -> None:
        key = normalize_trigger(trigger)
        response = response.strip()
        if not 1 <= len(key) <= 80 or key.startswith("/"):
            raise ValueError("The trigger must be plain text of 1–80 characters.")
        if not 1 <= len(response) <= 2000:
            raise ValueError("The response must contain 1–2000 characters.")
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            connection.execute(
                "INSERT INTO auto_replies (chat_id, trigger, response) VALUES (?, ?, ?) "
                "ON CONFLICT(chat_id, trigger) DO UPDATE SET response = excluded.response",
                (chat_id, key, response),
            )
        self._replies[(chat_id, key)] = response

    def remove_reply(self, chat_id: int, trigger: str) -> bool:
        key = (chat_id, normalize_trigger(trigger))
        if key not in self._replies:
            return False
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            connection.execute("DELETE FROM auto_replies WHERE chat_id = ? AND trigger = ?", key)
        del self._replies[key]
        return True

    def replies_for_chat(self, chat_id: int) -> list[str]:
        return sorted(trigger for group_id, trigger in self._replies if group_id == chat_id)

    def response_for(self, chat_id: int, text: str) -> str | None:
        return self._replies.get((chat_id, normalize_trigger(text)))
