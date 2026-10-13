"""Synthetic seasons with planted PRJ-01a effects (BUILD_PLAN Phase 4: "ratings recover
planted effects on synthetic data").

Nothing here is real-world data. Every number is a test setting in Settings, and every draw
comes from a Generator seeded by a string key. Planted, per season:

- team pass/run offense and defense effects ~ N(0, tau^2), AR(1) across seasons, constant
  within a season;
- pass and run intercepts (season-specific);
- league-wide home, rest, travel and time-zone coefficients on the offense-minus-defense
  terms (decision log 2026-10-12);
- a pass rate per team, and points per drive linear in realized offensive EPA/play (slope c).

Teams sit on a synthetic latitude/longitude grid; each site's time-zone offset is a step
function of longitude. Every team plays every week (no byes), so a team's travel origin is
its previous game's site; week 1 starts from home."""

from __future__ import annotations

import datetime as dt
import hashlib
import math
from dataclasses import dataclass, field

import numpy as np
import polars as pl

from ge.models.ratings import RATING_TYPES


def rng(key: str) -> np.random.Generator:
    return np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))


@dataclass(frozen=True)
class Settings:
    teams: int = 32
    seasons: int = 6
    weeks: int = 17
    plays_per_offense: int = 60
    tau: float = 0.08
    drift: float = 0.6
    int_pass: float = 0.05
    int_run: float = -0.08
    int_season_sd: float = 0.01
    beta: dict[str, float] = field(
        default_factory=lambda: {"home": 0.05, "rest": 0.004, "travel": -2.0e-5, "tz": -0.015}
    )
    sigma: float = 0.4
    pass_rate_low: float = 0.50
    pass_rate_high: float = 0.65
    neutral_share: float = 0.03
    rest_days: tuple[int, ...] = (4, 6, 7, 7, 7, 7, 8, 10, 13)
    lat_range: tuple[float, float] = (26.0, 47.0)
    lon_range: tuple[float, float] = (-122.0, -71.0)
    tz_steps: tuple[tuple[float, float], ...] = ((-112.0, -8.0), (-97.0, -7.0), (-85.0, -6.0))
    tz_east: float = -5.0
    drives_per_game: int = 11
    ppd: float = 2.0
    c: float = 6.0
    ppd_noise: float = 0.4
    radius_km: float = 6371.0
    first_season: int = 3001  # synthetic labels, far from any real season


@dataclass(frozen=True)
class Synth:
    settings: Settings
    teams: list[str]
    games: pl.DataFrame  # season, week, game_id, home_team, away_team, neutral, kickoff_utc
    features: pl.DataFrame  # game_id, team, home, rest_days, travel_km, tz_change_hours
    terms: pl.DataFrame  # game_id, posteam, defteam, home, d_rest, d_travel, d_tz
    plays: pl.DataFrame  # season, week, game_id, kickoff_utc, posteam, defteam, is_pass, epa, terms
    truth: dict[tuple[int, str, str], float]  # (season, team, type) -> planted effect
    intercepts: dict[tuple[int, str], float]  # (season, "pass" | "run") -> planted intercept
    pass_rate: dict[str, float]
    team_games: pl.DataFrame  # season, game_id, team, plays, epa_sum, points, drives


def _tz(s: Settings, lon: float) -> float:
    for edge, off in s.tz_steps:
        if lon < edge:
            return off
    return s.tz_east


def _km(s: Settings, a: tuple[float, float], b: tuple[float, float]) -> float:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * s.radius_km * math.asin(math.sqrt(min(1.0, h)))


