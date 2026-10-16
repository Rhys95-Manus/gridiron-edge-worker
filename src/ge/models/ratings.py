"""PRJ-01a model mode: opponent-adjusted team ratings and rating-implied game lines.

One weighted ridge (G6) over the season's OFF-01 qualifying plays:

    EPA = pass intercept or run intercept (unpenalized)
          + offense pass/run rating + defense pass/run rating (penalized)
          + COA-07 offset (home, rest, travel, time zone; league-wide, held fixed)

Plays are weighted 0.5^(g / h) by the offense's games ago, with the efficiency half-life and
the G6 penalty from the active Phase 3e fit for the season (never params.yaml, never refit).
In weeks 1-4 the ratings shrink toward the G4 carryover prior instead of 0. Ratings carry
approximate standard errors from the ridge posterior covariance. Expected points convert
expected EPA/play through the window's points-per-drive slope c and league drives per
team-game (decision log 2026-10-12).

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt
import polars as pl

from ge.config import REPO_ROOT
from ge.ingest.raw import DATA_ROOT

if TYPE_CHECKING:
    from ge.config import FittedFile
    from ge.metrics.coaching import CoachingRegistry
    from ge.metrics.context import MetricContext

RATINGS_FITTED_ROOT = REPO_ROOT / "config" / "ratings_fitted"
RATING_TYPES: tuple[str, ...] = ("off_pass", "off_run", "def_pass", "def_run")
COA07_TERMS: tuple[str, ...] = ("home", "rest", "travel", "tz")
# Columns of the offense-perspective COA-07 terms (offense minus defense; decision log
# 2026-10-12): home +1 / -1 / 0 at a neutral site, rest days, travel km, |time-zone hours|.
TERM_COLUMNS: Mapping[str, str] = {
    "home": "home",
    "rest": "d_rest",
    "travel": "d_travel",
    "tz": "d_tz",
}
# One row per play for fit_ratings.
PLAY_COLUMNS: tuple[str, ...] = (
    "game_id",
    "posteam",
    "defteam",
    "is_pass",
    "epa",
    "g_off",
    "offset",
)
# Window-constant keys in config/ratings_fitted/<version>/<window>.yaml (FittedFile schema;
# a standard error is stored under the value's key + "/se").
COA07_KEYS: Mapping[str, str] = {t: f"fit:COA-07/{t}" for t in COA07_TERMS}
C_KEY = "fit:PRJ-01/c"
LEAGUE_KEYS: Mapping[str, str] = {
    "league_epa": "fit:PRJ-01/league_epa_per_play",
    "league_ppd": "fit:PRJ-01/league_points_per_drive",
    "league_drives": "fit:PRJ-01/league_drives_per_team_game",
}
SE_SUFFIX = "/se"
# Phase 4b calibration (decision log 2026-10-13): actual home margin = a x 1[non-neutral] +
# b x raw spread; actual total = a_t + b_t x raw total.
CALIB_KEYS: Mapping[str, str] = {
    "a": "fit:PRJ-01/calib_a",
    "b": "fit:PRJ-01/calib_b",
    "a_t": "fit:PRJ-01/calib_a_t",
    "b_t": "fit:PRJ-01/calib_b_t",
    "a_se": "fit:PRJ-01/calib_a/se",
    "b_se": "fit:PRJ-01/calib_b/se",
    "a_t_se": "fit:PRJ-01/calib_a_t/se",
    "b_t_se": "fit:PRJ-01/calib_b_t/se",
    "ab_cov": "fit:PRJ-01/calib_ab_cov",
    "ab_t_cov": "fit:PRJ-01/calib_ab_t_cov",
}

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class Calibration:
    """PRJ-01a calibration of one window: OLS coefficients, standard errors, the covariance
    of each pair, and n (rated training games)."""

    a: float
    b: float
    a_t: float
    b_t: float
    a_se: float
    b_se: float
    a_t_se: float
    b_t_se: float
    ab_cov: float
    ab_t_cov: float
    n: int


def calibrate(games: pl.DataFrame) -> Calibration:
    """PRJ-01a calibration (decision log 2026-10-13): least squares on actual results only.
    margin = a x 1[non-neutral] + b x raw_spread (no other intercept: a is the home edge and
    never applies at a neutral site); total = a_t + b_t x raw_total. Columns: raw_spread,
    raw_total, neutral, margin, total. Standard errors are OLS, homoskedastic."""
    d = games.select("raw_spread", "raw_total", "neutral", "margin", "total")
    n = d.height
    if n < 3:
        raise ValueError(f"PRJ-01a: calibration needs at least 3 rated games, got {n}")
    nn = (~d["neutral"].cast(pl.Boolean)).cast(pl.Float64).to_numpy()
    xs = d["raw_spread"].cast(pl.Float64).to_numpy()
    xt = d["raw_total"].cast(pl.Float64).to_numpy()

    def ols(X: FloatArray, y: FloatArray) -> tuple[FloatArray, FloatArray]:
        xtx = X.T @ X
        b = np.linalg.solve(xtx, X.T @ y)
        r = y - X @ b
        return b, float(r @ r) / (n - X.shape[1]) * np.linalg.inv(xtx)

    bs, cs = ols(np.column_stack([nn, xs]), d["margin"].cast(pl.Float64).to_numpy())
    bt, ct = ols(np.column_stack([np.ones(n), xt]), d["total"].cast(pl.Float64).to_numpy())
    return Calibration(
        a=float(bs[0]),
        b=float(bs[1]),
        a_t=float(bt[0]),
        b_t=float(bt[1]),
        a_se=float(np.sqrt(cs[0, 0])),
        b_se=float(np.sqrt(cs[1, 1])),
        a_t_se=float(np.sqrt(ct[0, 0])),
        b_t_se=float(np.sqrt(ct[1, 1])),
        ab_cov=float(cs[0, 1]),
        ab_t_cov=float(ct[0, 1]),
        n=n,
    )


@dataclass(frozen=True)
class RatingsParams:
    """PRJ-01a / G6 / G3: the fitted values one season's ratings use."""

    window: str
    fit_version: str
    penalty: float
    h_efficiency: float
    h_usage: float


