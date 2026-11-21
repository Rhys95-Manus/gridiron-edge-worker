"""SHD-01 / SHD-02 / SHD-03 / SHD-04 / SHD-12: the tick's pure scheduler, on a fake clock.

Games are synthetic (no real-world schedule facts)."""

import datetime as dt

import pytest

from ge.config import load_params
from ge.shadow.schedule import (
    Attempt,
    GameKick,
    ShadowWindows,
    SnapshotType,
    StatusRec,
    judge,
    plan_tick,
    windows,
)

K = dt.datetime(2026, 11, 23, 18, 0, tzinfo=dt.UTC)
G = GameKick(game_id="2026_12_AAA_BBB", season=2026, week=12, kickoff_utc=K)
START = K - dt.timedelta(days=3)
M = dt.timedelta(minutes=1)
H = dt.timedelta(hours=1)


@pytest.fixture
def cfg() -> ShadowWindows:
    return ShadowWindows.from_params(load_params())


def test_windows_follow_bt01_shd02_shd04(cfg: ShadowWindows) -> None:
    w = {x.snapshot_type: x for x in windows(K, cfg)}
    assert set(w) == set(SnapshotType)
    t24 = w[SnapshotType.T24H]
    assert (t24.target, t24.open, t24.close) == (K - 24 * H, K - 24 * H - 15 * M, K - 23 * H)
    t90 = w[SnapshotType.T90M]
    assert (t90.target, t90.open, t90.close) == (K - 90 * M, K - 100 * M, K - 65 * M)
    cb = w[SnapshotType.CLOSE_BOOK]
    assert (cb.target, cb.open, cb.close) == (K - 5 * M, K - 9 * M, K - 1 * M)


def test_tick_and_schedule_age_params(cfg: ShadowWindows) -> None:
    assert cfg.tick == 5 * M
    assert cfg.schedule_max_age == 6 * H


def _due(now: dt.datetime, cfg: ShadowWindows, **kw: object) -> list[SnapshotType]:
    plan = plan_tick(now, [G], kw.get("status", {}), kw.get("attempts", {}), START, cfg)  # type: ignore[arg-type]
    return [d.window.snapshot_type for d in plan.due]


@pytest.mark.parametrize(
    ("offset", "due"),
    [
        (-24 * H - 16 * M, []),
        (-24 * H - 15 * M, [SnapshotType.T24H]),  # window edges are inclusive
        (-24 * H, [SnapshotType.T24H]),
        (-23 * H, [SnapshotType.T24H]),
        (-100 * M, [SnapshotType.T90M]),
        (-65 * M, [SnapshotType.T90M]),
        (-9 * M, [SnapshotType.CLOSE_BOOK]),
        (-1 * M, [SnapshotType.CLOSE_BOOK]),
    ],
)
def test_due_inside_windows(cfg: ShadowWindows, offset: dt.timedelta, due: list[str]) -> None:
    assert _due(K + offset, cfg, status=_closed_before(K + offset, cfg)) == due


def _closed_before(now: dt.datetime, cfg: ShadowWindows) -> dict[tuple[str, str], StatusRec]:
    """ok rows for every window that closed before now, so only the open one shows."""
    return {
        (G.game_id, w.snapshot_type): StatusRec("ok", w.target, w.target, w.target)
        for w in windows(K, cfg)
        if w.close < now
    }


def test_not_due_when_already_ok(cfg: ShadowWindows) -> None:
    now = K - 24 * H
    status = {(G.game_id, SnapshotType.T24H): StatusRec("ok", now - M, now - M, now - M)}
    assert _due(now, cfg, status=status) == []


