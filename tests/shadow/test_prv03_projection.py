"""PRV-03 projection mean, on synthetic data only (made-up IDs; no real players or games)."""

from __future__ import annotations

import math
import shutil
from pathlib import Path
from typing import Any

import polars as pl
import pytest
import yaml

from ge.config import FITTED_ROOT
from ge.pricer_v0.projection import (
    SERIES_STAT,
    Centring,
    PricerStop,
    Prv03Fit,
    centring,
    k_key,
    load_prv03_fit,
    project,
)
from ge.pricer_v0.reasons import PricerUnpriced
from ge.store.snapshot import FF_OPPORTUNITY_COLUMNS

SEASON = 2024
TARGET = f"{SEASON}_05_TMA_TMB"
H_USAGE = 6.0
H_EFF = 8.0
K = 40.0
FIT = Prv03Fit(
    window="test",
    usage_half_life=H_USAGE,
    k={"receptions": K, "receiving_yards": K, "rushing_yards": K},
    efficiency_half_life=H_EFF,
)


def gid(week: int, season: int = SEASON) -> str:
    return f"{season}_{week:02d}_TMA_TMB"


def ffrow(game_id: str, player: str = "P1", team: str = "TMA", **kw: Any) -> dict[str, Any]:
    row: dict[str, Any] = {c: 0.0 for c in FF_OPPORTUNITY_COLUMNS}
    row.update(game_id=game_id, player_id=player, posteam=team, position="WR")
    row.update(rec_attempt=5.0, receptions=3.0, receptions_exp=3.0)
    row.update(rec_yards_gained=30.0, rec_yards_gained_exp=30.0)
    row.update(kw)
    return row


def ff(rows: list[dict[str, Any]]) -> pl.DataFrame:
    schema = {
        c: pl.Utf8 if c in ("game_id", "player_id", "posteam", "position") else pl.Float64
        for c in FF_OPPORTUNITY_COLUMNS
    }
    return pl.DataFrame(rows, schema=schema)


def games(
    weeks: tuple[int, ...] = (1, 2, 3, 4), teams: tuple[str, ...] = ("TMA", "TMB")
) -> pl.DataFrame:
    """MetricContext.games shape: each team's visible games, g = 0 for the most recent."""
    rows = []
    for t in teams:
        for i, w in enumerate(sorted(weeks, reverse=True)):
            rows.append({"team": t, "game_id": gid(w), "week": w, "g": float(i)})
    return pl.DataFrame(
        rows, schema={"team": pl.Utf8, "game_id": pl.Utf8, "week": pl.Int64, "g": pl.Float64}
    )


MEANS = Centring(
    means={(g, s): 0.0 for g in ("QB", "RB", "WR", "TE", "Other") for s in SERIES_STAT.values()},
    label="test centring",
)


def run(
    frame: pl.DataFrame,
    stat: str = "receptions",
    centring_means: Centring = MEANS,
    team: str = "TMA",
    gms: pl.DataFrame | None = None,
    fit: Prv03Fit = FIT,
) -> Any:
    return project(
        frame,
        games() if gms is None else gms,
        target_game_id=TARGET,
        gsis_id="P1",
        team=team,
        stat=stat,
        centring_means=centring_means,
        fit=fit,
    )


def wmean(xs_by_g: dict[float, float], h: float) -> float:
    w = {g: 0.5 ** (g / h) for g in xs_by_g}
    return math.fsum(w[g] * x for g, x in xs_by_g.items()) / math.fsum(w.values())


def test_e_is_the_usage_weighted_mean_of_expected_values() -> None:
    rows = [
        ffrow(gid(w), receptions=e, receptions_exp=e)
        for w, e in ((1, 1.0), (2, 2.0), (3, 3.0), (4, 4.0))
    ]
    p = run(ff(rows))
    assert p.reason is None
    assert p.n_games == 4
    # week 4 is g = 0, week 1 is g = 3
    assert p.e == pytest.approx(wmean({0.0: 4.0, 1.0: 3.0, 2.0: 2.0, 3.0: 1.0}, H_USAGE), abs=1e-12)
    # actual = expected, centring 0 -> G = 0, mu = E
    assert p.g == pytest.approx(0.0, abs=1e-12)
    assert p.mu == pytest.approx(p.e, abs=1e-12)


