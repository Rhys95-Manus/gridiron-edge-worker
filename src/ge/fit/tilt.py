"""PRJ-02 rating tilt: the five per-window slopes.

Each slope is the play's outcome regressed on the offense's realized EPA per play on that side
in that game, centred on the season's league mean, with season intercepts: logistic for
completion, interception and fumble lost; least squares for yards after catch and yards per
carry. Standard errors are clustered by team-game (ruling B8, 2026-10-23). With season
intercepts in the model, the centring constant per season does not change the slope."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from ge.fit.clustered import logit_clustered, ols_clustered, season_dummies

TILT_COMPONENTS: tuple[tuple[str, str], ...] = (
    ("completion", "logistic"),
    ("yac", "least_squares"),
    ("interception", "logistic"),
    ("yards_per_carry", "least_squares"),
    ("fumble_lost", "logistic"),
)
# Which side's net rating each slope multiplies.
TILT_SIDE = {
    "completion": "pass",
    "yac": "pass",
    "interception": "pass",
    "yards_per_carry": "run",
    "fumble_lost": "run",
}


@dataclass(frozen=True)
class TiltFit:
    component: str
    slope: float
    se: float  # clustered by team-game
    se_classical: float
    n: int
    clusters: int
    events: int | None


def fit_tilt_slope(plays: pl.DataFrame, component: str) -> TiltFit:
    """PRJ-02 rating tilt: one component's slope from plays with columns season, team_game,
    x (the offense's realized same-side EPA/play in that game) and y (the outcome)."""
    kinds = dict(TILT_COMPONENTS)
    if component not in kinds:
        raise ValueError(f"PRJ-02: unknown tilt component {component!r}")
    d = plays.drop_nulls(["season", "team_game", "x", "y"])
    dummies, _ = season_dummies(d["season"].to_numpy())
    X = np.column_stack([dummies, d["x"].to_numpy().astype(np.float64)])
    y = d["y"].to_numpy().astype(np.float64)
    fit = (logit_clustered if kinds[component] == "logistic" else ols_clustered)(
        X, y, d["team_game"].to_numpy()
    )
    return TiltFit(
        component=component,
        slope=float(fit.coef[-1]),
        se=float(fit.se[-1]),
        se_classical=float(fit.se_classical[-1]),
        n=fit.n,
        clusters=fit.clusters,
        events=fit.events,
    )
