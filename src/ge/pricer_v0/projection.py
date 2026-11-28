"""PRV-03 projection mean: μ = E + m + G for one player, stat and game.

PRV-03: "μ = E + m + G. E is the G3 recency-weighted mean of the player's ff_opportunity
expected value for the stat over his prior games in his current team stint. m is the PLY-35
centring mean for his position group. G is his PLY-35 shrunk centred gap. The usage half-life is
G3's fitted usage half-life from the same params_fitted window file as k. A player needs at
least 3 prior games in the stint to be priced."

Spec sync #6 (2026-11-27) settles: the stint is PLY-35's (target season, the nflverse team PRV-02
mapped him to, every such game counts); a game counts when it qualifies under the PLY-35 rules
and its ff_opportunity row is visible at as_of; a null expected value counts as 0; g counts the
stint team's visible games (g = 0 for the most recent); E = Σ w·x / Σ w with the usage half-life
and is not shrunk; the position group is the PLY-35 group of the position on his most recent
qualifying row; k and the usage half-life come from config/params_fitted/v4/<window>.yaml and
must be fitted (no fallback); reason codes too_few_stint_games, no_centring_mean,
mu_not_positive, in that order.

G is PLY-35's shrunk centred gap: G1 shrink toward 0 of the G3-weighted mean centred gap per
game with PLY-35's efficiency half-life and n_eff. Spec sync #7 (2026-11-27): "G's weights use
conventions.g3_efficiency_half_life_games from the same params_fitted/v4 window file; it must be
fitted, else no_fitted_params. Stint rows from a position group with no centring mean are
dropped from G. Two or more ff_opportunity rows for the same player and game leave the player
unpriced as duplicate_ff_rows." Spec sync #8 (2026-11-27): "The duplicate_ff_rows check reads
all of the player's ff_opportunity rows visible at as_of in the target season before the target
game, for any team and whether or not the game qualifies. A missing efficiency half-life is
checked after no_centring_mean; mu_not_positive is not evaluated for that player."

Inputs are DataFrames the caller reads from the point-in-time snapshot: `ff` = ff_opportunity
rows visible at as_of (any seasons), `games` = the target season's visible team games with the
G3 games-ago index (MetricContext.games: team, game_id, week, g).

Data: nflverse; charting: FTN Data via nflverse; expected points: ffopportunity (ffverse) via
nflverse; data license not stated by the source.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from ge.config import FITTED_ROOT, _read_fitted, load_params, window_for
from ge.metrics.expected import STATS, centring_means, position_group, qualifying, raw_gaps
from ge.pricer_v0.reasons import PricerUnpriced

SPEC_ID = "PRV-03"
# PRV-03 (sync #6): "Live pricer v0 reads k and the usage half-life from
# config/params_fitted/v4/live.yaml. Walk-forward season S reads config/params_fitted/v4/S<S>.yaml."
FIT_VERSION = "v4"
USAGE_HALF_LIFE_KEY = "conventions.g3_usage_half_life_games"
EFFICIENCY_HALF_LIFE_KEY = "conventions.g3_efficiency_half_life_games"
# Kalshi series (PRV-01) -> PLY-35 stat name (ge.metrics.expected.STATS).
SERIES_STAT = {
    "KXNFLREC": "receptions",
    "KXNFLRECYDS": "receiving_yards",
    "KXNFLRSHYDS": "rushing_yards",
}
PRV_STATS = ("receptions", "receiving_yards", "rushing_yards")


def k_key(stat: str) -> str:
    """PRV-03: the fit-only key of PLY-35's fitted k for a stat."""
    return f"fit:k/PLY-35/{stat}"


class PricerStop(RuntimeError):
    """PRV-03: a required fitted value is missing; the pricer stops (never falls back)."""


@dataclass(frozen=True)
class Prv03Fit:
    """PRV-03's fitted inputs from one v4 window file. efficiency_half_life is None when the
    file has no fitted value (sync #7: no_fitted_params, not a stop)."""

    window: str
    usage_half_life: float
    k: Mapping[str, float]
    efficiency_half_life: float | None


