"""Application assembly and the command-line entry point."""

import argparse
import logging
import re
import sqlite3
import sys
from pathlib import Path

from telegram import BotCommand, Update
from telegram.error import Conflict, InvalidToken, TelegramError
from telegram.ext import (
    AIORateLimiter,
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from dise_bot import admin_i18n
from dise_bot.config import ConfigurationError, Settings, load_settings
from dise_bot.handlers.absolute import absolute_button
from dise_bot.handlers.activation import off_command, on_command
from dise_bot.handlers.aura import aura_button
from dise_bot.handlers.commands import (
    help_command,
    show_ablity,
    start,
    status_command,
    unknown_message,
    version_command,
)
from dise_bot.handlers.defense import (
    TIER_BUTTONS,
    defense_button,
    defense_command,
    show_defense,
)
from dise_bot.handlers.dice import dice_button, green_command, red_command
from dise_bot.handlers.errors import on_error
from dise_bot.handlers.force_join import (
    CHECK_CALLBACK,
    check_membership,
    force_join_gate,
    join_command,
    join_panel_button,
)
from dise_bot.handlers.management import (
    admin_command,
    auto_reply,
    ban_command,
    ban_gate,
    id_command,
    panel_button,
    panel_command,
    reply_command,
    unadmin_command,
    unban_command,
)
from dise_bot.handlers.reflect import reflect_button
from dise_bot.handlers.tag import remember_group_members, tag_command
from dise_bot.logging_config import configure_logging
from dise_bot.messages import (
    ABLITY_BUTTON,
    ABSOLUTE_BUTTON,
    BACK_BUTTON,
    CURSED_AURA_BUTTON,
    DEFENSE_BUTTON,
    GREEN_BUTTON,
    RED_BUTTON,
    REFLECT_BUTTON,
)
from dise_bot.services.activation import ActivationStore
from dise_bot.services.force_join import ForceJoinStore
from dise_bot.services.management import ManagementStore

logger = logging.getLogger(__name__)


async def set_commands(application: Application) -> None:
    try:
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Open the dice menu"),
                BotCommand("red", "Roll the red dice"),
                BotCommand("green", "Roll the green dice"),
                BotCommand("defense", "Open the defense menu"),
                BotCommand("on", "Enable your dice in this group"),
                BotCommand("off", "Disable your dice in this group"),
                BotCommand("status", "Show your dice status"),
                BotCommand("version", "Show the running bot version"),
                BotCommand("help", "Rules and dice odds"),
                BotCommand("id", "Show your Telegram user ID"),
                BotCommand("panel", "Open the bot management panel"),
                BotCommand("reply", "Manage group auto replies"),
                BotCommand("join", "Manage required membership channels"),
                BotCommand("tag", "Mention all group members on a replied message"),
            ]
        )
    except TelegramError as error:
        # A failed menu refresh should not prevent the bot from accepting commands.
        logger.warning("Could not refresh the command menu (%s).", type(error).__name__)
    logger.info("ᎠᏆᏟᎬ is connected. Starting polling.")