def test_exactly_three_games_is_priced_and_e_is_not_shrunk() -> None:
    rows = [
        ffrow(gid(w), receptions_exp=x, receptions=x) for w, x in ((2, 9.0), (3, 6.0), (4, 3.0))
    ]
    p = run(ff(rows))
    assert p.reason is None and p.n_games == 3
    assert p.e == pytest.approx(wmean({0.0: 3.0, 1.0: 6.0, 2.0: 9.0}, H_USAGE), abs=1e-12)


def test_two_games_is_too_few() -> None:
    p = run(ff([ffrow(gid(3)), ffrow(gid(4))]))
    assert p.reason is PricerUnpriced.TOO_FEW_STINT_GAMES
    assert p.n_games == 2 and p.mu is None


def test_a_game_with_no_target_or_carry_does_not_count() -> None:
    rows = [ffrow(gid(2)), ffrow(gid(3)), ffrow(gid(4), rec_attempt=0.0, rush_attempt=0.0)]
    assert run(ff(rows)).reason is PricerUnpriced.TOO_FEW_STINT_GAMES


def test_null_expected_value_counts_as_zero() -> None:
    rows = [ffrow(gid(w), receptions_exp=3.0, receptions=3.0) for w in (1, 2, 3)]
    rows.append(ffrow(gid(4), receptions_exp=None, receptions=0.0))
    p = run(ff(rows))
    assert p.e == pytest.approx(wmean({0.0: 0.0, 1.0: 3.0, 2.0: 3.0, 3.0: 3.0}, H_USAGE), abs=1e-12)


def test_a_missed_game_still_ages_older_games() -> None:
    # he missed week 3 (team g = 1): his games are g = 0, 2, 3
    rows = [
        ffrow(gid(w), receptions_exp=x, receptions=x) for w, x in ((1, 1.0), (2, 2.0), (4, 4.0))
    ]
    p = run(ff(rows))
    assert p.e == pytest.approx(wmean({0.0: 4.0, 2.0: 2.0, 3.0: 1.0}, H_USAGE), abs=1e-12)


def test_stint_is_the_mapped_team_even_across_a_trade_back() -> None:
    gms = games(teams=("TMA", "TMB"))
    rows = [
        ffrow(gid(1), receptions_exp=1.0, receptions=1.0),
        ffrow(gid(2), receptions_exp=2.0, receptions=2.0),
        ffrow(gid(3), team="TMB", receptions_exp=50.0, receptions=50.0),
        ffrow(gid(4), receptions_exp=4.0, receptions=4.0),
    ]
    p = run(ff(rows), gms=gms)
    assert p.reason is None and p.n_games == 3
    assert p.e == pytest.approx(wmean({0.0: 4.0, 2.0: 2.0, 3.0: 1.0}, H_USAGE), abs=1e-12)
    q = run(ff(rows), gms=gms, team="TMB")
    assert q.reason is PricerUnpriced.TOO_FEW_STINT_GAMES and q.n_games == 1


def test_earlier_seasons_never_count() -> None:
    rows = [ffrow(gid(w, SEASON - 1)) for w in (14, 15, 16, 17)]
    rows += [ffrow(gid(4))]
    assert run(ff(rows)).reason is PricerUnpriced.TOO_FEW_STINT_GAMES


def test_only_visible_games_count_and_the_target_game_never() -> None:
    rows = [ffrow(gid(3)), ffrow(gid(4)), ffrow(TARGET), ffrow(gid(9))]
    p = run(ff(rows))  # weeks 9 and the target are not in the visible games table
    assert p.reason is PricerUnpriced.TOO_FEW_STINT_GAMES and p.n_games == 2