@pytest.mark.parametrize(
    ("attempts", "expected"),
    [
        ([], "missed_not_run"),
        ([Attempt(K - 24 * H, "api_error", "HTTP 503")], "missed_api_error"),
        ([Attempt(K - 24 * H, "no_markets", "")], "missed_no_markets"),
        (
            [Attempt(K - 24 * H, "api_error", "x"), Attempt(K - 23 * H - M, "no_markets", "")],
            "missed_no_markets",  # the last attempt in the window decides
        ),
        ([Attempt(K - 30 * H, "api_error", "outside the window")], "missed_not_run"),
    ],
)
def test_miss_rows_when_window_closes(
    cfg: ShadowWindows, attempts: list[Attempt], expected: str
) -> None:
    now = K - 23 * H + M
    plan = plan_tick(now, [G], {}, {(G.game_id, SnapshotType.T24H): attempts}, START, cfg)
    assert plan.due == []
    [row] = plan.status_rows
    assert (row["game_id"], row["snapshot_type"], row["status"]) == (G.game_id, "T-24h", expected)
    assert row["target_ts"] == K - 24 * H and row["taken_ts"] is None
    assert row["season"] == 2026 and row["week"] == 12 and row["kickoff_utc"] == K


def test_miss_rows_are_written_once(cfg: ShadowWindows) -> None:
    now = K - 23 * H + M
    status = {(G.game_id, SnapshotType.T24H): StatusRec("missed_not_run", None, K - 24 * H, now)}
    assert plan_tick(now, [G], status, {}, START, cfg).status_rows == []


def test_windows_closed_before_capture_started_are_not_planned(cfg: ShadowWindows) -> None:
    now = K - 30 * M
    plan = plan_tick(now, [G], {}, {}, now, cfg)
    assert plan.due == [] and plan.status_rows == []


def test_window_open_at_start_is_planned(cfg: ShadowWindows) -> None:
    now = K - 24 * H + 30 * M
    assert [d.window.snapshot_type for d in plan_tick(now, [G], {}, {}, now, cfg).due] == [
        SnapshotType.T24H
    ]


def test_every_snapshot_type_gets_a_status_row(cfg: ShadowWindows) -> None:
    plan = plan_tick(K + M, [G], {}, {}, START, cfg)
    assert sorted(r["snapshot_type"] for r in plan.status_rows) == sorted(SnapshotType)
    assert {r["status"] for r in plan.status_rows} == {"missed_not_run"}


def test_judge_ok_and_ok_late(cfg: ShadowWindows) -> None:
    w = {x.snapshot_type: x for x in windows(K, cfg)}[SnapshotType.T24H]
    assert judge(w.target, w) == "ok"
    assert judge(w.open, w) == "ok"
    assert judge(w.target + M, w) == "ok_late"
    assert judge(w.close, w) == "ok_late"
    assert judge(w.close + M, w) is None
    assert judge(w.open - M, w) is None


def test_kickoff_moved_invalidates_and_replans(cfg: ShadowWindows) -> None:
    taken = K - 24 * H
    moved = GameKick(G.game_id, 2026, 12, K + 3 * H)
    status = {(G.game_id, SnapshotType.T24H): StatusRec("ok", taken, taken, taken)}
    now = moved.kickoff_utc - 24 * H
    plan = plan_tick(now, [moved], status, {}, START, cfg)
    [row] = plan.status_rows
    assert row["status"] == "invalid_kickoff_moved" and row["taken_ts"] == taken
    assert row["kickoff_utc"] == moved.kickoff_utc
    assert [d.window.snapshot_type for d in plan.due] == [SnapshotType.T24H]


def test_kickoff_moved_but_still_inside_tolerance_stays_valid(cfg: ShadowWindows) -> None:
    taken = K - 24 * H
    moved = GameKick(G.game_id, 2026, 12, K + 10 * M)
    status = {(G.game_id, SnapshotType.T24H): StatusRec("ok", taken, taken, taken)}
    plan = plan_tick(moved.kickoff_utc - 22 * H, [moved], status, {}, START, cfg)
    assert plan.status_rows == [] and plan.due == []


def test_plan_is_pure(cfg: ShadowWindows) -> None:
    args = (K - 24 * H, [G], {}, {}, START, cfg)
    assert plan_tick(*args) == plan_tick(*args)  # type: ignore[arg-type]


def test_now_must_be_aware(cfg: ShadowWindows) -> None:
    with pytest.raises(ValueError, match="aware"):
        plan_tick(dt.datetime(2026, 11, 23), [G], {}, {}, START, cfg)
