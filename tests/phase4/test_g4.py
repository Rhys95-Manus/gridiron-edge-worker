"""G4 in PRJ-01a on the fixture store (2023 in full, 2024 weeks 1-8).

Weeks 1-4: each team's ratings shrink toward last season's final ratings, regressed a further
1/3 toward 0 per side for a new play-caller or QB (offense: caller or QB; defense: caller), with
last season's final intercepts. From week 5 there is no prior. An unknown change raises. A
relocated team keeps its history by franchise."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ge.config import load_params, use_season
from ge.metrics.coaching import CoachingRegistry
from ge.metrics.context import MetricContext, build_context
from ge.models.ratings import (
    RATING_TYPES,
    build_prior,
    carry_by_franchise,
    fit_ratings,
    load_window_consts,
    ratings_for_game,
    ratings_params,
    season_plays,
)
from ge.store.snapshot import snapshot
from tests.phase3.conftest import G4_WEEK, STORE, first_game

EXTRA = float(load_params().conventions.g4_new_caller_or_qb_extra_regression.value)


def _ctx(week: int, registry: CoachingRegistry) -> MetricContext:
    return build_context(snapshot(first_game(week), root=STORE), registry)


def _setup(week: int, registry: CoachingRegistry, ratings_root: Path) -> tuple[Any, Any, Any]:
    ctx = _ctx(week, registry)
    with use_season(ctx.season):
        params = ratings_params(ctx.season)
    consts = load_window_consts(ctx.season, ratings_root)
    return ctx, params, consts


@pytest.mark.usefixtures("fit_env")
def test_prior_is_last_seasons_final_ratings_regressed_on_change(
    registry: CoachingRegistry, ratings_root: Path
) -> None:
    ctx, params, consts = _setup(G4_WEEK, registry, ratings_root)
    last = season_plays(ctx.prior_context(), ctx.season - 1, consts)
    teams_then = sorted(set(last["posteam"].to_list()) | set(last["defteam"].to_list()))
    base = fit_ratings(last, teams_then, penalty=params.penalty, h=params.h_efficiency, prior=None)
    prior = build_prior(ctx, params, consts)
    assert prior is not None
    assert (prior.int_pass, prior.int_run, prior.sigma2) == (
        base.int_pass,
        base.int_run,
        base.sigma2,
    )
    teams = sorted({t for t, _ in prior.ratings})
    assert len(teams) == 32  # no relocation between the fixture's 2023 and 2024
    unchanged_any = False
    for t in teams:
        for side in ("offense", "defense"):
            changed, _ = ctx.g4_changed(t, side)
            assert changed is not None
            unchanged_any |= not changed
            for k in RATING_TYPES:
                if not k.startswith(side[:3]):
                    continue
                b = base.values[(t, k)]
                want = b + EXTRA * (0.0 - b) if changed else b
                assert prior.ratings[(t, k)] == pytest.approx(want, abs=1e-15), (t, k)
    assert unchanged_any  # the synthetic registry keeps every caller


@pytest.mark.usefixtures("fit_env")
def test_forced_change_regresses_one_third(
    registry: CoachingRegistry, ratings_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MetricContext, "g4_changed", lambda self, t, side: (False, ""))
    ctx, params, consts = _setup(G4_WEEK, registry, ratings_root)
    none_changed = build_prior(ctx, params, consts)
    assert none_changed is not None
    team = sorted({t for t, _ in none_changed.ratings})[0]

    def one_change(self: MetricContext, t: str, side: Any) -> tuple[bool | None, str]:
        return (t == team and side == "offense"), ""

    monkeypatch.setattr(MetricContext, "g4_changed", one_change)
    ctx2, _, _ = _setup(G4_WEEK, registry, ratings_root)
    got = build_prior(ctx2, params, consts)
    assert got is not None
    for (t, k), v in none_changed.ratings.items():
        want = v * (1 - EXTRA) if (t == team and k.startswith("off")) else v
        assert got.ratings[(t, k)] == pytest.approx(want, abs=1e-15), (t, k)


@pytest.mark.usefixtures("fit_env")
def test_unknown_change_raises(
    registry: CoachingRegistry, ratings_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(MetricContext, "g4_changed", lambda self, t, side: (None, ""))
    ctx, params, consts = _setup(G4_WEEK, registry, ratings_root)
    with pytest.raises(NotImplementedError, match="G4"):
        build_prior(ctx, params, consts)


@pytest.mark.usefixtures("fit_env")
@pytest.mark.parametrize(("week", "has_prior"), [(4, True), (5, False)])
def test_prior_only_in_weeks_one_to_four(
    week: int, has_prior: bool, registry: CoachingRegistry, ratings_root: Path
) -> None:
    ctx, params, consts = _setup(week, registry, ratings_root)
    assert (build_prior(ctx, params, consts) is not None) is has_prior


@pytest.mark.usefixtures("fit_env")
def test_ratings_for_game_notes_g4(registry: CoachingRegistry, ratings_root: Path) -> None:
    got = ratings_for_game(
        first_game(G4_WEEK), root=STORE, ratings_root=ratings_root, registry=registry
    )
    assert any("G4" in n for n in got.notes)


def test_relocated_franchise_keeps_its_history() -> None:
    """Synthetic abbreviations (not real teams): OLD became NEW, same franchise."""
    last = {
        (t, k): float(i)
        for i, (t, k) in enumerate((t, k) for t in ("OLD", "KEPT") for k in RATING_TYPES)
    }
    fr = {"OLD": "F1", "NEW": "F1", "KEPT": "F2", "FRESH": "F3"}
    got = carry_by_franchise(last, ["NEW", "KEPT", "FRESH"], fr.__getitem__)
    for k in RATING_TYPES:
        assert got[("NEW", k)] == last[("OLD", k)]
        assert got[("KEPT", k)] == last[("KEPT", k)]
        assert ("FRESH", k) not in got