@dataclass(frozen=True)
class WindowConsts:
    """PRJ-01a / COA-07: one window's league-wide constants (config/ratings_fitted)."""

    window: str
    version: str
    coa07: Mapping[str, float]
    coa07_se: Mapping[str, float]
    c: float
    c_se: float
    league_epa: float
    league_ppd: float
    league_drives: float
    data_as_of: str | None = None  # the data cut the window file was fitted at
    calib: Calibration | None = None  # Phase 4b; None in r1 (raw lines only)


@dataclass(frozen=True)
class Prior:
    """G4: each team's starting ratings b0 (last season's final ratings, already regressed a
    further 1/3 toward 0 on a new play-caller or QB), last season's final intercepts, and its
    residual variance (for standard errors before any current-season play)."""

    ratings: Mapping[tuple[str, str], float]
    int_pass: float
    int_run: float
    sigma2: float


@dataclass(frozen=True)
class RatingTable:
    """PRJ-01a: ratings and approximate standard errors. `cov` is over `index`: the two
    intercepts, then (team, type) for every team and RATING_TYPES."""

    teams: tuple[str, ...]
    values: Mapping[tuple[str, str], float]
    se: Mapping[tuple[str, str], float]
    int_pass: float
    int_run: float
    index: tuple[object, ...]
    cov: FloatArray
    sigma2: float
    n_plays: int

    def frame(self) -> pl.DataFrame:
        """team, type, value, se; sorted."""
        rows = [
            {"team": t, "type": k, "value": self.values[(t, k)], "se": self.se[(t, k)]}
            for t in self.teams
            for k in RATING_TYPES
        ]
        return pl.DataFrame(rows).sort("team", "type")


@dataclass(frozen=True)
class GameLines:
    """PRJ-01a: rating-implied points, spread (home minus away) and total for one game."""

    game_id: str
    home_team: str
    away_team: str
    home_epa: float
    away_epa: float
    home_points: float
    away_points: float
    spread: float
    total: float
    spread_se: float
    total_se: float
    home_offset: float  # COA-07 offset in the home offense's expected EPA/play
    away_offset: float
    # Phase 4b: `spread` and `total` above are calibrated when the window has a calibration;
    # the raw rating-implied values are kept for diagnostics.
    raw_spread: float
    raw_total: float
    raw_spread_se: float
    raw_total_se: float
    neutral: bool


@dataclass(frozen=True)
class GameRatings:
    """Everything ratings_for_game computed for one game, for the CLI and the report."""

    game_id: str
    season: int
    week: int
    as_of: dt.datetime
    params: RatingsParams
    consts: WindowConsts
    table: RatingTable
    pass_rate: Mapping[str, float]
    lines: GameLines
    notes: tuple[str, ...]


# ---- fitted inputs ----


def ratings_params(season: int) -> RatingsParams:
    """PRJ-01a / G6 / G3: the G6 penalty and the efficiency and usage half-lives from the
    active Phase 3e fit for `season` (use_season). Raises NotImplementedError when the season
    has no fit: a half-life is never taken from params.yaml."""
    from ge.config import current_params, use_season
    from ge.metrics.conventions import g6_penalty

    with use_season(season):  # BT-07b: the holdout raises here
        a = current_params()
        f = a.fitted
        if f is None:
            raise NotImplementedError(
                f"PRJ-01a: season {season} has no Phase 3e fit, so no G6 penalty or half-lives"
            )
        h: dict[str, float] = {}
        for kind in ("efficiency", "usage"):
            key = f"conventions.g3_{kind}_half_life_games"
            if key not in f.values:
                raise NotImplementedError(
                    f"PRJ-01a: {key} is not fitted in {f.fit_version}/{f.window}"
                )
            h[kind] = float(f.values[key].value)
        return RatingsParams(f.window, f.fit_version, g6_penalty(), h["efficiency"], h["usage"])


def load_window_consts(season: int, root: Path = RATINGS_FITTED_ROOT) -> WindowConsts:
    """PRJ-01a / COA-07: the window constants for `season` from
    config/ratings_fitted/<active version>/<window>.yaml. Raises without them."""
    import yaml

    from ge.config import FittedFile, _check_fitted, _read_yaml, load_params, window_for

    window = window_for(season)  # BT-07b: the holdout raises here
    if window is None:
        raise NotImplementedError(f"PRJ-01a: season {season} is in no walk-forward window")
    active = root / "active.yaml"
    if not active.exists():
        raise NotImplementedError(f"PRJ-01a: no ratings constants ({active} is missing)")
    version = str(yaml.safe_load(active.read_text(encoding="utf-8"))["fit_version"])
    path = root / version / f"{window}.yaml"
    if not path.exists():
        raise NotImplementedError(f"PRJ-01a: no ratings constants for {window} ({path})")
    f = FittedFile.model_validate(_read_yaml(path))
    _check_fitted(f, path, load_params())

    def get(key: str) -> float:
        if key not in f.values:
            raise NotImplementedError(f"PRJ-01a: {key} missing from {path}")
        return float(f.values[key].value)

    return WindowConsts(
        window=window,
        version=version,
        coa07={t: get(k) for t, k in COA07_KEYS.items()},
        coa07_se={t: get(k + SE_SUFFIX) for t, k in COA07_KEYS.items()},
        c=get(C_KEY),
        c_se=get(C_KEY + SE_SUFFIX),
        league_epa=get(LEAGUE_KEYS["league_epa"]),
        league_ppd=get(LEAGUE_KEYS["league_ppd"]),
        league_drives=get(LEAGUE_KEYS["league_drives"]),
        data_as_of=f.data_as_of,
        calib=_calib_from(f, path) if CALIB_KEYS["a"] in f.values else None,
    )


