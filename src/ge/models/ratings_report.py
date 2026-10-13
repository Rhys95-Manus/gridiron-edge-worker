"""PRJ-01a Phase 4 report: walk-forward rating-implied lines against closing lines.

For each walk-forward season (2021-2024, never 2025) every game is rated from its own
snapshot; closing spread_line and total_line are read afterwards, only here, after checking
their sign convention. The report also shows whether totals error tracks team pace (the
formula uses league drives per team-game) and a run-penalty sensitivity check. Report only:
nothing here changes the model.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import polars as pl

from ge.config import REPO_ROOT
from ge.ingest.raw import DATA_ROOT
from ge.models.ratings import RATINGS_FITTED_ROOT

if TYPE_CHECKING:
    from ge.metrics.coaching import CoachingRegistry
    from ge.metrics.context import MetricContext
    from ge.store.holdout import Window

REPORT_ROOT = REPO_ROOT / "reports" / "phase4"


class LineSignError(ValueError):
    """The closing lines don't follow the sign convention the comparison assumes."""


def check_line_signs(schedules: pl.DataFrame) -> pl.DataFrame:
    """PRJ-01a report: per season, corr(spread_line, home_score - away_score) and
    corr(total_line, home_score + away_score). Raises LineSignError unless both are above
    0 in every season, so spread_line is home-favoured-positive before any comparison."""
    d = schedules.drop_nulls(["home_score", "away_score", "spread_line", "total_line"])
    rows = []
    for season in sorted(set(d["season"].to_list())):
        s = d.filter(pl.col("season") == season)
        margin = (s["home_score"] - s["away_score"]).cast(pl.Float64).to_numpy()
        points = (s["home_score"] + s["away_score"]).cast(pl.Float64).to_numpy()
        cs = float(np.corrcoef(s["spread_line"].cast(pl.Float64).to_numpy(), margin)[0, 1])
        ct = float(np.corrcoef(s["total_line"].cast(pl.Float64).to_numpy(), points)[0, 1])
        if not (cs > 0 and ct > 0):
            raise LineSignError(
                f"season {season}: corr(spread_line, home - away) = {cs:.3f}, corr(total_line, "
                f"home + away) = {ct:.3f}; the comparison assumes both are positive"
            )
        rows.append({"season": int(season), "n": s.height, "corr_spread": cs, "corr_total": ct})
    if not rows:
        raise LineSignError("no games with closing lines and final scores to check")
    return pl.DataFrame(rows)


@dataclass(frozen=True)
class ReportSettings:
    """The report's own settings (decision log 2026-10-12): the seasons and run-penalty
    scales of the sensitivity check, and the number of pace bins."""

    sensitivity_seasons: tuple[int, ...]
    scales: tuple[float, ...]
    pace_bins: int


def report_settings() -> ReportSettings:
    """PRJ-01a: from params.yaml (decision log 2026-10-12): sensitivity seasons S2023 to
    S2024 with the run-side penalty at 0.5x, 1x and 2x, and the number of pace bins."""
    from ge.config import load_params

    p = load_params().projection
    first = int(p.prj_01_sensitivity_first_season.value)
    last = int(p.prj_01_sensitivity_last_season.value)
    return ReportSettings(
        sensitivity_seasons=tuple(range(first, last + 1)),
        scales=(
            float(p.prj_01_sensitivity_low_scale.value),
            1.0,
            float(p.prj_01_sensitivity_high_scale.value),
        ),
        pace_bins=int(p.prj_01_pace_bins.value),
    )