def build_application(settings: Settings) -> Application:
    application = (
        Application.builder()
        .token(settings.token)
        .concurrent_updates(32)
        .connection_pool_size(64)
        .rate_limiter(AIORateLimiter(max_retries=1))
        .post_init(set_commands)
        .build()
    )
    application.bot_data["settings"] = settings
    application.bot_data["activation_store"] = ActivationStore(settings.state_db_path)
    application.bot_data["management_store"] = ManagementStore(
        settings.state_db_path, settings.owner_user_id
    )
    application.bot_data["force_join_store"] = ForceJoinStore(settings.state_db_path)
    application.bot_data["membership_cache"] = {}
    application.add_handler(TypeHandler(Update, remember_group_members), group=-3)
    application.add_handler(TypeHandler(Update, ban_gate), group=-2)
    application.add_handler(TypeHandler(Update, force_join_gate), group=-1)
    application.add_handler(CallbackQueryHandler(check_membership, pattern=CHECK_CALLBACK))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("on", on_command))
    application.add_handler(CommandHandler("off", off_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("version", version_command))
    # A reply-keyboard client may send the slash label without a command entity.
    application.add_handler(
        MessageHandler(filters.Regex(r"\A/on\Z") & ~filters.COMMAND, on_command)
    )
    application.add_handler(
        MessageHandler(filters.Regex(r"\A/off\Z") & ~filters.COMMAND, off_command)
    )
    application.add_handler(CommandHandler("red", red_command))
    application.add_handler(CommandHandler("green", green_command))
    application.add_handler(CommandHandler("defense", defense_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("panel", panel_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("unadmin", unadmin_command))
    application.add_handler(CommandHandler("reply", reply_command))
    application.add_handler(CommandHandler("join", join_command))
    application.add_handler(CommandHandler("tag", tag_command))
    panel_keys = {
        "panel",
        "ban",
        "unban",
        "add_admin",
        "remove_admin",
        "auto_replies",
        "settings",
        "language",
        "back",
    }
    panel_labels = {
        label
        for key in panel_keys
        for label in admin_i18n.button_labels(key)
    } | set(admin_i18n.LANGUAGE_BUTTONS.values())
    panel_pattern = (
        r"\A(?:" + "|".join(re.escape(label) for label in sorted(panel_labels)) + r")\Z"
    )
    application.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.Regex(panel_pattern), panel_button)
    )

    force_join_keys = {
        "force_join",
        "join_on",
        "join_off",
        "join_add",
        "join_remove",
        "join_list",
    }
    force_join_labels = {
        label
        for key in force_join_keys
        for label in admin_i18n.button_labels(key)
    }
    force_join_pattern = (
        r"\A(?:" + "|".join(re.escape(label) for label in sorted(force_join_labels)) + r")\Z"
    )
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.Regex(force_join_pattern),
            join_panel_button,
        )
    )

    dice_pattern = rf"\A(?:{re.escape(RED_BUTTON)}|{re.escape(GREEN_BUTTON)})\Z"
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(dice_pattern), dice_button)
    )
    application.add_handler(
        MessageHandler(filters.Regex(rf"\A{re.escape(DEFENSE_BUTTON)}\Z"), show_defense)
    )
    application.add_handler(
        MessageHandler(filters.Regex(rf"\A{re.escape(ABLITY_BUTTON)}\Z"), show_ablity)
    )
    application.add_handler(
        MessageHandler(filters.Regex(rf"\A{re.escape(ABSOLUTE_BUTTON)}\Z"), absolute_button)
    )
    application.add_handler(
        MessageHandler(filters.Regex(rf"\A{re.escape(CURSED_AURA_BUTTON)}\Z"), aura_button)
    )
    application.add_handler(
        MessageHandler(filters.Regex(rf"\A{re.escape(REFLECT_BUTTON)}\Z"), reflect_button)
    )
    application.add_handler(MessageHandler(filters.Regex(rf"\A{re.escape(BACK_BUTTON)}\Z"), start))
    tier_pattern = r"\A(?:" + "|".join(re.escape(label) for label in TIER_BUTTONS) + r")\Z"
    application.add_handler(MessageHandler(filters.Regex(tier_pattern), defense_button))
    application.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, auto_reply)
    )
    # Stay quiet for unrelated group messages and unsupported commands.
    application.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, unknown_message)
    )
    application.add_error_handler(on_error)
    return application


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ᎠᏆᏟᎬ Telegram bot.")
    parser.add_argument(
        "--env-file", type=Path, default=Path(".env"), help="Configuration file path"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check configuration without connecting"
    )
    args = parser.parse_args(argv)

    try:
        settings = load_settings(args.env_file)
    except (ConfigurationError, OSError) as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2

    if args.check:
        print("Configuration is valid. Token format checked; Telegram connection not tested.")
        return 0

    configure_logging(settings)
    try:
        application = build_application(settings)
    except (OSError, sqlite3.Error):
        logger.error("Could not open STATE_DB_PATH. Check that its directory is writable.")
        return 2
    logger.info("Starting dise bot with concurrent updates and no per-user cooldown.")
    try:
        application.run_polling(
            allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY, Update.CHAT_MEMBER],
            drop_pending_updates=True,
            bootstrap_retries=3,
            timeout=30,
        )
    except InvalidToken:
        logger.error("Telegram rejected BOT_TOKEN. Copy a valid token from @BotFather.")
        return 1
    except Conflict:
        logger.error("Another instance is using this bot token. Run only one polling instance.")
        return 1
    except TelegramError:
        logger.exception("Could not run the bot. Check your network connection and configuration.")
        return 1
    logger.info("Bot stopped.")
    return 0
