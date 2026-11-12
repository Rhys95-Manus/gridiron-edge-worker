"""PRJ-02 (E3) 4th-down go model for the simulator (ruling 2026-10-31): a league logistic with one
term per distance x field cell plus linear score differential and game seconds, weighted by the
PRJ-02 league level, fitted per window. COA-02's linear p_go is unchanged. The 200-event minimum
applies to the whole fit; a cell with no go-fors or no other decisions raises. Ruling 2026-11-01:
one more term, a slope on ln(ydstogo / L) in the last distance bin, L = that bin's lower edge.
Synthetic placeholder data only."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import polars as pl
import pytest

from ge.models.sim import arrays as A
from ge.models.sim.settings import load_sim
from tests.phase5.sim_synth import synthetic_game, synthetic_league

TOGO_UPPER, YL_UPPER = [1, 3], [40, 60]
LONG_LOWER = 4  # the last distance bin's lower edge, TOGO_UPPER[-1] + 1


def _rows(n: int, rng: np.random.Generator, cell_logit: list[float], b_sd: float, b_t: float,
          weeks: tuple[int, int] = (0, 50), b_long: float = 0.0) -> pl.DataFrame:  # fmt: skip
    togo = rng.integers(1, 12, n)
    yl = rng.integers(1, 100, n)
    sd = rng.integers(-21, 22, n)
    t = rng.integers(0, 3600, n)
    from ge.fit.sim_fits import go_cell

    c = go_cell(togo, yl, TOGO_UPPER, YL_UPPER)
    long_ln = np.where(togo >= LONG_LOWER, np.log(np.maximum(togo, 1) / LONG_LOWER), 0.0)
    eta = np.asarray(cell_logit)[c] + b_sd * sd + b_t * t + b_long * long_ln
    p = 1 / (1 + np.exp(-eta))
    return pl.DataFrame(
        {
            "week_index": rng.integers(weeks[0], weeks[1], n),
            "ydstogo": togo.astype(float),
            "yardline_100": yl.astype(float),
            "score_differential": sd.astype(float),
            "game_seconds_remaining": t.astype(float),
            "go": (rng.random(n) < p).astype(float),
        }
    )


def test_go_settings_come_from_config() -> None:
    g = load_sim().fourth_go
    assert g.togo_upper.value == TOGO_UPPER
    assert g.yardline_upper.value == YL_UPPER
    assert A.GO_CELLS == 9
    assert (*(f"cell{c}" for c in range(9)), "sd", "game_sec", "long_ln_togo") == A.GO_TERMS
    assert A.go_key("cell0") == "fit:PRJ-02/go/cell0"


def test_go_cell_uses_inclusive_upper_edges() -> None:
    from ge.fit.sim_fits import go_cell

    togo = np.array([1, 1, 1, 2, 3, 4, 10, 3])
    yl = np.array([40, 41, 61, 40, 60, 61, 1, 100])
    assert go_cell(togo, yl, TOGO_UPPER, YL_UPPER).tolist() == [0, 1, 2, 3, 4, 8, 6, 5]


def test_go_fit_recovers_planted_model_within_3_se() -> None:
    from ge.fit.sim_fits import fit_fourth_go

    rng = np.random.default_rng(31)
    cells = [2.0, 1.0, -0.5, 0.0, -0.8, -2.5, -2.0, -2.4, -3.8]  # synthetic
    b_sd, b_t, b_long = -0.05, -0.0004, -1.3
    fit = fit_fourth_go(_rows(60_000, rng, cells, b_sd, b_t, b_long=b_long), target_index=50,
                        h=1e9, togo_upper=TOGO_UPPER, yardline_upper=YL_UPPER)  # fmt: skip
    for c in range(9):
        assert abs(fit.cell[c] - cells[c]) < 3 * fit.cell_se[c], c
    assert abs(fit.score_differential - b_sd) < 3 * fit.score_differential_se
    assert abs(fit.game_seconds - b_t) < 3 * fit.game_seconds_se
    assert abs(fit.long_ln_togo - b_long) < 3 * fit.long_ln_togo_se
    assert sum(fit.cell_go) == fit.events and fit.n == 60_000
    assert [g + o for g, o in zip(fit.cell_go, fit.cell_other, strict=True)] == fit.cell_n


def test_go_fit_weights_recent_weeks() -> None:
    """Cell 0 goes 30% of the time in weeks 0-49 and 90% in weeks 50-99 (synthetic): a short
    half-life fits near the recent rate, a huge one near the pooled rate."""
    from ge.fit.sim_fits import fit_fourth_go

    rng = np.random.default_rng(7)
    lo = [np.log(0.3 / 0.7)] + [0.0] * 8
    hi = [np.log(0.9 / 0.1)] + [0.0] * 8
    rows = pl.concat([_rows(20_000, rng, lo, 0.0, 0.0, (0, 50)),
                      _rows(20_000, rng, hi, 0.0, 0.0, (50, 100))])  # fmt: skip
    kw = {"target_index": 100, "togo_upper": TOGO_UPPER, "yardline_upper": YL_UPPER}
    recent = fit_fourth_go(rows, h=2.0, **kw)
    pooled = fit_fourth_go(rows, h=1e9, **kw)
    assert 1 / (1 + np.exp(-recent.cell[0])) > 0.85
    assert 0.5 < 1 / (1 + np.exp(-pooled.cell[0])) < 0.7


@pytest.mark.parametrize("go_value", [1.0, 0.0])
def test_go_fit_needs_200_events_of_each_kind_overall(go_value: float) -> None:
    from ge.fit.sim_fits import fit_fourth_go

    rng = np.random.default_rng(3)
    rows = _rows(5_000, rng, [0.0] * 9, 0.0, 0.0)
    rows = rows.with_columns(
        pl.when(pl.int_range(pl.len()) >= 150).then(go_value).otherwise(pl.col("go")).alias("go")
    )  # the other kind keeps fewer than 200 rows
    with pytest.raises(NotImplementedError, match="PRJ-02"):
        fit_fourth_go(rows, target_index=50, h=8.0, togo_upper=TOGO_UPPER,
                      yardline_upper=YL_UPPER)  # fmt: skip


def test_go_fit_allows_thin_cells_but_not_empty_ones() -> None:
    """Ruling 2026-10-31: the minimum is on the whole fit. A cell with a handful of go-fors is
    fitted; a cell with none (or with nothing but go-fors) has no finite estimate and raises."""
    from ge.fit.sim_fits import fit_fourth_go, go_cell

    rng = np.random.default_rng(5)
    rows = _rows(40_000, rng, [0.0] * 8 + [-5.0], 0.0, 0.0)
    kw = {"target_index": 50, "h": 1e9, "togo_upper": TOGO_UPPER, "yardline_upper": YL_UPPER}
    fit = fit_fourth_go(rows, **kw)
    assert 0 < fit.cell_go[8] < 200
    c = go_cell(rows["ydstogo"].to_numpy(), rows["yardline_100"].to_numpy(), TOGO_UPPER, YL_UPPER)
    for value in (0.0, 1.0):
        bad = rows.with_columns(
            pl.when(pl.Series(c == 8)).then(value).otherwise(pl.col("go")).alias("go")
        )
        with pytest.raises(NotImplementedError, match="cell 8"):
            fit_fourth_go(bad, **kw)


def test_go_fit_needs_long_go_fors_at_two_distances() -> None:
    """Ruling 2026-11-01: the ln-distance slope has no finite estimate when every go-for in the
    last distance bin is at one distance."""
    from ge.fit.sim_fits import fit_fourth_go

    rng = np.random.default_rng(11)
    rows = _rows(40_000, rng, [0.0] * 9, 0.0, 0.0)
    rows = rows.with_columns(
        pl.when((pl.col("ydstogo") > LONG_LOWER) & (pl.col("go") == 1.0))
        .then(0.0)
        .otherwise(pl.col("go"))
        .alias("go")
    )  # 4+ go-fors only at 4th&4
    with pytest.raises(NotImplementedError, match=r"PRJ-02.*one distance"):
        fit_fourth_go(rows, target_index=50, h=1e9, togo_upper=TOGO_UPPER,
                      yardline_upper=YL_UPPER)  # fmt: skip


def test_fourth_go_rows_use_the_coa02_row_set() -> None:
    """Same decisions as COA-02: 4th-down pass, run, punt or field goal; garbage time (G7),
    no-play penalties and other downs out; go = pass or run."""
    from ge.fit.sim_fits import fourth_go_rows

    core = pl.DataFrame(
        {
            "week_index": [0, 0, 0, 0, 0, 0],
            "down": [4, 4, 4, 4, 3, 4],
            "play_type": ["run", "punt", "field_goal", "no_play", "pass", "pass"],
            "posteam": ["A"] * 6,
            "qtr": [1, 1, 2, 2, 1, 4],
            "wp": [0.5, 0.5, 0.5, 0.5, 0.5, 0.99],  # the last row is G7 garbage time
            "ydstogo": [1.0, 8.0, 5.0, 2.0, 3.0, 2.0],
            "yardline_100": [30.0, 70.0, 20.0, 40.0, 50.0, 30.0],
            "score_differential": [0.0, 3.0, -3.0, 0.0, 0.0, 21.0],
            "game_seconds_remaining": [3000.0, 2500.0, 1900.0, 1800.0, 3500.0, 200.0],
        }
    )
    r = fourth_go_rows(core)
    assert r["go"].to_list() == [1.0, 0.0, 0.0]
    assert set(r.columns) >= {"week_index", "go", "ydstogo", "yardline_100",
                              "score_differential", "game_seconds_remaining"}  # fmt: skip


def test_fit_keys_written() -> None:
    from ge.fit.sim_fits import GoFit
    from ge.fit.sim_job import SimOut, record_fourth_go

    fit = GoFit(
        cell=tuple(float(c) for c in range(9)),
        cell_se=(0.1,) * 9,
        score_differential=-0.05,
        score_differential_se=0.01,
        game_seconds=-0.0004,
        game_seconds_se=0.0001,
        long_ln_togo=-1.3,
        long_ln_togo_se=0.1,
        cell_n=[10] * 9,
        cell_go=[4] * 9,
        cell_other=[6] * 9,
        n=90,
        events=36,
        n_eff=80.0,
    )
    out = SimOut({}, {}, {}, {})
    record_fourth_go(out, fit, [2016, 2017])
    assert sorted(out.values) == sorted(A.go_key(t) for t in A.GO_TERMS)
    assert out.values[A.go_key("cell3")]["value"] == 3.0
    assert out.values[A.go_key("sd")]["value"] == -0.05
    assert out.values[A.go_key("game_sec")]["value"] == -0.0004
    assert out.values[A.go_key("long_ln_togo")]["value"] == -1.3
    assert {v["spec_id"] for v in out.values.values()} == {"PRJ-02"}
    assert out.diagnostics["fourth_go"]["cell_go"] == [4] * 9


def test_inputs_read_the_go_model_keys_in_order() -> None:
    from ge.models.sim.inputs import go_model

    vals = {A.go_key(t): float(i) for i, t in enumerate(A.GO_TERMS)}
    got = go_model(lambda key, spec_id: vals[key])
    assert got.tolist() == [float(i) for i in range(12)]


def test_engine_go_logit_reads_cell_score_and_time() -> None:
    from ge.models.sim.engine import go_logit

    p = np.array([float(10 * c) for c in range(9)] + [0.5, 0.01, 0.0])
    edges_t, edges_y = np.array([1.0, 3.0]), np.array([40.0, 60.0])
    assert go_logit(p, 1.0, 40.0, 0.0, 0.0, edges_t, edges_y) == 0.0
    assert go_logit(p, 3.0, 41.0, 0.0, 0.0, edges_t, edges_y) == 40.0
    assert go_logit(p, 7.0, 75.0, -4.0, 100.0, edges_t, edges_y) == 80.0 - 2.0 + 1.0


def test_engine_go_logit_adds_the_distance_term_only_in_the_last_bin() -> None:
    """Ruling 2026-11-01: slope x ln(togo / L), L = last distance bin's lower edge (4 here)."""
    from ge.models.sim.engine import go_logit

    p = np.array([float(10 * c) for c in range(9)] + [0.0, 0.0, -1.0])
    edges_t, edges_y = np.array([1.0, 3.0]), np.array([40.0, 60.0])
    assert go_logit(p, 4.0, 30.0, 0.0, 0.0, edges_t, edges_y) == 60.0
    assert go_logit(p, 8.0, 30.0, 0.0, 0.0, edges_t, edges_y) == 60.0 - np.log(2.0)
    assert go_logit(p, 16.0, 75.0, 0.0, 0.0, edges_t, edges_y) == 80.0 - np.log(4.0)
    assert go_logit(p, 3.0, 30.0, 0.0, 0.0, edges_t, edges_y) == 30.0
    assert go_logit(p, 1.0, 30.0, 0.0, 0.0, edges_t, edges_y) == 0.0


