"""Persistent game and bilingual admin keyboards."""

from telegram import ReplyKeyboardMarkup

from dise_bot import admin_i18n, messages


def dice_keyboard(
    *,
    group_controls: bool = False,
    manager: bool = False,
    manager_language: str = "en",
) -> ReplyKeyboardMarkup:
    rows = [
        [messages.DEFENSE_BUTTON, messages.ABLITY_BUTTON],
        [messages.RED_BUTTON],
        [messages.GREEN_BUTTON],
    ]
    if manager and not group_controls:
        rows.append([admin_i18n.button(manager_language, "panel")])
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
        selective=group_controls,
        input_field_placeholder="Choose your dice…",
    )


def panel_keyboard(*, owner: bool, language: str = "en") -> ReplyKeyboardMarkup:
    rows = [
        [
            admin_i18n.button(language, "ban"),
            admin_i18n.button(language, "unban"),
        ],
    ]
    if owner:
        rows.append(
            [
                admin_i18n.button(language, "add_admin"),
                admin_i18n.button(language, "remove_admin"),
            ]
        )
    rows.extend(
        [
            [admin_i18n.button(language, "force_join")],
            [admin_i18n.button(language, "auto_replies")],
            [admin_i18n.button(language, "settings")],
            [admin_i18n.button(language, "back")],
        ]
    )
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def admin_settings_keyboard(*, language: str) -> ReplyKeyboardMarkup:
    rows = [
        [
            admin_i18n.LANGUAGE_BUTTONS[admin_i18n.LANG_FA],
            admin_i18n.LANGUAGE_BUTTONS[admin_i18n.LANG_EN],
        ],
        [admin_i18n.button(language, "back")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def force_join_keyboard(*, language: str, enabled: bool) -> ReplyKeyboardMarkup:
    rows = [
        [
            admin_i18n.button(language, "join_on"),
            admin_i18n.button(language, "join_off"),
        ],
        [
            admin_i18n.button(language, "join_add"),
            admin_i18n.button(language, "join_remove"),
        ],
        [admin_i18n.button(language, "join_list")],
        [admin_i18n.button(language, "back")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def ablity_keyboard(*, group_controls: bool = False) -> ReplyKeyboardMarkup:
    rows = [[messages.BACK_BUTTON]]
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
        selective=group_controls,
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
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        is_persistent=True,
        selective=group_controls,
        input_field_placeholder="Choose your defense…",
    )