def test_position_group_is_from_the_most_recent_qualifying_row() -> None:
    rows = [
        ffrow(gid(1), position="TE"),
        ffrow(gid(2), position="TE"),
        ffrow(gid(3), position="WR"),
        ffrow(gid(4), position="TE", rec_attempt=0.0),
    ]
    assert run(ff(rows)).group == "WR"
    rows2 = [ffrow(gid(w), position="FB") for w in (2, 3, 4)]
    assert run(ff(rows2)).group == "Other"
    rows3 = [ffrow(gid(w), position=None) for w in (2, 3, 4)]
    assert run(ff(rows3)).group == "Other"


def test_no_centring_mean_for_the_group() -> None:
    means = Centring(means={("WR", "receptions"): 0.0}, label="x")
    rows = [ffrow(gid(w), position="TE") for w in (2, 3, 4)]
    p = run(ff(rows), centring_means=means)
    assert p.reason is PricerUnpriced.NO_CENTRING_MEAN and p.group == "TE"


def test_too_few_games_comes_before_no_centring_mean() -> None:
    means = Centring(means={}, label="x")
    assert (
        run(ff([ffrow(gid(4))]), centring_means=means).reason is PricerUnpriced.TOO_FEW_STINT_GAMES
    )


def test_mu_is_e_plus_m_plus_shrunk_centred_gap() -> None:
    m = 0.5
    means = Centring(means={("WR", "receiving_yards"): m}, label="x")
    # raw gaps (actual - expected) per team g: g0 +10, g1 -4, g2 +6
    data = {0.0: (40.0, 30.0), 1.0: (26.0, 30.0), 2.0: (36.0, 30.0)}
    week_of = {0.0: 4, 1.0: 3, 2.0: 2}
    rows = [
        ffrow(gid(week_of[g]), rec_yards_gained=a, rec_yards_gained_exp=x)
        for g, (a, x) in data.items()
    ]
    p = run(ff(rows), stat="receiving_yards", centring_means=means)
    w = {g: 0.5 ** (g / H_EFF) for g in data}
    centred = {g: (a - x) - m for g, (a, x) in data.items()}
    v_w = math.fsum(w[g] * centred[g] for g in data) / math.fsum(w.values())
    n_eff = math.fsum(w.values()) ** 2 / math.fsum(x * x for x in w.values())
    g_shrunk = n_eff * v_w / (n_eff + K)
    assert p.e == pytest.approx(30.0, abs=1e-12)
    assert p.m == pytest.approx(m, abs=1e-12)
    assert p.g_n_eff == pytest.approx(n_eff, abs=1e-12)
    assert p.g == pytest.approx(g_shrunk, abs=1e-12)
    assert p.mu == pytest.approx(30.0 + m + g_shrunk, abs=1e-12)


def test_mu_not_positive() -> None:
    means = Centring(means={("RB", "rushing_yards"): -5.0}, label="x")
    rows = [
        ffrow(
            gid(w),
            position="RB",
            rush_attempt=1.0,
            rush_yards_gained=0.0,
            rush_yards_gained_exp=2.0,
        )
        for w in (2, 3, 4)
    ]
    p = run(ff(rows), stat="rushing_yards", centring_means=means)
    assert p.reason is PricerUnpriced.MU_NOT_POSITIVE
    assert p.mu is not None and p.mu <= 0