def _sim(game, n=1500):  # type: ignore[no-untyped-def]
    from ge.models.sim.engine import simulate

    return simulate(game, synthetic_league(), n, game_id="G_GO", model_version="m1")


def test_engine_goes_only_in_the_cell_the_model_says() -> None:
    """Cell 0 (4th&1 inside the 40) at +30, every other cell at -30: the simulator goes for it on
    every 4th&1 inside the 40 and on no other 4th down (the diagnostic bins equal the go bins)."""
    game = replace(synthetic_game(), p_go=np.array([30.0] + [-30.0] * 8 + [0.0, 0.0, 0.0]))
    t = _sim(game).team.astype(np.int64)
    fc = A.FOURTH_CELLS
    go = t[..., A.R_4TH_GO0 : A.R_4TH_GO0 + fc]
    n4 = t[..., A.R_4TH_N0 : A.R_4TH_N0 + fc]
    assert n4[..., 0].sum() > 0
    assert (go[..., 0] == n4[..., 0]).all()
    assert go[..., 1:].sum() == 0


@pytest.mark.parametrize("n_terms", [5, 11])
def test_engine_refuses_old_go_models(n_terms: int) -> None:
    """The COA-02 coefficients (5) and the 2026-10-31 model without the distance term (11)."""
    game = replace(synthetic_game(), p_go=np.zeros(n_terms))
    with pytest.raises(ValueError, match="PRJ-02"):
        _sim(game, 10)
