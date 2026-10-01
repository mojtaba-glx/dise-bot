"""Console logs with token redaction, including exception tracebacks."""

import logging

from dise_bot.config import Settings


class RedactingFormatter(logging.Formatter):
    def __init__(self, token: str) -> None:
        super().__init__("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        self._token = token

    def format(self, record: logging.LogRecord) -> str:
        return super().format(record).replace(self._token, "[REDACTED]")


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter(settings.token))
    logging.basicConfig(level=settings.log_level, handlers=[handler], force=True)
    # Request URLs include the bot token; debug payloads can include user messages.
    for name in ("httpx", "httpcore", "telegram"):
        logging.getLogger(name).setLevel(logging.WARNING)
