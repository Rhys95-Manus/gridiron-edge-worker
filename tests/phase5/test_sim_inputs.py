"""Phase 5 fit inputs and the remaining v5 fits (rulings D1-D7, 2026-10-24). Every frame here is
a synthetic placeholder, not real games or players; every number is hand-computed in the test.

- D2: surface classes. D3/D6: tilt rows, x as written (the play included) and leave-one-out.
- D5: weather rows. D4: xpass/cp distillation. D7: Questionable/Doubtful play rows.
- v5 = v4 plus the Phase 5 keys, every v4 entry unchanged."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest
import yaml

from ge.config import ATTRIBUTION, FittedFile
from ge.fit.distill import DISTILL_FEATURES, design, distill_fit, predict
from ge.fit.sim_inputs import (
    game_status_rows,
    surface_class,
    tilt_rows,
    weather_rows,
)
from ge.fit.sim_write import write_v5


@pytest.mark.parametrize(
    ("raw", "cls"),
    [
        ("grass", "natural"),
        ("grass ", "natural"),
        ("fieldturf", "artificial"),
        ("matrixturf", "artificial"),
        ("sportturf", "artificial"),
        ("astroturf", "artificial"),
        ("a_turf", "artificial"),
        ("", None),
        (None, None),
    ],
)
def test_surface_classes(raw: str | None, cls: str | None) -> None:
    assert surface_class(raw) == cls


def test_surface_class_unknown_value_raises() -> None:
    with pytest.raises(ValueError, match="ENV-01"):
        surface_class("moonrock")


def _plays() -> pl.DataFrame:
    """One team-game (G1, AAA) with three pass plays and two designed runs, plus one garbage-
    time pass (4th quarter, wp 0.99) that G7 removes. Columns as nflverse pbp."""
    rows = [
        # pass, rush, att, cmp, sack, int, scr, kneel, epa, yac, yards, fum, qtr, wp
        (1, 0, 1, 1, 0, 0, 0, 0, 0.6, 5.0, 12, 0, 1, 0.5),
        (1, 0, 1, 0, 0, 1, 0, 0, -1.5, None, 0, 0, 2, 0.5),
        (1, 0, 0, 0, 1, 0, 0, 0, -0.9, None, -7, 0, 2, 0.5),  # sack: in x, not an attempt
        (0, 1, 0, 0, 0, 0, 0, 0, 0.2, None, 4, 0, 3, 0.5),
        (0, 1, 0, 0, 0, 0, 0, 0, -0.4, None, -1, 1, 3, 0.5),
        (1, 0, 1, 1, 0, 0, 0, 0, 2.0, 30.0, 40, 0, 4, 0.99),  # G7 garbage time: left out
    ]
    cols = "pass rush pass_attempt complete_pass sack interception qb_scramble qb_kneel epa"
    cols += " yards_after_catch yards_gained fumble_lost qtr wp"
    names = cols.split()
    data = {n: [r[i] for r in rows] for i, n in enumerate(names)}
    n = len(rows)
    return pl.DataFrame(
        {
            "game_id": ["G1"] * n,
            "season": [2016] * n,
            "posteam": ["AAA"] * n,
            "play_type": ["pass", "pass", "pass", "run", "run", "pass"],
            "qb_spike": [0] * n,
            "two_point_attempt": [0] * n,
            "half_seconds_remaining": [900] * n,
            **data,
        },
        schema_overrides={"yards_after_catch": pl.Float64},
    )


def test_tilt_rows_x_is_leave_one_out() -> None:
    """Ruling 2026-10-24: the fitted predictor x is leave-one-out (the play's own EPA removed),
    centred on the season league mean; the as-written value stays as x_written.
    Pass plays (incl. the sack): EPA 0.6, -1.5, -0.9; game mean and league mean -0.6, so
    x_written = 0. Leave-one-out (raw): completion row 1 -> (-1.5 - 0.9) / 2 = -1.2, centred
    -0.6; row 2 -> (0.6 - 0.9) / 2 = -0.15, centred 0.45. Runs: EPA 0.2, -0.4, mean -0.1;
    LOO raw row 4 -> -0.4 (centred -0.3), row 5 -> 0.2 (centred 0.3)."""
    r = tilt_rows(_plays())
    comp = r.filter(pl.col("component") == "completion").sort("y", descending=True)
    assert comp["y"].to_list() == [1.0, 0.0]
    assert comp["x"].to_list() == pytest.approx([-0.6, 0.45])
    assert comp["x_written"].to_list() == pytest.approx([0.0, 0.0])
    assert comp["x_raw"].to_list() == pytest.approx([-0.6, -0.6])
    assert comp["x_loo_raw"].to_list() == pytest.approx([-1.2, -0.15])
    ints = r.filter(pl.col("component") == "interception").sort("y")
    assert ints["y"].to_list() == [0.0, 1.0]
    yac = r.filter(pl.col("component") == "yac")
    assert yac["y"].to_list() == [5.0]
    ypc = r.filter(pl.col("component") == "yards_per_carry").sort("y")
    assert ypc["y"].to_list() == [-1.0, 4.0]
    assert ypc["x_raw"].to_list() == pytest.approx([-0.1, -0.1])
    assert ypc["x_loo_raw"].to_list() == pytest.approx([0.2, -0.4])
    assert ypc["x"].to_list() == pytest.approx([0.3, -0.3])
    fum = r.filter(pl.col("component") == "fumble_lost").sort("y")
    assert fum["y"].to_list() == [0.0, 1.0]
    assert set(r["team_game"].unique().to_list()) == {"G1|AAA"}


def test_weather_rows_completion_deep_and_fg() -> None:
    plays = pl.DataFrame(
        {
            "game_id": ["G1", "G1", "G1", "G1", "G2"],
            "season": [2016] * 5,
            "posteam": ["AAA"] * 5,
            "play_type": ["pass", "pass", "pass", "field_goal", "pass"],
            "pass": [1, 1, 1, 0, 1],
            "rush": [0] * 5,
            "pass_attempt": [1, 1, 0, 0, 1],
            "sack": [0, 0, 1, 0, 0],
            "complete_pass": [1, 0, 0, 0, 1],
            "air_yards": [25.0, None, None, None, 5.0],
            "field_goal_attempt": [0, 0, 0, 1, 0],
            "field_goal_result": [None, None, None, "made", None],
            "kick_distance": [None, None, None, 45.0, None],
            "qb_kneel": [0] * 5,
            "qb_spike": [0] * 5,
            "two_point_attempt": [0] * 5,
            "qtr": [1] * 5,
            "wp": [0.5] * 5,
            "half_seconds_remaining": [900] * 5,
        },
        schema_overrides={"field_goal_result": pl.String},
    )
    windows = pl.DataFrame(  # G2 has no ERA5 window (a dome game): left out
        {
            "game_id": ["G1"],
            "precipitation_mm": [1.0],
            "snowfall_cm": [0.0],
            "wind_speed_kmh": [20.0],
            "wind_gusts_kmh": [35.0],
            "temperature_c": [5.0],
        }
    )
    elevation = {"G1": 300.0}
    rows = weather_rows(plays, windows, elevation)
    comp = rows["completion"]
    assert comp["y"].to_list() == [1.0, 0.0]  # two attempts, the sack left out
    assert comp["wind_speed"].to_list() == [20.0, 20.0]
    assert rows["deep_attempt"]["y"].to_list() == [1.0]  # only the attempt with air_yards
    fg = rows["fg_make"]
    assert fg.select("y", "distance", "altitude").rows() == [(1.0, 45.0, 300.0)]


def test_distill_recovers_planted_fractional_logit() -> None:
    rng = np.random.default_rng(31)
    n = 20_000
    x = rng.normal(0, 1, (n, 2))
    eta = -0.3 + 0.8 * x[:, 0] - 0.5 * x[:, 1]
    target = 1 / (1 + np.exp(-eta))  # a smooth model's own probabilities, no noise
    fit = distill_fit(np.column_stack([np.ones(n), x]), target)
    assert fit.coef == pytest.approx([-0.3, 0.8, -0.5], abs=1e-6)
    assert fit.agreement.corr == pytest.approx(1.0, abs=1e-9)
    assert fit.agreement.mae == pytest.approx(0.0, abs=1e-6)
    assert len(fit.agreement.deciles) == 10


def _states(n: int, seed: int) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    return pl.DataFrame(
        {
            "down": rng.integers(1, 5, n).astype(float),
            "ydstogo": rng.integers(1, 20, n).astype(float),
            "yardline_100": rng.integers(1, 99, n).astype(float),
            "qtr": rng.integers(1, 5, n).astype(float),
            "half_seconds_remaining": rng.uniform(0, 1800, n),
            "game_seconds_remaining": rng.uniform(0, 3600, n),
            "score_differential": rng.integers(-21, 22, n).astype(float),
            "wp": rng.uniform(0.01, 0.99, n),
            "posteam_timeouts_remaining": rng.integers(0, 4, n).astype(float),
            "defteam_timeouts_remaining": rng.integers(0, 4, n).astype(float),
        }
    )


def test_xpass_and_wp_have_distance_within_each_down() -> None:
    """Ruling 2026-10-25: ydstogo enters linear and squared within each down (one pair per down
    level) instead of once overall; the other terms are unchanged."""
    d = _states(400, 41).with_columns(pl.lit(0.5).alias("xpass"))
    _, names, _ = design(d, "xpass")
    for lv in ("1.0", "2.0", "3.0", "4.0"):
        assert f"ydstogo|down={lv}" in names and f"ydstogo^2|down={lv}" in names
    assert "ydstogo" not in names and "ydstogo^2" not in names
    assert "down=2.0" in names  # the down indicators stay
    d2 = _states(400, 42).with_columns(pl.lit(0.5).alias("wp"))
    _, names_wp, _ = design(d2, "wp")
    assert "ydstogo|down=3.0" in names_wp


def test_planted_down_by_distance_pattern_is_reproduced() -> None:
    """Short yardage on 3rd down runs, on 1st down passes: a target with opposite distance
    slopes by down is fitted exactly (no noise), and predict() matches the design."""
    d = _states(20_000, 43)
    slope = d["down"].replace_strict({1.0: -0.2, 2.0: 0.0, 3.0: 0.3, 4.0: 0.25})
    eta = -1.0 + slope * d["ydstogo"] - 0.004 * d["yardline_100"]
    target = 1 / (1 + np.exp(-eta.to_numpy()))
    d = d.with_columns(pl.Series("xpass", target))
    X, names, used = design(d, "xpass")
    fit = distill_fit(X, used["xpass"].to_numpy(), names)
    assert fit.agreement.mae < 1e-4
    coef = dict(zip(names, fit.coef.tolist(), strict=True))
    np.testing.assert_allclose(predict(coef, used), target, atol=1e-4)


def test_distill_feature_lists_follow_the_spec() -> None:
    assert set(DISTILL_FEATURES["xpass"]) == {
        "down",
        "ydstogo",
        "yardline_100",
        "qtr",
        "half_seconds_remaining",
        "score_differential",
        "wp",
        "posteam_timeouts_remaining",
        "defteam_timeouts_remaining",
    }
    # ruling E1 (2026-10-24): wp(state) distilled from nflverse wp, no betting-line features
    assert set(DISTILL_FEATURES["wp"]) == {
        "score_differential",
        "game_seconds_remaining",
        "half_seconds_remaining",
        "yardline_100",
        "down",
        "ydstogo",
        "posteam_timeouts_remaining",
        "defteam_timeouts_remaining",
        "qtr",
    }
    assert set(DISTILL_FEATURES["cp"]) == {
        "air_yards",
        "yardline_100",
        "ydstogo",
        "down",
        "pass_location",
    }


def test_game_status_rows_offensive_players_and_offensive_snaps() -> None:
    """Q WR who played offense: played. Q TE with only special-teams snaps: not played. D QB
    with no snaps: not played. Q LB (defense): left out. Out RB: left out (not Q or D)."""
    injuries = pl.DataFrame(
        {
            "gsis_id": ["p1", "p2", "p3", "p4", "p5"],
            "team": ["AAA"] * 5,
            "week": [3] * 5,
            "position": ["WR", "TE", "QB", "LB", "RB"],
            "report_status": ["Questionable", "Questionable", "Doubtful", "Questionable", "Out"],
        }
    )
    snaps = pl.DataFrame(
        {
            "gsis_id": ["p1", "p2", "p4"],
            "team": ["AAA"] * 3,
            "week": [3] * 3,
            "offense_snaps": [40, 0, 0],
        }
    )
    team_weeks = pl.DataFrame({"team": ["AAA"], "week": [3]})
    r = game_status_rows(injuries, snaps, team_weeks).sort("gsis_id")
    assert r.select("gsis_id", "status", "played").rows() == [
        ("p1", "Questionable", True),
        ("p2", "Questionable", False),
        ("p3", "Doubtful", False),
    ]


def _v4_file(root: Path) -> None:
    body = {
        "fit_version": "v4",
        "window": "S2021",
        "test_season": 2021,
        "seasons": [2016, 2017, 2018, 2019, 2020],
        "data_as_of": "2026-10-09T00:00:00+00:00",
        "data_digest": "d4",
        "code_commit": "c4",
        "attribution": ATTRIBUTION,
        "values": {
            "fit:G6/penalty": {
                "spec_id": "G6",
                "status": "fitted",
                "value": 100.0,
                "method": "m",
                "seasons": [2016, 2017],
                "n": 5,
                "initial_value": None,
            }
        },
        "missing": {"fit:k/X/y": "why"},
        "no_signal": {"fit:k/Z/w": "none"},
    }
    (root / "v4").mkdir(parents=True)
    (root / "v4" / "S2021.yaml").write_text(yaml.safe_dump(body), encoding="utf-8")


def test_write_v5_keeps_every_v4_entry_and_adds_phase5_keys(tmp_path: Path) -> None:
    _v4_file(tmp_path)
    new = {
        "fit:PRJ-02/h_l": {
            "spec_id": "PRJ-02",
            "status": "fitted",
            "value": 8.0,
            "method": "m5",
            "seasons": [2016, 2017, 2018, 2019, 2020],
            "n": 105,
            "initial_value": None,
        }
    }
    path = write_v5(
        tmp_path,
        "S2021",
        values=new,
        missing={"fit:PRJ-02/x": "pending"},
        no_signal={"fit:MTC-05/completion/snowfall": "95% interval includes 0"},
        data_digest="d5",
        code_commit="c5",
        base="v4",
        version="v5",
    )
    v5 = yaml.safe_load(path.read_text(encoding="utf-8"))
    FittedFile.model_validate(v5)
    v4 = yaml.safe_load((tmp_path / "v4" / "S2021.yaml").read_text(encoding="utf-8"))
    for k, v in v4["values"].items():
        assert v5["values"][k] == v
    assert v5["values"]["fit:PRJ-02/h_l"]["value"] == 8.0
    assert v5["missing"]["fit:k/X/y"] == "why" and "fit:PRJ-02/x" in v5["missing"]
    assert v5["no_signal"]["fit:k/Z/w"] == "none"
    assert v5["fit_version"] == "v5"
    assert "v4" in path.read_text(encoding="utf-8").splitlines()[0]  # header names the base


def test_write_v5_refuses_to_overwrite_a_v4_key(tmp_path: Path) -> None:
    _v4_file(tmp_path)
    clash = {
        "fit:G6/penalty": {
            "spec_id": "G6",
            "status": "fitted",
            "value": 1.0,
            "method": "x",
            "seasons": [2016],
            "n": 1,
            "initial_value": None,
        }
    }
    with pytest.raises(ValueError, match="v4"):
        write_v5(
            tmp_path,
            "S2021",
            values=clash,
            missing={},
            no_signal={},
            data_digest="d",
            code_commit="c",
            base="v4",
            version="v5",
        )
