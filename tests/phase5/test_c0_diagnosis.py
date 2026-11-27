"""PRJ-02 C0 diagnosis (decision rows 2026-11-23: Q2, Q-C1 to Q-C7). Training seasons 2016-2020
are simulated with a test-season window only behind an explicit diagnosis window (in-sample,
disclosed); input ablations exist only on such builds. The gate, the production season runner and
every season 2021-2025 refuse it. Synthetic arrays come from tests/phase5/sim_synth.py (round
test numbers, not football data); the realdata test builds one real 2019 game."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import polars as pl
import pytest

from ge.models.sim import arrays as A
from ge.models.sim import backtest, diagnosis, gate, inputs
from ge.models.sim.arrays import GameArrays
from ge.models.sim.inputs import DiagnosisParts
from ge.models.sim.settings import load_sim
from ge.store.holdout import HoldoutReadError

from .sim_synth import synthetic_game


def _boom(*a: Any, **k: Any) -> Any:
    raise AssertionError("read attempted")


# ---------------------------------------------------------------- B1: seasons and windows


def test_production_runner_still_refuses_a_training_season(monkeypatch: pytest.MonkeyPatch,
                                                           tmp_path: Path) -> None:  # fmt: skip
    """Without the diagnosis window nothing changes: 2016-2020 have no fit window."""
    monkeypatch.setattr(backtest, "season_games", lambda season: ["2019_01_AAA_BBB"])
    monkeypatch.setattr(backtest, "build_game", _boom)
    with pytest.raises(NotImplementedError, match="PRJ-02: season 2019 has no fit window"):
        backtest.run_season(2019, n_runs=10, model_version="t", out_root=tmp_path)


@pytest.mark.parametrize("season", [2016, 2017, 2018, 2019, 2020])
def test_training_seasons_of_the_window_are_allowed(season: int) -> None:
    diagnosis.check_season(season, 2021)


@pytest.mark.parametrize("season", [2015, 2021, 2022, 2023, 2024, 2026])
def test_test_and_outside_seasons_are_refused(season: int) -> None:
    with pytest.raises(ValueError, match="C0"):
        diagnosis.check_season(season, 2021)


def test_a_test_season_is_refused_even_inside_a_later_window() -> None:
    with pytest.raises(ValueError, match="C0"):
        diagnosis.check_season(2021, 2022)


def test_holdout_is_refused_as_a_holdout_read() -> None:
    with pytest.raises(HoldoutReadError):
        diagnosis.check_season(2025, 2021)


@pytest.mark.parametrize("window", ["S2021", "S2024"])
def test_window_names(window: str) -> None:
    assert diagnosis.parse_window(window) == int(window[1:])


@pytest.mark.parametrize("window", ["S2020", "S2025", "live", "2021", "s2021"])
def test_bad_window_names_raise(window: str) -> None:
    with pytest.raises(ValueError, match="C0"):
        diagnosis.parse_window(window)


@pytest.mark.parametrize("game_id", ["2021_01_AAA_BBB", "2024_18_AAA_BBB", "2025_01_AAA_BBB"])
def test_build_game_refuses_a_diagnosis_window_on_2021_2025_before_any_read(
    monkeypatch: pytest.MonkeyPatch, game_id: str
) -> None:
    monkeypatch.setattr(inputs, "snapshot", _boom)
    with pytest.raises((ValueError, HoldoutReadError)):
        inputs.build_game(game_id, league=None, window_season=2021)  # type: ignore[arg-type]


@pytest.mark.parametrize("season", [2021, 2022, 2023, 2024, 2025])
def test_diagnosis_runner_refuses_2021_2025_before_any_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, season: int
) -> None:
    monkeypatch.setattr(diagnosis, "season_games", _boom)
    monkeypatch.setattr(diagnosis, "build_game", _boom)
    with pytest.raises((ValueError, HoldoutReadError)):
        diagnosis.run_diagnosis(season, window="S2021", n_runs=10, model_version="t",
                                chunk=0, chunk_size=70, out_root=tmp_path)  # fmt: skip
    assert not any(tmp_path.iterdir())


# ---------------------------------------------------------------- Q-C1: kickoff table


def test_training_season_kickoffs_use_only_the_window_same_era_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Q-C1: the window's kickoff rows of the game's era, at the window's target index; the
    snapshot's in-season rows are not read (the stub snapshot has no `collect`)."""
    seen: dict[str, Any] = {}

    def capture(league: Any, current: pl.DataFrame, **k: Any) -> str:
        seen.update(current=current, **k)
        return "table"

    monkeypatch.setattr(inputs, "game_kickoffs", capture)
    monkeypatch.setattr(inputs, "_fit_value", lambda key, sid: 3.0)
    league = SimpleNamespace(
        kickoff_season=np.array([2016.0, 2019.0, 2020.0, 2020.0]), kickoff_target_index=400
    )
    out = inputs._window_kickoffs(SimpleNamespace(season=2019, week=5), league)
    assert out == "table"
    assert seen["current"].height == 0
    assert seen["game_index"] == 400
    assert set(seen["seasons"]) == {2016, 2019, 2020}  # all in the game's era (game_rules.yaml)
    assert seen["h_l"] == 3.0