def test_rows_from_a_group_with_no_centring_mean_are_dropped_from_g() -> None:
    # Sync #7: his latest group (WR) has a mean; his older TE rows have none and leave G,
    # but they still count for E and for the 3-game minimum.
    m = 1.0
    means = Centring(means={("WR", "receiving_yards"): m}, label="x")
    rows = [
        ffrow(gid(1), position="TE", rec_yards_gained=90.0, rec_yards_gained_exp=10.0),
        ffrow(gid(2), position="TE", rec_yards_gained=0.0, rec_yards_gained_exp=10.0),
        ffrow(gid(3), position="WR", rec_yards_gained=36.0, rec_yards_gained_exp=30.0),
        ffrow(gid(4), position="WR", rec_yards_gained=26.0, rec_yards_gained_exp=30.0),
    ]
    p = run(ff(rows), stat="receiving_yards", centring_means=means)
    assert p.reason is None and p.n_games == 4 and p.group == "WR"
    assert p.e == pytest.approx(
        wmean({0.0: 30.0, 1.0: 30.0, 2.0: 10.0, 3.0: 10.0}, H_USAGE), abs=1e-12
    )
    kept = {0.0: (26.0 - 30.0) - m, 1.0: (36.0 - 30.0) - m}
    w = {g: 0.5 ** (g / H_EFF) for g in kept}
    v_w = math.fsum(w[g] * kept[g] for g in kept) / math.fsum(w.values())
    n_eff = math.fsum(w.values()) ** 2 / math.fsum(x * x for x in w.values())
    assert p.g_n_eff == pytest.approx(n_eff, abs=1e-12)
    assert p.g == pytest.approx(n_eff * v_w / (n_eff + K), abs=1e-12)
    assert p.mu == pytest.approx(p.e + m + p.g, abs=1e-12)


@pytest.mark.parametrize(
    ("other", "note"),
    [
        ({}, "same team, qualifying"),
        ({"posteam": "TMB"}, "other team"),
        ({"rec_attempt": 0.0}, "not qualifying"),
    ],
)
def test_two_ff_rows_for_one_game_is_duplicate_ff_rows(other: dict[str, Any], note: str) -> None:
    rows = [ffrow(gid(w)) for w in (1, 2, 3, 4)]
    rows.append(ffrow(gid(2), **other))
    p = run(ff(rows))
    assert p.reason is PricerUnpriced.DUPLICATE_FF_ROWS, note
    assert p.mu is None


def test_duplicate_ff_rows_comes_before_too_few_stint_games() -> None:
    rows = [ffrow(gid(4)), ffrow(gid(4))]
    assert run(ff(rows)).reason is PricerUnpriced.DUPLICATE_FF_ROWS


def test_duplicates_outside_the_target_season_or_for_other_players_do_not_count() -> None:
    rows = [ffrow(gid(w)) for w in (2, 3, 4)]
    rows += [ffrow(gid(16, SEASON - 1)), ffrow(gid(16, SEASON - 1))]
    rows += [ffrow(gid(3), player="P2"), ffrow(gid(3), player="P2")]
    assert run(ff(rows)).reason is None


def test_missing_efficiency_half_life_is_no_fitted_params() -> None:
    # Sync #7: G's efficiency half-life must be fitted, else no_fitted_params. Without G there
    # is no mu, so the earlier PRV-03 reasons are checked first and mu_not_positive cannot be.
    no_eff = Prv03Fit(window="test", usage_half_life=H_USAGE, k=FIT.k, efficiency_half_life=None)
    rows = [ffrow(gid(w)) for w in (2, 3, 4)]
    p = run(ff(rows), fit=no_eff)
    assert p.reason is PricerUnpriced.NO_FITTED_PARAMS
    assert p.mu is None and p.g is None
    assert p.e == pytest.approx(3.0, abs=1e-12)
    assert run(ff(rows[:2]), fit=no_eff).reason is PricerUnpriced.TOO_FEW_STINT_GAMES
    none_means = Centring(means={}, label="x")
    assert (
        run(ff(rows), fit=no_eff, centring_means=none_means).reason
        is PricerUnpriced.NO_CENTRING_MEAN
    )


def test_carries_mean_uses_the_same_games_and_usage_weights() -> None:
    rows = [
        ffrow(
            gid(w),
            position="RB",
            rush_attempt=c,
            rush_yards_gained=4 * c,
            rush_yards_gained_exp=4 * c,
        )
        for w, c in ((2, 10.0), (3, 0.0), (4, 20.0))
    ]
    p = run(ff(rows), stat="rushing_yards")
    assert p.carries_mean == pytest.approx(
        wmean({0.0: 20.0, 1.0: 0.0, 2.0: 10.0}, H_USAGE), abs=1e-12
    )