def walk_forward(
    seasons: Sequence[int],
    *,
    weeks: Sequence[int] | None = None,
    root: Path = DATA_ROOT,
    ratings_root: Path = RATINGS_FITTED_ROOT,
    registry: CoachingRegistry | None = None,
) -> pl.DataFrame:
    """PRJ-01a: one row per game of each season (or of `weeks` only): rating-implied spread
    and total with standard errors, window, penalty, half-lives, both teams' pace (OFF-10,
    OFF-11) as of the same snapshot; or the skip reason."""
    from ge.ingest.raw import read_latest
    from ge.metrics.context import build_context
    from ge.models.ratings import rate_context
    from ge.store.holdout import refuse_holdout
    from ge.store.snapshot import snapshot

    for s in seasons:
        refuse_holdout(s, "PRJ-01a walk-forward")  # BT-07b: before any read
    rows: list[dict[str, object]] = []
    for s in seasons:
        sched = read_latest(root, "schedules", s)
        if weeks is not None:
            sched = sched.filter(pl.col("week").is_in(list(weeks)))
        for r in sched.sort("gameday", "gametime", "game_id").iter_rows(named=True):
            base: dict[str, object] = {
                "season": s,
                "week": int(r["week"]),
                "game_id": r["game_id"],
                "game_type": r["game_type"],
                "home_team": r["home_team"],
                "away_team": r["away_team"],
            }
            try:
                ctx = build_context(snapshot(r["game_id"], root=root), registry)
                g = rate_context(ctx, ratings_root=ratings_root)
            except NotImplementedError as exc:
                rows.append({**base, "skip_reason": str(exc)})
                continue
            pace_plays, pace_seconds = _pace(ctx, g.lines.home_team, g.lines.away_team)
            rows.append(
                {
                    **base,
                    "as_of": g.as_of.isoformat(),
                    "home_points": g.lines.home_points,
                    "away_points": g.lines.away_points,
                    "spread": g.lines.spread,
                    "spread_se": g.lines.spread_se,
                    "total": g.lines.total,
                    "total_se": g.lines.total_se,
                    "home_offset": g.lines.home_offset,
                    "away_offset": g.lines.away_offset,
                    "window": g.params.window,
                    "fit_version": g.params.fit_version,
                    "penalty": g.params.penalty,
                    "h_efficiency": g.params.h_efficiency,
                    "h_usage": g.params.h_usage,
                    "consts_version": g.consts.version,
                    "c": g.consts.c,
                    "league_drives": g.consts.league_drives,
                    "pace_plays": pace_plays,
                    "pace_seconds": pace_seconds,
                    "notes": "; ".join(g.notes),
                }
            )
    return pl.DataFrame(rows, schema=_RATED_SCHEMA)


_RATED_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "season": pl.Int64,
    "week": pl.Int64,
    "game_id": pl.Utf8,
    "game_type": pl.Utf8,
    "home_team": pl.Utf8,
    "away_team": pl.Utf8,
    "as_of": pl.Utf8,
    "home_points": pl.Float64,
    "away_points": pl.Float64,
    "spread": pl.Float64,
    "spread_se": pl.Float64,
    "total": pl.Float64,
    "total_se": pl.Float64,
    "home_offset": pl.Float64,
    "away_offset": pl.Float64,
    "window": pl.Utf8,
    "fit_version": pl.Utf8,
    "penalty": pl.Float64,
    "h_efficiency": pl.Float64,
    "h_usage": pl.Float64,
    "consts_version": pl.Utf8,
    "c": pl.Float64,
    "league_drives": pl.Float64,
    "pace_plays": pl.Float64,
    "pace_seconds": pl.Float64,
    "notes": pl.Utf8,
    "skip_reason": pl.Utf8,
}


def _pace(ctx: MetricContext, home: str, away: str) -> tuple[float | None, float | None]:
    """Combined OFF-11 plays per game and mean OFF-10 seconds per snap of the two teams,
    shrunk, from the same context (None when either metric can't be computed)."""
    from ge.metrics.registry import shrunk

    def values(spec_id: str, stat: str) -> dict[str, float] | None:
        try:
            df = shrunk(ctx, spec_id, stat)
        except NotImplementedError:
            return None
        if "all" in set(df["cell"].to_list()):
            df = df.filter(pl.col("cell") == "all")
        return {
            str(e): float(v)
            for e, v in df.select("entity_id", "shrunk").iter_rows()
            if v is not None
        }

    plays = values("OFF-11", "plays_per_game")
    secs = values("OFF-10", "seconds_per_play")
    pp = (
        plays[home] + plays[away] if plays is not None and home in plays and away in plays else None
    )
    ps = (
        (secs[home] + secs[away]) / 2
        if secs is not None and home in secs and away in secs
        else None
    )
    return pp, ps