def _calib_from(f: FittedFile, path: Path) -> Calibration:
    missing = [k for k in CALIB_KEYS.values() if k not in f.values]
    if missing:
        raise NotImplementedError(f"PRJ-01a: {path} has a partial calibration: {missing}")
    v = {name: float(f.values[key].value) for name, key in CALIB_KEYS.items()}
    return Calibration(**v, n=int(f.values[CALIB_KEYS["a"]].n))


# ---- COA-07 terms ----

_SCHED_COLUMNS = (
    "game_id",
    "season",
    "week",
    "gameday",
    "gametime",
    "home_team",
    "away_team",
    "stadium_id",
    "location",
    "home_rest",
    "away_rest",
)


def coa07_features(
    schedules: pl.DataFrame,
    game_ids: Sequence[str],
    franchise: Callable[[str], str] | None = None,
) -> pl.DataFrame:
    """COA-07: per (game_id, team) for `game_ids`: home (+1 home, -1 away, 0 neutral site),
    rest_days, travel_km and tz_change_hours (signed). The travel origin comes from the same
    function as coa_07 (coaching.travel_origin): the previous game's stadium, or the home
    stadium after a bye, with games matched by `franchise` (nflverse teams table) so a
    relocated team keeps its history; without `franchise`, abbreviations are matched as
    they are. `schedules` holds the games before. When no earlier home game is in
    `schedules` (the first season of data), the origin after a bye is the team's next listed
    home stadium (schedules are published in advance)."""
    from bisect import bisect_left
    from collections import defaultdict
    from zoneinfo import ZoneInfo

    from ge.config import load_ingest
    from ge.ingest.stadiums import load_stadiums
    from ge.metrics.coaching import _haversine_km, travel_origin

    fr_of: Callable[[str], str] = franchise or (lambda abbr: abbr)
    stadia = {str(s["stadium_id"]): s for s in load_stadiums()}
    radius = float(load_ingest().geo.earth_mean_radius_km.value)
    rows = (
        schedules.select(list(_SCHED_COLUMNS))
        .unique("game_id", keep="first")
        .sort("gameday", "gametime", "game_id")
        .to_dicts()
    )
    by_id = {r["game_id"]: r for r in rows}
    games: dict[str, list[dict[str, object]]] = defaultdict(list)  # by franchise
    for r in rows:
        for fr in {fr_of(str(r["home_team"])), fr_of(str(r["away_team"]))}:
            games[fr].append(r)
    keys = {f: [(g["gameday"], g["gametime"], g["game_id"]) for g in gs] for f, gs in games.items()}

    out: list[dict[str, object]] = []
    for gid in sorted(set(game_ids)):
        t = by_id[gid]
        kickoff = dt.datetime.combine(
            dt.date.fromisoformat(str(t["gameday"])),
            dt.time.fromisoformat(str(t["gametime"])),
            ZoneInfo("America/New_York"),
        )
        dest = stadia[str(t["stadium_id"])]

        def offset(s: Mapping[str, object], kickoff: dt.datetime = kickoff) -> float:
            off = kickoff.astimezone(ZoneInfo(str(s["timezone"]))).utcoffset()
            assert off is not None
            return off.total_seconds() / 3600

        for side in ("home", "away"):
            team = str(t[f"{side}_team"])
            fr = fr_of(team)
            i = bisect_left(keys[fr], (t["gameday"], t["gametime"], gid))
            origin_id, _ = travel_origin(games[fr][:i], t, team, fr_of)
            if origin_id is None:
                later = [g for g in games[fr][i + 1 :] if fr_of(str(g["home_team"])) == fr][:1]
                if not later:
                    # Point-in-time, with no earlier season in the store: the travel origin
                    # can't be known, so the game can't be rated (raise, don't guess).
                    raise NotImplementedError(
                        f"COA-07: no home stadium for {team} in the schedules visible to this "
                        "game, so its travel origin is unknown"
                    )
                origin_id = str(later[0]["stadium_id"])
            origin = stadia[origin_id]
            neutral = t["location"] == "Neutral"
            out.append(
                {
                    "game_id": gid,
                    "team": team,
                    "side": side,
                    "home": 0.0 if neutral else (1.0 if side == "home" else -1.0),
                    "rest_days": float(str(t[f"{side}_rest"])),
                    "travel_km": _haversine_km(
                        float(str(origin["lat"])),
                        float(str(origin["lon"])),
                        float(str(dest["lat"])),
                        float(str(dest["lon"])),
                        radius,
                    ),
                    "tz_change_hours": offset(dest) - offset(origin),
                }
            )
    schema = {
        "game_id": pl.Utf8,
        "team": pl.Utf8,
        "side": pl.Utf8,
        "home": pl.Float64,
        "rest_days": pl.Float64,
        "travel_km": pl.Float64,
        "tz_change_hours": pl.Float64,
    }
    return pl.DataFrame(out, schema=schema)