def make(key: str, s: Settings | None = None) -> Synth:
    s = s or Settings()
    g = rng(key)
    teams = [f"T{i:02d}" for i in range(s.teams)]
    home_site = {t: (float(g.uniform(*s.lat_range)), float(g.uniform(*s.lon_range))) for t in teams}
    pass_rate = {t: float(g.uniform(s.pass_rate_low, s.pass_rate_high)) for t in teams}

    truth: dict[tuple[int, str, str], float] = {}
    intercepts: dict[tuple[int, str], float] = {}
    prev: dict[tuple[str, str], float] = {}
    games_rows, feat_rows, play_frames, tg_rows = [], [], [], []
    for si in range(s.seasons):
        season = s.first_season + si
        for t in teams:
            for k in RATING_TYPES:
                e = float(g.normal(0.0, s.tau))
                x = e if si == 0 else s.drift * prev[(t, k)] + math.sqrt(1 - s.drift**2) * e
                prev[(t, k)] = x
                truth[(season, t, k)] = x
        intercepts[(season, "pass")] = s.int_pass + float(g.normal(0.0, s.int_season_sd))
        intercepts[(season, "run")] = s.int_run + float(g.normal(0.0, s.int_season_sd))
        last_site = dict(home_site)
        start = dt.datetime(2100 + si, 9, 1, 17, 0, tzinfo=dt.UTC)
        for week in range(1, s.weeks + 1):
            order = [teams[i] for i in g.permutation(s.teams)]
            for gi in range(s.teams // 2):
                a, b = order[2 * gi], order[2 * gi + 1]
                home, away = (a, b) if g.random() < 0.5 else (b, a)
                neutral = bool(g.random() < s.neutral_share)
                site = (
                    (float(g.uniform(*s.lat_range)), float(g.uniform(*s.lon_range)))
                    if neutral
                    else home_site[home]
                )
                gid = f"{season}_{week:02d}_{away}_{home}"
                kick = start + dt.timedelta(days=7 * (week - 1), minutes=gi)
                games_rows.append(
                    {
                        "season": season,
                        "week": week,
                        "game_id": gid,
                        "home_team": home,
                        "away_team": away,
                        "neutral": neutral,
                        "kickoff_utc": kick,
                    }
                )
                feats = {}
                for team, is_home in ((home, True), (away, False)):
                    origin = last_site[team]
                    feats[team] = {
                        "game_id": gid,
                        "team": team,
                        "home": 0.0 if neutral else (1.0 if is_home else -1.0),
                        "rest_days": float(s.rest_days[int(g.integers(len(s.rest_days)))]),
                        "travel_km": _km(s, origin, site),
                        "tz_change_hours": _tz(s, site[1]) - _tz(s, origin[1]),
                    }
                    last_site[team] = site
                feat_rows += list(feats.values())
                for off, de in ((home, away), (away, home)):
                    fo, fd = feats[off], feats[de]
                    terms = {
                        "home": fo["home"],
                        "d_rest": fo["rest_days"] - fd["rest_days"],
                        "d_travel": fo["travel_km"] - fd["travel_km"],
                        "d_tz": abs(fo["tz_change_hours"]) - abs(fd["tz_change_hours"]),
                    }
                    shift = (
                        s.beta["home"] * terms["home"]
                        + s.beta["rest"] * terms["d_rest"]
                        + s.beta["travel"] * terms["d_travel"]
                        + s.beta["tz"] * terms["d_tz"]
                    )
                    n = s.plays_per_offense
                    is_pass = g.random(n) < pass_rate[off]
                    mean = np.where(
                        is_pass,
                        intercepts[(season, "pass")]
                        + truth[(season, off, "off_pass")]
                        + truth[(season, de, "def_pass")],
                        intercepts[(season, "run")]
                        + truth[(season, off, "off_run")]
                        + truth[(season, de, "def_run")],
                    )
                    epa = mean + shift + g.normal(0.0, s.sigma, n)
                    play_frames.append(
                        pl.DataFrame(
                            {
                                "season": [season] * n,
                                "week": [week] * n,
                                "game_id": [gid] * n,
                                "kickoff_utc": [kick] * n,
                                "posteam": [off] * n,
                                "defteam": [de] * n,
                                "is_pass": is_pass.tolist(),
                                "epa": epa.tolist(),
                                **{c: [float(v)] * n for c, v in terms.items()},
                            }
                        )
                    )
                    x = float(epa.mean())
                    tg_rows.append(
                        {
                            "season": season,
                            "game_id": gid,
                            "team": off,
                            "plays": n,
                            "epa_sum": float(epa.sum()),
                            "x": x,
                        }
                    )
    tg = pl.DataFrame(tg_rows)
    league_epa = float(tg["epa_sum"].sum() / tg["plays"].sum())
    noise = g.normal(0.0, s.ppd_noise, tg.height)
    ppd = s.ppd + s.c * (tg["x"].to_numpy() - league_epa) + noise
    team_games = tg.with_columns(
        pl.Series("points", ppd * s.drives_per_game),
        pl.lit(s.drives_per_game).alias("drives"),
    ).drop("x")
    features = pl.DataFrame(feat_rows)
    games = pl.DataFrame(games_rows)
    plays = pl.concat(play_frames)
    terms = plays.select(
        "game_id", "posteam", "defteam", "home", "d_rest", "d_travel", "d_tz"
    ).unique(maintain_order=True)
    return Synth(s, teams, games, features, terms, plays, truth, intercepts, pass_rate, team_games)


def with_offset(plays: pl.DataFrame, coefs: dict[str, float]) -> pl.DataFrame:
    """The COA-07 offset column from the given coefficients."""
    return plays.with_columns(
        (
            coefs["home"] * pl.col("home")
            + coefs["rest"] * pl.col("d_rest")
            + coefs["travel"] * pl.col("d_travel")
            + coefs["tz"] * pl.col("d_tz")
        ).alias("offset")
    )


def with_games_ago(plays: pl.DataFrame) -> pl.DataFrame:
    """G3: the offense's games ago within its season (g = 0 for its latest game here)."""
    order = (
        plays.select("season", "posteam", "game_id", "kickoff_utc")
        .unique()
        .sort(["season", "posteam", "kickoff_utc"], descending=[False, False, True])
        .with_columns(
            pl.int_range(pl.len()).over("season", "posteam").cast(pl.Float64).alias("g_off")
        )
        .select("season", "posteam", "game_id", "g_off")
    )
    return plays.join(order, on=["season", "posteam", "game_id"], how="left")


def season_frame(s: Synth, season: int, *, through_week: int | None = None) -> pl.DataFrame:
    """One season's plays as fit_ratings input, offsets at the planted coefficients."""
    p = s.plays.filter(pl.col("season") == season)
    if through_week is not None:
        p = p.filter(pl.col("week") <= through_week)
    return with_games_ago(with_offset(p, s.settings.beta))
