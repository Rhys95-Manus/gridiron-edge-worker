"""`ge` command line: one command per job. Every job is a placeholder until its phase is built."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    help="Gridiron Edge worker. Data: nflverse; charting: FTN Data via nflverse.",
    no_args_is_help=True,
    add_completion=False,
)

Season = Annotated[int | None, typer.Option(help="Season year, e.g. 2024.")]
Week = Annotated[int | None, typer.Option(help="Week number.")]
AsOf = Annotated[
    str | None,
    typer.Option("--as-of", help="ISO timestamp; only data pulled at or before it is read."),
]


def _not_built(job: str, phase: str) -> None:
    raise NotImplementedError(f"ge {job}: not built yet ({phase} in docs/BUILD_PLAN.md)")


ingest = typer.Typer(
    help="Pull nflverse, NWS, Kalshi and Wikidata public data (DATA-01 to DATA-09, DATA-13).",
    no_args_is_help=True,
)
app.add_typer(ingest, name="ingest")


def _seasons(spec: str | None) -> list[int]:
    from ge.config import load_ingest
    from ge.ingest.nflverse import current_season

    if not spec:
        return list(range(load_ingest().nflverse.first_season.value, current_season() + 1))
    if "-" in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def _user_agent() -> str:
    from ge.settings import Settings

    return Settings().nws_user_agent.get_secret_value()


@ingest.command("nflverse")
def ingest_nflverse_cmd(
    seasons: Annotated[str | None, typer.Option(help="e.g. 2016-2026 or 2024,2025")] = None,
    datasets: Annotated[str | None, typer.Option(help="comma-separated; default all")] = None,
) -> None:
    """DATA-01 to DATA-05: nflverse datasets into data/raw (idempotent)."""
    from ge.ingest.nflverse import ingest_nflverse

    results = ingest_nflverse(_seasons(seasons), datasets.split(",") if datasets else None)
    for r in results:
        print(f"{r.dataset:<18} {r.season}  {r.status:<13} {r.rows:>9}  {r.detail}")
    errors = [r for r in results if r.status == "error"]
    print(
        f"\n{len(results)} pulls: "
        + ", ".join(
            f"{s} {sum(r.status == s for r in results)}"
            for s in ("written", "unchanged", "not_published", "error")
        )
    )
    print("Data: nflverse; charting: FTN Data via nflverse")
    raise typer.Exit(1 if errors else 0)


@ingest.command("stadiums")
def ingest_stadiums_cmd() -> None:
    """DATA-13: generate config/stadiums.yaml from schedules + Wikidata and print it."""
    from ge.config import load_ingest
    from ge.ingest.jobs import run_stadiums

    raise typer.Exit(run_stadiums(load_ingest(), _user_agent()))


@ingest.command("weather")
def ingest_weather_cmd(
    days: Annotated[int | None, typer.Option(help="default: nws.forecast_window_days")] = None,
) -> None:
    """DATA-06: NWS hourly forecast for outdoor games in the next N days."""
    from ge.config import load_ingest
    from ge.ingest.jobs import run_weather

    cfg = load_ingest()
    raise typer.Exit(run_weather(cfg, _user_agent(), days or cfg.nws.forecast_window_days.value))


@ingest.command("kalshi")
def ingest_kalshi_cmd(
    season: Annotated[int, typer.Option(help="Season year")],
    week: Annotated[int, typer.Option(help="Week number")],
    history: Annotated[bool, typer.Option(help="also pull trades and hourly candles")] = False,
) -> None:
    """DATA-08: discover NFL series, then pull the week's markets, rules and order books."""
    from ge.config import load_ingest
    from ge.ingest.jobs import run_kalshi

    raise typer.Exit(run_kalshi(load_ingest(), season, week, history))


@ingest.command("collect")
def ingest_collect_cmd() -> None:
    """Scheduled pull: this week's Kalshi markets, this season's nflverse data (injuries, depth
    charts, schedules, play-by-play and the other weekly game data), then weather. Logs to
    logs/collect.log; exits 1 if any step failed."""
    from ge.ingest import collect

    code = collect.run_collect(collect.default_steps(), collect.LOG_PATH)
    print(f"\ncollect exit {code}; log: {collect.LOG_PATH}")
    print("Data: nflverse; charting: FTN Data via nflverse")
    raise typer.Exit(code)


