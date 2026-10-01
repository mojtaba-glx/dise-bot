"""Load and validate configuration without exposing credentials."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


class ConfigurationError(ValueError):
    """An actionable, safe-to-display configuration error."""


@dataclass(frozen=True, slots=True)
class Settings:
    token: str = field(repr=False)
    log_level: str = "INFO"
    state_db_path: Path = Path("data/activation.sqlite3")
    owner_user_id: int | None = None
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = field(default=None, repr=False)


def load_settings(env_file: Path = Path(".env")) -> Settings:
    # Real environment variables always take precedence over the file.
    values = {**dotenv_values(env_file, interpolate=False), **os.environ}
    token = (values.get("BOT_TOKEN") or "").strip()
    if not token:
        raise ConfigurationError("Set BOT_TOKEN in .env or in your environment before starting.")
    if not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token):
        raise ConfigurationError("BOT_TOKEN has an invalid format. Copy the token from @BotFather.")

    log_level = (values.get("LOG_LEVEL") or "INFO").strip().upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigurationError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL.")

    state_db_path = Path(values.get("STATE_DB_PATH") or "data/activation.sqlite3").expanduser()
    if state_db_path.exists() and state_db_path.is_dir():
        raise ConfigurationError("STATE_DB_PATH must point to a file, not a directory.")

    raw_owner = (values.get("OWNER_USER_ID") or "").strip()
    if raw_owner and (not raw_owner.isascii() or not raw_owner.isdecimal()):
        raise ConfigurationError("OWNER_USER_ID must be a positive numeric Telegram user ID.")
    owner_user_id = int(raw_owner) if raw_owner else None
    if owner_user_id is not None and not 0 < owner_user_id < 2**63:
        raise ConfigurationError("OWNER_USER_ID must be a positive numeric Telegram user ID.")

    raw_api_id = (values.get("TELEGRAM_API_ID") or "").strip()
    api_hash = (values.get("TELEGRAM_API_HASH") or "").strip() or None
    if raw_api_id and (not raw_api_id.isascii() or not raw_api_id.isdecimal()):
        raise ConfigurationError("TELEGRAM_API_ID must be a positive numeric value.")
    telegram_api_id = int(raw_api_id) if raw_api_id else None
    if (telegram_api_id is None) != (api_hash is None):
        raise ConfigurationError(
            "Set TELEGRAM_API_ID and TELEGRAM_API_HASH together for full /tag member sync."
        )

    return Settings(
        token=token,
        log_level=log_level,
        state_db_path=state_db_path,
        owner_user_id=owner_user_id,
        telegram_api_id=telegram_api_id,
        telegram_api_hash=api_hash,
    )
