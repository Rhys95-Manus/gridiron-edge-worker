"""PRJ-02 calibration gate, 2021-2024 (BUILD_PLAN Phase 5; plan phase5-calibration-gate.md,
rulings 2026-11-21). Read-only on a season run (data/sim_runs/<tag>/season=<S>.parquet) and the
nflverse store.

Gated, per season (G-Q1 (i)): the PRJ-02 acceptance test's league averages within the
params.yaml tolerances, on the games the run simulated (G-Q3). Definitions (ruling E14):
- points per team-game: final score including overtime;
- plays per team-game: OFF-11 qualifying plays (pass or rush, scrimmage, not G7 garbage time);
- pass rate: qualifying pass plays (sacks and scrimmage scrambles included) / qualifying plays;
- yards per pass attempt: passing yards on attempts, sacks excluded, over attempts (scrimmage
  plays; two-point tries are not plays in the simulation either, so they are out on both sides).
The simulation side uses R_PLAYS_G7, R_PASS_PLAYS_G7, R_PASS_YDS and R_PASS_ATT.

Reported, never gated: the SD of simulated margins against the actual 2016-2024 SD, the Phase 4
calibration of sim mean margin and total against results, the Phase 4 pace check, xpass/cp
agreement, ERA5 agreement and timing. 2025 is refused before any read (BT-07b)."""

from __future__ import annotations

import json
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from ge.config import FITTED_ROOT, ActiveParams, load_ingest, load_params, use_params, window_for
from ge.ingest.raw import DATA_ROOT, read_latest
from ge.metrics import plays as pf
from ge.store.holdout import refuse_holdout

RUNS_ROOT = DATA_ROOT.parent / "sim_runs"
WORK_ROOT = DATA_ROOT.parent / "fit_work"
GATE_METRICS = (
    "points_per_team_game",
    "plays_per_team_game",
    "pass_rate",
    "yards_per_pass_attempt",
)
# ruling D1 (2026-11-21): plays without the G7 filter, shown beside the gate, never gated
REPORTED_ALONGSIDE = ("plays_per_team_game_no_g7",)
_TOL_KEYS = {
    "points_per_team_game": "prj_02_tol_points_per_team_game",
    "plays_per_team_game": "prj_02_tol_plays_per_team_game",
    "pass_rate": "prj_02_tol_pass_rate",
    "yards_per_pass_attempt": "prj_02_tol_yards_per_pass_attempt",
}


def margin_sd_seasons() -> tuple[int, int]:
    """BUILD_PLAN's "actual 2016-2024 margin standard deviation (2025 is the holdout)": the BT-01
    range, first training season through the last test season."""
    b = load_params().backtest
    return int(b.bt_01_first_training_season.value), int(b.bt_01_last_test_season.value)


def tolerances() -> dict[str, float]:
    """PRJ-02: the acceptance tolerances, from params.yaml."""
    p = load_params().projection
    return {m: float(getattr(p, _TOL_KEYS[m]).value) for m in GATE_METRICS}


def _tot(df: pl.DataFrame, col: str) -> float:
    return float(df[f"home_{col}"].to_numpy().sum() + df[f"away_{col}"].to_numpy().sum())


def sim_averages(ok: pl.DataFrame) -> dict[str, float]:
    """PRJ-02 (E14): league averages over the simulated games (each game's per-run means)."""
    if ok["skip_reason"].is_not_null().any():
        raise ValueError("PRJ-02 gate: sim_averages takes simulated games only, not skipped rows")
    tg = 2 * ok.height
    return {
        "points_per_team_game": _tot(ok, "points") / tg,
        "plays_per_team_game": _tot(ok, "plays_g7") / tg,
        "pass_rate": _tot(ok, "pass_plays_g7") / _tot(ok, "plays_g7"),
        "yards_per_pass_attempt": _tot(ok, "pass_yds") / _tot(ok, "pass_att"),
        "plays_per_team_game_no_g7": _tot(ok, "plays") / tg,
    }


