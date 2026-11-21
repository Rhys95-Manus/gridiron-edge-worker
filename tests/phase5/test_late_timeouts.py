"""PRJ-02 late-half timeouts (fix round 2, approved by Rhys 2026-11-20;
plans/phase5-late-timeouts.md), behind config/sim.yaml late_timeouts.enabled. Inside the last
two minutes of the 2nd or 4th quarter: T1, the timeout decision comes at the end of a
running-clock play, before the clock runoff, and a called timeout draws the time to the next
snap from a league table of snap-to-snap seconds with a timeout between (running-clock
categories, inside/outside two minutes, each falling back to the other); T2, the offense then
the defense calls one at a league rate per [half, role, seconds bin (config
late_timeouts.seconds_upper, the last bin to two minutes), score state from that team's side], a
cell with fewer than min_category_events plays falling back to the cell without score state,
then without the seconds bin, then to the role in that half; T3, at the first scrimmage snap
inside two minutes of each half, each team's timeouts are set to the smaller of what it has and
a draw from the window's distribution of timeouts left there, by half and role. Diagnostic
counters never draw. Synthetic placeholder data only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from ge.models.sim import arrays as A
from ge.models.sim.league import (
    RUNNING_CLOCK,
    timeout_cell_rates,
    timeout_clock_table,
    timeouts_left_dist,
)
from ge.models.sim.settings import load_sim
from tests.phase5.sim_synth import _packed, synthetic_game, synthetic_league

GOLDEN = Path(__file__).parent / "fixtures" / "late_timeouts_off_hash.json"
DROP_FROM = 2022  # data correction D boundary (test setting; pairs below use row order, 2019)
NR = len(RUNNING_CLOCK)


# ---------------------------------------------------------------- settings and layout


def test_late_timeouts_settings_come_from_config() -> None:
    s = load_sim().late_timeouts
    assert s.enabled.value is True
    assert s.seconds_upper.value == [30, 60]
    for e in (s.enabled, s.seconds_upper):
        assert e.spec_id == "PRJ-02" and e.status == "initial"
    assert len(s.seconds_upper.value) == A.LT_SEC_BINS - 1


def test_counter_layout() -> None:
    assert A.R_LT_CALLED0 == A.R_EFG_ELIG_S0 + 2 * A.EFG_SEC_BINS
    assert A.R_LT_LEFT0 == A.R_LT_CALLED0 + 4
    assert A.R_EFG_ATT_S0 == A.R_LT_LEFT0 + 2
    assert A.NTEAM == A.R_EFG_ATT_S0 + 2 * A.EFG_SEC_BINS
    assert (A.LT_SEC_BINS, A.TL_VALUES) == (3, 4)


# ---------------------------------------------------------------- fits (synthetic plays)

_FLAGS = ("out_of_bounds", "complete_pass", "incomplete_pass", "sack", "interception",
          "fumble_lost", "touchdown", "two_point_attempt", "penalty")  # fmt: skip


def _row(gid: str, pid: float, qtr: float, sec: float, sd: float, kind: str, *,
         off_to: float = 2.0, def_to: float = 2.0) -> dict[str, object]:  # fmt: skip
    r: dict[str, object] = {f: 0 for f in _FLAGS}
    r.update(game_id=gid, play_id=pid, season=2019, game_half="Half1" if qtr <= 2 else "Half2",
             qtr=qtr, posteam="AAA", defteam="BBB", home_team="AAA", away_team="BBB",
             timeout=0, timeout_team=None, game_seconds_remaining=sec,
             half_seconds_remaining=sec, score_differential=sd,
             posteam_timeouts_remaining=off_to, defteam_timeouts_remaining=def_to,
             home_timeouts_remaining=off_to, away_timeouts_remaining=def_to, w=1.0)  # fmt: skip
    r["play_type"] = {"run": "run", "complete": "pass", "sack": "pass", "kneel": "qb_kneel",
                      "incomplete": "pass"}[kind]  # fmt: skip
    if kind == "complete":
        r["complete_pass"] = 1
    elif kind == "sack":
        r["sack"] = 1
    elif kind == "incomplete":
        r["incomplete_pass"] = 1
    return r


def _pair(gid: str, qtr: float, sec: float, sd: float, *, kind: str = "run",
          called: str | None = None, runoff: float = 6.0) -> list[dict[str, object]]:  # fmt: skip
    """A play of `kind` at `sec`, then (optionally) a timeout row by the offense AAA or the
    defense BBB, then an incomplete pass `runoff` seconds later (the next snap)."""
    rows = [_row(gid, 1.0, qtr, sec, sd, kind)]
    if called:
        t = _row(gid, 2.0, qtr, sec - runoff, sd, "incomplete")
        t.update(play_type="no_play", incomplete_pass=0, posteam=None, defteam=None, timeout=1,
                 timeout_team="AAA" if called == "off" else "BBB")  # fmt: skip
        rows.append(t)
    rows.append(_row(gid, 3.0, qtr, sec - runoff, sd, "incomplete"))
    return rows


def _frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema_overrides={"timeout_team": pl.String, "posteam": pl.String,
                                                "defteam": pl.String})  # fmt: skip


def test_timeout_clock_table_by_running_category() -> None:
    """Category = RUNNING_CLOCK index + len(RUNNING_CLOCK) x inside two minutes; an empty one
    falls back to the same outcome in the other regime."""
    rows = (_pair("a", 2, 100, 0, called="off", runoff=6.0)
            + _pair("b", 2, 90, 0, called="off", runoff=10.0)
            + _pair("c", 2, 400, 0, kind="complete", called="def", runoff=12.0)
            + _pair("d", 4, 80, 0, kind="sack", called="off", runoff=7.0)
            + _pair("e", 4, 50, 3, kind="kneel", called="def", runoff=3.0)
            + _pair("f", 2, 100, 0, runoff=30.0))  # no timeout: not in this table  # fmt: skip
    p = timeout_clock_table(_frame(rows), two_minute=120, min_events=1, drop_from=DROP_FROM)
    run_in = RUNNING_CLOCK.index("run_inbounds") + NR
    assert p.values[p.lo[run_in] : p.hi[run_in]].tolist() == [6.0, 10.0]
    assert p.cum[p.lo[run_in] : p.hi[run_in]].tolist() == pytest.approx([0.5, 1.0])
    comp_in = RUNNING_CLOCK.index("complete_inbounds") + NR
    assert p.source[comp_in] == comp_in - NR  # inside falls back to outside
    assert p.values[p.lo[comp_in] : p.hi[comp_in]].tolist() == [12.0]
    assert len(p.lo) == 2 * NR


def test_timeout_cell_rates_and_fallback() -> None:
    """Q4, offense (min_events = 2): 0-30 s trailing has 1 play (a timeout), 0-30 s tied 2 plays
    (none). Trailing 0-30 s is thin -> the cell without score state: 1/3. Tied 0-30 s: 0/2.
    31-60 s has no plays: trailing -> the cell without the seconds bin (1 play, thin) -> the role
    in the half: 1/3; tied -> without the seconds bin: 0/2. Leading 0-30 s -> without state 1/3."""
    rows = (_pair("a", 4, 20, -3, called="off") + _pair("b", 4, 25, 0) + _pair("c", 4, 28, 0)
            + _pair("q1", 2, 100, 0) + _pair("q2", 2, 110, 0))  # fmt: skip
    r = timeout_cell_rates(_frame(rows), two_minute=120, seconds_upper=[30, 60], min_events=2,
                           drop_from=DROP_FROM)  # fmt: skip
    assert r.shape == (2, 2, A.LT_SEC_BINS, 3)
    trailing, tied, leading = 0, 1, 2
    assert r[1, 0, 0, trailing] == pytest.approx(1 / 3)
    assert r[1, 0, 0, tied] == pytest.approx(0.0)
    assert r[1, 0, 0, leading] == pytest.approx(1 / 3)
    assert r[1, 0, 1, trailing] == pytest.approx(1 / 3)
    assert r[1, 0, 1, tied] == pytest.approx(0.0)
    assert r[1, 1, 0, :].tolist() == pytest.approx([0.0] * 3)  # the defense never called one


def test_timeout_cell_rates_raise_with_no_plays_for_a_role_and_half() -> None:
    rows = _pair("a", 4, 20, -3, called="off") + _pair("b", 4, 25, 0)  # no Q2 plays
    with pytest.raises(NotImplementedError, match="PRJ-02"):
        timeout_cell_rates(_frame(rows), two_minute=120, seconds_upper=[30, 60], min_events=1,
                           drop_from=DROP_FROM)  # fmt: skip


def test_timeouts_left_distribution() -> None:
    """The first scrimmage snap inside two minutes of each 2nd and 4th quarter, per role."""
    rows = [
        _row("g1", 1.0, 2, 300, 0, "run", off_to=3, def_to=3),  # outside two minutes: ignored
        _row("g1", 2.0, 2, 115, 0, "run", off_to=3, def_to=1),
        _row("g1", 3.0, 2, 60, 0, "run", off_to=0, def_to=1),  # not the first: ignored
        _row("g1", 4.0, 4, 100, 0, "run", off_to=2, def_to=2),
        _row("g2", 1.0, 2, 90, 0, "run", off_to=1, def_to=3),
        _row("g2", 2.0, 4, 30, 0, "kneel", off_to=0, def_to=2),
    ]
    p = timeouts_left_dist(_frame(rows), two_minute=120)
    assert p.shape == (2, 2, A.TL_VALUES)
    assert p[0, 0].tolist() == pytest.approx([0.0, 0.5, 0.0, 0.5])
    assert p[0, 1].tolist() == pytest.approx([0.0, 0.5, 0.0, 0.5])
    assert p[1, 0].tolist() == pytest.approx([0.5, 0.0, 0.5, 0.0])
    assert p[1, 1].tolist() == pytest.approx([0.0, 0.0, 1.0, 0.0])


# ---------------------------------------------------------------- engine


def test_t3_never_adds_timeouts() -> None:
    from ge.models.sim.engine import lt_left_draw, t3_timeouts

    probs = np.array([0.0, 0.0, 0.0, 1.0])
    assert lt_left_draw(probs, 0.5) == 3
    assert t3_timeouts(1, probs, 0.5) == 1
    assert t3_timeouts(3, np.array([0.25, 0.25, 0.25, 0.25]), 0.3) == 1


def _league(**kw):  # type: ignore[no-untyped-def]
    """Synthetic league with the late-timeouts arrays set for a test."""
    lg = synthetic_league()
    base = {"timeout_clock": _packed([[1.0]] * (2 * NR)),
            "timeout_cells": np.zeros((2, 2, A.LT_SEC_BINS, 3)),
            "timeouts_left": np.tile(np.array([0.0, 0.0, 0.0, 1.0]), (2, 2, 1))}  # fmt: skip
    return replace(lg, **{**base, **kw})


def _sim(game, league, n=500):  # type: ignore[no-untyped-def]
    from ge.models.sim.engine import simulate

    return simulate(game, league, n, game_id="G_LT", model_version="m1")


def _on():  # type: ignore[no-untyped-def]
    return replace(synthetic_game(), late_timeouts_on=True)


def _called(t: np.ndarray) -> np.ndarray:
    return t[..., A.R_LT_CALLED0 : A.R_LT_CALLED0 + 4]


def test_t2_no_timeouts_when_rates_are_zero() -> None:
    t = _sim(_on(), _league()).team.astype(np.int64)
    assert _called(t).sum() == 0


def test_t1_t2_offense_timeouts_stop_the_clock() -> None:
    """Offense rate 1 inside two minutes and a 1 s runoff after a timeout (test settings): the
    offense calls timeouts, the defense none, and the game has more plays than with rate 0."""
    cells = np.zeros((2, 2, A.LT_SEC_BINS, 3))
    cells[:, 0] = 1.0
    on = _sim(_on(), _league(timeout_cells=cells)).team.astype(np.int64)
    off = _sim(_on(), _league()).team.astype(np.int64)
    c = _called(on)
    assert c[..., [0, 2]].sum() > 0 and c[..., [1, 3]].sum() == 0  # half x 2 + role
    assert on[..., A.R_PLAYS].mean() > off[..., A.R_PLAYS].mean()


def test_t3_zero_timeouts_left_means_no_calls() -> None:
    cells = np.ones((2, 2, A.LT_SEC_BINS, 3))
    left0 = np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (2, 2, 1))
    t = _sim(_on(), _league(timeout_cells=cells, timeouts_left=left0)).team.astype(np.int64)
    assert _called(t).sum() == 0
    assert t[..., A.R_LT_LEFT0 : A.R_LT_LEFT0 + 2].sum() == 0


def test_t3_counts_timeouts_left_at_two_minutes() -> None:
    """Every team keeps 2 (test setting): the per-half counter is 4 (both teams) when the half
    had a snap inside two minutes, else 0."""
    left2 = np.tile(np.array([0.0, 0.0, 1.0, 0.0]), (2, 2, 1))
    t = _sim(_on(), _league(timeouts_left=left2)).team.astype(np.int64)
    per_half = t[..., A.R_LT_LEFT0 : A.R_LT_LEFT0 + 2].sum(axis=1)  # both sides
    assert set(np.unique(per_half).tolist()) <= {0, 4} and per_half.max() == 4


def test_path_off_counts_the_old_timeouts() -> None:
    """Path off: the C9 timeouts are still counted; teams have all 3 at two minutes."""
    t = _sim(synthetic_game(), _league()).team.astype(np.int64)
    assert _called(t).sum() > 0
    per_half = t[..., A.R_LT_LEFT0 : A.R_LT_LEFT0 + 2].sum(axis=1)
    assert set(np.unique(per_half).tolist()) <= {0, 6}


def test_early_fg_attempt_cells_sum_to_attempts() -> None:
    g = replace(synthetic_game(), early_fg_on=True, early_fg=np.array([30.0, 0.0, 0.0, 0.0]))
    t = _sim(g, _league()).team.astype(np.int64)
    cells = t[..., A.R_EFG_ATT_S0 : A.R_EFG_ATT_S0 + 2 * A.EFG_SEC_BINS].sum(-1)
    assert t[..., A.R_EFG_ATT].sum() > 0 and (cells == t[..., A.R_EFG_ATT]).all()


@pytest.mark.parametrize(
    "kw",
    [
        {"timeout_cells": np.zeros((2, 2, 3))},
        {"timeouts_left": np.full((2, 2, A.TL_VALUES), 0.3)},
        {"timeout_clock": _packed([[1.0]] * NR)},
    ],
)
def test_engine_refuses_bad_late_timeout_tables(kw: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="PRJ-02"):
        _sim(_on(), _league(**kw), 10)


def _digest(game) -> str:  # type: ignore[no-untyped-def]
    from ge.models.sim.engine import simulate

    r = simulate(game, synthetic_league(), 2000, game_id="G_DIAG_HASH", model_version="m1")
    h = hashlib.sha256()
    n = json.loads(GOLDEN.read_text(encoding="utf-8"))["nteam_at_capture"]
    for a in (r.team[:, :, :n], r.player, r.first_td, r.ot):
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def test_late_timeouts_off_leaves_outputs_identical() -> None:
    """Ruling Q6: the golden full-output hash pinned on 17ac50c (after data correction D, before
    any late-timeouts code); the path off must reproduce it."""
    want = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert synthetic_game().late_timeouts_on is False
    assert _digest(synthetic_game()) == want["regular"]
    assert _digest(synthetic_game(postseason=True)) == want["postseason"]


# ---------------------------------------------------------------- realdata (Q7)


def _actual(season: int) -> pl.DataFrame:
    from ge.ingest.raw import DATA_ROOT, read_latest

    return read_latest(DATA_ROOT, "pbp", season).with_columns(pl.col("qtr").cast(pl.Int64))


@pytest.mark.realdata
@pytest.mark.parametrize("season", [2024, 2023])
def test_replay_timeouts_left_at_two_minutes(season: int) -> None:
    """Q7 (a), tolerance max(0.05 timeouts, 3 SE): per half, the window's T3 mean timeouts left
    at the first scrimmage snap inside two minutes (offense and defense averaged, one each per
    game-half) vs the season's actual mean; SE clustered by game-half (the pair's mean)."""
    from ge.models.sim.backtest import load_window_league

    lg = load_window_league(season)
    tl = lg.timeouts_left
    k = np.arange(tl.shape[-1])
    p = _actual(season).filter(
        pl.col("qtr").is_in([2, 4])
        & (pl.col("half_seconds_remaining") <= lg.two_minute_seconds)
        & pl.col("posteam").is_not_null()
        & pl.col("play_type").is_in(["run", "pass", "qb_kneel", "qb_spike", "field_goal", "punt"])
    )
    first = p.sort("game_id", "play_id").group_by("game_id", "qtr", maintain_order=True).first()
    for h, q in enumerate((2, 4)):
        part = first.filter(pl.col("qtr") == q)
        pair = (part["posteam_timeouts_remaining"] + part["defteam_timeouts_remaining"]) / 2.0
        pair = pair.to_numpy().astype(np.float64)
        actual, se = float(pair.mean()), float(pair.std(ddof=1) / np.sqrt(len(pair)))
        model = float(((tl[h, 0] * k).sum() + (tl[h, 1] * k).sum()) / 2.0)
        tol = max(0.05, 3.0 * se)
        assert abs(model - actual) <= tol, (season, q, model, actual, se, tol)


@pytest.mark.realdata
@pytest.mark.parametrize("season", [2024, 2023])
@pytest.mark.parametrize("cat", list(RUNNING_CLOCK))
def test_replay_runoff_after_a_timeout(season: int, cat: str) -> None:
    """Q7 (b), tolerance max(1.0 s, 3 SE): per running-clock category, the window's T1 mean
    seconds to the next snap with a timeout between, inside two minutes, vs the season's actual
    mean (timeouts placed by data correction D)."""
    from ge.models.sim.backtest import load_window_league
    from ge.models.sim.league import snap_pairs

    lg = load_window_league(season)
    i = RUNNING_CLOCK.index(cat) + NR
    tc = lg.timeout_clock
    v, c = tc.values[tc.lo[i] : tc.hi[i]], tc.cum[tc.lo[i] : tc.hi[i]]
    model = float((v * np.diff(np.concatenate([[0.0], c]))).sum())
    drop_from = int(load_sim().league.timeout_drop_from_season.value)
    _, nxt = snap_pairs(_actual(season), drop_from=drop_from)
    y = (
        nxt.filter(
            (pl.col("half_seconds_remaining") <= lg.two_minute_seconds)
            & (pl.col("cat_name") == cat)
            & pl.col("_tb").fill_null(False)
            & pl.col("_gsr_n").is_not_null()
        )
        .select((pl.col("game_seconds_remaining") - pl.col("_gsr_n")).clip(0, None))
        .to_series()
        .to_numpy()
        .astype(np.float64)
    )
    assert len(y) >= 2, (season, cat, len(y))
    actual, se = float(y.mean()), float(y.std(ddof=1) / np.sqrt(len(y)))
    tol = max(1.0, 3.0 * se)
    assert abs(model - actual) <= tol, (season, cat, model, actual, se, len(y), tol)


# ---------------------------------------------------------------- inputs and output


def test_inputs_read_the_switch_from_config() -> None:
    from ge.models.sim.inputs import late_timeouts_on

    assert late_timeouts_on() is True


def test_summary_has_the_late_timeout_columns() -> None:
    from ge.models.sim import backtest

    cols = backtest.SUMMARY_COLUMNS
    names = [f"lt_called_h{h}_{r}" for h in (2, 4) for r in ("off", "def")]
    names += [f"lt_left_h{h}" for h in (2, 4)]
    names += [f"efg_att_s{b}_t{t}" for b in range(A.EFG_SEC_BINS) for t in (0, 1)]
    for side in ("home", "away"):
        for k in names:
            assert f"{side}_{k}" in cols
