"""MTC-05 / ENV-03 / ENV-04 weather coefficients, fitted per window (spec synced 2026-10-23).

One play-level logistic regression per outcome with every applicable factor in it and season
intercepts (ruling B4): deep-attempt share (`air_yards` >= 20) takes all five game-window
factors; completion takes precipitation, snowfall, gusts and temperature, and field-goal make
gusts, temperature and snowfall plus the caller's extra terms (distance, ENV-02 altitude):
wind speed is dropped from those two (ruling 2026-10-24). Standard errors are clustered by team-game
(ruling B8). An effect whose 95% interval includes 0 is "no detectable signal" and contributes
zero (BT-02). If wind and gusts both come out no-signal jointly while either is significant
fitted alone, the fit stops (WindGustsMasked) and the question goes to Rhys (ruling B4)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations

import numpy as np
import polars as pl

from ge.config import load_params
from ge.fit.clustered import logit_clustered, no_signal, season_dummies

WEATHER_FACTORS = ("precipitation", "snowfall", "wind_speed", "wind_gusts", "temperature")
# Ruling 2026-10-24 (after the B4 stop: wind and gusts, correlation about 0.89, hid each other
# in every window): completion and field-goal make keep gusts and drop wind speed; wind speed is
# not a fitted effect there and does not count as no-signal for the weather-risk flag.
OUTCOME_FACTORS: dict[str, tuple[str, ...]] = {
    "completion": ("precipitation", "snowfall", "wind_gusts", "temperature"),
    "deep_attempt": WEATHER_FACTORS,
    "fg_make": ("snowfall", "wind_gusts", "temperature"),
}
PASSING_OUTCOMES = ("completion", "deep_attempt")


class WindGustsMasked(RuntimeError):
    """Ruling B4: the joint fit hid a wind or gust effect that is significant alone."""


@dataclass(frozen=True)
class EffectFit:
    factor: str
    outcome: str
    coef: float
    se: float  # clustered by team-game
    se_classical: float
    no_signal: bool
    n: int
    clusters: int

    @property
    def applied(self) -> float:
        """The value the simulation uses: zero when no-signal (BT-02)."""
        return 0.0 if self.no_signal else self.coef


def _confidence() -> float:
    return float(load_params().fitting.bt_02_no_signal_confidence.value)


def _fit(
    plays: pl.DataFrame, outcome: str, factors: Sequence[str], extra: Sequence[str]
) -> dict[str, EffectFit]:
    cols = ["season", "team_game", "y", *factors, *extra]
    d = plays.select(cols).drop_nulls()
    dummies, _ = season_dummies(d["season"].to_numpy())
    X = np.column_stack(
        [dummies, *(d[c].to_numpy().astype(np.float64) for c in (*extra, *factors))]
    )
    fit = logit_clustered(X, d["y"].to_numpy().astype(np.float64), d["team_game"].to_numpy())
    off = dummies.shape[1]
    conf = _confidence()
    return {
        f: EffectFit(
            factor=f,
            outcome=outcome,
            coef=float(fit.coef[off + i]),
            se=float(fit.se[off + i]),
            se_classical=float(fit.se_classical[off + i]),
            no_signal=no_signal(float(fit.coef[off + i]), float(fit.se[off + i]), conf),
            n=fit.n,
            clusters=fit.clusters,
        )
        for i, f in enumerate((*extra, *factors))
    }


def fit_weather_effects(
    plays: pl.DataFrame, outcome: str, extra: Sequence[str] = ()
) -> dict[str, EffectFit]:
    """MTC-05: one outcome's joint fit. `plays` has season, team_game, y, the outcome's factors
    and any `extra` covariates; the result holds every factor and every extra term."""
    if outcome not in OUTCOME_FACTORS:
        raise ValueError(f"MTC-05: unknown weather outcome {outcome!r}")
    factors = OUTCOME_FACTORS[outcome]
    joint = _fit(plays, outcome, factors, extra)
    wind, gust = joint.get("wind_speed"), joint.get("wind_gusts")
    if wind is not None and gust is not None and wind.no_signal and gust.no_signal:
        alone = {f: _fit(plays, outcome, (f,), extra)[f] for f in ("wind_speed", "wind_gusts")}
        hidden = [a for a in alone.values() if not a.no_signal]
        if hidden:
            detail = "; ".join(f"{a.factor} alone {a.coef:.4g} (SE {a.se:.3g})" for a in hidden)
            raise WindGustsMasked(
                f"MTC-05 ({outcome}): wind and gusts are both no-signal jointly "
                f"(wind {wind.coef:.4g} SE {wind.se:.3g}, gusts {gust.coef:.4g} SE "
                f"{gust.se:.3g}) but significant alone: {detail}. Stop and ask (ruling B4)."
            )
    return joint


def factor_correlations(plays: pl.DataFrame) -> dict[tuple[str, str], float]:
    """Ruling B4: Pearson correlation of every pair of weather factors, over plays."""
    d = plays.select(WEATHER_FACTORS).drop_nulls()
    return {
        (a, b): float(np.corrcoef(d[a].to_numpy(), d[b].to_numpy())[0, 1])
        for a, b in combinations(WEATHER_FACTORS, 2)
    }
