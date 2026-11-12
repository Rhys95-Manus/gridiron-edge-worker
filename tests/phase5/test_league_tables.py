"""PRJ-02 league level (E10): h_L-weighted empirical distributions and rates, packed for the
simulation. Synthetic placeholder plays; every expected value is hand-computed."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from ge.models.sim.league import (
    CLOCK_CATEGORIES,
    clock_category,
    next_play_outcomes,
    pack_categories,
    timeout_rates,
    weighted_rate,
)


def test_pack_categories_weighted_cumulative() -> None:
    """Category 0: values 1, 3 with weights 1, 3 -> cumulative 0.25, 1.0 (sorted by value).
    Category 1: value 7 weight 2 -> 1.0. Category 2 empty -> falls back to the parent (0)."""
    df = pl.DataFrame({"cat": [0, 0, 1], "value": [3.0, 1.0, 7.0], "w": [3.0, 1.0, 2.0]})
    p = pack_categories(df, n_categories=3, parent=[0, 0, 0], min_events=1)
    lo, hi = p.lo[0], p.hi[0]
    assert p.values[lo:hi].tolist() == [1.0, 3.0]
    assert p.cum[lo:hi].tolist() == pytest.approx([0.25, 1.0])
    assert p.values[p.lo[1] : p.hi[1]].tolist() == [7.0]
    assert p.source[2] == 0  # empty category uses its parent's draws
    assert (p.lo[2], p.hi[2]) == (p.lo[0], p.hi[0])


def test_pack_falls_back_below_min_events() -> None:
    df = pl.DataFrame({"cat": [0, 0, 0, 1], "value": [1.0, 2.0, 3.0, 9.0], "w": [1.0] * 4})
    p = pack_categories(df, n_categories=2, parent=[0, 0], min_events=2)
    assert p.source[1] == 0  # one play in category 1 < 2


def test_weighted_rate() -> None:
    assert weighted_rate(np.array([1.0, 0.0, 1.0]), np.array([1.0, 2.0, 1.0])) == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("row", "category"),
    [
        ({"play_type": "run", "out_of_bounds": 0}, "run_inbounds"),
        ({"play_type": "run", "out_of_bounds": 1}, "out_of_bounds"),
        ({"play_type": "pass", "complete_pass": 1, "out_of_bounds": 0}, "complete_inbounds"),
        ({"play_type": "pass", "complete_pass": 1, "out_of_bounds": 1}, "out_of_bounds"),
        ({"play_type": "pass", "incomplete_pass": 1}, "incomplete"),
        ({"play_type": "pass", "sack": 1}, "sack"),
        ({"play_type": "pass", "interception": 1}, "turnover"),
        ({"play_type": "run", "fumble_lost": 1}, "turnover"),
        ({"play_type": "run", "touchdown": 1}, "score"),
        ({"play_type": "qb_kneel"}, "kneel"),
        ({"play_type": "qb_spike"}, "spike"),
        ({"play_type": "no_play", "penalty": 1}, "penalty"),
        ({"play_type": "punt"}, "punt"),
        ({"play_type": "kickoff"}, "kickoff"),
        ({"play_type": "field_goal"}, "field_goal"),
        ({"play_type": "extra_point"}, "try"),
    ],
)
def test_clock_category(row: dict[str, object], category: str) -> None:
    base = {
        "play_type": None,
        "out_of_bounds": 0,
        "complete_pass": 0,
        "incomplete_pass": 0,
        "sack": 0,
        "interception": 0,
        "fumble_lost": 0,
        "touchdown": 0,
        "penalty": 0,
        "two_point_attempt": 0,
    }
    df = pl.DataFrame([{**base, **row}], schema_overrides={"play_type": pl.String})
    got = df.select(clock_category().alias("c"))["c"][0]
    assert got == category
    assert category in CLOCK_CATEGORIES


def _timeout_game() -> pl.DataFrame:
    """Q4, inside 2:00: AAA (trailing, 2 timeouts) runs in bounds, AAA calls a timeout (an
    nflverse no_play row with timeout = 1 and no posteam), then AAA snaps again. Earlier, an
    accepted no-play penalty with no timeout."""
    cols = {
        "game_id": ["G"] * 5,
        "play_id": [1.0, 2.0, 3.0, 4.0, 5.0],
        "game_half": ["Half2"] * 5,
        "qtr": [4.0] * 5,
        "posteam": ["AAA", "AAA", "AAA", None, "AAA"],
        "defteam": ["BBB", "BBB", "BBB", None, "BBB"],
        "play_type": ["run", "no_play", "run", "no_play", "pass"],
        "penalty": [0, 1, 0, 0, 0],
        "timeout": [0, 0, 0, 1, 0],
        "timeout_team": [None, None, None, "AAA", None],
        "game_seconds_remaining": [200.0, 160.0, 110.0, 80.0, 80.0],
        "half_seconds_remaining": [200.0, 160.0, 110.0, 80.0, 80.0],
        "score_differential": [-3.0] * 5,
        "posteam_timeouts_remaining": [2.0, 2.0, 2.0, 1.0, 1.0],
        "defteam_timeouts_remaining": [3.0] * 5,
        "out_of_bounds": [0] * 5,
        "complete_pass": [0] * 5,
        "incomplete_pass": [0, 0, 0, 0, 1],
        "sack": [0] * 5,
        "interception": [0] * 5,
        "fumble_lost": [0] * 5,
        "touchdown": [0] * 5,
        "two_point_attempt": [0] * 5,
        "w": [1.0] * 5,
    }
    return pl.DataFrame(
        cols,
        schema_overrides={"timeout_team": pl.String, "posteam": pl.String, "defteam": pl.String},
    )


def test_timeout_rows_are_not_snaps() -> None:
    df = _timeout_game()
    got = df.select(clock_category().alias("c"))["c"].to_list()
    assert got == ["run_inbounds", "penalty", "run_inbounds", None, "incomplete"]


def test_offense_timeout_rate_inside_two_minutes() -> None:
    """The only running-clock play inside 2:00 (play 3, Q4, offense trailing with timeouts) is
    followed by an offense timeout: the offense-trailing Q4 rate is 1, the defense's 0."""
    rates, _ = timeout_rates(_timeout_game(), two_minute=120)
    assert rates[1, 0, 0] == pytest.approx(1.0)  # second half, offense, trailing
    assert rates[1, 1, 2] == pytest.approx(0.0)  # second half, defense, leading


def test_next_play_outcomes_for_punts() -> None:
    """Game G: AAA punts from its own 30 (yardline_100 70); BBB's next snap is at its 40
    (yardline_100 60), so possession changed. A timeout row in between is skipped."""
    plays = pl.DataFrame(
        {
            "game_id": ["G", "G", "G"],
            "play_id": [10, 11, 12],
            "game_half": ["Half1"] * 3,
            "posteam": ["AAA", None, "BBB"],
            "play_type": ["punt", None, "run"],
            "yardline_100": [70.0, None, 60.0],
            "return_touchdown": [0, 0, 0],
            "penalty": [0, 0, 0],
            "td_team": [None, None, None],
        },
        schema_overrides={"td_team": pl.String},
    )
    out = next_play_outcomes(plays, "punt")
    assert out.select("yardline_100", "changed", "next_yardline_100", "return_td").rows() == [
        (70.0, True, 60.0, False)
    ]
