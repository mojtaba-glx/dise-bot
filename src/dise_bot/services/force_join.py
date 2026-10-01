"""Persist multiple chats required for using the bot."""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RequiredChat:
    chat_id: int
    title: str
    join_url: str


class ForceJoinStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path, timeout=5)) as connection:
            with connection:
                # Legacy single-channel table is kept for backward-compatible migration.
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS force_join ("
                    "singleton INTEGER PRIMARY KEY CHECK (singleton = 1), "
                    "chat_id INTEGER NOT NULL, title TEXT NOT NULL, join_url TEXT NOT NULL, "
                    "enabled INTEGER NOT NULL DEFAULT 1)"
                )
                columns = {row[1] for row in connection.execute("PRAGMA table_info(force_join)")}
                if "enabled" not in columns:
                    connection.execute(
                        "ALTER TABLE force_join ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1"
                    )

                connection.execute(
                    "CREATE TABLE IF NOT EXISTS force_join_channels ("
                    "chat_id INTEGER PRIMARY KEY, title TEXT NOT NULL, join_url TEXT NOT NULL)"
                )
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS force_join_settings ("
                    "singleton INTEGER PRIMARY KEY CHECK (singleton = 1), "
                    "enabled INTEGER NOT NULL DEFAULT 0)"
                )

                legacy = connection.execute(
                    "SELECT chat_id, title, join_url, enabled "
                    "FROM force_join WHERE singleton = 1"
                ).fetchone()
                if legacy is not None:
                    connection.execute(
                        "INSERT OR IGNORE INTO force_join_channels "
                        "(chat_id, title, join_url) VALUES (?, ?, ?)",
                        legacy[:3],
                    )
                    connection.execute(
                        "INSERT OR IGNORE INTO force_join_settings (singleton, enabled) "
                        "VALUES (1, ?)",
                        (legacy[3],),
                    )
                    # The legacy row must not resurrect a channel removed later.
                    connection.execute("DELETE FROM force_join WHERE singleton = 1")
                else:
                    connection.execute(
                        "INSERT OR IGNORE INTO force_join_settings (singleton, enabled) "
                        "VALUES (1, 0)"
                    )

            rows = connection.execute(
                "SELECT chat_id, title, join_url FROM force_join_channels ORDER BY chat_id"
            ).fetchall()
            setting = connection.execute(
                "SELECT enabled FROM force_join_settings WHERE singleton = 1"
            ).fetchone()

        self.configured_chats = [RequiredChat(*row) for row in rows]
        self.enabled = bool(setting[0]) if setting else False

    @property
    def required_chats(self) -> list[RequiredChat]:
        return list(self.configured_chats) if self.enabled else []

    # Backward-compatible accessors used by older callers/tests.
    @property
    def configured_chat(self) -> RequiredChat | None:
        return self.configured_chats[0] if self.configured_chats else None

    @property
    def required_chat(self) -> RequiredChat | None:
        chats = self.required_chats
        return chats[0] if chats else None

    def add_chat(self, chat: RequiredChat, *, enable: bool = True) -> None:
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            connection.execute(
                "INSERT INTO force_join_channels (chat_id, title, join_url) "
                "VALUES (?, ?, ?) ON CONFLICT(chat_id) DO UPDATE SET "
                "title = excluded.title, join_url = excluded.join_url",
                (chat.chat_id, chat.title, chat.join_url),
            )
            if enable:
                connection.execute(
                    "UPDATE force_join_settings SET enabled = 1 WHERE singleton = 1"
                )
        by_id = {item.chat_id: item for item in self.configured_chats}
        by_id[chat.chat_id] = chat
        self.configured_chats = sorted(by_id.values(), key=lambda item: item.chat_id)
        if enable:
            self.enabled = True

    def set_required_chat(self, chat: RequiredChat) -> None:
        self.add_chat(chat, enable=True)

    def update_chat(self, chat: RequiredChat) -> None:
        self.add_chat(chat, enable=False)

    def remove_chat(self, chat_id: int) -> bool:
        exists = any(item.chat_id == chat_id for item in self.configured_chats)
        if not exists:
            return False
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            connection.execute("DELETE FROM force_join_channels WHERE chat_id = ?", (chat_id,))
        self.configured_chats = [
            item for item in self.configured_chats if item.chat_id != chat_id
        ]
        if not self.configured_chats:
            self.disable()
        return True

    def enable(self) -> None:
        if not self.configured_chats:
            raise ValueError("Set at least one channel before enabling required membership.")
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            connection.execute(
                "UPDATE force_join_settings SET enabled = 1 WHERE singleton = 1"
            )
        self.enabled = True

    def disable(self) -> None:
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            connection.execute(
                "UPDATE force_join_settings SET enabled = 0 WHERE singleton = 1"
            )
        self.enabled = False