def franchise_of(ctx: MetricContext) -> Callable[[str], str]:
    """A team abbreviation's franchise from the context's nflverse teams table (abbreviations
    the table doesn't know stand for themselves)."""

    def franchise(abbr: str) -> str:
        try:
            return ctx.franchise(abbr)
        except KeyError:
            return abbr

    return franchise


def franchise_map(teams: pl.DataFrame) -> Callable[[str], str]:
    """The same lookup from an nflverse teams table (DATA-04: team_abbr -> team_id)."""
    d = dict(teams.select("team_abbr", "team_id").iter_rows()) if teams.height else {}
    return lambda abbr: str(d.get(abbr, abbr))


def pbp_sides(pbp: pl.DataFrame) -> pl.DataFrame:
    """Each game's home and away team as play-by-play names them (game_id, side, team)."""
    g = pbp.select("game_id", "home_team", "away_team").unique("game_id", keep="first")
    return pl.concat(
        [
            g.select("game_id", pl.lit(side).alias("side"), pl.col(f"{side}_team").alias("team"))
            for side in ("home", "away")
        ]
    )


def align_to_pbp(features: pl.DataFrame, sides: pl.DataFrame) -> pl.DataFrame:
    """Rename each game's teams to play-by-play's abbreviations, matched by home/away role.
    nflverse play-by-play names relocated franchises by their current abbreviation in earlier
    seasons while the schedules keep the abbreviation of the time, so a join on team would
    miss those games. Games with no play-by-play keep the schedules' names."""
    return (
        features.join(sides.rename({"team": "_pbp_team"}), on=["game_id", "side"], how="left")
        .with_columns(pl.coalesce("_pbp_team", "team").alias("team"))
        .drop("_pbp_team")
    )


def offense_terms(features: pl.DataFrame) -> pl.DataFrame:
    """COA-07 in PRJ-01a: per (game_id, posteam, defteam), the offense's home value and the
    offense-minus-defense differences in rest, travel and |time-zone change| (TERM_COLUMNS)."""
    f = features.select("game_id", "team", "home", "rest_days", "travel_km", "tz_change_hours")
    opp = f.select(
        "game_id",
        pl.col("team").alias("defteam"),
        pl.col("rest_days").alias("_rest"),
        pl.col("travel_km").alias("_travel"),
        pl.col("tz_change_hours").alias("_tz"),
    )
    return (
        f.join(opp, on="game_id")
        .filter(pl.col("team") != pl.col("defteam"))
        .select(
            "game_id",
            pl.col("team").alias("posteam"),
            "defteam",
            "home",
            (pl.col("rest_days") - pl.col("_rest")).alias("d_rest"),
            (pl.col("travel_km") - pl.col("_travel")).alias("d_travel"),
            (pl.col("tz_change_hours").abs() - pl.col("_tz").abs()).alias("d_tz"),
        )
        .sort("game_id", "posteam")
    )


def term_offset(terms: pl.DataFrame, coefs: Mapping[str, float]) -> pl.Series:
    """COA-07 in PRJ-01a: sum of coefficient x term over COA07_TERMS, one value per row."""
    expr = pl.lit(0.0)
    for i, t in enumerate(COA07_TERMS):
        term = float(coefs[t]) * pl.col(TERM_COLUMNS[t])
        expr = term if i == 0 else expr + term
    return terms.select(expr.alias("offset")).to_series()


# ---- p_A ----


def pass_rates(plays: pl.DataFrame, h: float) -> dict[str, float]:
    """PRJ-01a p_A: each offense's recency-weighted pass share of qualifying plays, weights
    0.5^(g / h) with g the team's games ago counted across the season boundary (decision log
    2026-10-12). Columns: posteam, game_id, kickoff_utc, is_pass."""
    import math
    from collections import defaultdict

    games = (
        plays.select("posteam", "game_id", "kickoff_utc")
        .unique()
        .sort(["posteam", "kickoff_utc", "game_id"], descending=[False, True, True])
        .with_columns(pl.int_range(pl.len()).over("posteam").cast(pl.Float64).alias("_g"))
    )
    rows = plays.select("posteam", "game_id", "is_pass").join(
        games.select("posteam", "game_id", "_g"), on=["posteam", "game_id"]
    )
    num: dict[str, list[float]] = defaultdict(list)
    den: dict[str, list[float]] = defaultdict(list)
    for team, _, is_pass, g in rows.iter_rows():
        w = 0.5 ** (g / h)
        den[team].append(w)
        num[team].append(w if is_pass else 0.0)
    return {t: math.fsum(num[t]) / math.fsum(den[t]) for t in sorted(den)}


# ---- the ridge ----

GroupRow = tuple[tuple[int, ...], tuple[float, ...]]


@dataclass(frozen=True)
class RidgeFit:
    """A grouped weighted ridge: coefficients, sigma^2 (A^-1) and the play counts."""

    b: FloatArray
    cov: FloatArray
    sigma2: float
    n: int