# ---------------------------------------------------------------- ablation (Q-C4, Q-C6)

PARTS = DiagnosisParts(
    cmp_tilt=(0.30, -0.20),
    cmp_w=(-0.05, -0.05),
    yac_tilt=(0.80, -0.10),
    int_tilt=(-0.25, 0.15),
    ypc_tilt=(0.40, -0.35),
    mtc01=(0.10, 0.05),
    fum_tilt=(0.0, 0.0),
    sack_league=(-2.5, -2.5),
    sack_eta=(-2.3, -2.7),
    sack_ol=(0.2, 0.0),
    yac_cap=1.0,
    ypc_cap=0.5,
)


def _game() -> GameArrays:
    """The synthetic game with team fields composed from PARTS as _build composes them, varied
    style and player fields, and side 0's last player row as padding (n_players)."""
    g = synthetic_game()
    t = g.team.copy()
    p = PARTS
    for s in (0, 1):
        t[s, A.T_CMP_SHIFT] = p.cmp_tilt[s] + p.cmp_w[s]
        t[s, A.T_YAC_SHIFT] = float(np.clip(p.yac_tilt[s], -p.yac_cap, p.yac_cap))
        t[s, A.T_INT_SHIFT] = p.int_tilt[s]
        t[s, A.T_YPC_SHIFT] = float(np.clip(p.ypc_tilt[s] + p.mtc01[s], -p.ypc_cap, p.ypc_cap))
        t[s, A.T_FUM_SHIFT] = p.fum_tilt[s]
        t[s, A.T_SACK_LOGIT] = float(p.sack_eta[s] + p.sack_ol[s])
        t[s, A.T_DEEP_SHIFT] = 0.07
        t[s, A.T_FG_SHIFT] = -0.04
        t[s, A.T_EXPL_SHIFT] = 0.03
    t[0, A.T_PACE_N], t[1, A.T_PACE_N] = 26.0, 30.0
    t[0, A.T_PROE_N], t[1, A.T_PROE_N] = 0.02, -0.04
    t[0, A.T_GO_OVER], t[1, A.T_GO_OVER] = 0.05, -0.01
    t[0, A.T_CELL0], t[1, A.T_CELL0] = 0.2, 0.1
    pl_ = g.player.copy()
    pl_[:, :, A.P_CROE] = 0.03
    pl_[:, :, A.P_YACOE] = 0.4
    pl_[:, :, A.P_RYOE] = -0.2
    pl_[:, :, A.P_SCR_SHIFT] = 0.5
    pl_[:, :, A.P_MTC02] = 1.08
    pl_[:, :, A.P_AVAIL] = 0.6
    n = g.n_players.copy()
    n[0] -= 1
    return dataclasses.replace(g, team=t, player=pl_, n_players=n)


