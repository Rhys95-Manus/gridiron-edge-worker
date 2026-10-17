"""Decision log 2026-10-16: the extended attribution line is the only one written from
2026-10-16; the validator still accepts the previous line, but only on the fitted files written
before that date (params fits v1-v3, ratings fits r1-r2), which hold no ff_opportunity data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ge.config import ATTRIBUTION, LEGACY_ATTRIBUTION, load_params, params_for

FIRST = int(load_params().backtest.bt_01_first_training_season.value)
OLD_LINE = "Data: nflverse; charting: FTN Data via nflverse"


def _body(version: str, attribution: str) -> dict[str, Any]:
    return {
        "fit_version": version,
        "window": "S2023",
        "test_season": 2023,
        "seasons": list(range(FIRST, 2023)),
        "data_as_of": "2026-10-09T00:00:00+00:00",
        "data_digest": "0" * 64,
        "code_commit": "test",
        "attribution": attribution,
        "values": {},
        "missing": {},
    }


def _root(tmp: Path, version: str, attribution: str) -> Path:
    r = tmp / "pf"
    (r / version).mkdir(parents=True)
    (r / version / "S2023.yaml").write_text(
        yaml.safe_dump(_body(version, attribution)), encoding="utf-8"
    )
    (r / "active.yaml").write_text(f"fit_version: {version}\n", encoding="utf-8")
    return r


def test_legacy_line_is_the_previous_line() -> None:
    assert LEGACY_ATTRIBUTION.line == OLD_LINE
    assert LEGACY_ATTRIBUTION.fit_versions == ("v1", "v2", "v3", "r1", "r2")


@pytest.mark.parametrize("version", ["v1", "v2", "v3", "r1", "r2"])
def test_old_line_accepted_on_files_written_before_2026_10_16(tmp_path: Path, version: str) -> None:
    params_for(2023, _root(tmp_path, version, OLD_LINE))


@pytest.mark.parametrize("version", ["v4", "r3", "tv"])
def test_old_line_rejected_on_any_other_file(tmp_path: Path, version: str) -> None:
    with pytest.raises(ValueError, match="attribution"):
        params_for(2023, _root(tmp_path, version, OLD_LINE))


@pytest.mark.parametrize("version", ["v3", "v4"])
def test_new_line_accepted(tmp_path: Path, version: str) -> None:
    params_for(2023, _root(tmp_path, version, ATTRIBUTION))