def _is1(c: str) -> pl.Expr:
    return (pl.col(c) == 1).fill_null(False)


def actual_averages(pbp: pl.DataFrame, sched: pl.DataFrame) -> dict[str, float]:
    """PRJ-02 (E14): the same league averages from nflverse play-by-play and schedules, over the
    schedule's games (two team-games each)."""
    tg = 2 * sched.height
    with use_params(ActiveParams(load_params(), None)):
        has_team = pl.col("posteam").is_not_null()
        q = pbp.filter(has_team & pf.qualifying())
        q_all = pbp.filter(has_team & (_is1("pass") | _is1("rush")) & pf.scrimmage())
        att = pbp.filter(has_team & _is1("pass_attempt") & ~_is1("sack") & pf.scrimmage())
    yds = float(att.filter(_is1("complete_pass"))["yards_gained"].to_numpy().sum())
    pts = float(sched["home_score"].to_numpy().sum() + sched["away_score"].to_numpy().sum())
    return {
        "points_per_team_game": pts / tg,
        "plays_per_team_game": q.height / tg,
        "pass_rate": q.filter(_is1("pass")).height / q.height,
        "yards_per_pass_attempt": yds / att.height,
        "plays_per_team_game_no_g7": q_all.height / tg,
    }


def check(sim: dict[str, float], actual: dict[str, float]) -> pl.DataFrame:
    """PRJ-02: one row per gated metric: sim, actual, diff (sim - actual), tolerance, passed
    (|diff| <= tolerance)."""
    tol = tolerances()
    rows = [
        {
            "metric": m,
            "sim": sim[m],
            "actual": actual[m],
            "diff": sim[m] - actual[m],
            "tolerance": tol[m],
            "passed": abs(sim[m] - actual[m]) <= tol[m],
        }
        for m in GATE_METRICS
    ]
    return pl.DataFrame(rows)


