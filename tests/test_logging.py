import logging
import sys

from dise_bot.logging_config import RedactingFormatter


def test_token_is_redacted_from_formatted_message_and_traceback():
    token = "123456:OFFLINE_SECRET"
    try:
        raise RuntimeError(f"Request failed: https://api.telegram.org/bot{token}/sendMessage")
    except RuntimeError:
        record = logging.LogRecord(
            "test", logging.ERROR, __file__, 1, "Token: %s", (token,), sys.exc_info()
        )
    formatted = RedactingFormatter(token).format(record)
    assert token not in formatted
    assert "[REDACTED]" in formatted
    assert "RuntimeError" in formatted