@ingest.command("fees-check")
def ingest_fees_check_cmd(
    pdf: Annotated[str | None, typer.Option(help="path to a saved fee schedule PDF")] = None,
) -> None:
    """EDG-02: alert if Kalshi's API fees for included series differ from fees.yaml, or
    (with --pdf) if the fee PDF's effective date differs."""
    from ge.config import load_ingest
    from ge.ingest.jobs import run_fees_check

    raise typer.Exit(run_fees_check(load_ingest(), pdf))


@ingest.command("report")
def ingest_report_cmd() -> None:
    """Weather-history coverage, latest injury report week and FTN join rates."""
    from ge.config import load_ingest
    from ge.ingest.jobs import run_report

    raise typer.Exit(run_report(load_ingest()))


store = typer.Typer(
    help="Point-in-time store (BT-01): DuckDB views and per-game snapshots.",
    no_args_is_help=True,
)
app.add_typer(store, name="store")


@store.command("build")
def store_build_cmd() -> None:
    """BT-01: write data/store.duckdb (a view per dataset over every version, plus games)."""
    from ge.store.db import DB_PATH, build

    counts = build()
    for name, n in counts.items():
        print(f"{name:<22} {n:>10}")
    print(f"\nwrote {DB_PATH}")
    print("Data: nflverse; charting: FTN Data via nflverse")


@store.command("snapshot")
def store_snapshot_cmd(
    game: Annotated[str, typer.Option("--game", help="nflverse game_id")],
    as_of: AsOf = None,
    pass_: Annotated[
        str,
        typer.Option("--pass", help="decision (kickoff - 24 h) or inactives (kickoff - 90 min)"),
    ] = "decision",
    closing_line_backtest: Annotated[
        bool, typer.Option("--closing-line-backtest", help="show closing lines before kickoff")
    ] = False,
) -> None:
    """BT-01: print a summary of one game's inputs as they stood at as_of."""
    import datetime as dt

    from ge.store.snapshot import ATTRIBUTION, snapshot

    when = dt.datetime.fromisoformat(as_of.replace("Z", "+00:00")) if as_of else None
    if when is not None and when.tzinfo is None:
        raise typer.BadParameter("--as-of needs a time zone, e.g. 2026-10-03T17:00:00Z")
    if pass_ not in ("decision", "inactives"):
        raise typer.BadParameter("--pass must be decision or inactives")
    snap = snapshot(game, when, pass_=pass_, closing_line_backtest=closing_line_backtest)  # type: ignore[arg-type]
    print(f"{snap.game_id}  season {snap.season} week {snap.week}")
    print(f"kickoff {snap.kickoff_utc.isoformat()}   as_of {snap.as_of.isoformat()} ({snap.pass_})")
    print("\ntables")
    for t in snap.tables:
        df = snap.collect(t)
        print(f"  {t:<20} {df.height:>8} rows {df.width:>4} cols")
    tg = snap.collect("target_game")
    if tg.height:
        cols = [
            c
            for c in (
                "away_team",
                "home_team",
                "stadium",
                "roof",
                "temp",
                "wind",
                "spread_line",
                "total_line",
            )
            if c in tg.columns
        ]
        print("\ntarget game: " + ", ".join(f"{c}={tg[c][0]}" for c in cols))
    inj = snap.collect("injuries")
    if inj.height and "report_status" in inj.columns:
        wk = inj.filter((inj["season"] == snap.season) & (inj["week"] == snap.week))
        teams = [tg["away_team"][0], tg["home_team"][0]] if tg.height else []
        mine = wk.filter(wk["team"].is_in(teams))
        print(f"\ninjury report, week {snap.week}, these two teams: {mine.height} rows")
        for status, n in sorted(
            mine.group_by("report_status").len().iter_rows(), key=lambda r: str(r[0])
        ):
            print(f"  {status or '(no game status)'}: {n}")
    print("\nlabels")
    for lb in snap.labels:
        print(f"  - {lb}")
    print("\nversions read")
    for v in snap.vintages:
        print(f"  {v}")
    print(f"\ndigest {snap.digest()}")
    print(ATTRIBUTION)


@app.command()
def metrics(
    season: Annotated[int, typer.Option(help="Season year, e.g. 2026.")],
    through_week: Annotated[
        int, typer.Option("--through-week", "--week", help="Last completed week to include.")
    ],
    as_of: AsOf = None,
) -> None:
    """Compute team, player and coaching metrics (OFF-, DEF-, PLY-, COA-) through a week."""
    import datetime as dt

    from ge.metrics.job import run_metrics

    when = dt.datetime.fromisoformat(as_of.replace("Z", "+00:00")) if as_of else None
    if when is not None and when.tzinfo is None:
        raise typer.BadParameter("--as-of needs a time zone, e.g. 2026-10-03T17:00:00Z")
    run = run_metrics(season, through_week, as_of=when)
    print(run.summary)
    print(f"\nwrote {run.folder}")