def grouped_ridge(
    groups: Mapping[tuple[object, ...], tuple[GroupRow, list[float], list[float]]],
    p: int,
    lam: FloatArray,
    b0: FloatArray,
) -> RidgeFit:
    """G6: minimise sum_i w_i (y_i - x_g b)^2 + sum_j lam_j (b_j - b0_j)^2, where every play i
    in group g shares the design row x_g (sparse: column indices and values). Group sums are
    exactly rounded (math.fsum) and groups are taken in sorted order, so the result does not
    depend on the order of the plays (rule 6). Covariance: sigma^2 (X'WX + Lambda)^-1, with
    sigma^2 = sum w r^2 / sum w (decision log 2026-10-12: approximate)."""
    import math

    A = np.diag(np.asarray(lam, dtype=np.float64).copy())
    rhs = np.asarray(lam, dtype=np.float64) * np.asarray(b0, dtype=np.float64)
    keys = sorted(groups, key=repr)
    for k in keys:
        (cols, vals), ws, ys = groups[k]
        sw = math.fsum(ws)
        swy = math.fsum(w * y for w, y in zip(ws, ys, strict=True))
        ix = np.asarray(cols, dtype=np.intp)
        v = np.asarray(vals, dtype=np.float64)
        A[np.ix_(ix, ix)] += sw * np.outer(v, v)
        rhs[ix] += swy * v
    b = np.asarray(np.linalg.solve(A, rhs), dtype=np.float64)
    sse: list[float] = []
    total_w: list[float] = []
    n = 0
    for k in keys:
        (cols, vals), ws, ys = groups[k]
        f = math.fsum(b[c] * v for c, v in zip(cols, vals, strict=True))
        sse.append(math.fsum(w * (y - f) ** 2 for w, y in zip(ws, ys, strict=True)))
        total_w.extend(ws)
        n += len(ws)
    sigma2 = math.fsum(sse) / math.fsum(total_w)
    cov = np.asarray(sigma2 * np.linalg.inv(A), dtype=np.float64)
    return RidgeFit(b, cov, sigma2, n)


def _index(teams: Sequence[str]) -> tuple[object, ...]:
    return ("int_pass", "int_run", *((t, k) for t in teams for k in RATING_TYPES))


def fit_ratings(
    plays: pl.DataFrame,
    teams: Sequence[str],
    *,
    penalty: float,
    h: float,
    prior: Prior | None,
    run_penalty_scale: float = 1.0,
) -> RatingTable:
    """PRJ-01a / G6: the weighted ridge over `plays` (PLAY_COLUMNS). Pass and run intercepts
    unpenalized; team ratings penalized toward the G4 prior's b0 when `prior` is given (weeks
    1-4), else toward 0. With no plays the ratings are b0 and the intercepts the prior's.
    `run_penalty_scale` multiplies the penalty on run columns only (report sensitivity check;
    the model always uses 1)."""
    import math

    teams = tuple(sorted(teams))
    index = _index(teams)
    col = {name: i for i, name in enumerate(index)}
    p = len(index)
    lam = np.zeros(p)
    b0 = np.zeros(p)
    for name, i in col.items():
        if isinstance(name, tuple):
            lam[i] = penalty * (run_penalty_scale if str(name[1]).endswith("_run") else 1.0)
            if prior is not None:
                b0[i] = float(prior.ratings.get((str(name[0]), str(name[1])), 0.0))

    if plays.is_empty():
        if prior is None:
            raise ValueError("PRJ-01a: no plays and no G4 prior to rate from")
        cov = np.zeros((p, p))
        for i in range(2, p):
            cov[i, i] = prior.sigma2 / lam[i]
        return _table(teams, index, b0, cov, prior.int_pass, prior.int_run, prior.sigma2, 0)

    unknown = (set(plays["posteam"]) | set(plays["defteam"])) - set(teams)
    if unknown:
        raise ValueError(f"PRJ-01a: plays for teams not being rated: {sorted(unknown)}")
    groups: dict[tuple[object, ...], tuple[GroupRow, list[float], list[float]]] = {}
    for off, de, is_pass, epa, g, offset in plays.select(
        "posteam", "defteam", "is_pass", "epa", "g_off", "offset"
    ).iter_rows():
        kind = "pass" if is_pass else "run"
        key = (off, de, kind)
        if key not in groups:
            cols = (col[f"int_{kind}"], col[(off, f"off_{kind}")], col[(de, f"def_{kind}")])
            groups[key] = ((cols, (1.0, 1.0, 1.0)), [], [])
        groups[key][1].append(0.5 ** (g / h))
        groups[key][2].append(epa - offset)
    if not any(k[2] == "pass" for k in groups) or not any(k[2] == "run" for k in groups):
        raise ValueError("PRJ-01a: need both pass and run plays to estimate the intercepts")
    fit = grouped_ridge(groups, p, lam, b0)
    assert math.isfinite(fit.sigma2)
    return _table(teams, index, fit.b, fit.cov, fit.b[0], fit.b[1], fit.sigma2, fit.n)


def _table(
    teams: tuple[str, ...],
    index: tuple[object, ...],
    b: FloatArray,
    cov: FloatArray,
    int_pass: float,
    int_run: float,
    sigma2: float,
    n: int,
) -> RatingTable:
    values: dict[tuple[str, str], float] = {}
    se: dict[tuple[str, str], float] = {}
    for i, name in enumerate(index):
        if isinstance(name, tuple):
            key = (str(name[0]), str(name[1]))
            values[key] = float(b[i])
            se[key] = float(np.sqrt(cov[i, i]))
    return RatingTable(
        teams, values, se, float(int_pass), float(int_run), index, cov, float(sigma2), n
    )


