"""PRJ-01a / COA-07 per-window fit: the league-wide constants every rating in a window uses.

For one walk-forward window (training seasons 2016 to S - 1; or the live window), read only
through the Phase 3e Reader (BT-07a / BT-07b guard):

- COA-07 coefficients: one pooled ridge over every qualifying play of the training seasons,
  every play weighted equally, with season-specific pass and run intercepts and the four
  COA-07 terms unpenalized and team-season pass/run offense and defense effects penalized
  with the window's G6 penalty.
- League EPA/play, points per drive and drives per team-game over the training seasons.
- c: least squares through the origin at the team-game level on realized values, (points
  per drive - league) against (offensive EPA/play - league); not on rating predictions.

Written to config/ratings_fitted/<version>/<window>.yaml (decision log 2026-10-12).

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from ge.ingest.raw import DATA_ROOT
from ge.models.ratings import (
    C_KEY,
    COA07_KEYS,
    COA07_TERMS,
    LEAGUE_KEYS,
    RATING_TYPES,
    RATINGS_FITTED_ROOT,
    SE_SUFFIX,
    TERM_COLUMNS,
    GroupRow,
    align_to_pbp,
    coa07_features,
    grouped_ridge,
    offense_terms,
    pbp_sides,
)
from ge.store.holdout import Window


class MissingTrainingData(ValueError):
    """A window's training season has no play-by-play or schedules in the store."""


@dataclass(frozen=True)
class Coa07Fit:
    """COA-07: league-wide coefficients and standard errors from the pooled window fit."""

    coefs: Mapping[str, float]
    se: Mapping[str, float]
    intercepts: Mapping[tuple[int, str], float]
    sigma2: float
    n_plays: int


@dataclass(frozen=True)
class CFit:
    """PRJ-01a: the points-per-drive slope and the league constants it is centred on."""

    c: float
    c_se: float
    league_epa: float
    league_ppd: float
    league_drives: float
    n_team_games: int


@dataclass(frozen=True)
class WindowFit:
    window: str
    seasons: tuple[int, ...]
    coa07: Coa07Fit
    c: CFit
    based_on_fit: str
    data_as_of: dt.datetime
    data_digest: str


def pooled_coa07(plays: pl.DataFrame, penalty: float) -> Coa07Fit:
    """COA-07: the pooled ridge. `plays` columns: season, game_id, posteam, defteam, is_pass,
    epa and the TERM_COLUMNS of ge.models.ratings. Every play weighs 1; season pass and run
    intercepts and the four COA-07 coefficients are unpenalized, team-season pass/run offense
    and defense effects are penalized (decision log 2026-10-12)."""
    seasons = sorted(set(plays["season"].to_list()))
    names: list[object] = [(s, kind) for s in seasons for kind in ("pass", "run")]
    names += [("coa07", t) for t in COA07_TERMS]
    team_seasons = sorted(
        {(s, t) for s, t in plays.select("season", "posteam").unique().iter_rows()}
        | {(s, t) for s, t in plays.select("season", "defteam").unique().iter_rows()}
    )
    names += [(s, t, k) for s, t in team_seasons for k in RATING_TYPES]
    col = {n: i for i, n in enumerate(names)}
    p = len(names)
    lam = np.array([penalty if isinstance(n, tuple) and len(n) == 3 else 0.0 for n in names])
    term_cols = [TERM_COLUMNS[t] for t in COA07_TERMS]
    groups: dict[tuple[object, ...], tuple[GroupRow, list[float], list[float]]] = {}
    for s, gid, off, de, is_pass, epa, *terms in plays.select(
        "season", "game_id", "posteam", "defteam", "is_pass", "epa", *term_cols
    ).iter_rows():
        kind = "pass" if is_pass else "run"
        key = (s, gid, off, de, kind)
        if key not in groups:
            cols = (
                col[(s, kind)],
                *(col[("coa07", t)] for t in COA07_TERMS),
                col[(s, off, f"off_{kind}")],
                col[(s, de, f"def_{kind}")],
            )
            vals = (1.0, *(float(v) for v in terms), 1.0, 1.0)
            groups[key] = ((cols, vals), [], [])
        groups[key][1].append(1.0)
        groups[key][2].append(float(epa))
    fit = grouped_ridge(groups, p, lam, np.zeros(p))
    se = np.sqrt(np.diag(fit.cov))
    return Coa07Fit(
        coefs={t: float(fit.b[col[("coa07", t)]]) for t in COA07_TERMS},
        se={t: float(se[col[("coa07", t)]]) for t in COA07_TERMS},
        intercepts={(s, k): float(fit.b[col[(s, k)]]) for s in seasons for k in ("pass", "run")},
        sigma2=fit.sigma2,
        n_plays=fit.n,
    )


