"""Persistent dice and defense menus with the original style of lettering."""

from telegram import ReplyKeyboardMarkup

from dise_bot import messages


def dice_keyboard(*, group_controls: bool = False, manager: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [messages.DEFENSE_BUTTON, messages.ABLITY_BUTTON],
        [messages.RED_BUTTON],
        [messages.GREEN_BUTTON],
    ]
    if group_controls:
        rows.append(["/on", "/off"])
    if manager and not group_controls:
        rows.append([messages.PANEL_BUTTON])
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose your dice…",
    )


def panel_keyboard(*, owner: bool) -> ReplyKeyboardMarkup:
    rows = [
        [messages.BAN_BUTTON, messages.UNBAN_BUTTON],
    ]
    if owner:
        rows.append([messages.ADD_ADMIN_BUTTON, messages.REMOVE_ADMIN_BUTTON])
        rows.append([messages.FORCE_JOIN_BUTTON])
    rows.extend([[messages.AUTO_REPLIES_BUTTON], [messages.BACK_BUTTON]])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def ablity_keyboard(*, group_controls: bool = False) -> ReplyKeyboardMarkup:
    rows = [[messages.BACK_BUTTON]]
    if group_controls:
        rows.append(["/on", "/off"])
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="ABLITY",
    )


def defense_keyboard(*, group_controls: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [messages.CURSED_AURA_BUTTON],
        [messages.LIGHT_BUTTON, messages.HEAVY_BUTTON],
        [messages.SUPER_BUTTON, messages.GOD_BUTTON],
        [messages.GOLD_BUTTON, messages.ABSOLUTE_BUTTON],
        [messages.REFLECT_BUTTON],
        [messages.BACK_BUTTON],
    ]
    if group_controls:
        rows.append(["/on", "/off"])
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose your defense…",
    )