def load_prv03_fit(season: int, root: Path = FITTED_ROOT) -> Prv03Fit:
    """PRV-03: k per stat, the usage half-life and G's efficiency half-life from
    params_fitted/v4/<window>.yaml, where the window is BT-07a's for `season` (S<S> walk-forward,
    live after the holdout). A missing file, k or usage half-life raises PricerStop; a missing
    efficiency half-life loads as None (sync #7: the player is unpriced as no_fitted_params)."""
    window = window_for(season)
    if window is None:
        raise PricerStop(f"{SPEC_ID}: season {season} has no params_fitted window")
    path = root / FIT_VERSION / f"{window}.yaml"
    if not path.exists():
        raise PricerStop(f"{SPEC_ID}: {path} is missing")
    st = path.stat()
    fitted = _read_fitted(path, st.st_mtime_ns, st.st_size)
    if fitted.fit_version != FIT_VERSION:
        raise PricerStop(f"{SPEC_ID}: {path} is fit version {fitted.fit_version!r}")

    def need(key: str) -> float:
        if key not in fitted.values:
            raise PricerStop(f"{SPEC_ID}: {key} is not fitted in {FIT_VERSION}/{window}")
        return float(fitted.values[key].value)

    eff = fitted.values.get(EFFICIENCY_HALF_LIFE_KEY)
    return Prv03Fit(
        window=window,
        usage_half_life=need(USAGE_HALF_LIFE_KEY),
        k={stat: need(k_key(stat)) for stat in PRV_STATS},
        efficiency_half_life=None if eff is None else float(eff.value),
    )


@dataclass(frozen=True)
class Centring:
    """PLY-35 centring means (group, stat) -> mean raw gap, and the label saying which season
    they come from."""

    means: Mapping[tuple[str, str], float]
    label: str


def centring(ff: pl.DataFrame, games: pl.DataFrame, season: int) -> Centring:
    """PLY-35 rules: the unweighted mean raw gap per (group, stat) over the target season's
    qualifying visible player-games; until the target season has visible games in 3 distinct
    weeks, the previous season's full-season mean, labelled. Same rule and helpers as
    ge.metrics.expected.ply_35."""
    cur = _season_rows(ff, season)
    weeks = games.filter(pl.col("game_id").is_in(cur["game_id"].unique().to_list()))[
        "week"
    ].n_unique()
    min_weeks = load_params().player.ply_35_centring_min_weeks.value
    if weeks < min_weeks:
        prev, _ = qualifying(_season_rows(ff, season - 1))
        means = centring_means(raw_gaps(prev))
        label = (
            f"centring: season {season - 1} full-season mean (season {season} has games "
            f"visible in {weeks} week(s), fewer than {int(min_weeks)})"
        )
    else:
        rows, _ = qualifying(cur)
        gaps = raw_gaps(rows).join(
            games.select(pl.col("team").alias("posteam"), "game_id"),
            on=["posteam", "game_id"],
            how="inner",
        )
        means = centring_means(gaps)
        label = f"centring: season {season} games visible at as_of"
    return Centring(means={k: m for k, (m, _) in means.items()}, label=label)


def _season_rows(ff: pl.DataFrame, season: int) -> pl.DataFrame:
    return ff.filter(pl.col("game_id").str.starts_with(f"{season}_"))


def _total(row: Mapping[str, Any], cols: tuple[str, ...]) -> float:
    """A null value counts as 0 (PRV-03, sync #6; PLY-35's raw_gaps does the same)."""
    return math.fsum(float(row[c] or 0.0) for c in cols)


@dataclass(frozen=True)
class Projection:
    """PRV-03 result. `reason` is None when priced; then mu, e, m and g are set. `group` is
    set whenever the player has a qualifying game. carries_mean is the G3 usage-weighted mean
    rush_attempt over the same games (PRV-06 compound model)."""

    gsis_id: str
    team: str
    stat: str
    n_games: int
    group: str | None
    e: float | None
    m: float | None
    g: float | None
    g_n_eff: float | None
    mu: float | None
    carries_mean: float | None
    centring_label: str
    reason: PricerUnpriced | None


