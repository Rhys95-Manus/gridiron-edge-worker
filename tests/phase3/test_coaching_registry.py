"""COA-01: the hand-maintained staff and play-caller registry, one row per team, season and
role, each with its own source_url, supporting quote and confidence (schema of 2026-10-07).
A role with no row is blank and falls back to the G4 head-coach stand-in; it never rejects
the team's other rows. Rows here are synthetic placeholders, not real coaches."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from ge.metrics.coaching import (
    CONFIDENCE,
    REGISTRY_COLUMNS,
    REGISTRY_PATH,
    ROLES,
    RegistryError,
    load_registry,
)
from tests.phase3.registry_rows import staff, write


def test_schema() -> None:
    assert REGISTRY_COLUMNS == (
        "team",
        "season",
        "role",
        "person",
        "effective_date",
        "source_url",
        "quote",
        "confidence",
    )
    assert ROLES == (
        "head_coach",
        "offensive_coordinator",
        "defensive_coordinator",
        "offensive_play_caller",
        "defensive_play_caller",
    )
    assert CONFIDENCE == ("team_or_major", "local_or_team_focused", "ranking_only")


def test_rows_load_by_role(tmp_path: Path) -> None:
    reg = load_registry(write(tmp_path / "r.csv", staff("AAA", "2024-09-08")))
    on = dt.date(2024, 9, 10)
    assert reg.caller("AAA", "offense", on) == "TEST-OPC-AAA"
    assert reg.caller("AAA", "defense", on) == "TEST-DPC-AAA"
    assert reg.person("AAA", "head_coach", on) == "TEST-HC-AAA"
    assert reg.caller("AAA", "offense", dt.date(2024, 9, 7)) is None  # before effective date
    assert reg.caller("BBB", "offense", on) is None
    cur = reg.current("AAA", on)
    assert set(cur) == set(ROLES)
    assert cur["head_coach"].confidence == "team_or_major"
    assert cur["head_coach"].quote == "synthetic test row"


def test_blank_role_is_just_absent(tmp_path: Path) -> None:
    """A team with no defensive play-caller row keeps its other roles."""
    rows = staff("AAA", "2024-09-08", roles=ROLES[:4])
    reg = load_registry(write(tmp_path / "r.csv", rows))
    on = dt.date(2024, 10, 1)
    assert reg.caller("AAA", "defense", on) is None
    assert reg.caller("AAA", "offense", on) == "TEST-OPC-AAA"
    assert "defensive_play_caller" not in reg.current("AAA", on)


def test_in_season_change_by_role(tmp_path: Path) -> None:
    rows = staff("AAA", "2024-09-08")
    rows += [{**rows[3], "person": "TEST-NEW", "effective_date": "2024-10-15"}]
    reg = load_registry(write(tmp_path / "r.csv", rows))
    assert reg.caller("AAA", "offense", dt.date(2024, 10, 14)) == "TEST-OPC-AAA"
    assert reg.caller("AAA", "offense", dt.date(2024, 10, 15)) == "TEST-NEW"
    assert reg.person("AAA", "head_coach", dt.date(2024, 10, 20)) == "TEST-HC-AAA"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_url", ""),
        ("source_url", "not a url"),
        ("effective_date", ""),
        ("effective_date", "2024-13-01"),
        ("team", ""),
        ("person", ""),
        ("quote", ""),
        ("role", "special_teams_coordinator"),
        ("confidence", "certain"),
        ("season", "twenty"),
    ],
)
def test_invalid_rows_are_rejected(tmp_path: Path, field: str, value: str) -> None:
    rows = staff("AAA", "2024-09-08")
    rows[0] = {**rows[0], field: value}
    with pytest.raises(RegistryError, match=field):
        load_registry(write(tmp_path / "r.csv", rows))


def test_duplicate_team_role_date_is_rejected(tmp_path: Path) -> None:
    rows = staff("AAA", "2024-09-08")
    rows.append({**rows[0], "person": "TEST-OTHER"})
    with pytest.raises(RegistryError, match="duplicate"):
        load_registry(write(tmp_path / "r.csv", rows))


def test_wrong_header_is_rejected(tmp_path: Path) -> None:
    p = tmp_path / "r.csv"
    p.write_text("team,effective_date\nAAA,2024-01-01\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="columns"):
        load_registry(p)


def test_repo_registry_loads_and_is_sourced() -> None:
    """config/coaching_registry.csv: every row validates; at most one row per team, role and
    date; every row has a quote and a confidence."""
    reg = load_registry(REGISTRY_PATH)
    keys = [(r.team, r.role, r.effective_date) for r in reg.rows]
    assert len(keys) == len(set(keys))
    assert all(r.quote and r.confidence in CONFIDENCE for r in reg.rows)