def _changed(
    a: GameArrays, b: GameArrays
) -> tuple[set[tuple[int, int]], set[tuple[int, int, int]]]:
    team = {(int(s), int(f)) for s, f in zip(*np.nonzero(a.team != b.team), strict=True)}
    ne = ~((a.player == b.player) | (np.isnan(a.player) & np.isnan(b.player)))
    player = {(int(s), int(i), int(f)) for s, i, f in zip(*np.nonzero(ne), strict=True)}
    return team, player


def _players(g: GameArrays, fields: tuple[int, ...]) -> set[tuple[int, int, int]]:
    return {(s, i, f) for s in (0, 1) for i in range(int(g.n_players[s])) for f in fields}


STYLE = (A.T_PACE_N, A.T_PACE_LEAD, A.T_PACE_TRAIL, A.T_PROE_N, A.T_PROE_LEAD, A.T_PROE_TRAIL,
         A.T_GO_OVER, A.T_TWO_PT, *range(A.T_CELL0, A.T_CELL0 + 8))  # fmt: skip
DEV = (A.P_CROE, A.P_YACOE, A.P_RYOE, A.P_SCR_SHIFT)


def test_tilt_probe_k_is_a_config_value() -> None:
    k = load_sim().c0.tilt_probe_k
    assert k.value == 2 and k.status == "initial" and k.spec_id == "PRJ-02"


def test_variant_list() -> None:
    assert diagnosis.VARIANTS == (
        "baseline", "no_tilt", "no_matchup", "no_environment", "no_player_dev",
        "no_qd_availability", "style_neutral", "tilt_only", "tilt_x2", "baseline_seed2",
    )  # fmt: skip
    # Q-C2: the stop-rule test counts only variants that change one named input or mechanism
    assert diagnosis.SINGLE_INPUT == (
        "no_tilt", "no_matchup", "no_environment", "no_player_dev", "no_qd_availability",
        "style_neutral", "tilt_x2",
    )  # fmt: skip


@pytest.mark.parametrize("variant", ["baseline", "baseline_seed2"])
def test_baseline_variants_leave_every_array_identical(variant: str) -> None:
    g = _game()
    v = diagnosis.variant_arrays(g, PARTS, variant, tilt_k=2.0)
    assert _changed(g, v) == (set(), set())
    assert v.team.tobytes() == g.team.tobytes() and v.player.tobytes() == g.player.tobytes()


def test_no_tilt_removes_only_the_tilt() -> None:
    g, p = _game(), PARTS
    v = diagnosis.variant_arrays(g, p, "no_tilt", tilt_k=2.0)
    for s in (0, 1):
        assert v.team[s, A.T_CMP_SHIFT] == p.cmp_w[s]
        assert v.team[s, A.T_YAC_SHIFT] == 0.0
        assert v.team[s, A.T_INT_SHIFT] == 0.0
        assert v.team[s, A.T_YPC_SHIFT] == float(np.clip(p.mtc01[s], -p.ypc_cap, p.ypc_cap))
        assert v.team[s, A.T_FUM_SHIFT] == 0.0
    team, player = _changed(g, v)
    allowed = {(s, f) for s in (0, 1) for f in (A.T_CMP_SHIFT, A.T_YAC_SHIFT, A.T_INT_SHIFT,
                                               A.T_YPC_SHIFT, A.T_FUM_SHIFT)}  # fmt: skip
    assert team <= allowed and player == set()


