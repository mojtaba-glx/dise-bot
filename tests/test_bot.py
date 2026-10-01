"""Exercise actual PTB routing with an in-memory Telegram HTTP transport."""

import asyncio
import json
import sqlite3
from dataclasses import dataclass, field
from unittest.mock import Mock, patch

import pytest
from telegram import Update
from telegram.error import Conflict, Forbidden, NetworkError
from telegram.request import HTTPXRequest

from dise_bot import admin_i18n, messages
from dise_bot.app import build_application, set_commands
from dise_bot.config import Settings
from dise_bot.services.activation import ActivationStore
from dise_bot.services.dice import DiceColor
from dise_bot.services.force_join import ForceJoinStore, RequiredChat
from dise_bot.services.management import ManagementStore

BOT_USER = {"id": 123456789, "is_bot": True, "first_name": "Dise", "username": "DiseTestBot"}
TOKEN = "123456789:TEST_TOKEN_FOR_OFFLINE_TESTS_ONLY"


@dataclass
class FakeTelegram:
    calls: list = field(default_factory=list)
    fail_next_send: Exception | None = None
    send_gate: asyncio.Event | None = None
    two_sends_started: asyncio.Event = field(default_factory=asyncio.Event)
    waiting_sends: int = 0
    member_statuses: dict[object, str] = field(default_factory=dict)
    bot_status: str = "administrator"
    bot_can_invite: bool = True
    fail_member_check: bool = False

    def respond(self, url, request_data):
        method = url.rsplit("/", 1)[-1]
        params = request_data.parameters if request_data else {}
        self.calls.append((method, params))
        if method == "getMe":
            result = BOT_USER
        elif method == "setMyCommands":
            result = True
        elif method == "getChat":
            target = params["chat_id"]
            if target in (-100888, "-100888"):
                chat_id, title, username = -100888, "Private required channel", None
            elif target in (-100999, "-100999", "@secondchannel"):
                chat_id, title, username = -100999, "Second required channel", "secondchannel"
            else:
                chat_id, title, username = -100777, "Required channel", "testchannel"
            result = {
                "id": chat_id,
                "type": "channel",
                "title": title,
                "accent_color_id": 0,
                "max_reaction_count": 0,
                "accepted_gift_types": {
                    "unlimited_gifts": False,
                    "limited_gifts": False,
                    "unique_gifts": False,
                    "premium_subscription": False,
                    "gifts_from_channels": False,
                },
            }
            if username:
                result["username"] = username
        elif method == "getChatMember":
            if self.fail_member_check:
                raise NetworkError("membership check unavailable")
            user_id = params["user_id"]
            status = (
                self.bot_status
                if user_id == BOT_USER["id"]
                else self.member_statuses.get(
                    (params["chat_id"], user_id),
                    self.member_statuses.get(user_id, "left"),
                )
            )
            result = {
                "status": status,
                "user": {"id": user_id, "is_bot": user_id == BOT_USER["id"], "first_name": "Test"},
            }
            if status == "restricted":
                result["is_member"] = True
                result.update(
                    {
                        "can_change_info": False,
                        "can_invite_users": False,
                        "can_pin_messages": False,
                        "can_send_messages": False,
                        "can_send_polls": False,
                        "can_send_other_messages": False,
                        "can_add_web_page_previews": False,
                        "can_manage_topics": False,
                        "until_date": 0,
                        "can_send_audios": False,
                        "can_send_documents": False,
                        "can_send_photos": False,
                        "can_send_videos": False,
                        "can_send_video_notes": False,
                        "can_send_voice_notes": False,
                        "can_edit_tag": False,
                    }
                )
            if status == "administrator":
                result.update(
                    {
                        "can_be_edited": False,
                        "is_anonymous": False,
                        "can_manage_chat": True,
                        "can_delete_messages": False,
                        "can_manage_video_chats": False,
                        "can_restrict_members": False,
                        "can_promote_members": False,
                        "can_change_info": False,
                        "can_invite_users": self.bot_can_invite,
                        "can_post_stories": False,
                        "can_edit_stories": False,
                        "can_delete_stories": False,
                    }
                )
        elif method == "createChatInviteLink":
            result = {
                "invite_link": f"https://t.me/+Generated{len(self.calls)}",
                "creator": BOT_USER,
                "creates_join_request": False,
                "is_primary": False,
                "is_revoked": False,
            }
        elif method in ("answerCallbackQuery", "editMessageText"):
            result = True
        elif method == "sendMessage":
            if self.fail_next_send:
                error, self.fail_next_send = self.fail_next_send, None
                raise error
            result = {
                "message_id": len(self.calls),
                "date": 1700000000,
                "from": BOT_USER,
                "chat": {"id": params["chat_id"], "type": "private"},
                "text": params["text"],
            }
        else:
            raise AssertionError(f"Unexpected Telegram method: {method}")
        return 200, json.dumps({"ok": True, "result": result}).encode()

    @property
    def sent(self):
        return [params for method, params in self.calls if method == "sendMessage"]


@pytest.fixture
async def bot_app(monkeypatch, tmp_path):
    api = FakeTelegram()

    async def fake_request(self, url, method, request_data=None, **kwargs):
        if url.endswith("/sendMessage") and api.send_gate is not None:
            api.waiting_sends += 1
            if api.waiting_sends >= 2:
                api.two_sends_started.set()
            try:
                await api.send_gate.wait()
            finally:
                api.waiting_sends -= 1
        return api.respond(url, request_data)

    monkeypatch.setattr(HTTPXRequest, "do_request", fake_request)
    app = build_application(
        Settings(token=TOKEN, state_db_path=tmp_path / "activation.sqlite3", owner_user_id=1)
    )
    async with app:
        yield app, api