def simulated_games(
    sim: pl.DataFrame, expected: Sequence[str]
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """G-Q3: the run must hold every game of the season once and nothing else; returns
    (simulated rows, skipped rows)."""
    ids = sim["game_id"].to_list()
    if len(ids) != len(set(ids)):
        raise ValueError("PRJ-02 gate: the run lists a game more than once")
    missing = sorted(set(expected) - set(ids))
    if missing:
        raise ValueError(f"PRJ-02 gate: games missing from the run: {missing}")
    extra = sorted(set(ids) - set(expected))
    if extra:
        raise ValueError(f"PRJ-02 gate: games in the run not in the season: {extra}")
    ok = sim.filter(pl.col("skip_reason").is_null())
    return ok, sim.filter(pl.col("skip_reason").is_not_null())


def pooled_margin_sd(ok: pl.DataFrame) -> float:
    """Reported: the SD of every simulated run's margin across the season's games, from each
    game's run mean, run SD (population) and run count."""
    n = ok["n_runs"].to_numpy().astype(np.float64)
    m = ok["margin_mean"].to_numpy().astype(np.float64)
    s = ok["margin_sd"].to_numpy().astype(np.float64)
    grand = float((n * m).sum() / n.sum())
    return float(np.sqrt((n * (s * s + (m - grand) ** 2)).sum() / n.sum()))


def _season_schedule(season: int, data_root: Path) -> pl.DataFrame:
    s = read_latest(data_root, "schedules", season).filter(pl.col("season") == season)
    return s.sort("gameday", "gametime", "game_id")


def actual_margin_sd(seasons: Sequence[int], *, data_root: Path = DATA_ROOT) -> float:
    """Reported: the SD of actual home margins over the seasons' played games (population)."""
    for s in seasons:
        refuse_holdout(s, "PRJ-02 gate margin SD")  # before any read (BT-07b)
    parts = []
    for s in seasons:
        sc = _season_schedule(s, data_root).drop_nulls(["home_score", "away_score"])
        parts.append((sc["home_score"] - sc["away_score"]).cast(pl.Float64).to_numpy())
    return float(np.concatenate(parts).std())


def compared(ok: pl.DataFrame, sched: pl.DataFrame, pace: pl.DataFrame | None) -> pl.DataFrame:
    """The simulated games in the Phase 4 report's shape: spread = sim mean margin, total = sim
    mean total, with closing lines, results, game type and (if given) the Phase 4 pace."""
    from ge.models.ratings_report import compare_to_lines

    rated = ok.select(
        "game_id",
        "season",
        pl.col("margin_mean").alias("spread"),
        pl.col("total_mean").alias("total"),
    )
    out = compare_to_lines(rated, sched).join(
        sched.select("game_id", "game_type"), on="game_id", how="left"
    )
    if pace is not None:
        out = out.join(
            pace.select("game_id", "pace_plays", "pace_seconds"), on="game_id", how="left"
        )
    return out


@dataclass(frozen=True)
class SeasonGate:
    season: int
    games: int
    ok: pl.DataFrame
    skipped: pl.DataFrame
    sim: dict[str, float]
    actual: dict[str, float]
    checks: pl.DataFrame
    skipped_actual: dict[str, float] | None
    schedule: pl.DataFrame


def season_gate(
    tag: str, season: int, *, runs_root: Path = RUNS_ROOT, data_root: Path = DATA_ROOT
) -> SeasonGate:
    """PRJ-02: one season's gate on run `tag`."""
    refuse_holdout(season, "PRJ-02 calibration gate")  # before any read (BT-07b)
    sim = pl.read_parquet(runs_root / tag / f"season={season}.parquet")
    sched = _season_schedule(season, data_root)
    ok, skipped = simulated_games(sim, sched["game_id"].to_list())
    pbp = read_latest(data_root, "pbp", season)
    ids = ok["game_id"].to_list()
    act = actual_averages(
        pbp.filter(pl.col("game_id").is_in(ids)), sched.filter(pl.col("game_id").is_in(ids))
    )
    sk = skipped["game_id"].to_list()
    sk_act = (
        actual_averages(
            pbp.filter(pl.col("game_id").is_in(sk)), sched.filter(pl.col("game_id").is_in(sk))
        )
        if sk
        else None
    )
    s = sim_averages(ok)
    return SeasonGate(season, sim.height, ok, skipped, s, act, check(s, act), sk_act, sched)


def phase4_pace(path: Path | None = None) -> pl.DataFrame:
    """The Phase 4 report's per-game pre-game pace (combined OFF-11 plays per game, mean OFF-10
    seconds), from reports/phase4/ratings_walkforward.csv."""
    from ge.models.ratings_report import REPORT_ROOT

    p = path or REPORT_ROOT / "ratings_walkforward.csv"
    return pl.read_csv(p, infer_schema_length=None).select("game_id", "pace_plays", "pace_seconds")


def distill_agreement(season: int) -> dict[str, dict[str, float]]:
    """Reported: xpass/cp agreement with nflverse on the window's training plays, as the fit
    recorded it (data/fit_work/<fit_version>/sim/diagnostics_<window>.json)."""
    window = window_for(season)
    active = yaml.safe_load((FITTED_ROOT / "active.yaml").read_text(encoding="utf-8"))
    path = WORK_ROOT / str(active["fit_version"]) / "sim" / f"diagnostics_{window}.json"
    d = json.loads(path.read_text(encoding="utf-8"))["distill"]
    return {k: {"corr": v["corr"], "mae": v["mae"], "n": v["n"]} for k, v in d.items()}


def _fmt(x: float | None, nd: int = 3) -> str:
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{nd}f}"