def test_tilt_x2_doubles_only_the_tilt() -> None:
    g, p = _game(), PARTS
    v = diagnosis.variant_arrays(g, p, "tilt_x2", tilt_k=2.0)
    for s in (0, 1):
        assert v.team[s, A.T_CMP_SHIFT] == 2.0 * p.cmp_tilt[s] + p.cmp_w[s]
        assert v.team[s, A.T_YAC_SHIFT] == float(np.clip(2.0 * p.yac_tilt[s], -1.0, 1.0))
        assert v.team[s, A.T_INT_SHIFT] == 2.0 * p.int_tilt[s]
        assert v.team[s, A.T_YPC_SHIFT] == float(
            np.clip(2.0 * p.ypc_tilt[s] + p.mtc01[s], -0.5, 0.5)
        )
    assert v.team[0, A.T_YAC_SHIFT] == 1.0  # the E5 cap still binds
    team, player = _changed(g, v)
    assert {f for _, f in team} <= {A.T_CMP_SHIFT, A.T_YAC_SHIFT, A.T_INT_SHIFT, A.T_YPC_SHIFT,
                                    A.T_FUM_SHIFT}  # fmt: skip
    assert player == set()


def test_no_matchup_removes_mtc01_mtc02_and_the_mtc03_team_part() -> None:
    g, p = _game(), PARTS
    v = diagnosis.variant_arrays(g, p, "no_matchup", tilt_k=2.0)
    for s in (0, 1):
        assert v.team[s, A.T_YPC_SHIFT] == float(np.clip(p.ypc_tilt[s], -0.5, 0.5))
        assert v.team[s, A.T_SACK_LOGIT] == float(p.sack_league[s] + p.sack_ol[s])
    team, player = _changed(g, v)
    assert {f for _, f in team} <= {A.T_YPC_SHIFT, A.T_SACK_LOGIT}
    assert player == _players(g, (A.P_MTC02,))
    assert np.all(v.player[0, : g.n_players[0], A.P_MTC02] == 1.0)


def test_no_environment_removes_weather_altitude_and_surface() -> None:
    g, p = _game(), PARTS
    v = diagnosis.variant_arrays(g, p, "no_environment", tilt_k=2.0)
    for s in (0, 1):
        assert v.team[s, A.T_CMP_SHIFT] == p.cmp_tilt[s]
        assert v.team[s, A.T_DEEP_SHIFT] == 0.0
        assert v.team[s, A.T_FG_SHIFT] == 0.0
        assert v.team[s, A.T_EXPL_SHIFT] == 0.0
    team, player = _changed(g, v)
    assert {f for _, f in team} == {A.T_CMP_SHIFT, A.T_DEEP_SHIFT, A.T_FG_SHIFT, A.T_EXPL_SHIFT}
    assert player == set()


def test_no_player_dev_zeroes_player_deviations_on_real_rows_only() -> None:
    g = _game()
    v = diagnosis.variant_arrays(g, PARTS, "no_player_dev", tilt_k=2.0)
    team, player = _changed(g, v)
    assert team == set()
    assert player == _players(g, DEV)  # side 0's padding row is untouched
    assert np.all(v.player[1, :, list(DEV)] == 0.0)


def test_no_qd_availability_plays_everyone_and_drops_the_ol_absence_part() -> None:
    g, p = _game(), PARTS
    v = diagnosis.variant_arrays(g, p, "no_qd_availability", tilt_k=2.0)
    for s in (0, 1):
        assert v.team[s, A.T_SACK_LOGIT] == float(p.sack_eta[s] + 0.0)
    team, player = _changed(g, v)
    assert team == {(0, A.T_SACK_LOGIT)}  # side 1 has no OL absence part
    assert player == _players(g, (A.P_AVAIL,))


def test_style_neutral_sets_both_sides_to_their_mean() -> None:
    g = _game()
    v = diagnosis.variant_arrays(g, PARTS, "style_neutral", tilt_k=2.0)
    for f in STYLE:
        assert v.team[0, f] == v.team[1, f] == (g.team[0, f] + g.team[1, f]) / 2
    team, player = _changed(g, v)
    assert {f for _, f in team} == {A.T_PACE_N, A.T_PROE_N, A.T_GO_OVER, A.T_CELL0}
    assert player == set()


