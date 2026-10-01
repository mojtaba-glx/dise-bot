from pathlib import Path

import pytest

from dise_bot.app import main
from dise_bot.config import ConfigurationError, load_settings

TOKEN = "123456789:TEST_TOKEN_FOR_OFFLINE_TESTS_ONLY"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("BOT_TOKEN", "COOLDOWN_SECONDS", "LOG_LEVEL", "STATE_DB_PATH", "OWNER_USER_ID"):
        monkeypatch.delenv(name, raising=False)


def test_environment_overrides_file_and_token_is_not_in_repr(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("BOT_TOKEN=111:FILE_TOKEN\nCOOLDOWN_SECONDS=2\nLOG_LEVEL=debug\n")
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    settings = load_settings(env_file)
    assert settings.token == TOKEN
    assert settings.log_level == "DEBUG"
    assert TOKEN not in repr(settings)


def test_missing_token_has_actionable_error(tmp_path):
    with pytest.raises(ConfigurationError, match="Set BOT_TOKEN"):
        load_settings(tmp_path / "missing.env")


@pytest.mark.parametrize("token", ["invalid-secret", "123:bad secret", "your_bot_token_here"])
def test_invalid_token_is_not_echoed(token, tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", token)
    with pytest.raises(ConfigurationError) as exc:
        load_settings(tmp_path / ".env")
    assert token not in str(exc.value)


def test_old_cooldown_setting_no_longer_blocks_startup(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    monkeypatch.setenv("COOLDOWN_SECONDS", "obsolete")
    assert load_settings(tmp_path / ".env").token == TOKEN


def test_unknown_log_level_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")
    with pytest.raises(ConfigurationError, match="LOG_LEVEL"):
        load_settings(tmp_path / ".env")


def test_state_db_path_can_be_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    monkeypatch.setenv("STATE_DB_PATH", str(tmp_path / "state.sqlite3"))
    assert load_settings(tmp_path / ".env").state_db_path == tmp_path / "state.sqlite3"


def test_state_db_path_rejects_existing_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    monkeypatch.setenv("STATE_DB_PATH", str(tmp_path))
    with pytest.raises(ConfigurationError, match="must point to a file"):
        load_settings(tmp_path / ".env")


def test_owner_id_can_be_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    monkeypatch.setenv("OWNER_USER_ID", "12345")
    assert load_settings(tmp_path / ".env").owner_user_id == 12345


@pytest.mark.parametrize("value", ["0", "-1", "abc", "۱۲۳", str(2**63)])
def test_invalid_owner_id_is_rejected(tmp_path, monkeypatch, value):
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    monkeypatch.setenv("OWNER_USER_ID", value)
    with pytest.raises(ConfigurationError, match="OWNER_USER_ID"):
        load_settings(tmp_path / ".env")


def test_check_cli_works_without_connecting(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    assert main(["--check", "--env-file", str(tmp_path / ".env")]) == 0
    output = capsys.readouterr()
    assert "Telegram connection not tested" in output.out
    assert TOKEN not in output.out + output.err


def test_missing_token_cli_returns_configuration_exit_code(tmp_path, capsys):
    assert main(["--check", "--env-file", str(Path(tmp_path) / ".env")]) == 2
    assert "Set BOT_TOKEN" in capsys.readouterr().err
