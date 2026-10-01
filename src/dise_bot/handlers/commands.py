from telegram import Update
from telegram.ext import ContextTypes

from dise_bot import messages
from dise_bot.handlers.management import manager_store, pending_panel_input
from dise_bot.keyboards import ablity_keyboard, dice_keyboard
from dise_bot.services.activation import is_group


def main_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    return dice_keyboard(
        group_controls=is_group(update),
        manager=bool(user and manager_store(context).is_manager(user.id)),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        context.user_data.pop("pending_panel_action", None)
        await update.effective_message.reply_text(
            messages.GROUP_WELCOME if is_group(update) else messages.WELCOME,
            reply_markup=main_keyboard(update, context),
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(
            messages.HELP, reply_markup=main_keyboard(update, context)
        )


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