# ---- expected points and lines ----


def expected_epa(
    table: RatingTable, offense: str, defense: str, p: float, offset: float
) -> tuple[float, FloatArray]:
    """PRJ-01a: expected EPA/play for `offense` against `defense` and its gradient over
    table.index (for the delta method)."""
    v = table.values
    e = (
        p * (table.int_pass + v[(offense, "off_pass")] + v[(defense, "def_pass")])
        + (1 - p) * (table.int_run + v[(offense, "off_run")] + v[(defense, "def_run")])
        + offset
    )
    col = {name: i for i, name in enumerate(table.index)}
    grad = np.zeros(len(table.index))
    for name, weight in (
        ("int_pass", p),
        ("int_run", 1 - p),
        ((offense, "off_pass"), p),
        ((defense, "def_pass"), p),
        ((offense, "off_run"), 1 - p),
        ((defense, "def_run"), 1 - p),
    ):
        grad[col[name]] += weight
    return float(e), grad


def expected_points(epa: float, consts: WindowConsts) -> float:
    """PRJ-01a: league drives per team-game x (league points per drive + c x (epa - league
    EPA/play))."""
    return consts.league_drives * (consts.league_ppd + consts.c * (epa - consts.league_epa))


def game_lines(
    table: RatingTable,
    game_id: str,
    home: str,
    away: str,
    pass_rate: Mapping[str, float],
    terms: pl.DataFrame,
    consts: WindowConsts,
) -> GameLines:
    """PRJ-01a: rating-implied spread (home minus away points) and total, with delta-method
    standard errors from the ratings' covariance. `terms` holds the game's two offense rows;
    the home offense's home term is 0 at a neutral site. With a window calibration (Phase 4b)
    the returned spread and total are calibrated: a x 1[non-neutral] + b x raw spread and
    a_t + b_t x raw total, with variance b^2 Var(raw) + Var(calibration line at raw)."""
    import math

    def row(off: str, de: str) -> pl.DataFrame:
        r = terms.filter((pl.col("posteam") == off) & (pl.col("defteam") == de))
        if r.height != 1:
            raise ValueError(f"PRJ-01a: {game_id}: expected one COA-07 row for {off}")
        return r

    rh, ra = row(home, away), row(away, home)
    oh, oa = float(term_offset(rh, consts.coa07)[0]), float(term_offset(ra, consts.coa07)[0])
    neutral = float(rh["home"][0]) == 0.0
    eh, gh = expected_epa(table, home, away, pass_rate[home], oh)
    ea, ga = expected_epa(table, away, home, pass_rate[away], oa)
    ph, pa = expected_points(eh, consts), expected_points(ea, consts)
    k = consts.league_drives * consts.c
    gs, gt = k * (gh - ga), k * (gh + ga)
    raw_s, raw_t = ph - pa, ph + pa
    se_s, se_t = math.sqrt(float(gs @ table.cov @ gs)), math.sqrt(float(gt @ table.cov @ gt))
    spread, total, spread_se, total_se = raw_s, raw_t, se_s, se_t
    cal = consts.calib
    if cal is not None:
        ind = 0.0 if neutral else 1.0
        spread = ind * cal.a + cal.b * raw_s
        total = cal.a_t + cal.b_t * raw_t
        var_s = cal.b**2 * se_s**2 + (
            ind * ind * cal.a_se**2 + raw_s**2 * cal.b_se**2 + 2 * ind * raw_s * cal.ab_cov
        )
        var_t = cal.b_t**2 * se_t**2 + (
            cal.a_t_se**2 + raw_t**2 * cal.b_t_se**2 + 2 * raw_t * cal.ab_t_cov
        )
        spread_se, total_se = math.sqrt(var_s), math.sqrt(var_t)
    return GameLines(
        game_id,
        home,
        away,
        eh,
        ea,
        ph,
        pa,
        spread,
        total,
        spread_se,
        total_se,
        oh,
        oa,
        raw_s,
        raw_t,
        se_s,
        se_t,
        neutral,
    )


def neutral_margins(
    table: RatingTable, pass_rate: Mapping[str, float], consts: WindowConsts
) -> pl.DataFrame:
    """PRJ-01a ranking (decision log 2026-10-12): each team's implied neutral-site point
    margin against a league-average opponent (ratings 0, mean pass rate), with its standard
    error; sorted best first. With a window calibration the margin is b x raw (a never
    applies at a neutral site) and the error adds b's uncertainty."""
    import math

    p_avg = math.fsum(pass_rate[t] for t in table.teams) / len(table.teams)
    col = {name: i for i, name in enumerate(table.index)}
    k = consts.league_drives * consts.c
    rows = []
    for t in table.teams:
        p = pass_rate[t]
        v = table.values
        e_off = p * (table.int_pass + v[(t, "off_pass")]) + (1 - p) * (
            table.int_run + v[(t, "off_run")]
        )
        e_def = p_avg * (table.int_pass + v[(t, "def_pass")]) + (1 - p_avg) * (
            table.int_run + v[(t, "def_run")]
        )
        g = np.zeros(len(table.index))
        g[col["int_pass"]] += k * (p - p_avg)
        g[col["int_run"]] += k * ((1 - p) - (1 - p_avg))
        g[col[(t, "off_pass")]] += k * p
        g[col[(t, "off_run")]] += k * (1 - p)
        g[col[(t, "def_pass")]] -= k * p_avg
        g[col[(t, "def_run")]] -= k * (1 - p_avg)
        margin = expected_points(e_off, consts) - expected_points(e_def, consts)
        se = math.sqrt(float(g @ table.cov @ g))
        cal = consts.calib
        if cal is not None:
            se = math.sqrt(cal.b**2 * se**2 + margin**2 * cal.b_se**2)
            margin = cal.b * margin
        rows.append({"team": t, "margin": margin, "se": se})
    return pl.DataFrame(rows).sort(["margin", "team"], descending=[True, False])