def team_games(
    pbp: pl.DataFrame, schedules: pl.DataFrame, *, exclude_turnovers: bool = False
) -> pl.DataFrame:
    """PRJ-01a: one row per (season, game_id, team): plays and summed EPA over the team's
    offensive qualifying plays, points (its final score in the schedules, overtime and
    non-offensive scores included) and drives (distinct fixed_drive in possession). Games
    need a final score and play-by-play. `exclude_turnovers` (report diagnostic only) leaves
    interceptions and lost fumbles out of the plays and EPA."""
    from collections import defaultdict

    from ge.metrics import plays as pf

    epa: dict[tuple[str, str], list[float]] = defaultdict(list)
    q = pbp.filter(pf.qualifying() & pl.col("epa").is_not_null() & pl.col("posteam").is_not_null())
    if exclude_turnovers:
        turnover = (pl.col("interception") == 1).fill_null(False) | (
            pl.col("fumble_lost") == 1
        ).fill_null(False)
        q = q.filter(~turnover)
    for gid, team, x in q.select("game_id", "posteam", "epa").iter_rows():
        epa[(gid, team)].append(float(x))
    drives = (
        pbp.filter(pl.col("posteam").is_not_null() & pl.col("fixed_drive").is_not_null())
        .group_by("game_id", "posteam")
        .agg(pl.col("fixed_drive").n_unique().alias("drives"))
        .rename({"posteam": "team"})
    )
    scored = schedules.filter(
        pl.col("home_score").is_not_null() & pl.col("away_score").is_not_null()
    )
    pts = pl.concat(
        [
            scored.select(
                "season",
                "game_id",
                pl.lit(side).alias("side"),
                pl.col(f"{side}_team").alias("team"),
                pl.col(f"{side}_score").cast(pl.Int64).alias("points"),
            )
            for side in ("home", "away")
        ]
    )
    # Play-by-play's team names (relocated franchises differ in earlier seasons).
    pts = align_to_pbp(pts, pbp_sides(pbp)).drop("side")
    offense = pl.DataFrame(
        [
            {"game_id": g, "team": t, "plays": len(xs), "epa_sum": math.fsum(xs)}
            for (g, t), xs in sorted(epa.items())
        ],
        schema={"game_id": pl.Utf8, "team": pl.Utf8, "plays": pl.Int64, "epa_sum": pl.Float64},
    )
    return (
        pts.with_columns(pl.col("season").cast(pl.Int64))
        .join(offense, on=["game_id", "team"])
        .join(drives.with_columns(pl.col("drives").cast(pl.Int64)), on=["game_id", "team"])
        .select("season", "game_id", "team", "plays", "epa_sum", "points", "drives")
        .sort("game_id", "team")
    )


def fit_c(games: pl.DataFrame) -> CFit:
    """PRJ-01a: league constants over `games` (from team_games) and c by least squares
    through the origin on realized (points/drive - league) against (EPA/play - league)."""
    g = games.filter((pl.col("plays") > 0) & (pl.col("drives") > 0))
    plays = g["plays"].to_list()
    epa = g["epa_sum"].to_list()
    points = g["points"].to_list()
    drives = g["drives"].to_list()
    n = len(plays)
    if n < 2:
        raise ValueError("PRJ-01a: c needs at least two team-games")
    league_epa = math.fsum(epa) / math.fsum(plays)
    league_ppd = math.fsum(points) / math.fsum(drives)
    league_drives = math.fsum(drives) / n
    x = [e / p - league_epa for e, p in zip(epa, plays, strict=True)]
    y = [pt / d - league_ppd for pt, d in zip(points, drives, strict=True)]
    sxx = math.fsum(v * v for v in x)
    c = math.fsum(a * b for a, b in zip(x, y, strict=True)) / sxx
    s2 = math.fsum((b - c * a) ** 2 for a, b in zip(x, y, strict=True)) / (n - 1)
    return CFit(c, math.sqrt(s2 / sxx), league_epa, league_ppd, league_drives, n)


