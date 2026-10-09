"""Section 4 slots (spec synced 2026-10-08): usage rank within the team. At each position, rank
by snap share over the team's games before the target game (tiebreak: target share for WR and
TE, carry share for RB and QB); the depth chart only with no game history yet (week 1 or a newly
signed player), its ties broken by last season's snaps on any team, then gsis_id. Slots:
QB1, RB1, RB2, WR1, WR2, WR3, TE1. Players are synthetic IDs."""

from __future__ import annotations

from ge.metrics.slots import History, rank_position, slot_labels


def H(snap: float, tb: float = 0.0) -> History:
    return History(snap_share=snap, tiebreak_share=tb)


def test_rank_by_prior_snap_share() -> None:
    hist = {"a": H(0.6), "b": H(0.9), "c": H(0.3)}
    assert rank_position("WR", ["a", "b", "c"], hist, {}, {}) == ["b", "a", "c"]


def test_tiebreak_target_share_for_wr_te() -> None:
    hist = {"a": H(0.8, 0.10), "b": H(0.8, 0.25)}
    assert rank_position("WR", ["a", "b"], hist, {}, {}) == ["b", "a"]
    assert rank_position("TE", ["a", "b"], hist, {}, {}) == ["b", "a"]


def test_tiebreak_carry_share_for_rb_qb() -> None:
    hist = {"a": H(0.5, 0.40), "b": H(0.5, 0.20)}
    assert rank_position("RB", ["b", "a"], hist, {}, {}) == ["a", "b"]


def test_full_tie_goes_by_gsis_id() -> None:
    hist = {"z": H(0.5, 0.2), "m": H(0.5, 0.2)}
    assert rank_position("WR", ["z", "m"], hist, {}, {}) == ["m", "z"]


def test_week_one_uses_depth_chart_with_last_season_tiebreak() -> None:
    depth = {"a": 1.0, "b": 1.0, "c": 2.0, "d": 1.0}
    last = {"a": 300.0, "b": 700.0}  # d has no last-season snaps
    assert rank_position("WR", ["a", "b", "c", "d", "e"], {}, depth, last) == [
        "b",
        "a",
        "d",
        "c",
        "e",  # not on the chart: last
    ]


def test_new_signing_inserted_at_depth_chart_rank() -> None:
    hist = {"a": H(0.9), "b": H(0.7), "c": H(0.4)}
    depth = {"a": 1.0, "n": 1.0, "b": 2.0, "c": 3.0}  # n ties a on the chart
    last = {"a": 900.0, "n": 500.0}
    # Depth order: a, n (tie broken by last season's snaps), b, c -> n is second.
    assert rank_position("WR", ["a", "b", "c", "n"], hist, depth, last) == ["a", "n", "b", "c"]


def test_new_signing_off_chart_goes_last() -> None:
    hist = {"a": H(0.9), "b": H(0.7)}
    assert rank_position("WR", ["n", "a", "b"], hist, {"a": 1.0, "b": 2.0}, {}) == ["a", "b", "n"]


def test_slot_labels_and_caps() -> None:
    assert slot_labels("WR", ["a", "b", "c", "d"]) == {"a": "WR1", "b": "WR2", "c": "WR3"}
    assert slot_labels("RB", ["a", "b", "c"]) == {"a": "RB1", "b": "RB2"}
    assert slot_labels("TE", ["a", "b"]) == {"a": "TE1"}
    assert slot_labels("QB", ["a", "b"]) == {"a": "QB1"}
    assert slot_labels("FB", ["a"]) == {}
