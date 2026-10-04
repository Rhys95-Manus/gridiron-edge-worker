"""COA-01: the hand-maintained staff and play-caller registry. Validation fails any row
without a source_url or effective date (BUILD_PLAN Phase 3). Rows here are synthetic
placeholders, not real coaches."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from ge.metrics.coaching import REGISTRY_COLUMNS, REGISTRY_PATH, RegistryError, load_registry

GOOD = {
    "team": "AAA",
    "head_coach": "TEST-HC",
    "offensive_coordinator": "TEST-OC",
    "defensive_coordinator": "TEST-DC",
    "offensive_play_caller": "TEST-OC",
    "defensive_play_caller": "TEST-DC",
    "effective_date": "2024-02-01",
    "source_url": "https://example.invalid/a",
}


def _write(path: Path, rows: list[dict[str, str]]) -> Path:
    lines = [",".join(REGISTRY_COLUMNS)]
    lines += [",".join(r[c] for c in REGISTRY_COLUMNS) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_valid_row_loads(tmp_path: Path) -> None:
    reg = load_registry(_write(tmp_path / "r.csv", [GOOD]))
    assert reg.caller("AAA", "offense", dt.date(2024, 9, 1)) == "TEST-OC"
    assert reg.caller("AAA", "defense", dt.date(2024, 9, 1)) == "TEST-DC"
    assert reg.caller("AAA", "offense", dt.date(2024, 1, 1)) is None  # before effective date
    assert reg.caller("BBB", "offense", dt.date(2024, 9, 1)) is None


def test_latest_row_on_or_before_date_wins(tmp_path: Path) -> None:
    later = {**GOOD, "offensive_play_caller": "TEST-HC", "effective_date": "2024-10-15"}
    reg = load_registry(_write(tmp_path / "r.csv", [GOOD, later]))
    assert reg.caller("AAA", "offense", dt.date(2024, 10, 14)) == "TEST-OC"
    assert reg.caller("AAA", "offense", dt.date(2024, 10, 15)) == "TEST-HC"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_url", ""),
        ("source_url", "not a url"),
        ("effective_date", ""),
        ("effective_date", "2024-13-01"),
        ("team", ""),
        ("offensive_play_caller", ""),
    ],
)
def test_invalid_rows_are_rejected(tmp_path: Path, field: str, value: str) -> None:
    with pytest.raises(RegistryError, match=field):
        load_registry(_write(tmp_path / "r.csv", [{**GOOD, field: value}]))


def test_wrong_header_is_rejected(tmp_path: Path) -> None:
    p = tmp_path / "r.csv"
    p.write_text("team,effective_date\nAAA,2024-01-01\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="columns"):
        load_registry(p)


def test_repo_registry_loads() -> None:
    """config/coaching_registry.csv exists and every row in it validates."""
    assert REGISTRY_PATH.exists()
    load_registry(REGISTRY_PATH)