def compare_to_lines(rated: pl.DataFrame, schedules: pl.DataFrame) -> pl.DataFrame:
    """PRJ-01a report: joins closing lines and results onto `rated`: spread_diff = rating
    spread - spread_line, total_diff = rating total - total_line, and the same against the
    actual margin and total."""
    lines = schedules.select(
        "game_id",
        *(["location"] if "location" in schedules.columns else []),
        pl.col("spread_line").cast(pl.Float64),
        pl.col("total_line").cast(pl.Float64),
        "home_score",
        "away_score",
    ).unique("game_id", keep="first")
    margin = (pl.col("home_score") - pl.col("away_score")).cast(pl.Float64)
    points = (pl.col("home_score") + pl.col("away_score")).cast(pl.Float64)
    return rated.join(lines, on="game_id", how="left").with_columns(
        (pl.col("spread") - pl.col("spread_line")).alias("spread_diff"),
        (pl.col("total") - pl.col("total_line")).alias("total_diff"),
        (pl.col("spread") - margin).alias("spread_vs_actual"),
        (pl.col("total") - points).alias("total_vs_actual"),
    )


def _phase() -> pl.Expr:
    return (
        pl.when(pl.col("game_type") == "REG")
        .then(pl.lit("REG"))
        .otherwise(pl.lit("POST"))
        .alias("phase")
    )


def summarise(compared: pl.DataFrame) -> pl.DataFrame:
    """PRJ-01a report: per season (and per week): n, mean absolute and mean signed
    difference for spread and total. Regular season and postseason are separate rows."""
    d = compared.drop_nulls(["spread_diff", "total_diff"]).with_columns(_phase())
    aggs = [
        pl.len().alias("n"),
        pl.col("spread_diff").abs().mean().alias("spread_mad"),
        pl.col("spread_diff").mean().alias("spread_bias"),
        pl.col("total_diff").abs().mean().alias("total_mad"),
        pl.col("total_diff").mean().alias("total_bias"),
    ]
    by_season = (
        d.group_by("season", "phase")
        .agg(aggs)
        .with_columns(pl.lit(None, dtype=pl.Int64).alias("week"))
    )
    by_week = d.group_by("season", "phase", "week").agg(aggs)
    cols = ["season", "phase", "week", "n", "spread_mad", "spread_bias", "total_mad", "total_bias"]
    return (
        pl.concat(
            [
                by_season.select(cols),
                by_week.with_columns(pl.col("week").cast(pl.Int64)).select(cols),
            ]
        )
        .with_columns(pl.col("n").cast(pl.Int64))
        .sort(["season", "phase", "week"], descending=[False, True, False], nulls_last=False)
    )


def _ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Slope and its standard error, with an intercept."""
    slope, se, _, _ = _ols_full(x, y)
    return slope, se


def _ols_full(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float, float]:
    """Slope, its standard error, intercept, its standard error (OLS with an intercept)."""
    n = len(x)
    xbar = float(x.mean())
    xc = x - xbar
    sxx = float(xc @ xc)
    slope = float(xc @ (y - y.mean())) / sxx
    icpt = float(y.mean()) - slope * xbar
    resid = y - icpt - slope * x
    if n <= 2:
        return slope, math.nan, icpt, math.nan
    s2 = float(resid @ resid) / (n - 2)
    return slope, math.sqrt(s2 / sxx), icpt, math.sqrt(s2 * (1 / n + xbar * xbar / sxx))


def calibration(compared: pl.DataFrame) -> pl.DataFrame:
    """PRJ-01a report: per season, the closing line and the actual result each regressed on
    the model spread (margin = home - away) and on the model total: slope and intercept with
    standard errors. A slope of 1 and intercept of 0 means the model's numbers are on the
    target's scale."""
    d = compared.drop_nulls(
        ["spread", "total", "spread_line", "total_line", "home_score", "away_score"]
    )
    rows = []
    for season in sorted(set(d["season"].to_list())):
        s = d.filter(pl.col("season") == season)
        margin = (s["home_score"] - s["away_score"]).cast(pl.Float64).to_numpy()
        points = (s["home_score"] + s["away_score"]).cast(pl.Float64).to_numpy()
        targets = {
            ("spread", "closing_line"): s["spread_line"].cast(pl.Float64).to_numpy(),
            ("spread", "actual"): margin,
            ("total", "closing_line"): s["total_line"].cast(pl.Float64).to_numpy(),
            ("total", "actual"): points,
        }
        for (model, target), y in targets.items():
            x = s[model].cast(pl.Float64).to_numpy()
            slope, slope_se, icpt, icpt_se = _ols_full(x, y)
            rows.append(
                {
                    "season": int(season),
                    "model": model,
                    "target": target,
                    "n": s.height,
                    "slope": slope,
                    "slope_se": slope_se,
                    "intercept": icpt,
                    "intercept_se": icpt_se,
                }
            )
    return pl.DataFrame(rows)