def test_tilt_only_is_the_union_of_the_other_ablations() -> None:
    g = _game()
    v = diagnosis.variant_arrays(g, PARTS, "tilt_only", tilt_k=2.0)
    step = g
    for name in ("no_matchup", "no_environment", "no_player_dev", "no_qd_availability",
                 "style_neutral"):  # fmt: skip
        step = diagnosis.variant_arrays(step, PARTS, name, tilt_k=2.0)
    # one pass over all five equals the five one at a time (PARTS-based fields recomposed once)
    assert v.player.tobytes() == step.player.tobytes()
    for s in (0, 1):
        assert v.team[s, A.T_SACK_LOGIT] == PARTS.sack_league[s]
        assert v.team[s, A.T_YPC_SHIFT] == float(np.clip(PARTS.ypc_tilt[s], -0.5, 0.5))
        assert v.team[s, A.T_CMP_SHIFT] == PARTS.cmp_tilt[s]
    for f in STYLE:
        assert v.team[0, f] == v.team[1, f]


def test_unknown_variant_raises() -> None:
    with pytest.raises(ValueError, match="C0"):
        diagnosis.variant_arrays(_game(), PARTS, "no_coaches", tilt_k=2.0)


def test_ablation_without_a_diagnosis_build_raises() -> None:
    """A production build carries no DiagnosisParts, so it cannot be ablated."""
    with pytest.raises(ValueError, match="--diagnosis-window"):
        diagnosis.variant_arrays(_game(), None, "no_tilt", tilt_k=2.0)


# ---------------------------------------------------------------- runner and gate


def test_runner_uses_one_seed_for_every_variant_and_writes_a_chunk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    g = _game()
    lines = SimpleNamespace(spread=1.0, total=40.0, raw_spread=0.5, raw_total=41.0)
    info = SimpleNamespace(
        week=3,
        home="BBB",
        away="AAA",
        postseason=False,
        neutral=False,
        league="lg",
        parts=PARTS,
        ratings=SimpleNamespace(lines=lines),
    )
    seeds: list[tuple[str, str]] = []
    monkeypatch.setattr(
        diagnosis, "season_games", lambda s: ["2019_01_A", "2019_01_B", "2019_02_C"]
    )
    monkeypatch.setattr(diagnosis, "load_window_league", lambda s: "league")
    monkeypatch.setattr(diagnosis, "build_game", lambda gid, lg, *, window_season: (g, info))

    def sim(arr: GameArrays, league: Any, n: int, *, game_id: str, model_version: str) -> str:
        seeds.append((game_id, model_version))
        return "r"

    monkeypatch.setattr(diagnosis, "simulate", sim)
    monkeypatch.setattr(diagnosis, "summarize", lambda r: {"margin_mean": 0.0})
    path = diagnosis.run_diagnosis(2019, window="S2021", n_runs=10, model_version="c0",
                                   chunk=1, chunk_size=2, out_root=tmp_path)  # fmt: skip
    assert path == tmp_path / "c0" / "season=2019" / "chunk=01.parquet"
    df = pl.read_parquet(path)
    assert df["game_id"].unique().to_list() == ["2019_02_C"]
    assert df["variant"].to_list() == list(diagnosis.VARIANTS)
    assert set(df["fit_window"].to_list()) == {"S2021"}
    assert {mv for _, mv in seeds} == {"c0", "c0-seed2"}
    assert [mv for _, mv in seeds].count("c0-seed2") == 1


def test_gate_refuses_a_diagnosis_tag_before_any_read(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="diagnosis"):
        gate.season_gate("diagnosis/phase5-c0", 2021, runs_root=tmp_path, data_root=tmp_path)