@app.command()
def fit(
    as_of: Annotated[
        str, typer.Option(help="Data cut: each dataset's latest pull at or before this time.")
    ],
    window: Annotated[
        str, typer.Option(help="S2021, S2022, S2023, S2024, live, or all (default).")
    ] = "all",
    fit_version: Annotated[str, typer.Option(help="Folder under config/params_fitted/.")] = "v1",
    fresh: Annotated[bool, typer.Option(help="Re-extract every season.")] = False,
    compare_to: Annotated[
        str | None, typer.Option(help="Earlier fit version to compare against in the report.")
    ] = None,
    data_root: Annotated[Path | None, typer.Option(hidden=True)] = None,
    work_root: Annotated[Path | None, typer.Option(hidden=True)] = None,
    out_root: Annotated[Path | None, typer.Option(hidden=True)] = None,
) -> None:
    """Phase 3e (BT-02 core): fit k, half-lives, G6 penalty, role priors, p_go, availability
    rates and the OL factor walk-forward; writes config/params_fitted/<version>/<window>.yaml.
    The hidden root options (tests) only choose where to read and write: windows and every
    read still go through the same holdout checks (BT-07b)."""
    import datetime as dt

    from ge.config import ATTRIBUTION, FITTED_ROOT
    from ge.fit.job import WORK_ROOT, run_fit
    from ge.fit.report import write_report
    from ge.ingest.raw import DATA_ROOT
    from ge.store.holdout import Window

    when = dt.datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    if when.tzinfo is None:
        raise typer.BadParameter("--as-of needs a time zone, e.g. 2026-10-08T00:00:00Z")
    windows = Window.walk_forward() if window == "all" else [Window.named(window)]
    fitted_root = out_root or FITTED_ROOT
    results = run_fit(
        windows,
        fit_version,
        when,
        root=data_root or DATA_ROOT,
        work_root=work_root or WORK_ROOT,
        out_root=fitted_root,
        fresh=fresh,
    )
    path = write_report(results, windows, fit_version, root=fitted_root, compare_to=compare_to)
    for name, out in results.items():
        print(
            f"{name}: {len(out.values)} fitted, {len(out.no_signal)} no detectable signal, "
            f"{len(out.missing)} missing"
        )
    print(f"report: {path}")
    print(ATTRIBUTION)


def _when(as_of: str | None) -> dt.datetime | None:
    if as_of is None:
        return None
    when = dt.datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    if when.tzinfo is None:
        raise typer.BadParameter("--as-of needs a time zone, e.g. 2026-10-03T17:00:00Z")
    return when


@app.command()
def ratings(
    season: Annotated[int, typer.Option(help="Season year, e.g. 2026.")],
    through_week: Annotated[
        int, typer.Option("--through-week", "--week", help="Last completed week to include.")
    ],
    as_of: AsOf = None,
    data_root: Annotated[Path | None, typer.Option(hidden=True)] = None,
    ratings_root: Annotated[Path | None, typer.Option(hidden=True)] = None,
) -> None:
    """PRJ-01a: all 32 teams ranked by rating-implied neutral-site margin, with each rating's
    standard error. The hidden root options (tests) only choose where to read."""
    from ge.config import ATTRIBUTION
    from ge.ingest.raw import DATA_ROOT
    from ge.metrics.job import anchor_game
    from ge.models.ratings import (
        RATING_TYPES,
        RATINGS_FITTED_ROOT,
        neutral_margins,
        ratings_for_game,
    )
    from ge.store.holdout import refuse_holdout

    refuse_holdout(season, "ge ratings")  # BT-07b: before any read
    root = data_root or DATA_ROOT
    game = anchor_game(season, through_week, root)
    got = ratings_for_game(
        game, _when(as_of), root=root, ratings_root=ratings_root or RATINGS_FITTED_ROOT
    )
    ranked = neutral_margins(got.table, got.pass_rate, got.consts)
    print(
        f"PRJ-01a ratings, season {season} through week {through_week} (as of "
        f"{got.as_of.isoformat()}); fit {got.params.fit_version}/{got.params.window}, "
        f"ratings constants {got.consts.version}/{got.consts.window}"
    )
    print("EPA/play ratings with approximate standard errors (penalty treated as known)")
    header = ["rank", "team", "margin", "se", "pass_rate", *RATING_TYPES]
    print("  ".join(header))
    vals, ses = got.table.values, got.table.se
    for i, r in enumerate(ranked.iter_rows(named=True), start=1):
        t = r["team"]
        cells = [f"{vals[(t, k)]:+.3f} ({ses[(t, k)]:.3f})" for k in RATING_TYPES]
        print(
            f"{i:>4}  {t:<4}  {r['margin']:+.2f}  {r['se']:.2f}  {got.pass_rate[t]:.3f}  "
            + "  ".join(cells)
        )
    for note in got.notes:
        print(f"note: {note}")
    print(ATTRIBUTION)