def test_unknown_stat_raises() -> None:
    with pytest.raises(ValueError):
        run(ff([ffrow(gid(w)) for w in (2, 3, 4)]), stat="tds")


# ---- centring ----


def test_centring_uses_target_season_when_three_weeks_are_visible() -> None:
    rows = [
        ffrow(gid(1), player="A", receptions=4.0, receptions_exp=3.0),
        ffrow(gid(2), player="A", receptions=3.0, receptions_exp=3.0),
        ffrow(gid(3), player="B", receptions=1.0, receptions_exp=3.0),
        ffrow(gid(3), player="C", rec_attempt=0.0, receptions=9.0),  # not qualifying
        ffrow(gid(17, SEASON - 1), player="A", receptions=9.0, receptions_exp=0.0),
    ]
    c = centring(ff(rows), games(weeks=(1, 2, 3)), SEASON)
    assert c.means[("WR", "receptions")] == pytest.approx((1.0 + 0.0 - 2.0) / 3, abs=1e-12)
    assert str(SEASON) in c.label


def test_centring_falls_back_to_previous_season_before_three_weeks() -> None:
    rows = [
        ffrow(gid(1), player="A", receptions=4.0, receptions_exp=3.0),
        ffrow(gid(2), player="A", receptions=3.0, receptions_exp=3.0),
        ffrow(gid(16, SEASON - 1), player="A", receptions=9.0, receptions_exp=0.0),
        ffrow(gid(17, SEASON - 1), player="B", receptions=1.0, receptions_exp=0.0),
    ]
    c = centring(ff(rows), games(weeks=(1, 2)), SEASON)
    assert c.means[("WR", "receptions")] == pytest.approx(5.0, abs=1e-12)
    assert str(SEASON - 1) in c.label


# ---- fitted inputs ----


def test_live_fit_reads_v4_live_k_and_usage_half_life() -> None:
    raw = yaml.safe_load((FITTED_ROOT / "v4" / "live.yaml").read_text(encoding="utf-8"))["values"]
    fit = load_prv03_fit(SEASON + 2)
    assert fit.window == "live"
    assert fit.usage_half_life == raw["conventions.g3_usage_half_life_games"]["value"]
    assert fit.efficiency_half_life == raw["conventions.g3_efficiency_half_life_games"]["value"]
    for stat in SERIES_STAT.values():
        assert fit.k[stat] == raw[k_key(stat)]["value"]


def test_walk_forward_season_reads_its_window_file() -> None:
    assert load_prv03_fit(2022).window == "S2022"


def _copy_v4(tmp_path: Path) -> Path:
    root = tmp_path / "params_fitted"
    shutil.copytree(FITTED_ROOT / "v4", root / "v4")
    return root


def test_missing_window_file_stops(tmp_path: Path) -> None:
    root = _copy_v4(tmp_path)
    (root / "v4" / "S2023.yaml").unlink()
    with pytest.raises(PricerStop):
        load_prv03_fit(2023, root=root)


@pytest.mark.parametrize(
    "key", ["conventions.g3_usage_half_life_games", "fit:k/PLY-35/rushing_yards"]
)
def test_missing_fitted_value_stops_never_falls_back(tmp_path: Path, key: str) -> None:
    root = _copy_v4(tmp_path)
    path = root / "v4" / "S2023.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    del data["values"][key]
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(PricerStop):
        load_prv03_fit(2023, root=root)


def test_missing_efficiency_half_life_loads_as_none_not_a_stop(tmp_path: Path) -> None:
    root = _copy_v4(tmp_path)
    path = root / "v4" / "S2023.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    del data["values"]["conventions.g3_efficiency_half_life_games"]
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    fit = load_prv03_fit(2023, root=root)
    assert fit.efficiency_half_life is None
    assert fit.usage_half_life > 0


def test_season_before_the_walk_forward_stops() -> None:
    with pytest.raises(PricerStop):
        load_prv03_fit(2019)