def test_gate_refuses_a_run_file_with_diagnosis_columns(tmp_path: Path) -> None:
    (tmp_path / "t").mkdir()
    pl.DataFrame(
        {"game_id": ["g"], "variant": ["baseline"], "fit_window": ["S2021"]}
    ).write_parquet(tmp_path / "t" / "season=2021.parquet")
    with pytest.raises(ValueError, match="diagnosis"):
        gate.season_gate("t", 2021, runs_root=tmp_path, data_root=tmp_path / "no_data")


# ---------------------------------------------------------------- CLI: behind --diagnosis-window

# Same plain output on every terminal: CI prints the error box in colour at 80 columns, which
# splits the option name (Rhys 2026-11-27, "Yes, fix and push").
PLAIN = {"NO_COLOR": "1", "COLUMNS": "200", "TERM": "dumb"}


def test_cli_chunk_flags_need_a_diagnosis_window(monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    from ge.cli import app

    monkeypatch.setattr(backtest, "run_season", _boom)
    monkeypatch.setattr(diagnosis, "run_diagnosis", _boom)
    r = CliRunner(env=PLAIN).invoke(app, ["sim-season", "--season", "2019", "--model-version", "t",
                                 "--chunk", "0", "--chunk-size", "70"])  # fmt: skip
    assert r.exit_code != 0
    assert "--diagnosis-window" in str(r.exception) + r.output


def test_cli_diagnosis_window_runs_the_diagnosis_runner(monkeypatch: pytest.MonkeyPatch,
                                                        tmp_path: Path) -> None:  # fmt: skip
    from typer.testing import CliRunner

    from ge.cli import app

    seen: dict[str, Any] = {}

    def fake(season: int, **k: Any) -> Path:
        seen.update(season=season, **k)
        return tmp_path / "x.parquet"

    monkeypatch.setattr(backtest, "run_season", _boom)
    monkeypatch.setattr(diagnosis, "run_diagnosis", fake)
    args = ["sim-season", "--season", "2019", "--model-version", "phase5-c0",
            "--diagnosis-window", "S2021", "--chunk", "2", "--chunk-size", "70"]  # fmt: skip
    r = CliRunner(env=PLAIN).invoke(app, args)
    assert r.exit_code == 0, r.output
    assert seen["season"] == 2019 and seen["window"] == "S2021"
    assert seen["chunk"] == 2 and seen["chunk_size"] == 70 and seen["model_version"] == "phase5-c0"


# ---------------------------------------------------------------- one real 2019 game


@pytest.mark.realdata
def test_real_2019_game_builds_with_the_s2021_window() -> None:
    from ge.config import params_for

    sched = backtest.read_latest(backtest.DATA_ROOT, "schedules", 2019).filter(
        (pl.col("season") == 2019) & (pl.col("week") == 5)
    )
    gid = sched.sort("game_id")["game_id"][0]
    league = backtest.load_window_league(2021)
    with pytest.raises(NotImplementedError):  # without the window: no fit for 2019
        inputs.build_game(gid, league)
    g, info = inputs.build_game(gid, league, window_season=2021)
    assert info.ratings.consts.window == "S2021"
    p = info.parts
    assert p is not None
    slope = params_for(2021).fit_status("fit:PRJ-02/tilt/completion")[1]
    rt = info.ratings.table.values
    sides = (info.home, info.away)
    for s in (0, 1):
        net = rt[(sides[s], "off_pass")] + rt[(sides[1 - s], "def_pass")]
        assert p.cmp_tilt[s] == slope * net
    # the parts recompose the built arrays exactly
    assert diagnosis.variant_arrays(g, p, "baseline", tilt_k=2.0).team.tobytes() == g.team.tobytes()
    v = diagnosis.variant_arrays(g, p, "no_tilt", tilt_k=2.0)
    assert np.all(v.team[:, A.T_INT_SHIFT] == 0.0)
