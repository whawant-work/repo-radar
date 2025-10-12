from __future__ import annotations

import os
from pathlib import Path

import pytest

from repo_radar import LoadOptions, RepoRadarConfigError, load_config


def test_env_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMEZONE", "Asia/Seoul")
    monkeypatch.setenv("DAILY_AT", "08:30")
    monkeypatch.setenv("EMAIL_TO", "a@x.com,b@y.com")
    monkeypatch.setenv("EMAIL_FROM", "noreply@x.com")
    cfg = load_config()
    assert cfg.timezone == "Asia/Seoul"
    assert cfg.daily_at == "08:30"
    assert cfg.email.email_to == ["a@x.com", "b@y.com"]


@pytest.mark.parametrize("bad_time", ["9:00", "24:00", "12:60", "ab:cd"])  # invalid HH:MM
def test_invalid_daily_at_raises(monkeypatch: pytest.MonkeyPatch, bad_time: str) -> None:
    monkeypatch.setenv("DAILY_AT", bad_time)
    with pytest.raises(RepoRadarConfigError):
        load_config()


def test_invalid_repo_format_raises() -> None:
    # validation still applies when providing programmatically
    from repo_radar.config import Config, _validate

    cfg = Config(repos=["badformat"])
    with pytest.raises(RepoRadarConfigError):
        _validate(cfg)


def test_email_from_required_when_to(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_TO", "a@x.com")
    if "EMAIL_FROM" in os.environ:
        monkeypatch.delenv("EMAIL_FROM", raising=False)
    with pytest.raises(RepoRadarConfigError):
        load_config()


def test_dotenv_basic_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Put a .env in working dir
    env_file = tmp_path / ".env"
    env_file.write_text("TIMEZONE=Asia/Tokyo\nDAILY_AT=11:11\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    cfg = load_config(LoadOptions(load_dotenv=True))
    assert cfg.timezone == "Asia/Tokyo"
    assert cfg.daily_at == "11:11"


def test_dotenv_custom_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    env_file = cfg_dir / ".env"
    env_file.write_text("TIMEZONE=UTC\nDAILY_AT=06:00\n", encoding="utf-8")
    # do not chdir; use explicit path
    cfg = load_config(LoadOptions(load_dotenv=True, dotenv_path=env_file))
    assert cfg.daily_at == "06:00"


def test_dotenv_does_not_override_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # OS env should win over .env when override=False
    env_file = tmp_path / ".env"
    env_file.write_text("DAILY_AT=03:00\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DAILY_AT", "04:00")
    cfg = load_config(LoadOptions(load_dotenv=True, dotenv_override=False))
    assert cfg.daily_at == "04:00"


def test_dotenv_override_true_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DAILY_AT=03:30\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DAILY_AT", "05:00")
    cfg = load_config(LoadOptions(load_dotenv=True, dotenv_override=True))
    assert cfg.daily_at == "03:30"


def test_disable_dotenv_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("TIMEZONE=Asia/Seoul\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    # Explicitly disable .env
    cfg = load_config(LoadOptions(load_dotenv=False))
    # default is UTC
    assert cfg.timezone == "UTC"