def project(
    ff: pl.DataFrame,
    games: pl.DataFrame,
    *,
    target_game_id: str,
    gsis_id: str,
    team: str,
    stat: str,
    centring_means: Centring,
    fit: Prv03Fit,
) -> Projection:
    """PRV-03 for one player and stat at as_of. `team` is the nflverse team PRV-02 mapped him
    to; `games` holds that season's visible team games (team, game_id, week, g)."""
    if stat not in PRV_STATS:
        raise ValueError(f"{SPEC_ID}: stat {stat!r} is not one of {PRV_STATS}")
    actual_cols, expected_cols = STATS[stat]
    season = int(target_game_id.split("_", 1)[0])
    season_rows = _season_rows(ff, season).filter(
        (pl.col("player_id") == gsis_id) & (pl.col("game_id") != target_game_id)
    )
    duplicated = season_rows["game_id"].n_unique() != season_rows.height
    mine = season_rows.filter(pl.col("posteam") == team)
    rows, _ = qualifying(mine)
    team_games = games.filter(pl.col("team") == team).select("game_id", "g")
    rows = (
        rows.join(team_games, on="game_id", how="inner")
        .with_columns(position_group(pl.col("position")))
        .sort("g", "game_id")
    )
    n = rows.height
    group = str(rows["group"][0]) if n else None

    def result(reason: PricerUnpriced | None, **values: float | None) -> Projection:
        base: dict[str, float | None] = dict.fromkeys(
            ("e", "m", "g", "g_n_eff", "mu", "carries_mean")
        )
        base.update(values)
        return Projection(
            gsis_id=gsis_id,
            team=team,
            stat=stat,
            n_games=n,
            group=group,
            centring_label=centring_means.label,
            reason=reason,
            **base,
        )

    if duplicated:
        return result(PricerUnpriced.DUPLICATE_FF_ROWS)
    if n < load_params().pricer_v0.prv_03_min_prior_games_in_stint.value:
        return result(PricerUnpriced.TOO_FEW_STINT_GAMES)

    records = list(rows.iter_rows(named=True))
    w_use = [0.5 ** (float(r["g"]) / fit.usage_half_life) for r in records]
    sum_w = math.fsum(w_use)
    e = math.fsum(w * _total(r, expected_cols) for w, r in zip(w_use, records, strict=True)) / sum_w
    carries = (
        math.fsum(w * _total(r, ("rush_attempt",)) for w, r in zip(w_use, records, strict=True))
        / sum_w
    )
    assert group is not None
    if (group, stat) not in centring_means.means:
        return result(PricerUnpriced.NO_CENTRING_MEAN, e=e, carries_mean=carries)
    m = centring_means.means[(group, stat)]
    if fit.efficiency_half_life is None:
        return result(PricerUnpriced.NO_FITTED_PARAMS, e=e, m=m, carries_mean=carries)
    efficiency_half_life = fit.efficiency_half_life

    # G: PLY-35's centred gap (each game centred on its own row's group mean), G3-weighted with
    # the efficiency half-life, G1-shrunk toward 0 with n_eff and the fitted k. Rows whose group
    # has no centring mean are dropped from G (sync #7); the most recent row's group has one, so
    # at least one row is left.
    kept = [r for r in records if (str(r["group"]), stat) in centring_means.means]
    centred = [
        _total(r, actual_cols)
        - _total(r, expected_cols)
        - centring_means.means[(str(r["group"]), stat)]
        for r in kept
    ]
    w_eff = [0.5 ** (float(r["g"]) / efficiency_half_life) for r in kept]
    sum_e = math.fsum(w_eff)
    value_w = math.fsum(w * c for w, c in zip(w_eff, centred, strict=True)) / sum_e
    n_eff = sum_e**2 / math.fsum(w * w for w in w_eff)
    k = fit.k[stat]
    g = n_eff * value_w / (n_eff + k)
    mu = e + m + g
    reason = PricerUnpriced.MU_NOT_POSITIVE if mu <= 0 else None
    return result(reason, e=e, m=m, g=g, g_n_eff=n_eff, mu=mu, carries_mean=carries)
