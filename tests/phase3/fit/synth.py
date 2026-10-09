"""Synthetic data with planted values for the Phase 3e fitters (BUILD_PLAN 3e: "split-half k
recovers a planted stabilization point on synthetic data"). Nothing here is real-world data:
every number is a test setting chosen here, and every draw comes from a seeded Generator."""

from __future__ import annotations

import hashlib

import numpy as np
import polars as pl


def rng(key: str) -> np.random.Generator:
    return np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))


def binomial_units(
    *, k: float, mu: float, entities: int, games: int, per_game: int, key: str
) -> pl.DataFrame:
    """G1 planted exactly: each entity's true rate p ~ Beta(mu k, (1 - mu) k), so the posterior
    mean after n plays is (n * observed + k * mu) / (n + k). Units: one play, x in {0, 1}."""
    g = rng(key)
    p = g.beta(mu * k, (1 - mu) * k, size=entities)
    n = games * per_game
    x = (g.random((entities, n)) < p[:, None]).astype(np.float64)
    return pl.DataFrame(
        {
            "entity": np.repeat([f"e{i:05d}" for i in range(entities)], n),
            "game": np.tile(np.repeat([f"g{j:03d}" for j in range(games)], per_game), entities),
            "x": x.ravel(),
        }
    )


def gaussian_units(
    *, tau: float, sigma: float, entities: int, games: int, per_game: int, key: str
) -> pl.DataFrame:
    """Entity mean ~ N(0, tau^2), plays ~ N(mean, sigma^2): k = sigma^2 / tau^2."""
    g = rng(key)
    mean = g.normal(0.0, tau, size=entities)
    n = games * per_game
    x = mean[:, None] + g.normal(0.0, sigma, size=(entities, n))
    return pl.DataFrame(
        {
            "entity": np.repeat([f"e{i:05d}" for i in range(entities)], n),
            "game": np.tile(np.repeat([f"g{j:03d}" for j in range(games)], per_game), entities),
            "x": x.ravel(),
        }
    )


def logistic_rows(
    *, coef: np.ndarray, n: int, key: str, offset_sd: float = 0.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """y ~ Bernoulli(sigmoid(X coef + offset)); X = [1, four features on mixed scales]."""
    g = rng(key)
    feats = np.column_stack(
        [
            g.integers(1, 21, n).astype(float),  # like yards to go
            g.integers(1, 100, n).astype(float),  # like yardline
            g.normal(0.0, 10.0, n),  # like score differential
            g.uniform(0.0, 3600.0, n),  # like seconds remaining
        ]
    )
    X = np.column_stack([np.ones(n), feats])
    off = g.normal(0.0, offset_sd, n) if offset_sd else np.zeros(n)
    p = 1.0 / (1.0 + np.exp(-(X @ coef + off)))
    y = (g.random(n) < p).astype(float)
    return X, y, off


def league_plays(
    *,
    teams: int,
    weeks: int,
    plays_per_game: int,
    tau: float,
    sigma: float,
    home: float,
    key: str,
) -> tuple[pl.DataFrame, dict[str, float], dict[str, float]]:
    """G6: one season of plays with planted offense / defense effects ~ N(0, tau^2), a home
    term and play noise N(0, sigma^2). Each week every team plays once (random pairings)."""
    g = rng(key)
    names = [f"T{i:02d}" for i in range(teams)]
    off = dict(zip(names, g.normal(0.0, tau, teams), strict=True))
    de = dict(zip(names, g.normal(0.0, tau, teams), strict=True))
    rows: list[tuple[str, int, str, str, str, int, float]] = []
    for w in range(1, weeks + 1):
        order = g.permutation(teams)
        for a, b in zip(order[::2], order[1::2], strict=True):
            hm, aw = names[a], names[b]
            gid = f"S_{w:02d}_{aw}_{hm}"
            for pos, dfn, is_home in ((hm, aw, 1), (aw, hm, 0)):
                mu = off[pos] + de[dfn] + home * is_home
                for e in g.normal(mu, sigma, plays_per_game):
                    rows.append((gid, w, pos, dfn, hm, is_home, float(e)))
    df = pl.DataFrame(
        rows,
        schema={
            "game_id": pl.Utf8,
            "week": pl.Int64,
            "posteam": pl.Utf8,
            "defteam": pl.Utf8,
            "home_team": pl.Utf8,
            "is_home": pl.Int64,
            "epa": pl.Float64,
        },
        orient="row",
    )
    return df.with_columns(pl.lit(2000).alias("season")), off, de


def local_level_units(
    *, alpha: float, entities: int, games: int, plays: int, key: str
) -> pl.DataFrame:
    """G3: a random-walk true level (step sd sqrt(q)) observed with per-game noise sd sqrt(r),
    q / r = alpha^2 / (1 - alpha): the steady-state Kalman gain is alpha, so the best
    exponentially weighted mean decays by (1 - alpha) per game."""
    g = rng(key)
    r = 1.0
    q = alpha * alpha / (1 - alpha) * r
    level = np.cumsum(g.normal(0.0, np.sqrt(q), (entities, games)), axis=1)
    # Per-game mean of `plays` units with total game-mean noise variance r.
    unit_sd = np.sqrt(r * plays)
    x = level[:, :, None] + g.normal(0.0, unit_sd, (entities, games, plays))
    return pl.DataFrame(
        {
            "entity": np.repeat([f"e{i:05d}" for i in range(entities)], games * plays),
            "gi": np.tile(np.repeat(np.arange(games), plays), entities),
            "x": x.ravel(),
        }
    )