def c_diagnostic(
    window: Window,
    as_of: dt.datetime,
    *,
    root: Path = DATA_ROOT,
) -> dict[str, float]:
    """PRJ-01a report diagnostic (not a model input): over the window's training seasons,
    league qualifying plays per drive, c as fitted, and c refit with turnover plays
    (interceptions, lost fumbles) left out of x. Reads only through the window's Reader."""
    from ge.fit.history import Reader

    reader = Reader(root, window, as_of)
    full, no_to = [], []
    for s in window.seasons:
        pbp = reader.frame("pbp", s)
        sched = reader.frame("schedules", s)
        if pbp.is_empty() or sched.is_empty():
            raise MissingTrainingData(
                f"PRJ-01a: window {window.name} has no {s} play-by-play or schedules"
            )
        full.append(team_games(pbp, sched))
        no_to.append(team_games(pbp, sched, exclude_turnovers=True))
    games = pl.concat(full)
    base = fit_c(games)
    alt = fit_c(pl.concat(no_to))
    plays, drives = games["plays"].to_list(), games["drives"].to_list()
    return {
        "plays_per_drive": math.fsum(plays) / math.fsum(drives),
        "c": base.c,
        "c_se": base.c_se,
        "c_no_turnovers": alt.c,
        "c_no_turnovers_se": alt.c_se,
        "n_team_games": base.n_team_games,
    }


def fit_window(
    window: Window,
    as_of: dt.datetime,
    *,
    root: Path = DATA_ROOT,
    fitted_root: Path | None = None,
) -> WindowFit:
    """PRJ-01a / COA-07: the whole window fit, reading only the window's training seasons
    through the Phase 3e Reader (BT-07a / BT-07b). The G6 penalty is the window's Phase 3e
    fit (never refit). A training season without play-by-play or schedules raises."""
    from contextlib import nullcontext

    from ge.config import use_fitted_root
    from ge.fit.history import Reader
    from ge.metrics import plays as pf
    from ge.models.ratings import ratings_params
    from ge.store.holdout import holdout_season, refuse_holdout

    if window.test_season is not None:
        refuse_holdout(window.test_season, "PRJ-01a window fit")  # a fit to test on 2025
    season = window.test_season if window.test_season is not None else holdout_season() + 1
    with use_fitted_root(fitted_root) if fitted_root is not None else nullcontext():
        params = ratings_params(season)
    reader = Reader(root, window, as_of)
    play_frames, game_frames = [], []
    for s in window.seasons:
        pbp = reader.frame("pbp", s)
        sched = reader.frame("schedules", s)
        if pbp.is_empty() or sched.is_empty():
            raise MissingTrainingData(
                f"PRJ-01a: window {window.name} has no {s} play-by-play or schedules"
            )
        prev = reader.frame("schedules", s - 1) if s - 1 in window.seasons else pl.DataFrame()
        both = pl.concat([prev, sched], how="diagonal_relaxed") if prev.height else sched
        q = pbp.filter(pf.qualifying() & pl.col("epa").is_not_null())
        feats = coa07_features(both, q["game_id"].unique().to_list())
        terms = offense_terms(align_to_pbp(feats, pbp_sides(pbp)))
        plays = q.select(
            pl.lit(s).cast(pl.Int64).alias("season"),
            "game_id",
            "posteam",
            "defteam",
            (pl.col("pass") == 1).fill_null(False).alias("is_pass"),
            pl.col("epa").cast(pl.Float64),
        ).join(terms, on=["game_id", "posteam", "defteam"], how="left")
        missing = plays.filter(pl.any_horizontal(pl.col(list(TERM_COLUMNS.values())).is_null()))
        if missing.height:
            raise ValueError(
                f"PRJ-01a: {missing.height} plays in {s} have no COA-07 terms "
                f"(games {sorted(set(missing['game_id']))[:5]})"
            )
        play_frames.append(plays)
        game_frames.append(team_games(pbp, sched))
    coa = pooled_coa07(pl.concat(play_frames), params.penalty)
    cfit = fit_c(pl.concat(game_frames))
    return WindowFit(
        window.name,
        tuple(window.seasons),
        coa,
        cfit,
        f"{params.fit_version}/{params.window}",
        as_of,
        reader.digest(),
    )


