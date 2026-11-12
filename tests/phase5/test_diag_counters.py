"""PRJ-02 diagnostic counters (approved 2026-10-30): red zone, 4th-down decisions, 1st/2nd-down
yards by play kind, 2nd-down distance, no-play penalties, possessions alive at the end of a half,
field goals by distance. They read the play and never draw, so every earlier output stays
byte-identical. Synthetic placeholder games only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from ge.models.sim import arrays as A
from ge.models.sim.settings import load_sim
from tests.phase5.sim_synth import _logit, _one, _run_packed, synthetic_game, synthetic_league

FIXTURE = Path(__file__).parent / "fixtures" / "diag_counters_hash.json"
OLD_NTEAM = 73


def _sim(game, league, n=2000, gid="G_DIAG"):  # type: ignore[no-untyped-def]
    from ge.models.sim.engine import simulate

    return simulate(game, league, n, game_id=gid, model_version="m1")


def _t(r) -> np.ndarray:  # type: ignore[no-untyped-def]
    return r.team.astype(np.int64)


def test_diagnostic_settings_come_from_config() -> None:
    d = load_sim().diagnostics
    assert d.red_zone_max_yardline.value == 20
    assert d.fourth_togo_upper.value == [1, 3]
    assert d.fourth_yardline_upper.value == [40, 60]
    assert d.early_deep_air_min.value == 10
    assert d.fg_distance_lower.value == [30, 40, 50]


def test_counter_layout_is_contiguous_and_keeps_the_old_counters() -> None:
    blocks = [
        (A.R_RZ_TRIPS, 1), (A.R_RZ_TD, 1), (A.R_RZ_FG_ATT, 1),
        (A.R_4TH_N0, A.FOURTH_CELLS), (A.R_4TH_GO0, A.FOURTH_CELLS),
        (A.R_4TH_CONV0, A.FOURTH_CELLS),
        (A.R_EARLY_N0, 2 * A.EARLY_KINDS), (A.R_EARLY_YDS0, 2 * A.EARLY_KINDS),
        (A.R_SECOND_ATT0, A.THIRD_BINS), (A.R_SECOND_CONV0, A.THIRD_BINS),
        (A.R_PEN_OFF, 1), (A.R_PEN_DEF, 1), (A.R_PEN_DEF_FD, 1), (A.R_END_HALF, 1),
        (A.R_FG_ATT_D0, A.FG_DIST_BINS), (A.R_FG_MADE_D0, A.FG_DIST_BINS),
    ]  # fmt: skip
    idx = [i for start, width in blocks for i in range(start, start + width)]
    assert idx == list(range(OLD_NTEAM, A.NTEAM))
    assert A.FOURTH_CELLS == 9 and A.EARLY_KINDS == 5 and A.FG_DIST_BINS == 4


def _digest(postseason: bool) -> str:
    r = _sim(synthetic_game(postseason=postseason), synthetic_league(), gid="G_DIAG_HASH")
    h = hashlib.sha256()
    for a in (r.team[:, :, :OLD_NTEAM], r.player, r.first_td, r.ot):
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def test_earlier_outputs_are_byte_identical() -> None:
    want = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert _digest(False) == want["regular"]
    assert _digest(True) == want["postseason"]


def test_counters_are_consistent() -> None:
    game = synthetic_game()
    r = _sim(game, synthetic_league(), 3000)
    t = _t(r)
    fc = A.FOURTH_CELLS
    go = t[..., A.R_4TH_GO0 : A.R_4TH_GO0 + fc]
    conv = t[..., A.R_4TH_CONV0 : A.R_4TH_CONV0 + fc]
    n4 = t[..., A.R_4TH_N0 : A.R_4TH_N0 + fc]
    early_n = t[..., A.R_EARLY_N0 : A.R_EARLY_N0 + 2 * A.EARLY_KINDS]
    second_n = early_n[..., A.EARLY_KINDS :]
    sec_att = t[..., A.R_SECOND_ATT0 : A.R_SECOND_ATT0 + A.THIRD_BINS]
    sec_conv = t[..., A.R_SECOND_CONV0 : A.R_SECOND_CONV0 + A.THIRD_BINS]
    fg_att = t[..., A.R_FG_ATT_D0 : A.R_FG_ATT_D0 + A.FG_DIST_BINS]
    fg_made = t[..., A.R_FG_MADE_D0 : A.R_FG_MADE_D0 + A.FG_DIST_BINS]

    assert (t[..., A.R_RZ_TD] + t[..., A.R_RZ_FG_ATT] <= t[..., A.R_RZ_TRIPS]).all()
    assert (t[..., A.R_RZ_TRIPS] <= t[..., A.R_DRIVES]).all()
    assert (t[..., A.R_RZ_TD] <= t[..., A.R_OFF_TD]).all()
    assert (go.sum(-1) + t[..., A.R_FG_ATT] + t[..., A.R_PUNTS] == n4.sum(-1)).all()
    assert (conv <= go).all() and (go <= n4).all()
    assert (early_n.sum(-1) + t[..., A.R_THIRD_ATT] + go.sum(-1) == t[..., A.R_PLAYS]).all()
    assert (second_n.sum(-1) == sec_att.sum(-1)).all()
    assert (sec_conv <= sec_att).all()
    assert (fg_att.sum(-1) == t[..., A.R_FG_ATT]).all()
    assert (fg_made.sum(-1) == t[..., A.R_FG_MADE]).all()
    assert (fg_made <= fg_att).all()
    assert (t[..., A.R_PEN_DEF_FD] <= t[..., A.R_PEN_DEF]).all()
    sack_n = early_n[..., [A.E_SACK, A.EARLY_KINDS + A.E_SACK]].sum(-1)
    assert (sack_n <= t[..., A.R_PASS_PLAYS]).all()
    max_ot = int(game.ot[A.O_MAX_PERIODS])
    assert (t[..., A.R_END_HALF].sum(-1) <= 2 + r.ot.astype(np.int64) * max_ot).all()
    # every counter group fires somewhere in 3000 synthetic games
    for k in (A.R_RZ_TRIPS, A.R_RZ_TD, A.R_RZ_FG_ATT, A.R_PEN_OFF, A.R_PEN_DEF, A.R_PEN_DEF_FD,
              A.R_END_HALF):  # fmt: skip
        assert t[..., k].sum() > 0, k
    assert go.sum() > 0 and conv.sum() > 0 and early_n[..., A.E_DEEP].sum() > 0


def _runs_only(game):  # type: ignore[no-untyped-def]
    return replace(game, xpass=_logit(-30.0))  # P(pass) ~ 0: designed runs only (test setting)


def _quiet(league, run: list[float]):  # type: ignore[no-untyped-def]
    """Every designed run gains a value from `run`; no penalties, no fumbles (test settings)."""
    return replace(league, run_yards=_run_packed([run] * 11), penalty_offense_rate=0.0,
                   penalty_defense_rate=0.0, fumble_run_rate=0.0)  # fmt: skip


def test_long_touchdowns_never_reach_the_red_zone() -> None:
    lg = _quiet(synthetic_league(), [100.0])
    t = _t(_sim(_runs_only(synthetic_game()), lg, 500))
    assert t[..., A.R_OFF_TD].sum() > 0
    assert t[..., A.R_RZ_TRIPS].sum() == 0


def test_drives_starting_inside_the_20_are_red_zone_trips() -> None:
    lg = _quiet(synthetic_league(), [100.0])
    lg = replace(lg, kickoff_next_yardline=np.full(3, 15.0))
    t = _t(_sim(_runs_only(synthetic_game()), lg, 500))
    assert t[..., A.R_OFF_TD].sum() > 0
    assert (t[..., A.R_RZ_TD] == t[..., A.R_OFF_TD]).all()  # every TD drive was a trip
    assert (t[..., A.R_RZ_TRIPS] >= t[..., A.R_OFF_TD]).all()  # kneel-out drives are trips too


def test_losses_put_every_4th_down_long_and_count_early_yards() -> None:
    game = replace(_runs_only(synthetic_game()), p_go=np.array([30.0] * 9 + [0.0, 0.0, 0.0]))
    t = _t(_sim(game, _quiet(synthetic_league(), [-2.0]), 500))
    fc = A.FOURTH_CELLS
    go = t[..., A.R_4TH_GO0 : A.R_4TH_GO0 + fc].reshape(*t.shape[:2], 3, 3)
    n4 = t[..., A.R_4TH_N0 : A.R_4TH_N0 + fc].reshape(*t.shape[:2], 3, 3)
    assert n4.sum() > 0 and n4[..., :2, :].sum() == 0  # all 4+ to go
    assert (go == n4).all()  # always goes for it
    assert t[..., A.R_4TH_CONV0 : A.R_4TH_CONV0 + fc].sum() == 0
    assert (t[..., A.R_DOWNS] == go.sum(axis=(-1, -2))).all()
    for d in (0, 1):
        k = d * A.EARLY_KINDS + A.E_RUN
        assert t[..., A.R_EARLY_N0 + k].sum() > 0
        assert (t[..., A.R_EARLY_YDS0 + k] == -2 * t[..., A.R_EARLY_N0 + k]).all()
    sec = t[..., A.R_SECOND_ATT0 : A.R_SECOND_ATT0 + A.THIRD_BINS]
    assert sec[..., 5].sum() > 0 and sec[..., :5].sum() == 0  # 2nd & 12: the 11+ bin


def test_defensive_penalties_counted() -> None:
    lg = replace(synthetic_league(), penalty_offense_rate=0.0, penalty_defense_rate=1.0,
                 penalty_defense_first_down=1.0)  # fmt: skip
    t = _t(_sim(synthetic_game(), lg, 200))
    assert t[..., A.R_PEN_DEF].sum() > 0
    assert (t[..., A.R_PEN_DEF] == t[..., A.R_PEN_DEF_FD]).all()
    assert t[..., A.R_PEN_OFF].sum() == 0 and t[..., A.R_PLAYS].sum() == 0


def test_field_goals_binned_by_kick_distance() -> None:
    for offset, b in ((1000.0, 3), (-1000.0, 0)):
        lg = replace(synthetic_league(), fg_offset=_one([offset]))
        t = _t(_sim(synthetic_game(), lg, 500))
        att = t[..., A.R_FG_ATT_D0 : A.R_FG_ATT_D0 + A.FG_DIST_BINS]
        assert att[..., b].sum() == t[..., A.R_FG_ATT].sum() > 0