@app.command("ratings-fit")
def ratings_fit(
    as_of: Annotated[
        str, typer.Option(help="Data cut: each dataset's latest pull at or before this time.")
    ],
    window: Annotated[
        str, typer.Option(help="S2021, S2022, S2023, S2024, live, or all (default).")
    ] = "all",
    version: Annotated[str, typer.Option(help="Folder under config/ratings_fitted/.")] = "r1",
    data_root: Annotated[Path | None, typer.Option(hidden=True)] = None,
    out_root: Annotated[Path | None, typer.Option(hidden=True)] = None,
) -> None:
    """PRJ-01a / COA-07: fit each window's COA-07 coefficients, league constants and c;
    writes config/ratings_fitted/<version>/<window>.yaml."""
    from ge.config import ATTRIBUTION
    from ge.ingest.raw import DATA_ROOT
    from ge.models.ratings import RATINGS_FITTED_ROOT
    from ge.models.ratings_window import run_ratings_fit
    from ge.store.holdout import Window

    when = _when(as_of)
    assert when is not None
    windows = Window.walk_forward() if window == "all" else [Window.named(window)]
    paths = run_ratings_fit(
        windows,
        version,
        when,
        root=data_root or DATA_ROOT,
        out_root=out_root or RATINGS_FITTED_ROOT,
    )
    for name, path in paths.items():
        print(f"{name}: {path}")
    print(ATTRIBUTION)


@app.command("ratings-report")
def ratings_report(
    seasons: Annotated[str, typer.Option(help="Walk-forward seasons, e.g. 2021-2024.")],
    data_root: Annotated[Path | None, typer.Option(hidden=True)] = None,
    ratings_root: Annotated[Path | None, typer.Option(hidden=True)] = None,
    out_dir: Annotated[Path | None, typer.Option(hidden=True)] = None,
) -> None:
    """PRJ-01a: the Phase 4 walk-forward report (rating-implied lines vs closing lines)."""
    from ge.config import ATTRIBUTION
    from ge.ingest.raw import DATA_ROOT
    from ge.models.ratings import RATINGS_FITTED_ROOT
    from ge.models.ratings_report import REPORT_ROOT, report_settings, write_report
    from ge.store.holdout import refuse_holdout

    years = _seasons(seasons)
    for s in years:
        refuse_holdout(s, "ge ratings-report")  # BT-07b: before any read
    path = write_report(
        years,
        report_settings(),
        root=data_root or DATA_ROOT,
        ratings_root=ratings_root or RATINGS_FITTED_ROOT,
        out_dir=out_dir or REPORT_ROOT,
    )
    print(f"report: {path}")
    print(ATTRIBUTION)


@app.command()
def simulate(season: Season = None, week: Week = None, as_of: AsOf = None) -> None:
    """Run the game simulation (PRJ-02)."""
    _not_built("simulate", "Phase 5")


@app.command()
def price(season: Season = None, week: Week = None, as_of: AsOf = None) -> None:
    """Price Kalshi markets (PRJ-03 to PRJ-06)."""
    _not_built("price", "Phase 6")


@app.command()
def sync(season: Season = None, week: Week = None, as_of: AsOf = None) -> None:
    """Write projections and recommendations to Base44."""
    _not_built("sync", "Phase 9")


@app.command()
def backtest(season: Season = None, week: Week = None, as_of: AsOf = None) -> None:
    """Walk-forward backtest and Historical Performance Report (BT-01 to BT-07)."""
    _not_built("backtest", "Phase 8")


if __name__ == "__main__":
    app()
