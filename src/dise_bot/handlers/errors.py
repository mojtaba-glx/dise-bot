import logging

from telegram import Update
from telegram.error import (
    Conflict,
    Forbidden,
    InvalidToken,
    NetworkError,
    RetryAfter,
    TelegramError,
)
from telegram.ext import ContextTypes

from dise_bot.messages import UNEXPECTED_ERROR

logger = logging.getLogger(__name__)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    if isinstance(error, (Conflict, InvalidToken)):
        logger.error(
            "Bot stopped: %s. Check BOT_TOKEN and ensure only one polling instance is running.",
            type(error).__name__,
        )
        context.application.stop_running()
        return

    if isinstance(error, (Forbidden, NetworkError, RetryAfter)):
        logger.warning(
            "Telegram request failed (%s); the roll will not be replayed.", type(error).__name__
        )
        return

    exception_info = (type(error), error, error.__traceback__) if error else None
    logger.error("Update handler failed.", exc_info=exception_info)
    # Do not serialize the Update: it contains user messages and identifying data.
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(UNEXPECTED_ERROR)
        except TelegramError:
            logger.warning("Could not deliver the error notice.")