def incoming(
    app,
    text,
    *,
    user_id=42,
    chat_type="private",
    chat_id=None,
    update_id=1,
    command_entities=True,
    reply_to_user=None,
):
    if chat_id is None:
        chat_id = user_id if chat_type == "private" else -100123
    message = {
        "message_id": update_id,
        "date": 1700000000,
        "chat": {"id": chat_id, "type": chat_type, "title": "Test group"},
        "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
        "text": text,
    }
    if text.startswith("/") and command_entities:
        message["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
    if reply_to_user is not None:
        message["reply_to_message"] = {
            "message_id": 999,
            "date": 1700000000,
            "chat": message["chat"],
            "from": {"id": reply_to_user, "is_bot": False, "first_name": "Target"},
            "text": "earlier message",
        }
    return Update.de_json({"update_id": update_id, "message": message}, app.bot)


def incoming_join_check(app, *, user_id=42, chat_type="private"):
    chat_id = user_id if chat_type == "private" else -100123
    return Update.de_json(
        {
            "update_id": 900,
            "callback_query": {
                "id": "check-1",
                "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
                "chat_instance": "test",
                "data": "force_join_check",
                "message": {
                    "message_id": 200,
                    "date": 1700000000,
                    "chat": {"id": chat_id, "type": chat_type, "title": "Test group"},
                    "from": BOT_USER,
                    "text": "Join the channel",
                },
            },
        },
        app.bot,
    )


async def test_start_sends_original_buttons_and_persistent_keyboard(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/start"))
    assert len(api.sent) == 1
    reply = api.sent[0]
    assert reply["text"] == messages.WELCOME
    markup = reply["reply_markup"]
    assert markup["keyboard"] == [
        [{"text": messages.DEFENSE_BUTTON}, {"text": messages.ABLITY_BUTTON}],
        [{"text": "🎲🔴 ᎠᏆᏟᎬ 🔴🎲"}],
        [{"text": "🎲🟢 ᎠᏆᏟᎬ 🟢🎲"}],
    ]
    assert markup["is_persistent"] is True
    assert markup["resize_keyboard"] is True


@pytest.mark.parametrize(
    ("text", "color", "result", "expected"),
    [
        (messages.RED_BUTTON, DiceColor.RED, -10, "-10"),
        (messages.GREEN_BUTTON, DiceColor.GREEN, 1, "+1"),
        ("/red", DiceColor.RED, -1, "-1"),
        ("/green", DiceColor.GREEN, 10, "+10"),
        ("/red@DiseTestBot", DiceColor.RED, -5, "-5"),
    ],
)
async def test_commands_and_buttons_roll_once(bot_app, text, color, result, expected):
    app, api = bot_app
    with patch("dise_bot.handlers.dice.roll", return_value=result) as roll:
        await app.process_update(incoming(app, text))
        roll.assert_called_once_with(color)
    assert [item["text"] for item in api.sent] == [expected]


async def test_help_command_explains_weighted_odds(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/help"))
    assert [item["text"] for item in api.sent] == [messages.HELP]


async def test_ablity_button_opens_screen_and_back_returns_to_main_menu(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, messages.ABLITY_BUTTON))
    assert api.sent[-1]["text"] == messages.ABLITY_MENU
    assert api.sent[-1]["reply_markup"]["keyboard"] == [[{"text": messages.BACK_BUTTON}]]
    await app.process_update(incoming(app, messages.BACK_BUTTON))
    assert api.sent[-1]["text"] == messages.WELCOME


async def test_ablity_screen_has_no_activation_buttons_in_group(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/on", chat_type="group"))
    await app.process_update(incoming(app, messages.ABLITY_BUTTON, chat_type="group"))
    assert api.sent[-1]["text"] == messages.ABLITY_MENU
    assert api.sent[-1]["reply_markup"]["keyboard"] == [[{"text": messages.BACK_BUTTON}]]
    assert api.sent[-1]["reply_markup"]["selective"] is True


async def test_every_rapid_click_produces_its_own_result(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.dice.roll", side_effect=[-3, 8, 5, -1]) as roll:
        for text in (messages.RED_BUTTON, messages.GREEN_BUTTON, "/green", "/red"):
            await app.process_update(incoming(app, text))
        assert roll.call_count == 4
    assert [item["text"] for item in api.sent] == ["-3", "+8", "+5", "-1"]


async def test_polling_queue_processes_rapid_clicks_concurrently(bot_app):
    app, api = bot_app
    api.send_gate = asyncio.Event()
    await app.start()
    try:
        for update_id in (1, 2):
            await app.update_queue.put(incoming(app, "/green", update_id=update_id))
        # Both replies must reach the transport before either is allowed to finish.
        await asyncio.wait_for(api.two_sends_started.wait(), timeout=2)
        assert api.waiting_sends == 2
        api.send_gate.set()
        await asyncio.wait_for(app.update_queue.join(), timeout=2)
        assert len(api.sent) == 2
    finally:
        api.send_gate.set()
        await app.stop()


async def test_defense_menu_and_back_navigation(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, messages.DEFENSE_BUTTON))
    assert api.sent[-1]["text"] == messages.DEFENSE_MENU
    rows = api.sent[-1]["reply_markup"]["keyboard"]
    assert rows == [
        [{"text": messages.CURSED_AURA_BUTTON}],
        [{"text": messages.LIGHT_BUTTON}, {"text": messages.HEAVY_BUTTON}],
        [{"text": messages.SUPER_BUTTON}, {"text": messages.GOD_BUTTON}],
        [{"text": messages.GOLD_BUTTON}, {"text": messages.ABSOLUTE_BUTTON}],
        [{"text": messages.REFLECT_BUTTON}],
        [{"text": messages.BACK_BUTTON}],
    ]
    assert "25% · 50% · 75% · 100%" in api.sent[-1]["text"]
    await app.process_update(incoming(app, messages.BACK_BUTTON))
    assert api.sent[-1]["text"] == messages.WELCOME


async def test_absolute_button_returns_a_random_signed_value(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.absolute.roll_absolute", return_value=-25):
        await app.process_update(incoming(app, messages.ABSOLUTE_BUTTON))
    assert len(api.sent) == 1
    assert messages.ABSOLUTE_NEG_LINE in api.sent[0]["text"]
    assert "🔻" not in api.sent[0]["text"]


async def test_absolute_button_shows_explicit_plus_for_positives(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.absolute.roll_absolute", return_value=40):
        await app.process_update(incoming(app, messages.ABSOLUTE_BUTTON))
    assert messages.ABSOLUTE_POS_LINE in api.sent[0]["text"]


async def test_absolute_button_shows_plain_label_for_zero(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.absolute.roll_absolute", return_value=0):
        await app.process_update(incoming(app, messages.ABSOLUTE_BUTTON))
    assert messages.ABSOLUTE_ZERO_LINE in api.sent[0]["text"]


async def test_reflect_button_returns_a_random_signed_value(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.reflect.roll_reflect", return_value=-25):
        await app.process_update(incoming(app, messages.REFLECT_BUTTON))
    assert len(api.sent) == 1
    assert messages.REFLECT_NEG_LINE in api.sent[0]["text"]
    assert "🔻" not in api.sent[0]["text"]


async def test_reflect_button_shows_explicit_plus_for_positives(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.reflect.roll_reflect", return_value=40):
        await app.process_update(incoming(app, messages.REFLECT_BUTTON))
    assert messages.REFLECT_POS_LINE in api.sent[0]["text"]


async def test_reflect_button_shows_plain_label_for_zero(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.reflect.roll_reflect", return_value=0):
        await app.process_update(incoming(app, messages.REFLECT_BUTTON))
    assert messages.REFLECT_ZERO_LINE in api.sent[0]["text"]


async def test_aura_button_returns_a_random_value_with_energy_cost(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.aura.roll_cursed_aura", return_value=25):
        await app.process_update(incoming(app, messages.CURSED_AURA_BUTTON))
    assert len(api.sent) == 1
    assert messages.AURA_VALUE_LINE.format(25) in api.sent[0]["text"]
    assert "Energy cost: 10" in api.sent[0]["text"]


@pytest.mark.parametrize(
    ("button", "roll", "expected"),
    [
        (messages.LIGHT_BUTTON, 1, 10),
        (messages.HEAVY_BUTTON, 9, 55),
        (messages.SUPER_BUTTON, 5, 40),
        (messages.GOD_BUTTON, 1, 25),
        (messages.GOLD_BUTTON, 9, 70),
    ],
)
async def test_tier_buttons_roll_and_calculate_in_one_reply(bot_app, button, roll, expected):
    app, api = bot_app
    with (
        patch("dise_bot.handlers.defense.roll_defense", return_value=roll) as pick,
        patch("dise_bot.handlers.defense.show_percent_result", return_value=False),
    ):
        await app.process_update(incoming(app, button))
        pick.assert_called_once()
    assert len(api.sent) == 1
    assert f"Roll: +{roll}" in api.sent[0]["text"]
    assert messages.DEFENSE_VALUE_LINE.format(expected) in api.sent[0]["text"]


@pytest.mark.parametrize("percent", [-25, -50, -75, -100])
async def test_tier_buttons_sometimes_show_a_random_percent(bot_app, percent):
    app, api = bot_app
    with (
        patch("dise_bot.handlers.defense.roll_defense", return_value=9),
        patch("dise_bot.handlers.defense.show_percent_result", return_value=True),
        patch("dise_bot.handlers.defense.roll_percent", return_value=percent),
    ):
        await app.process_update(incoming(app, messages.GOD_BUTTON))
    assert len(api.sent) == 1
    assert "Roll: +9" in api.sent[0]["text"]
    assert messages.DEFENSE_PERCENT_LINE.format(percent) in api.sent[0]["text"]
    assert "ᗪᖴ" not in api.sent[0]["text"]


async def test_explicit_defense_roll_always_shows_the_calculated_value(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.defense.show_percent_result", return_value=True):
        await app.process_update(incoming(app, "/defense gold +9"))
    assert messages.DEFENSE_VALUE_LINE.format(70) in api.sent[0]["text"]


async def test_defense_command_accepts_explicit_positive_roll(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.defense.roll_defense") as pick:
        await app.process_update(incoming(app, "/defense gold +9"))
        pick.assert_not_called()
    assert messages.DEFENSE_VALUE_LINE.format(70) in api.sent[0]["text"]


@pytest.mark.parametrize("args", ["silver 3", "light 10", "light -1", "light", "light 3 extra"])
async def test_invalid_defense_input_does_not_roll_or_guess(bot_app, args):
    app, api = bot_app
    with patch("dise_bot.handlers.defense.roll_defense") as pick:
        await app.process_update(incoming(app, f"/defense {args}"))
        pick.assert_not_called()
    assert "Rolls: +1 to +9" in api.sent[0]["text"]


async def test_one_user_cannot_block_another(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/red", user_id=1))
    await app.process_update(incoming(app, "/green", user_id=2))
    assert len(api.sent) == 2
    assert api.sent[0]["text"].startswith("-")
    assert api.sent[1]["text"].startswith("+")


async def test_unrelated_group_messages_are_ignored_but_commands_work(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "hello", chat_type="group"))
    await app.process_update(incoming(app, "/red@AnotherBot", chat_type="group"))
    assert not api.sent
    await app.process_update(incoming(app, "/green@DiseTestBot", chat_type="group"))
    assert not api.sent
    await app.process_update(incoming(app, "/on@DiseTestBot", chat_type="group"))
    await app.process_update(incoming(app, "/green@DiseTestBot", chat_type="group"))
    assert len(api.sent) == 2
    assert messages.CREDIT in api.sent[0]["text"]
    assert api.sent[1]["text"].startswith("+")


@pytest.mark.parametrize(
    "button",
    [
        messages.RED_BUTTON,
        messages.GREEN_BUTTON,
        messages.LIGHT_BUTTON,
        messages.HEAVY_BUTTON,
        messages.SUPER_BUTTON,
        messages.GOD_BUTTON,
        messages.GOLD_BUTTON,
        messages.CURSED_AURA_BUTTON,
        messages.ABSOLUTE_BUTTON,
        messages.REFLECT_BUTTON,
        "/red",
        "/green",
        "/defense gold 9",
    ],
)
async def test_group_rolls_are_off_until_the_sender_uses_on(bot_app, button):
    app, api = bot_app
    await app.process_update(incoming(app, button, chat_type="group"))
    assert not api.sent


async def test_on_and_off_change_only_one_user_in_one_group(bot_app):
    app, api = bot_app
    store = app.bot_data["activation_store"]
    await app.process_update(incoming(app, "/on", user_id=11, chat_type="group"))
    assert store.is_enabled(-100123, 11)
    assert not store.is_enabled(-100123, 12)
    assert not store.is_enabled(-100456, 11)
    assert api.sent[-1]["text"] == messages.ON_MESSAGE
    labels = [
        button["text"]
        for row in api.sent[-1]["reply_markup"]["keyboard"]
        for button in row
    ]
    assert "🟢 ON" not in labels
    assert "🔴 OFF" not in labels
    assert "⚙️ STATUS" not in labels

    await app.process_update(incoming(app, "/on", user_id=12, chat_type="group"))
    await app.process_update(
        incoming(app, "/on", user_id=11, chat_type="supergroup", chat_id=-100456)
    )
    await app.process_update(incoming(app, "/off", user_id=11, chat_type="group"))
    assert not store.is_enabled(-100123, 11)
    assert store.is_enabled(-100123, 12)
    assert store.is_enabled(-100456, 11)
    assert api.sent[-1]["text"] == messages.OFF_MESSAGE
    assert messages.CREDIT == "بات ساخته شده توسط @Anthony_0088"

    before = len(api.sent)
    await app.process_update(incoming(app, messages.RED_BUTTON, user_id=11, chat_type="group"))
    assert len(api.sent) == before
    await app.process_update(incoming(app, messages.GREEN_BUTTON, user_id=12, chat_type="group"))
    assert len(api.sent) == before + 1
    assert api.sent[-1]["text"].startswith("+")


async def test_group_menus_stay_hidden_until_that_member_turns_them_on(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/start", chat_type="group"))
    assert api.sent[-1]["text"].startswith(messages.GROUP_WELCOME)
    assert "/on" in api.sent[-1]["text"]
    assert messages.STATUS_OFF_MESSAGE in api.sent[-1]["text"]
    assert api.sent[-1]["reply_markup"] == {"remove_keyboard": True, "selective": True}

    await app.process_update(incoming(app, messages.DEFENSE_BUTTON, chat_type="group"))
    assert api.sent[-1]["text"] == messages.PANEL_OFF_MESSAGE
    assert api.sent[-1]["reply_markup"] == {"remove_keyboard": True, "selective": True}

    await app.process_update(incoming(app, "/on", chat_type="group"))
    assert api.sent[-1]["reply_markup"]["selective"] is True
    await app.process_update(incoming(app, messages.DEFENSE_BUTTON, chat_type="group"))
    assert api.sent[-1]["text"] == messages.GROUP_DEFENSE_MENU
    assert api.sent[-1]["reply_markup"]["selective"] is True


async def test_defense_dice_respect_the_same_group_switch(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/on", chat_type="group"))
    with (
        patch("dise_bot.handlers.defense.roll_defense", return_value=3),
        patch("dise_bot.handlers.defense.show_percent_result", return_value=False),
    ):
        await app.process_update(incoming(app, messages.LIGHT_BUTTON, chat_type="group"))
    assert messages.DEFENSE_VALUE_LINE.format(20) in api.sent[-1]["text"]
    await app.process_update(incoming(app, "/off", chat_type="group"))
    with patch("dise_bot.handlers.aura.roll_cursed_aura") as pick:
        await app.process_update(incoming(app, messages.CURSED_AURA_BUTTON, chat_type="group"))
        pick.assert_not_called()


@pytest.mark.parametrize("command", ["/on", "/off"])
async def test_on_off_are_group_only_and_private_dice_keep_working(bot_app, command):
    app, api = bot_app
    await app.process_update(incoming(app, command))
    assert api.sent[-1]["text"] == messages.GROUP_ONLY_MESSAGE
    await app.process_update(incoming(app, "/red"))
    assert api.sent[-1]["text"].startswith("-")


async def test_slash_keyboard_buttons_work_without_command_entities(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/on", chat_type="group", command_entities=False))
    assert api.sent[-1]["text"] == messages.ON_MESSAGE
    await app.process_update(incoming(app, "/off", chat_type="group", command_entities=False))
    assert api.sent[-1]["text"] == messages.OFF_MESSAGE


async def test_on_command_restores_full_keyboard_after_personal_off(bot_app):
    app, api = bot_app
    store = app.bot_data["activation_store"]

    await app.process_update(incoming(app, "/on", user_id=71, chat_type="group"))
    await app.process_update(incoming(app, "/off", user_id=71, chat_type="group"))
    assert not store.is_enabled(-100123, 71)
    assert api.sent[-1]["reply_markup"] == {"remove_keyboard": True, "selective": True}

    await app.process_update(incoming(app, "/on", user_id=71, chat_type="group"))
    assert store.is_enabled(-100123, 71)
    assert api.sent[-1]["text"] == messages.ON_MESSAGE
    markup = api.sent[-1]["reply_markup"]
    assert markup["selective"] is True
    labels = [button["text"] for row in markup["keyboard"] for button in row]
    assert "🟢 ON" not in labels
    assert "🔴 OFF" not in labels
    assert "⚙️ STATUS" not in labels


async def test_status_command_shows_only_the_requesting_users_state(bot_app):
    app, api = bot_app

    await app.process_update(incoming(app, "/status", user_id=51, chat_type="group"))
    assert api.sent[-1]["text"] == messages.STATUS_OFF_MESSAGE

    await app.process_update(incoming(app, "/on", user_id=51, chat_type="group"))
    await app.process_update(incoming(app, "/status", user_id=51, chat_type="group"))
    assert api.sent[-1]["text"] == messages.STATUS_ON_MESSAGE

    await app.process_update(incoming(app, "/status", user_id=52, chat_type="group"))
    assert api.sent[-1]["text"] == messages.STATUS_OFF_MESSAGE


async def test_private_status_and_version_commands(bot_app):
    app, api = bot_app

    await app.process_update(incoming(app, "/status"))
    assert api.sent[-1]["text"] == messages.PRIVATE_STATUS_MESSAGE

    await app.process_update(incoming(app, "/version"))
    assert api.sent[-1]["text"] == "🎲 ᎠᏆᏟᎬ Bot v1.2.1"


async def test_one_members_off_does_not_change_another_members_activation(bot_app):
    app, api = bot_app
    store = app.bot_data["activation_store"]

    await app.process_update(incoming(app, "/on", user_id=61, chat_type="group"))
    await app.process_update(incoming(app, "/on", user_id=62, chat_type="group"))
    assert store.is_enabled(-100123, 61)
    assert store.is_enabled(-100123, 62)

    await app.process_update(incoming(app, "/off", user_id=61, chat_type="group"))
    assert not store.is_enabled(-100123, 61)
    assert store.is_enabled(-100123, 62)
    assert api.sent[-1]["reply_markup"] == {"remove_keyboard": True, "selective": True}

    before = len(api.sent)
    with patch("dise_bot.handlers.dice.roll", return_value=9):
        await app.process_update(
            incoming(app, messages.GREEN_BUTTON, user_id=62, chat_type="group")
        )
    assert len(api.sent) == before + 1
    assert api.sent[-1]["text"] == "+9"
    assert api.sent[-1]["reply_markup"]["selective"] is True


async def test_activation_survives_a_new_store_instance(bot_app, tmp_path):
    app, _ = bot_app
    await app.process_update(incoming(app, "/on", user_id=42, chat_type="group"))
    path = tmp_path / "activation.sqlite3"
    reloaded = ActivationStore(path)
    assert reloaded.is_enabled(-100123, 42)
    reloaded.set_enabled(-100123, 42, enabled=False)
    assert not ActivationStore(path).is_enabled(-100123, 42)


async def test_unknown_private_text_shows_hint_without_rolling(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.dice.roll") as roll:
        await app.process_update(incoming(app, "hello"))
        roll.assert_not_called()
    assert api.sent[0]["text"] == messages.UNKNOWN_MESSAGE


async def test_updates_without_messages_are_safe(bot_app):
    app, api = bot_app
    await app.process_update(Update(update_id=99))
    assert not api.sent


@pytest.mark.parametrize("error", [NetworkError("offline"), Forbidden("blocked")])
async def test_failed_delivery_does_not_retry_or_reroll(bot_app, error):
    app, api = bot_app
    api.fail_next_send = error
    with patch("dise_bot.handlers.dice.roll", return_value=8) as roll:
        await app.process_update(incoming(app, "/green"))
        roll.assert_called_once()
    assert len(api.sent) == 1


async def test_unexpected_error_has_friendly_reply(bot_app):
    app, api = bot_app
    with patch("dise_bot.handlers.dice.roll", side_effect=RuntimeError("test failure")):
        await app.process_update(incoming(app, "/red"))
    assert [item["text"] for item in api.sent] == [messages.UNEXPECTED_ERROR]


async def test_conflicting_instance_stops_polling(bot_app, monkeypatch):
    app, api = bot_app
    stop = Mock()
    monkeypatch.setattr(type(app), "stop_running", stop)
    await app.process_error(None, Conflict("Another poller is running"))
    stop.assert_called_once()
    assert not api.sent


async def test_command_menu_is_english(bot_app):
    app, api = bot_app
    await set_commands(app)
    commands = [params for method, params in api.calls if method == "setMyCommands"][0]["commands"]
    assert [command["command"] for command in commands] == [
        "start",
        "red",
        "green",
        "defense",
        "on",
        "off",
        "status",
        "version",
        "help",
        "id",
        "panel",
        "reply",
        "join",
        "tag",
    ]
    assert all(command["description"].isascii() for command in commands)


async def test_owner_panel_and_private_id(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/id", user_id=1))
    assert api.sent[-1]["text"] == "Your Telegram user ID: 1"
    await app.process_update(incoming(app, "/start", user_id=1))
    assert api.sent[-1]["reply_markup"]["keyboard"][-1] == [{"text": messages.PANEL_BUTTON}]
    await app.process_update(incoming(app, messages.PANEL_BUTTON, user_id=1))
    labels = [button["text"] for row in api.sent[-1]["reply_markup"]["keyboard"] for button in row]
    assert messages.ADD_ADMIN_BUTTON in labels
    assert messages.AUTO_REPLIES_BUTTON in labels
    await app.process_update(incoming(app, "/panel", user_id=42))
    assert api.sent[-1]["text"] == "Access denied."


async def test_owner_settings_button_routes_and_persian_language_persists(bot_app, tmp_path):
    app, api = bot_app
    store = app.bot_data["management_store"]

    await app.process_update(incoming(app, "/panel", user_id=1))
    await app.process_update(
        incoming(app, admin_i18n.button("en", "settings"), user_id=1)
    )
    assert api.sent[-1]["text"].startswith("⚙️ Admin settings")
    settings_labels = [
        button["text"]
        for row in api.sent[-1]["reply_markup"]["keyboard"]
        for button in row
    ]
    assert admin_i18n.LANGUAGE_BUTTONS["fa"] in settings_labels
    assert admin_i18n.LANGUAGE_BUTTONS["en"] in settings_labels

    await app.process_update(
        incoming(app, admin_i18n.LANGUAGE_BUTTONS["fa"], user_id=1)
    )
    assert store.language_for(1) == "fa"
    assert "زبان فعلی" in api.sent[-1]["text"]
    assert ManagementStore(
        tmp_path / "activation.sqlite3",
        owner_user_id=1,
    ).language_for(1) == "fa"

    await app.process_update(
        incoming(app, admin_i18n.button("fa", "back"), user_id=1)
    )
    assert "پنل مدیریت" in api.sent[-1]["text"]

    await app.process_update(
        incoming(app, admin_i18n.button("fa", "settings"), user_id=1)
    )
    assert "تنظیمات ادمین" in api.sent[-1]["text"]

    await app.process_update(
        incoming(app, admin_i18n.button("fa", "back"), user_id=1)
    )
    await app.process_update(
        incoming(app, admin_i18n.button("fa", "force_join"), user_id=1)
    )
    assert "عضویت اجباری" in api.sent[-1]["text"]


async def test_owner_and_admin_permissions_and_global_ban(bot_app, tmp_path):
    app, api = bot_app
    store = app.bot_data["management_store"]
    await app.process_update(incoming(app, "/admin 12", user_id=42))
    assert not store.is_admin(12)
    await app.process_update(incoming(app, "/admin 12", user_id=1))
    assert store.is_admin(12)
    await app.process_update(incoming(app, "/admin 14", user_id=12))
    assert not store.is_admin(14)
    await app.process_update(incoming(app, "/ban 1", user_id=12))
    assert not store.is_banned(1)
    await app.process_update(incoming(app, "/ban 13", user_id=12))
    assert store.is_banned(13)
    before = len(api.sent)
    await app.process_update(incoming(app, "/start", user_id=13))
    await app.process_update(incoming(app, "/id", user_id=13))
    assert len(api.sent) == before
    await app.process_update(incoming(app, "/unban 13", user_id=12))
    assert not store.is_banned(13)
    await app.process_update(incoming(app, "/start", user_id=13))
    assert api.sent[-1]["text"] == messages.WELCOME
    reloaded = ManagementStore(tmp_path / "activation.sqlite3", owner_user_id=1)
    assert reloaded.is_admin(12)
    assert not reloaded.is_banned(13)


async def test_panel_buttons_accept_id_and_reply_target(bot_app):
    app, api = bot_app
    store = app.bot_data["management_store"]
    await app.process_update(incoming(app, "/panel", user_id=1))
    await app.process_update(incoming(app, messages.BAN_BUTTON, user_id=1))
    await app.process_update(incoming(app, "77", user_id=1))
    assert store.is_banned(77)
    assert api.sent[-1]["text"] == "User 77 banned from this bot."
    await app.process_update(
        incoming(app, "/unban", user_id=1, chat_type="group", reply_to_user=77)
    )
    assert not store.is_banned(77)
    await app.process_update(incoming(app, messages.ADD_ADMIN_BUTTON, user_id=42))
    assert api.sent[-1]["text"] == "Access denied."


async def test_group_persian_auto_reply_is_exact_and_group_scoped(bot_app, tmp_path):
    app, api = bot_app
    group = {"chat_type": "group", "chat_id": -100123}
    await app.process_update(incoming(app, "/reply add سلام | درود!", user_id=1, **group))
    assert "saved" in api.sent[-1]["text"]
    await app.process_update(incoming(app, " سلام  ", user_id=42, **group))
    assert api.sent[-1]["text"] == "درود!"
    before = len(api.sent)
    await app.process_update(incoming(app, "سلام خوبی", user_id=42, **group))
    await app.process_update(incoming(app, "سلام", user_id=42, chat_type="group", chat_id=-100456))
    assert len(api.sent) == before
    await app.process_update(incoming(app, "/reply list", user_id=1, **group))
    assert "سلام" in api.sent[-1]["text"]
    await app.process_update(incoming(app, "/reply add چی | جواب", user_id=42, **group))
    assert app.bot_data["management_store"].response_for(-100123, "چی") is None
    await app.process_update(incoming(app, "/ban 42", user_id=1))
    before = len(api.sent)
    await app.process_update(incoming(app, "سلام", user_id=42, **group))
    assert len(api.sent) == before
    reloaded = ManagementStore(tmp_path / "activation.sqlite3", owner_user_id=1)
    assert reloaded.response_for(-100123, "سلام") == "درود!"
    await app.process_update(incoming(app, "/reply remove سلام", user_id=1, **group))
    assert app.bot_data["management_store"].response_for(-100123, "سلام") is None


async def test_tag_uses_full_mtproto_member_list_in_three_member_batches(bot_app):
    app, api = bot_app
    group = {"chat_type": "group", "chat_id": -100123}
    members = [(user_id, f"Member {user_id}") for user_id in (1, 11, 12, 13, 14, 15, 16)]
    before = len(api.sent)

    with (
        patch("dise_bot.handlers.tag.fetch_all_members_mtproto", return_value=members) as fetch,
        patch("dise_bot.handlers.tag.asyncio.sleep") as sleep,
    ):
        await app.process_update(
            incoming(app, "/tag", user_id=1, reply_to_user=11, **group)
        )

    fetch.assert_awaited_once()
    sent = api.sent[before:]
    assert len(sent) == 5
    assert [item["text"] for item in sent[1::2]] == [
        "⏳ ادامه تگ اعضا...",
        "⏳ ادامه تگ اعضا...",
    ]
    tag_messages = sent[0::2]
    assert [len(item["entities"]) for item in tag_messages] == [3, 3, 1]
    mentioned_ids = [
        entity["user"]["id"]
        for item in tag_messages
        for entity in item["entities"]
    ]
    assert mentioned_ids == [1, 11, 12, 13, 14, 15, 16]
    assert all(
        entity["type"] == "text_mention"
        for item in tag_messages
        for entity in item["entities"]
    )
    assert all(item["reply_parameters"]["message_id"] == 999 for item in sent)
    assert sleep.await_count == 4


async def test_tag_refuses_partial_local_list_when_mtproto_is_not_configured(bot_app):
    app, api = bot_app
    group = {"chat_type": "group", "chat_id": -100123}

    await app.process_update(incoming(app, "hello", user_id=11, **group))
    await app.process_update(
        incoming(app, "/tag", user_id=1, reply_to_user=11, **group)
    )
    assert "TELEGRAM_API_ID" in api.sent[-1]["text"]
    assert "TELEGRAM_API_HASH" in api.sent[-1]["text"]


async def test_tag_requires_reply_and_manager_permission(bot_app):
    app, api = bot_app
    group = {"chat_type": "group", "chat_id": -100123}

    await app.process_update(incoming(app, "/tag", user_id=1, **group))
    assert api.sent[-1]["text"] == "Reply to a message, then send /tag."

    before = len(api.sent)
    await app.process_update(
        incoming(app, "/tag", user_id=42, reply_to_user=1, **group)
    )
    assert len(api.sent) == before


def test_known_group_members_persist_and_can_be_deactivated(tmp_path):
    path = tmp_path / "state.sqlite3"
    store = ManagementStore(path, owner_user_id=1)
    store.remember_group_member(-100123, 11, "Member Eleven")
    assert store.group_members(-100123) == [(11, "Member Eleven")]

    reloaded = ManagementStore(path, owner_user_id=1)
    assert reloaded.group_members(-100123) == [(11, "Member Eleven")]
    reloaded.remember_group_member(-100123, 11, "Member Eleven", active=False)
    assert reloaded.group_members(-100123) == []


async def test_admin_can_manage_group_replies_but_not_roles(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/admin 12", user_id=1))
    await app.process_update(incoming(app, "/reply add ميرم | برو", user_id=12, chat_type="group"))
    await app.process_update(incoming(app, "میرم", user_id=42, chat_type="group"))
    assert api.sent[-1]["text"] == "برو"
    await app.process_update(incoming(app, "/admin 14", user_id=12))
    assert not app.bot_data["management_store"].is_admin(14)


def test_management_stays_disabled_without_owner_id(tmp_path):
    path = tmp_path / "state.sqlite3"
    ManagementStore(path, owner_user_id=1).set_admin(12, enabled=True)
    store = ManagementStore(path, owner_user_id=None)
    assert not store.is_manager(1)
    assert not store.is_manager(12)


async def test_owner_enables_force_join_and_member_can_roll(bot_app, tmp_path):
    app, api = bot_app
    await app.process_update(incoming(app, "/join set @testchannel", user_id=1))
    store = app.bot_data["force_join_store"]
    assert store.enabled
    assert len(store.required_chats) == 1
    required = store.required_chats[0]
    assert required.chat_id == -100777
    assert required.join_url == "https://t.me/testchannel"
    assert ForceJoinStore(tmp_path / "activation.sqlite3").required_chats == [required]

    before = len(api.sent)
    with patch("dise_bot.handlers.dice.roll") as roll:
        await app.process_update(incoming(app, "/red", user_id=42))
        roll.assert_not_called()
    assert len(api.sent) == before + 1
    prompt = api.sent[-1]
    assert "Join all required channels" in prompt["text"]
    buttons = prompt["reply_markup"]["inline_keyboard"]
    assert buttons[0][0]["url"] == "https://t.me/testchannel"
    assert buttons[-1][0]["callback_data"] == "force_join_check"

    await app.process_update(incoming_join_check(app))
    assert api.calls[-1][0] == "answerCallbackQuery"
    assert "Join all required channels first" in api.calls[-1][1]["text"]

    api.member_statuses[42] = "member"
    await app.process_update(incoming_join_check(app))
    assert api.calls[-2][0] == "answerCallbackQuery"
    assert api.calls[-1][0] == "editMessageText"

    with patch("dise_bot.handlers.dice.roll", return_value=-3):
        await app.process_update(incoming(app, "/red", user_id=42))
    assert api.sent[-1]["text"] == "-3"


async def test_multiple_required_channels_all_must_be_joined(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/join add @testchannel", user_id=1))
    await app.process_update(incoming(app, "/join add @secondchannel", user_id=1))
    store = app.bot_data["force_join_store"]
    assert not store.enabled
    assert {chat.chat_id for chat in store.configured_chats} == {-100777, -100999}

    await app.process_update(incoming(app, "/join on", user_id=1))
    assert store.enabled
    assert len(store.required_chats) == 2

    api.member_statuses[(-100777, 42)] = "member"
    api.member_statuses[(-100999, 42)] = "left"
    before = len(api.sent)
    with patch("dise_bot.handlers.dice.roll") as roll:
        await app.process_update(incoming(app, "/green", user_id=42))
        roll.assert_not_called()
    prompt = api.sent[-1]
    assert len(prompt["reply_markup"]["inline_keyboard"]) == 3
    assert "Second required channel" in prompt["text"]

    api.member_statuses[(-100999, 42)] = "member"
    with patch("dise_bot.handlers.dice.roll", return_value=8):
        await app.process_update(incoming(app, "/green", user_id=42))
    assert len(api.sent) == before + 2
    assert api.sent[-1]["text"] == "+8"


async def test_force_join_group_gate_only_checks_bot_interactions(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/join set @testchannel", user_id=1))
    before = len(api.sent)
    await app.process_update(incoming(app, "hello", chat_type="group"))
    await app.process_update(incoming(app, "/red@OtherBot", chat_type="group"))
    assert len(api.sent) == before

    await app.process_update(incoming(app, "/on", chat_type="group"))
    assert "Join all required channels" in api.sent[-1]["text"]
    assert not app.bot_data["activation_store"].is_enabled(-100123, 42)

    api.member_statuses[42] = "restricted"
    await app.process_update(incoming(app, "/on", chat_type="group"))
    assert api.sent[-1]["text"] == messages.ON_MESSAGE


async def test_force_join_blocks_auto_replies_and_bans_take_priority(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/join set @testchannel", user_id=1))
    await app.process_update(incoming(app, "/reply add سلام | درود", user_id=1, chat_type="group"))
    await app.process_update(incoming(app, "سلام", user_id=42, chat_type="group"))
    assert "Join all required channels" in api.sent[-1]["text"]

    await app.process_update(incoming(app, "/ban 42", user_id=1))
    before = len(api.sent)
    await app.process_update(incoming(app, "سلام", user_id=42, chat_type="group"))
    assert len(api.sent) == before
    await app.process_update(incoming(app, "/id", user_id=43))
    assert api.sent[-1]["text"] == "Your Telegram user ID: 43"


async def test_force_join_generates_private_link_and_can_toggle(bot_app, tmp_path):
    app, api = bot_app
    api.bot_status = "member"
    await app.process_update(incoming(app, "/join add @testchannel", user_id=1))
    assert not app.bot_data["force_join_store"].configured_chats
    assert "Make this bot an admin" in api.sent[-1]["text"]

    api.bot_status = "administrator"
    await app.process_update(incoming(app, "/join add -100888", user_id=1))
    store = app.bot_data["force_join_store"]
    assert not store.enabled
    first_link = store.configured_chats[0].join_url
    assert first_link.startswith("https://t.me/+Generated")
    assert any(method == "createChatInviteLink" for method, _ in api.calls)

    await app.process_update(incoming(app, "/join add -100888 https://evil.com/x", user_id=1))
    assert store.configured_chats[0].join_url == first_link

    await app.process_update(
        incoming(app, "/join add -100888 https://t.me/+PrivateInvite", user_id=1)
    )
    assert store.configured_chats[0].join_url == "https://t.me/+PrivateInvite"

    await app.process_update(incoming(app, "/join on", user_id=1))
    assert store.enabled
    refreshed_link = store.required_chats[0].join_url
    assert refreshed_link.startswith("https://t.me/+Generated")

    await app.process_update(incoming(app, "/join off", user_id=1))
    assert not store.enabled
    assert not store.required_chats
    assert store.configured_chats

    persisted = ForceJoinStore(tmp_path / "activation.sqlite3")
    assert not persisted.enabled
    assert persisted.configured_chats == store.configured_chats

    await app.process_update(incoming(app, "/join on", user_id=1))
    assert store.enabled
    assert ForceJoinStore(tmp_path / "activation.sqlite3").required_chats == store.required_chats


async def test_force_join_panel_buttons_and_per_admin_language(bot_app, tmp_path):
    app, api = bot_app
    await app.process_update(incoming(app, "/admin 12", user_id=1))
    store = app.bot_data["management_store"]
    assert store.is_admin(12)

    await app.process_update(incoming(app, "/panel", user_id=12))
    labels = [
        button["text"]
        for row in api.sent[-1]["reply_markup"]["keyboard"]
        for button in row
    ]
    assert admin_i18n.button("en", "force_join") in labels
    assert admin_i18n.button("en", "settings") in labels

    await app.process_update(
        incoming(app, admin_i18n.button("en", "settings"), user_id=12)
    )
    await app.process_update(
        incoming(
            app,
            admin_i18n.LANGUAGE_BUTTONS[admin_i18n.LANG_FA],
            user_id=12,
        )
    )
    assert store.language_for(12) == "fa"
    assert ManagementStore(
        tmp_path / "activation.sqlite3",
        owner_user_id=1,
    ).language_for(12) == "fa"

    await app.process_update(incoming(app, "/panel", user_id=12))
    labels = [
        button["text"]
        for row in api.sent[-1]["reply_markup"]["keyboard"]
        for button in row
    ]
    assert admin_i18n.button("fa", "force_join") in labels
    assert admin_i18n.button("fa", "settings") in labels

    await app.process_update(
        incoming(app, admin_i18n.button("fa", "force_join"), user_id=12)
    )
    membership_labels = [
        button["text"]
        for row in api.sent[-1]["reply_markup"]["keyboard"]
        for button in row
    ]
    assert admin_i18n.button("fa", "join_on") in membership_labels
    assert admin_i18n.button("fa", "join_off") in membership_labels
    assert admin_i18n.button("fa", "join_add") in membership_labels
    assert admin_i18n.button("fa", "join_remove") in membership_labels

    await app.process_update(
        incoming(app, admin_i18n.button("fa", "join_add"), user_id=12)
    )
    await app.process_update(incoming(app, "@testchannel", user_id=12))
    assert len(app.bot_data["force_join_store"].configured_chats) == 1

    await app.process_update(
        incoming(app, admin_i18n.button("fa", "join_on"), user_id=12)
    )
    assert app.bot_data["force_join_store"].enabled

    await app.process_update(incoming(app, "/start", user_id=12))
    assert "Join all required channels" in api.sent[-1]["text"]

    await app.process_update(
        incoming(app, admin_i18n.button("fa", "force_join"), user_id=12)
    )
    assert "عضویت اجباری" in api.sent[-1]["text"]

    await app.process_update(
        incoming(app, admin_i18n.button("fa", "join_off"), user_id=12)
    )
    assert not app.bot_data["force_join_store"].enabled

    await app.process_update(incoming(app, "/panel", user_id=1))
    owner_labels = [
        button["text"]
        for row in api.sent[-1]["reply_markup"]["keyboard"]
        for button in row
    ]
    assert admin_i18n.button("en", "settings") in owner_labels


async def test_force_join_panel_permission_and_check_failure(bot_app):
    app, api = bot_app
    await app.process_update(incoming(app, "/panel", user_id=1))
    labels = [
        button["text"]
        for row in api.sent[-1]["reply_markup"]["keyboard"]
        for button in row
    ]
    assert admin_i18n.button("en", "force_join") in labels

    await app.process_update(
        incoming(app, admin_i18n.button("en", "force_join"), user_id=1)
    )
    assert admin_i18n.button("en", "join_on") in {
        button["text"]
        for row in api.sent[-1]["reply_markup"]["keyboard"]
        for button in row
    }

    await app.process_update(incoming(app, "/join add @testchannel", user_id=42))
    assert not app.bot_data["force_join_store"].configured_chats

    await app.process_update(incoming(app, "/join set @testchannel", user_id=1))
    api.fail_member_check = True
    await app.process_update(incoming(app, "/green", user_id=42))
    assert "Join all required channels" in api.sent[-1]["text"]
    await app.process_update(incoming_join_check(app))
    assert "Could not verify membership" in api.calls[-1][1]["text"]


def test_existing_force_join_database_is_migrated_to_multi_channel_store(tmp_path):
    path = tmp_path / "state.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE force_join (singleton INTEGER PRIMARY KEY, "
            "chat_id INTEGER NOT NULL, title TEXT NOT NULL, join_url TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO force_join VALUES (1, -100777, 'Old channel', 'https://t.me/oldchannel')"
        )

    store = ForceJoinStore(path)
    old = RequiredChat(-100777, "Old channel", "https://t.me/oldchannel")
    assert store.enabled
    assert store.configured_chats == [old]
    assert store.required_chats == [old]

    second = RequiredChat(-100999, "Second", "https://t.me/second")
    store.add_chat(second, enable=False)
    assert set(store.configured_chats) == {old, second}

    store.disable()
    reloaded = ForceJoinStore(path)
    assert not reloaded.enabled
    assert set(reloaded.configured_chats) == {old, second}

    reloaded.enable()
    assert set(ForceJoinStore(path).required_chats) == {old, second}

    assert reloaded.remove_chat(-100777)
    assert reloaded.configured_chats == [second]
    assert ForceJoinStore(path).configured_chats == [second]