def write_window_file(fit: WindowFit, version: str, out_root: Path = RATINGS_FITTED_ROOT) -> Path:
    """PRJ-01a: config/ratings_fitted/<version>/<window>.yaml, with provenance (FittedFile
    schema: attribution, seasons, data cut and digest, code commit; per value its spec ID,
    method, seasons and n)."""
    import yaml

    from ge.config import ATTRIBUTION
    from ge.fit.job import _commit

    seasons = list(fit.seasons)
    span = f"{min(seasons)}-{max(seasons)}"
    coa_method = (
        f"pooled ridge over every qualifying play of {span}, each play weighted equally: season "
        "pass and run intercepts and the four COA-07 terms (home +1/-1/0, rest and travel "
        "offense minus defense, |time-zone change| offense minus defense) unpenalized, "
        f"team-season pass/run offense and defense effects penalized at the G6 penalty of "
        f"Phase 3e fit {fit.based_on_fit} (decision log 2026-10-12)"
    )
    se_method = "approximate standard error sigma^2 (X'X + Lambda)^-1, penalty treated as known"
    c_method = (
        f"least squares through the origin over {span} team-games on realized values: points "
        "per drive minus league against offensive EPA/play minus league (decision log 2026-10-12)"
    )

    def value(spec_id: str, v: float, method: str, n: int) -> dict[str, object]:
        return {
            "spec_id": spec_id,
            "status": "fitted",
            "value": float(v),
            "method": method,
            "seasons": list(seasons),  # a copy each, so the YAML has no anchors
            "n": int(n),
            "initial_value": None,
        }

    values: dict[str, object] = {}
    for t, key in COA07_KEYS.items():
        values[key] = value("COA-07", fit.coa07.coefs[t], coa_method, fit.coa07.n_plays)
        values[key + SE_SUFFIX] = value("COA-07", fit.coa07.se[t], se_method, fit.coa07.n_plays)
    n_games = fit.c.n_team_games
    values[C_KEY] = value("PRJ-01", fit.c.c, c_method, n_games)
    values[C_KEY + SE_SUFFIX] = value("PRJ-01", fit.c.c_se, "OLS standard error of c", n_games)
    league = {
        "league_epa": (fit.c.league_epa, f"mean EPA over qualifying plays, {span}"),
        "league_ppd": (fit.c.league_ppd, f"total points / total drives over team-games, {span}"),
        "league_drives": (fit.c.league_drives, f"mean drives per team-game, {span}"),
    }
    for name, key in LEAGUE_KEYS.items():
        v, method = league[name]
        values[key] = value("PRJ-01", v, method, n_games)
    test_season = None if fit.window == "live" else int(fit.window[1:])
    body = {
        "fit_version": version,
        "window": fit.window,
        "test_season": test_season,
        "seasons": list(seasons),
        "data_as_of": fit.data_as_of.isoformat(),
        "data_digest": fit.data_digest,
        "code_commit": _commit(),
        "attribution": ATTRIBUTION,
        "values": dict(sorted(values.items())),
        "missing": {},
    }
    folder = out_root / version
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{fit.window}.yaml"
    path.write_text(
        "# Phase 4 ratings constants. Generated by `ge ratings-fit`; do not edit by hand.\n"
        + yaml.safe_dump(body, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
        newline="\n",
    )
    return path


def run_ratings_fit(
    windows: Sequence[Window],
    version: str,
    as_of: dt.datetime,
    *,
    root: Path = DATA_ROOT,
    out_root: Path = RATINGS_FITTED_ROOT,
) -> dict[str, Path]:
    """PRJ-01a: fit and write every window. config/ratings_fitted/active.yaml is set by hand
    (as for the Phase 3e fit)."""
    return {
        w.name: write_window_file(fit_window(w, as_of, root=root), version, out_root)
        for w in windows
    }