def home_edge(compared: pl.DataFrame) -> pl.DataFrame:
    """PRJ-01a report: per season, non-neutral games only: the model's combined COA-07 home
    effect in points (league drives x c x (home offset - away offset), each game with its own
    window's constants), the closing-line home edge (mean spread_line) and the mean actual
    home margin."""
    d = compared.filter(pl.col("location") != "Neutral").drop_nulls(
        ["home_offset", "away_offset", "c", "league_drives"]
    )
    return (
        d.with_columns(
            (
                pl.col("league_drives")
                * pl.col("c")
                * (pl.col("home_offset") - pl.col("away_offset"))
            ).alias("_pts"),
            (pl.col("home_score") - pl.col("away_score")).cast(pl.Float64).alias("_margin"),
        )
        .group_by("season")
        .agg(
            pl.len().alias("n"),
            pl.col("_pts").mean().alias("model_coa07_home_points"),
            pl.col("spread_line").mean().alias("closing_line_home_edge"),
            pl.col("_margin").mean().alias("actual_home_margin"),
        )
        .with_columns(pl.col("n").cast(pl.Int64))
        .sort("season")
    )


def diagnostic_window(season: int) -> Window:
    """The window whose training seasons the c diagnostic reads for a walk-forward season."""
    from ge.store.holdout import Window

    return Window.for_test_season(season)