def write_report(
    tag: str,
    seasons: Sequence[int],
    out_dir: Path,
    *,
    runs_root: Path = RUNS_ROOT,
    data_root: Path = DATA_ROOT,
) -> Path:
    """PRJ-02 gate report: reports/phase5/gate/<tag>/gate.md and gate_checks.csv."""
    from ge.config import ATTRIBUTION
    from ge.ingest.weather_era5 import ATTRIBUTION as WEATHER_ATTRIBUTION
    from ge.ingest.weather_era5 import schedule_agreement
    from ge.models.ratings_report import calibration, pace_breakdown

    for s in seasons:
        refuse_holdout(s, "PRJ-02 calibration gate")  # before any read (BT-07b)
    z95 = statistics.NormalDist().inv_cdf(0.975)
    gates = [season_gate(tag, s, runs_root=runs_root, data_root=data_root) for s in seasons]
    pace = phase4_pace()
    lo, hi = margin_sd_seasons()
    sd_all = actual_margin_sd(range(lo, hi + 1), data_root=data_root)
    lines = [f"# PRJ-02 calibration gate — {tag}", ""]
    lines += ["## Gated: league averages within the PRJ-02 tolerances (every season)", ""]
    lines += ["| season | metric | sim | actual | sim - actual | tolerance | pass |",
              "|---|---|---|---|---|---|---|"]  # fmt: skip
    rows = []
    for g in gates:
        for r in g.checks.iter_rows(named=True):
            rows.append({"season": g.season, **r})
            lines.append(
                f"| {g.season} | {r['metric']} | {r['sim']:.4f} | {r['actual']:.4f} | "
                f"{r['diff']:+.4f} | {r['tolerance']:g} | {'PASS' if r['passed'] else 'FAIL'} |"
            )
    verdict = all(r["passed"] for r in rows)
    lines += ["", f"**Gate: {'PASS' if verdict else 'FAIL'}** (every season, every metric).", ""]
    lines += ["Reported alongside, not gated (ruling D1): plays without the G7 filter", "",
              "| season | sim | actual | sim - actual |", "|---|---|---|---|"]  # fmt: skip
    for g in gates:
        for k in REPORTED_ALONGSIDE:
            a, b = g.sim[k], g.actual[k]
            lines.append(f"| {g.season} | {a:.4f} | {b:.4f} | {a - b:+.4f} |")
    lines.append("")
    lines += ["## Games", "", "| season | games | simulated | skipped |", "|---|---|---|---|"]
    for g in gates:
        lines.append(f"| {g.season} | {g.games} | {g.ok.height} | {g.skipped.height} |")
    for g in gates:
        if g.skipped.height:
            reasons = sorted({str(r)[:90] for r in g.skipped["skip_reason"].to_list()})
            assert g.skipped_actual is not None
            lines += ["", f"{g.season} skipped games (actuals for those games, not gated):",
                      *(f"- {k}: {_fmt(v)}" for k, v in g.skipped_actual.items()),
                      *(f"- reason: {r}" for r in reasons)]  # fmt: skip
    lines += ["", "## Reported: SD of margins", "",
              f"Actual home-margin SD {lo}-{hi} (schedules, played games): {sd_all:.3f}", "",
              "| season | sim SD (all runs) | actual SD (season) |", "|---|---|---|"]  # fmt: skip
    for g in gates:
        sc = g.schedule.drop_nulls(["home_score", "away_score"])
        a = float((sc["home_score"] - sc["away_score"]).cast(pl.Float64).to_numpy().std())
        lines.append(f"| {g.season} | {pooled_margin_sd(g.ok):.3f} | {a:.3f} |")
    comp = pl.concat([compared(g.ok, g.schedule, pace) for g in gates], how="diagonal_relaxed")
    cal = calibration(comp)
    lines += ["", "## Reported: sim mean margin and total vs results (Phase 4 calibration)", "",
              "| season | model | target | n | slope | 95% interval | intercept | intercept SE |",
              "|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for r in cal.iter_rows(named=True):
        lo_s, hi_s = r["slope"] - z95 * r["slope_se"], r["slope"] + z95 * r["slope_se"]
        lines.append(
            f"| {r['season']} | {r['model']} | {r['target']} | {r['n']} | {r['slope']:.3f} | "
            f"[{lo_s:.3f}, {hi_s:.3f}] | {r['intercept']:+.3f} | {r['intercept_se']:.3f} |"
        )
    lines += ["", "Mean sim margin - actual margin (home bias), regular season, non-neutral:", ""]
    lines += ["| season | n | mean | SE | 95% interval |", "|---|---|---|---|---|"]
    for s in seasons:
        d = comp.filter(
            (pl.col("season") == s) & (pl.col("game_type") == "REG")
            & (pl.col("location") != "Neutral")
        ).drop_nulls("spread_vs_actual")  # fmt: skip
        x = d["spread_vs_actual"].to_numpy().astype(np.float64)
        m, se = float(x.mean()), float(x.std(ddof=1) / np.sqrt(x.size))
        lines.append(
            f"| {s} | {x.size} | {m:+.3f} | {se:.3f} | [{m - z95 * se:+.3f}, {m + z95 * se:+.3f}] |"
        )
    bins = int(load_params().projection.prj_01_pace_bins.value)
    binned, slopes = pace_breakdown(comp, bins)
    lines += ["", "## Reported: pace check (Phase 4 definition; total_diff = sim total - line)", "",
              "| bin | n | pace min | pace max | sim - line | sim - actual |",
              "|---|---|---|---|---|---|"]  # fmt: skip
    for r in binned.iter_rows(named=True):
        lines.append(
            f"| {r['bin']} | {r['n']} | {r['pace_min']:.1f} | {r['pace_max']:.1f} | "
            f"{r['total_diff_mean']:+.3f} | {r['total_vs_actual_mean']:+.3f} |"
        )
    lines += ["", "| season | n | total slope per play | 95% interval | spread slope (control) |",
              "|---|---|---|---|---|"]  # fmt: skip
    for r in slopes.iter_rows(named=True):
        t, tse = r["total_slope"], r["total_slope_se"]
        lines.append(
            f"| {r['season']} | {r['n']} | {t:+.4f} | [{t - z95 * tse:+.4f}, {t + z95 * tse:+.4f}] "
            f"| {r['spread_slope']:+.4f} |"
        )
    lines += ["", "## Reported: xpass / cp agreement with nflverse (training plays, window)", "",
              "| season | model | corr | MAE | n |", "|---|---|---|---|---|"]  # fmt: skip
    for s in seasons:
        for k, v in distill_agreement(s).items():
            lines.append(f"| {s} | {k} | {v['corr']:.3f} | {v['mae']:.4f} | {int(v['n'])} |")
    mph = float(load_ingest().open_meteo.mph_to_kmh.value)
    ag = pl.concat(
        [
            schedule_agreement(
                g.schedule, read_latest(data_root, "era5_game_window", g.season), mph_to_kmh=mph
            )
            for g in gates
        ],
        how="diagonal_relaxed",
    )
    lines += ["", "## Reported: ERA5 vs schedules temp and wind", "", ag.write_csv(), ""]
    lines += ["## Reported: timing", "", "| season | runs per game | sim s/game mean | max | "
              "build s/game mean |", "|---|---|---|---|---|"]  # fmt: skip
    for g in gates:
        runs = int(g.ok["n_runs"].to_numpy().max())
        sim_s = g.ok["sim_seconds"].to_numpy().astype(np.float64)
        build_s = g.ok["build_seconds"].to_numpy().astype(np.float64)
        lines.append(
            f"| {g.season} | {runs} | {sim_s.mean():.2f} | {sim_s.max():.2f} | "
            f"{build_s.mean():.1f} |"
        )
    lines += ["", ATTRIBUTION, WEATHER_ATTRIBUTION, ""]
    out = out_dir / tag
    out.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_csv(out / "gate_checks.csv")
    path = out / "gate.md"
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path
