"""Persist the optional chat that users must join before using the bot."""

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
            row = connection.execute(
                "SELECT chat_id, title, join_url, enabled FROM force_join WHERE singleton = 1"
            ).fetchone()
        self.configured_chat = RequiredChat(*row[:3]) if row else None
        self.enabled = bool(row[3]) if row else False

    @property
    def required_chat(self) -> RequiredChat | None:
        return self.configured_chat if self.enabled else None

    def set_required_chat(self, chat: RequiredChat) -> None:
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            connection.execute(
                "INSERT INTO force_join (singleton, chat_id, title, join_url, enabled) "
                "VALUES (1, ?, ?, ?, 1) ON CONFLICT(singleton) DO UPDATE SET "
                "chat_id = excluded.chat_id, title = excluded.title, "
                "join_url = excluded.join_url, enabled = 1",
                (chat.chat_id, chat.title, chat.join_url),
            )
        self.configured_chat = chat
        self.enabled = True

    def enable(self) -> None:
        if self.configured_chat is None:
            raise ValueError("Set a channel before enabling required membership.")
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            connection.execute("UPDATE force_join SET enabled = 1 WHERE singleton = 1")
        self.enabled = True

    def disable(self) -> None:
        with closing(sqlite3.connect(self._path, timeout=5)) as connection, connection:
            connection.execute("UPDATE force_join SET enabled = 0 WHERE singleton = 1")
        self.enabled = False