# ---- from a snapshot ----

_PLAY_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "game_id": pl.Utf8,
    "season": pl.Int64,
    "week": pl.Int64,
    "kickoff_utc": pl.Datetime("us", "UTC"),
    "posteam": pl.Utf8,
    "defteam": pl.Utf8,
    "is_pass": pl.Boolean,
    "epa": pl.Float64,
    "g_off": pl.Float64,
    "home": pl.Float64,
    "d_rest": pl.Float64,
    "d_travel": pl.Float64,
    "d_tz": pl.Float64,
    "offset": pl.Float64,
}


def _schedules_with_target(ctx: MetricContext) -> pl.DataFrame:
    from ge.store.known_at import with_kickoff

    sched = with_kickoff(ctx.snap.collect("schedules"))
    tg = ctx.snap.collect("target_game")
    return pl.concat([sched, tg], how="diagonal_relaxed") if tg.height else sched


def season_plays(ctx: MetricContext, season: int, consts: WindowConsts) -> pl.DataFrame:
    """PRJ-01a: `season`'s visible OFF-01 qualifying plays in the context's snapshot as
    PLAY_COLUMNS (plus season, week, kickoff_utc and the TERM_COLUMNS), with the offense's
    games ago within that season and the COA-07 offset from the window's coefficients."""
    from ge.metrics import plays as pf

    if season != ctx.season:
        raise ValueError(f"PRJ-01a: context is season {ctx.season}, asked for {season}")
    p = ctx.plays
    if p.is_empty():
        return pl.DataFrame(schema=_PLAY_SCHEMA)
    p = p.filter(pf.qualifying() & pl.col("epa").is_not_null())
    if p.is_empty():
        return pl.DataFrame(schema=_PLAY_SCHEMA)
    sched = _schedules_with_target(ctx)
    feats = coa07_features(sched, p["game_id"].unique().to_list(), franchise_of(ctx))
    terms = offense_terms(align_to_pbp(feats, pbp_sides(p)))
    kick = sched.select("game_id", "kickoff_utc").unique("game_id", keep="first")
    out = (
        p.select(
            "game_id",
            pl.lit(season).cast(pl.Int64).alias("season"),
            pl.col("week").cast(pl.Int64),
            "posteam",
            "defteam",
            (pl.col("pass") == 1).fill_null(False).alias("is_pass"),
            pl.col("epa").cast(pl.Float64),
            pl.col("g_off").cast(pl.Float64),
        )
        .join(kick, on="game_id", how="left")
        .join(terms, on=["game_id", "posteam", "defteam"], how="left")
    )
    out = out.with_columns(term_offset(out, consts.coa07))
    return out.select(list(_PLAY_SCHEMA))


def carry_by_franchise(
    last: Mapping[tuple[str, str], float],
    teams_now: Sequence[str],
    franchise: Callable[[str], str],
) -> dict[tuple[str, str], float]:
    """G4: last season's final ratings keyed by this season's team abbreviations, matched by
    franchise so a relocated team keeps its history. A team with no history gets none."""
    then = {franchise(t): t for t in sorted({t for t, _ in last})}
    out: dict[tuple[str, str], float] = {}
    for t in teams_now:
        old = then.get(franchise(t))
        if old is None:
            continue
        for k in RATING_TYPES:
            if (old, k) in last:
                out[(t, k)] = last[(old, k)]
    return out


def rated_teams(ctx: MetricContext, cur: pl.DataFrame) -> list[str]:
    """PRJ-01a (ruling 2026-10-14): the teams that can affect the target game's lines, under
    play-by-play names: its two teams plus every team with plays this season so far. Other
    teams are left out of that game's rating table (they share no plays with it), so G4's
    unknown-change rule never blocks a game over a team that doesn't touch it. From week 2
    every team has played, so the table holds all teams."""
    name = team_names(ctx)
    tg = ctx.snap.collect("target_game").row(0, named=True)
    teams = {name(str(tg["home_team"])), name(str(tg["away_team"]))}
    teams |= set(cur["posteam"].to_list()) | set(cur["defteam"].to_list())
    return sorted(teams)


