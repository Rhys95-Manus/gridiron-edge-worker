"""PRJ-02 early-down field-goal diagnostic counters (approved by Rhys 2026-11-19, option B;
plans/phase5-efg-counters.md). Eligible early-down snaps are also counted by seconds left in the
half (bins from config/sim.yaml diagnostics.early_fg_seconds_upper, inclusive upper edges; the
last bin runs to early_fg.max_seconds) x offense timeout left (no, yes): cell = bin x 2 + timeout.
They read the snap and never draw. The season output carries efg_elig, efg_att and the 8 cells.
Synthetic placeholder data only."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ge.models.sim import arrays as A
from ge.models.sim.settings import load_sim
from tests.phase5.sim_synth import synthetic_game, synthetic_league

CELLS = 2 * A.EFG_SEC_BINS


def test_seconds_edges_come_from_config() -> None:
    e = load_sim().diagnostics.early_fg_seconds_upper
    assert e.value == [5, 10, 20]
    assert e.spec_id == "PRJ-02" and e.status == "initial"
    assert len(e.value) == A.EFG_SEC_BINS - 1


def test_counter_layout() -> None:
    assert A.EFG_SEC_BINS == 4
    assert A.R_EFG_ELIG_S0 == A.R_EFG_ATT + 1
    # the next block starts right after the cells (late-half timeouts, 2026-11-20)
    assert A.R_LT_CALLED0 == A.R_EFG_ELIG_S0 + CELLS


def test_seconds_cell() -> None:
    from ge.models.sim.engine import efg_sec_cell

    edges = np.array([5.0, 10.0, 20.0])
    # half_sec, timeout left -> cell
    cases = [
        ((0.0, False), 0), ((5.0, False), 0), ((5.0, True), 1), ((6.0, False), 2),
        ((10.0, True), 3), ((11.0, False), 4), ((20.0, True), 5), ((21.0, False), 6),
        ((30.0, True), 7),
    ]  # fmt: skip
    for (s, t), want in cases:
        assert efg_sec_cell(s, t, edges) == want, (s, t)


def _sim(game):  # type: ignore[no-untyped-def]
    from ge.models.sim.engine import simulate

    return simulate(game, synthetic_league(), 500, game_id="G_EFG", model_version="m1")


def _on(coef: tuple[float, ...]):  # type: ignore[no-untyped-def]
    return replace(synthetic_game(), early_fg_on=True, early_fg=np.array(coef, dtype=np.float64))


def _cells(t: np.ndarray) -> np.ndarray:
    return t[..., A.R_EFG_ELIG_S0 : A.R_EFG_ELIG_S0 + CELLS]


def test_cells_sum_to_eligible_snaps() -> None:
    for coef in ((-1e6, 0.0, 0.0, 0.0), (30.0, 0.0, 0.0, 0.0)):
        t = _sim(_on(coef)).team.astype(np.int64)
        assert t[..., A.R_EFG_ELIG].sum() > 0
        assert (_cells(t).sum(-1) == t[..., A.R_EFG_ELIG]).all()


def test_cells_zero_with_the_path_off() -> None:
    t = _sim(synthetic_game()).team
    assert _cells(t).sum() == 0


def test_cells_do_not_draw() -> None:
    """On with P = 0 exactly: every output but the early-FG counters equals the path off."""
    off = _sim(synthetic_game())
    on = _sim(_on((-1e6, 0.0, 0.0, 0.0)))
    keep = list(range(A.R_EFG_ELIG))
    assert np.array_equal(off.team[..., keep], on.team[..., keep])
    assert np.array_equal(off.player, on.player) and np.array_equal(off.ot, on.ot)
    assert np.array_equal(off.first_td, on.first_td)


def _names() -> list[str]:
    return ["efg_elig", "efg_att"] + [
        f"efg_elig_s{b}_t{t}" for b in range(A.EFG_SEC_BINS) for t in (0, 1)
    ]


def test_summary_has_the_early_fg_columns() -> None:
    from ge.models.sim import backtest

    cols = backtest.SUMMARY_COLUMNS
    for side in ("home", "away"):
        for k in _names():
            assert f"{side}_{k}" in cols


def test_summarize_maps_the_early_fg_counters() -> None:
    from ge.models.sim import backtest
    from ge.models.sim.engine import SimResult

    team = np.zeros((2, 2, A.NTEAM), dtype=np.int32)
    idx = [A.R_EFG_ELIG, A.R_EFG_ATT, *range(A.R_EFG_ELIG_S0, A.R_EFG_ELIG_S0 + CELLS)]
    for j, i in enumerate(idx):
        team[:, 0, i] = 10 + j  # home
        team[:, 1, i] = 100 + j  # away
    r = SimResult(team=team, player=np.zeros((2, 2, 1, 1), dtype=np.int32),
                  first_td=np.zeros((2, 2), dtype=np.int32), ot=np.zeros(2, dtype=np.int8),
                  player_ids=((), ()))  # fmt: skip
    row = backtest.summarize(r)
    for j, k in enumerate(_names()):
        assert row[f"home_{k}"] == 10 + j and row[f"away_{k}"] == 100 + j
