"""PRJ-02 kickoff eras (K1, rulings 2026-11-01 and 2026-11-02): a game's kickoff table draws only
from kickoffs played under the same free-kick touchback rule (eras in config/game_rules.yaml,
from rulebook text), plus the game's own season up to the game (point in time), weighted by h_L
from the game's week. Fewer than min_category_events such kickoffs raise. Synthetic placeholder
rows only, except the config checks."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import pytest
import yaml

from ge.models.sim.league import game_kickoffs, kickoff_rows, load_league, save_league
from ge.models.sim.rules import GAME_RULES_PATH, GameRuleMissing, kickoff_era, load_game_rules
from tests.phase5.sim_synth import synthetic_league

# ---------------------------------------------------------------- eras from config


def test_eras_split_at_the_touchback_spot_text() -> None:
    first = kickoff_era(2016)
    assert all(kickoff_era(s) == first for s in range(2016, 2024))
    assert kickoff_era(2024) != first
    assert kickoff_era(2026) not in (first, kickoff_era(2024))


@pytest.mark.parametrize("season", [2015, 2025])
def test_a_season_with_no_era_raises(season: int) -> None:
    with pytest.raises(GameRuleMissing, match="PRJ-02"):
        kickoff_era(season)


def test_era_quotes_are_short_and_checked_elsewhere() -> None:
    f = load_game_rules()
    seen: set[int] = set()
    for era in f.kickoff_eras.values():
        assert era.spec_id == "PRJ-02"
        assert all(len(q.split()) < 15 for q in era.quotes)
        assert not set(era.seasons) & set(era.absent_in)
        assert not set(era.seasons) & seen
        seen |= set(era.seasons)
    assert seen == set(f.sources)  # every captured season is in exactly one era


def test_overlapping_eras_are_refused(tmp_path: Path) -> None:
    raw = yaml.safe_load(GAME_RULES_PATH.read_text(encoding="utf-8"))
    names = list(raw["kickoff_eras"])
    raw["kickoff_eras"][names[1]]["seasons"].append(raw["kickoff_eras"][names[0]]["seasons"][0])
    p = tmp_path / "game_rules.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="kickoff era"):
        load_game_rules(p)


# ---------------------------------------------------------------- rows


def _plays() -> pl.DataFrame:
    """Two kickoffs (posteam = the receiving team): BBB receives and snaps at yardline 70; late
    in Q4, AAA receives while leading by 7 (the kicking team trails) and snaps at 60."""
    return pl.DataFrame(
        {
            "game_id": ["G"] * 4,
            "play_id": [1, 2, 3, 4],
            "season": [2000] * 4,
            "week_index": [5] * 4,
            "game_half": ["Half1", "Half1", "Half2", "Half2"],
            "qtr": [1, 1, 4, 4],
            "game_seconds_remaining": [3600.0, 3595.0, 100.0, 95.0],
            "score_differential": [0.0, 0.0, 7.0, 7.0],
            "posteam": ["BBB", "BBB", "AAA", "AAA"],
            "play_type": ["kickoff", "run", "kickoff", "pass"],
            "yardline_100": [65.0, 70.0, 65.0, 60.0],
            "return_touchdown": [0, 0, 0, 0],
            "own_kickoff_recovery_td": [0, 0, 0, 0],
            "penalty": [0, 0, 0, 0],
            "td_team": [None, None, None, None],
        },
        schema_overrides={"td_team": pl.String},
    )


def test_kickoff_rows_keep_season_week_and_late_flag() -> None:
    r = kickoff_rows(_plays(), late_kickoff_seconds=300)
    assert r.select("season", "week_index", "late", "changed", "next_yardline").rows() == [
        (2000, 5, 0, 0.0, 70.0),
        (2000, 5, 1, 0.0, 60.0),
    ]
    assert r["return_td"].to_list() == [0.0, 0.0] and r["kicking_td"].to_list() == [0.0, 0.0]


def _window_league():  # type: ignore[no-untyped-def]
    """Window kickoff rows: seasons 2001, 2002, 2002 at weeks 10, 40, 41 (synthetic)."""
    return replace(
        synthetic_league(),
        kickoff_changed=np.zeros(3),
        kickoff_next_yardline=np.array([74.0, 75.0, 76.0]),
        kickoff_return_td=np.zeros(3),
        kickoff_kicking_td=np.zeros(3),
        kickoff_season=np.array([2001.0, 2002.0, 2002.0]),
        kickoff_week_index=np.array([10.0, 40.0, 41.0]),
        kickoff_late=np.zeros(3),
        kickoff_target_index=42,
    )


def _current(week_index: list[int], yardline: list[float]) -> pl.DataFrame:
    n = len(week_index)
    return pl.DataFrame(
        {
            "season": [2003] * n,
            "week_index": week_index,
            "late": [0] * n,
            "changed": [0.0] * n,
            "next_yardline": yardline,
            "return_td": [0.0] * n,
            "kicking_td": [0.0] * n,
        }
    )


def test_game_table_uses_same_era_window_rows_and_earlier_games() -> None:
    lg = game_kickoffs(_window_league(), _current([42, 43], [69.0, 70.0]), seasons={2001, 2002},
                       game_index=44, h_l=1.0, min_events=1)  # fmt: skip
    assert lg.kickoff_next_yardline.tolist() == [74.0, 75.0, 76.0, 69.0, 70.0]
    assert lg.kickoff.n[0] == 5
    w = 0.5 ** (44 - np.array([10.0, 40.0, 41.0, 42.0, 43.0]))
    k = lg.kickoff
    got = np.diff(np.concatenate([[0.0], k.cum[k.lo[0] : k.hi[0]]]))
    rows = k.values[k.lo[0] : k.hi[0]].astype(np.int64)
    assert np.allclose(got, w[rows] / w.sum())


def test_game_table_leaves_out_other_eras() -> None:
    lg = game_kickoffs(_window_league(), _current([42, 43], [69.0, 70.0]), seasons=set(),
                       game_index=44, h_l=1.0, min_events=1)  # fmt: skip
    assert lg.kickoff_next_yardline.tolist() == [69.0, 70.0]
    assert lg.kickoff.n[0] == 2


def test_too_few_same_era_kickoffs_raise() -> None:
    with pytest.raises(NotImplementedError, match="PRJ-02 kickoff era"):
        game_kickoffs(_window_league(), _current([42, 43], [69.0, 70.0]), seasons=set(),
                      game_index=44, h_l=1.0, min_events=3)  # fmt: skip


def test_late_category_still_falls_back_to_the_other_kickoffs() -> None:
    lg = game_kickoffs(_window_league(), _current([42], [69.0]), seasons={2002},
                       game_index=44, h_l=1.0, min_events=1)  # fmt: skip
    assert lg.kickoff.n[1] == 0
    assert lg.kickoff.source[1] == 0


def test_a_kickoff_after_the_game_is_refused() -> None:
    with pytest.raises(ValueError, match="PRJ-02"):
        game_kickoffs(_window_league(), _current([45], [69.0]), seasons={2002},
                      game_index=44, h_l=1.0, min_events=1)  # fmt: skip


def test_raw_kickoff_rows_survive_save_and_load(tmp_path: Path) -> None:
    lg = _window_league()
    save_league(lg, tmp_path / "w.npz")
    back = load_league(tmp_path / "w.npz")
    assert back.kickoff_season.tolist() == lg.kickoff_season.tolist()
    assert back.kickoff_week_index.tolist() == lg.kickoff_week_index.tolist()
    assert back.kickoff_late.tolist() == lg.kickoff_late.tolist()
    assert back.kickoff_target_index == 42