def build_prior(
    ctx: MetricContext,
    params: RatingsParams,
    consts: WindowConsts,
    teams: Sequence[str] | None = None,
) -> Prior | None:
    """G4 for PRJ-01a: None after week 4. In weeks 1-4, last season's final ratings (a full
    fit of last season's plays, same penalty and half-life), regressed a further 1/3 toward
    0 per side for a team with a new play-caller or QB (MetricContext.g4_changed), and last
    season's final intercepts, for `teams` (default: rated_teams). An unknown change for one
    of them raises NotImplementedError (G4) with the reason."""
    from ge.metrics.conventions import carryover_prior, in_carryover_window

    if ctx.week is None or not in_carryover_window(ctx.week):
        return None
    prev = ctx.prior_context()
    last = season_plays(prev, ctx.season - 1, consts)
    if last.is_empty():
        raise NotImplementedError(
            f"G4: weeks 1-4 of {ctx.season} need last season's ratings; {ctx.season - 1} has no "
            "plays in the snapshot"
        )
    teams_then = sorted(set(last["posteam"].to_list()) | set(last["defteam"].to_list()))
    base = fit_ratings(last, teams_then, penalty=params.penalty, h=params.h_efficiency, prior=None)
    if teams is None:
        teams = rated_teams(ctx, season_plays(ctx, ctx.season, consts))
    teams_now = sorted(teams)
    carried = carry_by_franchise(base.values, teams_now, ctx.franchise)
    ratings: dict[tuple[str, str], float] = {}
    for t in teams_now:
        for side in ("offense", "defense"):
            changed, note = ctx.g4_changed(t, side)
            if changed is None:
                raise NotImplementedError(
                    f"G4: {t} {side}: whether the play-caller or quarterback changed is "
                    f"unknown{note}"
                )
            for k in RATING_TYPES:
                if k.startswith(side[:3]):
                    ratings[(t, k)] = carryover_prior(
                        carried.get((t, k), 0.0), 0.0, changed=changed
                    )
    return Prior(ratings, base.int_pass, base.int_run, base.sigma2)


def team_names(ctx: MetricContext) -> Callable[[str], str]:
    """Each franchise under its play-by-play abbreviation. nflverse play-by-play names a
    relocated franchise by its current abbreviation in earlier seasons while the schedules
    keep the abbreviation of the time; ratings are keyed by play-by-play's names (this
    season's where it has plays, else last season's). Matched by franchise (teams table)."""
    pbp = ctx.snap.collect("pbp")
    names: dict[str, str] = {}
    if pbp.height:
        for season in sorted(set(pbp["season"].to_list())):
            s = pbp.filter(pl.col("season") == season)
            for t in sorted(set(s["home_team"].to_list()) | set(s["away_team"].to_list())):
                try:
                    names[ctx.franchise(t)] = t
                except KeyError:
                    continue

    def name(abbr: str) -> str:
        try:
            return names.get(ctx.franchise(abbr), abbr)
        except KeyError:
            return abbr

    return name


def rate_context(
    ctx: MetricContext,
    *,
    ratings_root: Path = RATINGS_FITTED_ROOT,
    run_penalty_scale: float = 1.0,
    params: RatingsParams | None = None,
    consts: WindowConsts | None = None,
) -> GameRatings:
    """PRJ-01a for the context's target game (ratings_for_game without building the
    snapshot; the walk-forward report reuses the context for pace). `params` and `consts`
    default to the season's own window; the Phase 4b calibration passes its window's values
    to rate that window's training seasons."""
    from ge.config import use_season
    from ge.store.holdout import refuse_holdout

    season = ctx.season
    refuse_holdout(season, "PRJ-01a ratings")
    params = params or ratings_params(season)
    consts = consts or load_window_consts(season, ratings_root)
    cur = season_plays(ctx, season, consts)
    name = team_names(ctx)
    teams = rated_teams(ctx, cur)
    with use_season(season):
        prior = build_prior(ctx, params, consts, teams)
    table = fit_ratings(
        cur,
        teams,
        penalty=params.penalty,
        h=params.h_efficiency,
        prior=prior,
        run_penalty_scale=run_penalty_scale,
    )
    last = season_plays(ctx.prior_context(), season - 1, consts)
    both = pl.concat([last, cur]).select("posteam", "game_id", "kickoff_utc", "is_pass")
    rates = pass_rates(both, params.h_usage)
    tg = ctx.snap.collect("target_game").row(0, named=True)
    gid = str(tg["game_id"])
    home, away = name(str(tg["home_team"])), name(str(tg["away_team"]))
    feats = coa07_features(_schedules_with_target(ctx), [gid], franchise_of(ctx))
    feats = feats.with_columns(
        pl.col("team").map_elements(name, return_dtype=pl.Utf8).alias("team")
    )
    terms = offense_terms(feats)
    lines = game_lines(table, gid, home, away, rates, terms, consts)
    notes: list[str] = []
    if prior is not None:
        notes.append(
            f"G4 carryover prior (week {ctx.week}): ratings shrink toward {season - 1}'s final "
            "ratings, regressed a further 1/3 toward 0 for a new play-caller or QB"
        )
    if cur.is_empty():
        notes.append(f"no {season} plays yet: intercepts are {season - 1}'s final values")
    return GameRatings(
        gid,
        season,
        int(ctx.snap.week),
        ctx.snap.as_of,
        params,
        consts,
        table,
        rates,
        lines,
        tuple(notes),
    )


def ratings_for_game(
    game_id: str,
    as_of: dt.datetime | None = None,
    *,
    root: Path = DATA_ROOT,
    ratings_root: Path = RATINGS_FITTED_ROOT,
    registry: CoachingRegistry | None = None,
    run_penalty_scale: float = 1.0,
) -> GameRatings:
    """PRJ-01a: ratings and lines for one game, built only from snapshot(game_id, as_of)
    (rule 5). Raises for the holdout season (BT-07b) and NotImplementedError (G4) when a
    team's play-caller or QB change is unknown in weeks 1-4."""
    from ge.metrics.context import build_context
    from ge.store.holdout import refuse_holdout
    from ge.store.snapshot import snapshot

    refuse_holdout(int(game_id.split("_", 1)[0]), "PRJ-01a ratings")  # before any read
    ctx = build_context(snapshot(game_id, as_of, root=root), registry)
    return rate_context(ctx, ratings_root=ratings_root, run_penalty_scale=run_penalty_scale)
