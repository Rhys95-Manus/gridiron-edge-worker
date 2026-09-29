"""`ge ingest` subcommands exist; config/ingest.yaml loads strictly; the NWS User-Agent is a
secret that never appears in output."""

import copy

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from ge.cli import app
from ge.config import INGEST_PATH, IngestConfig, load_ingest
from ge.settings import Settings

SUBCOMMANDS = ["nflverse", "stadiums", "weather", "kalshi", "fees-check", "report"]


def test_ingest_lists_its_subcommands() -> None:
    result = CliRunner().invoke(app, ["ingest", "--help"])
    assert result.exit_code == 0, result.output
    for sub in SUBCOMMANDS:
        assert sub in result.output


def test_ingest_yaml_loads_and_rejects_missing_keys() -> None:
    load_ingest()
    raw = yaml.safe_load(INGEST_PATH.read_text(encoding="utf-8"))
    for group, entries in raw.items():
        for name in entries:
            data = copy.deepcopy(raw)
            del data[group][name]
            with pytest.raises(ValidationError):
                IngestConfig.model_validate(data)


def test_every_ingest_setting_has_a_source() -> None:
    raw = yaml.safe_load(INGEST_PATH.read_text(encoding="utf-8"))
    for group, entries in raw.items():
        for name, e in entries.items():
            assert e["source"].strip(), f"{group}.{name}"
            assert e["status"] in {"initial", "fitted"}, f"{group}.{name}"


def test_user_agent_is_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NWS_USER_AGENT", "(TestApp, test@example.invalid)")
    s = Settings(_env_file=None)
    assert "test@example.invalid" not in repr(s)
    assert "test@example.invalid" not in str(s.model_dump())
    assert s.nws_user_agent.get_secret_value() == "(TestApp, test@example.invalid)"


def test_missing_user_agent_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NWS_USER_AGENT", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
