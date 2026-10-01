from telegram import Update
from telegram.ext import ContextTypes

from dise_bot import __version__, messages
from dise_bot.handlers.management import manager_store, pending_panel_input
from dise_bot.keyboards import ablity_keyboard, dice_keyboard
from dise_bot.services.activation import ActivationStore, is_group


def main_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    return dice_keyboard(
        group_controls=is_group(update),
        manager=bool(user and manager_store(context).is_manager(user.id)),
    )


def activation_status_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    if not is_group(update):
        return messages.PRIVATE_STATUS_MESSAGE
    chat, user = update.effective_chat, update.effective_user
    if chat is None or user is None or user.is_bot:
        return messages.STATUS_OFF_MESSAGE
    store: ActivationStore = context.application.bot_data["activation_store"]
    return (
        messages.STATUS_ON_MESSAGE
        if store.is_enabled(chat.id, user.id)
        else messages.STATUS_OFF_MESSAGE
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        context.user_data.pop("pending_panel_action", None)
        text = messages.WELCOME
        if is_group(update):
            text = f"{messages.GROUP_WELCOME}\n\n{activation_status_text(update, context)}"
        await update.effective_message.reply_text(
            text,
            reply_markup=main_keyboard(update, context),
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            messages.HELP, reply_markup=main_keyboard(update, context)
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            activation_status_text(update, context),
            reply_markup=main_keyboard(update, context),
        )


async def version_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(f"🎲 ᎠᏆᏟᎬ Bot v{__version__}")


async def show_ablity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            messages.ABLITY_MENU,
            reply_markup=ablity_keyboard(group_controls=is_group(update)),
        )


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        if await pending_panel_input(update, context):
            return
        await update.effective_message.reply_text(
            messages.UNKNOWN_MESSAGE, reply_markup=main_keyboard(update, context)
        )
