"""MTC-01 yards-per-carry matchup shift on synthetic frames (registry reads patched).

Ruling 2026-10-27: when no run cell has the minimum carries on both sides, MTC-01 is 0 and the
league value is not read. With no qualifying cell every cell uses the overall devs, so the
formula cancels to 0 whatever the league value is; before a season's first play (2024 week 1:
the opener and the Friday game) that league value is null."""

from __future__ import annotations

from typing import Any

import polars as pl
import pytest

from ge.config import load_params
from ge.metrics.plays import RUN_CELLS
from ge.models.sim import inputs

OFF, DFN = "AAA", "BBB"
LAM = 0.5


def _min_carries() -> float:
    return float(load_params().matchup.mtc_01_min_carries_per_cell.value)


def _shrunk_frame(
    spec_id: str, team: str, values: dict[str, float], k: float = 50.0
) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "spec_id": [spec_id] * len(values),
            "team": [team] * len(values),
            "cell": list(values),
            "shrunk": list(values.values()),
            "k": [k] * len(values),
        }
    )


def _raw_frame(
    team: str, carries: dict[str, float], league_ypc: dict[str, float | None]
) -> pl.DataFrame:
    rows: list[dict[str, Any]] = [
        {"entity_type": "team", "team": team, "stat": "carries", "cell": c, "value": n}
        for c, n in carries.items()
    ]
    rows += [
        {"entity_type": "league", "team": None, "stat": stat, "cell": c, "value": v}
        for c, v in league_ypc.items()
        for stat in (["ypc_team"] if c == "all" else ["ypc"])
    ]
    return pl.DataFrame(rows, schema_overrides={"value": pl.Float64, "team": pl.String})


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    carries: dict[str, float],
    league_ypc: dict[str, float | None],
) -> None:
    cell_ypc = {c: 4.0 + 0.1 * i for i, c in enumerate(RUN_CELLS)}
    share = {c: 1.0 / len(RUN_CELLS) for c in RUN_CELLS}
    frames = {
        ("OFF-12", "ypc"): _shrunk_frame("OFF-12", OFF, cell_ypc),
        ("DEF-03", "ypc"): _shrunk_frame("DEF-03", DFN, cell_ypc),
        ("OFF-12", "ypc_team"): _shrunk_frame("OFF-12", OFF, {"all": 4.6}),
        ("DEF-03", "ypc_team"): _shrunk_frame("DEF-03", DFN, {"all": 4.2}),
        ("OFF-12", "share"): _shrunk_frame("OFF-12", OFF, share),
    }
    raws = {
        "OFF-12": _raw_frame(OFF, carries, league_ypc),
        "DEF-03": _raw_frame(DFN, carries, league_ypc),
    }
    monkeypatch.setattr(inputs, "shrunk", lambda ctx, spec_id, stat: frames[(spec_id, stat)])
    monkeypatch.setattr(inputs, "raw", lambda ctx, spec_id: raws[spec_id])


def test_no_qualifying_cell_is_zero_without_the_league_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No carries this season and a null league value (a season's first game): MTC-01 = 0."""
    _patch(
        monkeypatch,
        carries={c: 0.0 for c in RUN_CELLS},
        league_ypc={"all": None, **{c: None for c in RUN_CELLS}},
    )
    assert inputs._mtc01(None, OFF, DFN, LAM) == 0.0  # type: ignore[arg-type]


def test_one_qualifying_cell_keeps_the_formula(monkeypatch: pytest.MonkeyPatch) -> None:
    """One cell at the minimum on both sides: lambda x s_c x [(dev_off_c + dev_def_c) -
    (dev_off_all + dev_def_all)], every other cell cancelling."""
    c0 = RUN_CELLS[0]
    lg_cell = {c: 4.3 for c in RUN_CELLS}
    _patch(
        monkeypatch,
        carries={c: (_min_carries() if c == c0 else 0.0) for c in RUN_CELLS},
        league_ypc={"all": 4.4, **lg_cell},
    )
    s = 1.0 / len(RUN_CELLS)
    dev_cell = (4.0 - 4.3) + (4.0 - 4.3)
    dev_all = (4.6 - 4.4) + (4.2 - 4.4)
    expected = LAM * s * (dev_cell - dev_all)
    assert inputs._mtc01(None, OFF, DFN, LAM) == pytest.approx(expected, rel=1e-12)  # type: ignore[arg-type]