def pace_breakdown(compared: pl.DataFrame, bins: int) -> tuple[pl.DataFrame, pl.DataFrame]:
    """PRJ-01a report (descriptive): games in `bins` equal-count bins of combined pace (both
    teams' OFF-11 plays per game) with mean signed total_diff against the line and against
    the actual total, and per season the OLS slope of total_diff on combined pace with its
    standard error; spread_diff alongside as a control."""
    order = ["pace_plays", "game_id"] if "game_id" in compared.columns else ["pace_plays"]
    d = compared.drop_nulls(["pace_plays", "total_diff", "spread_diff"]).sort(order)
    n = d.height
    d = d.with_columns(((pl.int_range(pl.len()) * bins) // max(n, 1)).alias("bin"))
    has_seconds = "pace_seconds" in d.columns
    binned = (
        d.group_by("bin")
        .agg(
            pl.len().alias("n"),
            pl.col("pace_plays").min().alias("pace_min"),
            pl.col("pace_plays").max().alias("pace_max"),
            pl.col("pace_plays").mean().alias("pace_plays_mean"),
            (
                pl.col("pace_seconds").mean() if has_seconds else pl.lit(None, dtype=pl.Float64)
            ).alias("pace_seconds_mean"),
            pl.col("total_diff").mean().alias("total_diff_mean"),
            pl.col("total_vs_actual").mean().alias("total_vs_actual_mean"),
            pl.col("spread_diff").mean().alias("spread_diff_mean"),
        )
        .with_columns(pl.col("n").cast(pl.Int64))
        .sort("bin")
    )
    rows = []
    for season in sorted(set(d["season"].to_list())):
        s = d.filter(pl.col("season") == season)
        x = s["pace_plays"].to_numpy().astype(np.float64)
        ts, tse = _ols(x, s["total_diff"].to_numpy().astype(np.float64))
        ss, sse = _ols(x, s["spread_diff"].to_numpy().astype(np.float64))
        rows.append(
            {
                "season": int(season),
                "n": s.height,
                "total_slope": ts,
                "total_slope_se": tse,
                "spread_slope": ss,
                "spread_slope_se": sse,
            }
        )
    return binned, pl.DataFrame(rows)


def next_week_errors(
    plays: pl.DataFrame,
    teams: Sequence[str],
    *,
    penalty: float,
    h: float,
    scales: Sequence[float],
) -> pl.DataFrame:
    """PRJ-01a sensitivity (report only): for each week w >= 2, ratings fitted on earlier
    weeks with the run-side penalty at each scale predict week w's plays (pass plays with the
    pass prediction, run plays with the run prediction). Returns scale, side, n, mse.
    `plays` columns: week, game_id, kickoff_utc, posteam, defteam, is_pass, epa, offset; games
    ago are counted within each training slice."""
    from ge.models.ratings import fit_ratings

    weeks = sorted(set(plays["week"].to_list()))
    rows = []
    for scale in scales:
        sq: dict[str, list[float]] = {"pass": [], "run": []}
        for w in weeks:
            if w < 2:
                continue
            train = plays.filter(pl.col("week") < w)
            if train.is_empty():
                continue
            order = (
                train.select("posteam", "game_id", "kickoff_utc")
                .unique()
                .sort(["posteam", "kickoff_utc", "game_id"], descending=[False, True, True])
                .with_columns(
                    pl.int_range(pl.len()).over("posteam").cast(pl.Float64).alias("g_off")
                )
                .select("posteam", "game_id", "g_off")
            )
            t = fit_ratings(
                train.join(order, on=["posteam", "game_id"]),
                teams,
                penalty=penalty,
                h=h,
                prior=None,
                run_penalty_scale=scale,
            )
            for off, de, is_pass, epa, offset in (
                plays.filter(pl.col("week") == w)
                .select("posteam", "defteam", "is_pass", "epa", "offset")
                .iter_rows()
            ):
                kind = "pass" if is_pass else "run"
                pred = (
                    (t.int_pass if kind == "pass" else t.int_run)
                    + t.values[(off, f"off_{kind}")]
                    + t.values[(de, f"def_{kind}")]
                    + offset
                )
                sq[kind].append((epa - pred) ** 2)
        for kind in ("pass", "run"):
            n = len(sq[kind])
            rows.append(
                {
                    "scale": float(scale),
                    "side": kind,
                    "n": n,
                    "mse": math.fsum(sq[kind]) / n if n else math.nan,
                }
            )
    return pl.DataFrame(rows)


def _sensitivity_plays(season: int, root: Path, coefs: dict[str, float]) -> pl.DataFrame:
    """One walk-forward season's qualifying plays with COA-07 offsets, for the sensitivity
    check (read after the fact; each week is predicted only from earlier weeks)."""
    from ge.config import window_for
    from ge.ingest.raw import read_latest
    from ge.metrics import plays as pf
    from ge.models.ratings import coa07_features, offense_terms, term_offset
    from ge.store.known_at import with_kickoff

    window = window_for(season)
    if window is None or not window.startswith("S"):
        raise ValueError(
            f"PRJ-01a: the sensitivity check runs on walk-forward seasons, not {season}"
        )
    pbp = read_latest(root, "pbp", season)
    sched = read_latest(root, "schedules", season)
    try:
        prev = read_latest(root, "schedules", season - 1)
        both = pl.concat([prev, sched], how="diagonal_relaxed")
    except FileNotFoundError:
        both = sched
    q = pbp.filter(pf.qualifying() & pl.col("epa").is_not_null())
    terms = offense_terms(coa07_features(both, q["game_id"].unique().to_list()))
    kick = with_kickoff(sched).select("game_id", "kickoff_utc")
    out = (
        q.select(
            pl.col("week").cast(pl.Int64),
            "game_id",
            "posteam",
            "defteam",
            (pl.col("pass") == 1).fill_null(False).alias("is_pass"),
            pl.col("epa").cast(pl.Float64),
        )
        .join(kick, on="game_id", how="left")
        .join(terms, on=["game_id", "posteam", "defteam"], how="left")
    )
    return out.with_columns(term_offset(out, coefs))


def _md(df: pl.DataFrame, digits: int = 3) -> str:
    """A Markdown table."""

    def cell(v: object) -> str:
        if v is None:
            return ""
        if isinstance(v, float):
            return "" if math.isnan(v) else f"{v:.{digits}f}"
        return str(v)

    head = "| " + " | ".join(df.columns) + " |"
    rule = "| " + " | ".join("---" for _ in df.columns) + " |"
    body = ["| " + " | ".join(cell(v) for v in r) + " |" for r in df.iter_rows()]
    return "\n".join([head, rule, *body])


def write_report(
    seasons: Sequence[int],
    settings: ReportSettings,
    *,
    weeks: Sequence[int] | None = None,
    root: Path = DATA_ROOT,
    ratings_root: Path = RATINGS_FITTED_ROOT,
    registry: CoachingRegistry | None = None,
    out_dir: Path = REPORT_ROOT,
) -> Path:
    """PRJ-01a: reports/phase4/ratings_walkforward.md and ratings_walkforward.csv (one row
    per game)."""
    import datetime as dt

    from ge.config import ATTRIBUTION
    from ge.ingest.raw import read_latest
    from ge.models.ratings import load_window_consts, ratings_params
    from ge.models.ratings_window import MissingTrainingData, c_diagnostic
    from ge.store.holdout import refuse_holdout

    for s in (*seasons, *settings.sensitivity_seasons):
        refuse_holdout(s, "PRJ-01a report")  # BT-07b: before any read
    rated = walk_forward(
        seasons, weeks=weeks, root=root, ratings_root=ratings_root, registry=registry
    )
    sched = pl.concat([read_latest(root, "schedules", s) for s in seasons], how="diagonal_relaxed")
    signs = check_line_signs(sched)  # before any comparison
    compared = compare_to_lines(rated, sched)
    ok = compared.filter(pl.col("skip_reason").is_null())
    summary = summarise(ok)
    bins, slopes = pace_breakdown(ok, settings.pace_bins)
    net_home = (
        ok.with_columns(_phase(), (pl.col("home_offset") - pl.col("away_offset")).alias("net"))
        .group_by("season", "phase")
        .agg(
            pl.len().alias("n"),
            pl.col("net").mean().alias("mean_home_minus_away"),
            pl.col("net").std().alias("sd"),
        )
        .with_columns(pl.col("n").cast(pl.Int64))
        .sort(["season", "phase"], descending=[False, True])
    )

    calib = calibration(ok)
    edge = home_edge(ok)
    c_rows = []
    for s in seasons:
        c = load_window_consts(s, ratings_root)
        if c.data_as_of is None:
            raise ValueError(
                f"PRJ-01a: {c.version}/{c.window} has no data cut for the c diagnostic"
            )
        cut = dt.datetime.fromisoformat(c.data_as_of)
        w = diagnostic_window(s)
        try:
            c_rows.append(
                {"season": s, "window": w.name, **c_diagnostic(w, cut, root=root), "note": ""}
            )
        except MissingTrainingData as exc:  # shown in the report, never silently dropped
            c_rows.append({"season": s, "window": w.name, "note": f"unavailable: {exc}"})
    c_diag = pl.DataFrame(c_rows, infer_schema_length=None)

    windows = []
    for s in seasons:
        p = ratings_params(s)
        c = load_window_consts(s, ratings_root)
        windows.append(
            {
                "season": s,
                "window": c.window,
                "constants": c.version,
                "phase3e_fit": f"{p.fit_version}/{p.window}",
                "penalty": p.penalty,
                "h_efficiency": p.h_efficiency,
                "h_usage": p.h_usage,
                **{f"{t}": c.coa07[t] for t in c.coa07},
                **{f"{t}_se": c.coa07_se[t] for t in c.coa07_se},
                "c": c.c,
                "c_se": c.c_se,
                "league_epa_per_play": c.league_epa,
                "league_points_per_drive": c.league_ppd,
                "league_drives_per_team_game": c.league_drives,
            }
        )
    sens_parts = []
    for s in settings.sensitivity_seasons:
        p = ratings_params(s)
        c = load_window_consts(s, ratings_root)
        plays = _sensitivity_plays(s, root, dict(c.coa07))
        teams = sorted(set(plays["posteam"].to_list()) | set(plays["defteam"].to_list()))
        e = next_week_errors(
            plays, teams, penalty=p.penalty, h=p.h_efficiency, scales=settings.scales
        )
        sens_parts.append(
            e.with_columns(
                pl.lit(s).alias("season"),
                pl.col("scale")
                .map_elements(lambda v: f"{v:g}x", return_dtype=pl.Utf8)
                .alias("run_penalty"),
            ).select("season", "run_penalty", "side", "n", "mse")
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "ratings_walkforward.csv"
    compared.sort("season", "week", "game_id").write_csv(csv_path)
    skipped = rated.filter(pl.col("skip_reason").is_not_null())
    years = ", ".join(str(s) for s in seasons)
    parts = [
        "# Phase 4: rating-implied lines against closing lines (PRJ-01a)",
        "",
        f"Seasons {years}, walk-forward (each season rated with its own window's fits; never "
        "the 2025 holdout, BT-07b). Every game is rated only from its own snapshot "
        "(snapshot(game_id), decision-time as_of). Closing lines and results are read only "
        "here, after the fact. Report only: no pass/fail; beating the market is Phase 8's "
        "question.",
        "",
        f"Rated: {rated.height - skipped.height} games; skipped: {skipped.height} "
        "(listed at the end).",
        "",
        "## Sign convention",
        "",
        "nflverse schedules `spread_line` is positive when the home team is favoured: home team "
        "favoured = positive. Checked in every season before any comparison (both "
        "correlations must be positive):",
        "",
        _md(signs),
        "",
        "So spread_diff = rating spread (home minus away points) - spread_line, and total_diff "
        "= rating total - total_line, with no sign flip. Points are final scores including "
        "overtime and non-offensive scores, as the closing lines and Kalshi settle them: "
        "Kalshi's FOOTBALLSPREAD contract terms count all scoring in overtime periods toward "
        "the final margin, and FOOTBALLTOTALS counts overtime for all markets unless stated "
        "otherwise (contract terms retrieved 2026-10-12 from assets.kalshi.com).",
        "",
        "## Differences by season",
        "",
        "Mean absolute difference (mad) and mean signed difference (bias); regular season "
        "(REG) and postseason (POST) separately.",
        "",
        _md(summary.filter(pl.col("week").is_null()).drop("week")),
        "",
        "## Differences by week",
        "",
        _md(summary.filter(pl.col("week").is_not_null())),
        "",
        "## Calibration",
        "",
        "Per season, the closing line and the actual result regressed on the model spread "
        "(home minus away) and on the model total, with approximate standard errors. Slope 1 "
        "and intercept 0 would mean the model's numbers sit on the target's scale; a slope "
        "below 1 against the actual result means the model's spreads or totals are too spread "
        "out.",
        "",
        _md(calib, digits=4),
        "",
        "## Window constants",
        "",
        "COA-07 coefficients (home +1/-1/0; rest days, travel km and |time-zone hours| as "
        "offense minus defense), the points-per-drive slope c, the league constants, and the "
        "Phase 3e G6 penalty and half-lives each window reads. Standard errors are "
        "approximate (penalty treated as known, residuals homoskedastic); no significance "
        "conclusions are drawn from them alone.",
        "",
        _md(pl.DataFrame(windows), digits=6),
        "",
        "Home, travel and time zone are strongly collinear (the away offense nearly always "
        "travels further), so the coefficients are not read one at a time. Their combined "
        "COA-07 effect in the rated games, home offense's offset minus away offense's (EPA/play):",
        "",
        _md(net_home, digits=4),
        "",
        "The same combined effect in points (league drives per team-game x c x (home offset - "
        "away offset), each game with its window's constants) next to the closing-line home "
        "edge (mean spread_line) and the mean actual home margin, non-neutral games:",
        "",
        _md(edge, digits=3),
        "",
        "### c diagnostic",
        "",
        "Over each window's training seasons: league qualifying plays per drive, c as fitted, "
        "and c refit with turnover plays (interceptions and lost fumbles) left out of x. "
        "Report only; the model uses c as fitted.",
        "",
        _md(c_diag, digits=4),
        "",
        "Expected points = league drives per team-game x (league points per drive + c x "
        "(expected EPA/play - league EPA/play)). The Phase 3e penalty was cross-validated for "
        "one rating per team; with pass and run rated separately the run ratings rest on fewer "
        "plays and shrink harder (see the sensitivity check below). It is not refit here.",
        "",
        "## Totals against pace (report only)",
        "",
        "The totals use league drives per team-game, so team pace is ignored. Games in "
        f"{settings.pace_bins} equal-count bins of combined pace (both teams' OFF-11 plays per "
        "game, shrunk, as of the game's snapshot; mean OFF-10 seconds per snap alongside):",
        "",
        _md(bins),
        "",
        "Per season, the OLS slope of total_diff (and of spread_diff, as a control) on combined "
        "pace, with standard errors:",
        "",
        _md(slopes, digits=4),
        "",
        "## Run-penalty sensitivity (report only)",
        "",
        "Ratings refit for each week from earlier weeks only, with the run-side penalty at "
        + ", ".join(f"{v:g}x" for v in settings.scales)
        + " the fitted value (pass unchanged); mean squared next-week EPA/play prediction "
        "error for pass plays and run plays separately. The model is not changed on the basis "
        "of this check.",
        "",
        _md(pl.concat(sens_parts), digits=5) if sens_parts else "(no seasons requested)",
        "",
        "## Skipped games",
        "",
        _md(skipped.select("season", "week", "game_id", "skip_reason"))
        if skipped.height
        else "None.",
        "",
        f"Per-game rows: {csv_path.name}.",
        "",
        ATTRIBUTION,
        "",
    ]
    path = out_dir / "ratings_walkforward.md"
    path.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    return path
