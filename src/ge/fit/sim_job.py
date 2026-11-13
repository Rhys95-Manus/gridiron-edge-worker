"""`ge fit-sim`: the Phase 5 per-window fits, written as fit v5 = v4 plus these keys.

For each window (S2021..S2024 on 2016..S-1, live on 2016-2024), from that window's seasons only:
- PRJ-02 league level h_L, the field-goal-attempt-vs-punt model (ruling C8) and the 4th-down
  go model (ruling 2026-10-31)
- PRJ-02 rating-tilt slopes (five components; SEs clustered by team-game, B8), fitted on the
  leave-one-out predictor (ruling 2026-10-24), with the as-written fit beside it for the report
- PRJ-02 xpass(state) and cp(state), distilled from nflverse's own values (D4)
- MTC-05 weather coefficients on completion, deep-attempt share and field-goal make (with
  distance and ENV-02 altitude), ENV-01 surface on explosive rate and yards per carry (B4, D1,
  D2, D5); no-signal effects are listed and contribute zero; wind and gusts hidden by the joint
  fit stop the run (B4)
- PLY-14 P(plays | Questionable) and P(plays | Doubtful) (D7)

Each season is extracted once into data/fit_work/<version>/sim/season=<s>/ through a Reader
limited to 2016-2024 (as Phase 3e does), and each window reads only its own seasons
(BT-07a / BT-07b); 2025 is never read. Diagnostics for the Phase 5 report are written beside
the work files.

Data: nflverse; charting: FTN Data via nflverse; expected points: ffopportunity (ffverse) via
nflverse; data license not stated by the source. Weather: Open-Meteo.com (ERA5), CC BY 4.0."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shutil
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from ge.config import FITTED_ROOT, ActiveParams, load_params, use_params
from ge.fit.availability import _rate
from ge.fit.clustered import logit_clustered, no_signal, ols_clustered, season_dummies
from ge.fit.distill import design, distill_fit
from ge.fit.history import Reader, season_view
from ge.fit.job import _commit
from ge.fit.league_level import choose_league_half_life
from ge.fit.sim_fits import (
    FgPuntFit,
    GoFit,
    SticksFit,
    fit_fg_vs_punt,
    fit_fourth_go,
    fit_sticks,
    fourth_go_rows,
    league_week_series,
    sticks_rows,
)
from ge.fit.sim_inputs import (
    game_status_rows,
    surface_class,
    tilt_rows,
    weather_rows,
)
from ge.fit.sim_write import write_v5
from ge.fit.tilt import TILT_COMPONENTS, TILT_SIDE, TiltFit, fit_tilt_slope
from ge.fit.weather import OUTCOME_FACTORS, factor_correlations, fit_weather_effects
from ge.ingest.raw import DATA_ROOT
from ge.ingest.stadiums import load_stadiums, stadium_for_game
from ge.metrics import plays as pf
from ge.metrics.coaching import load_registry
from ge.metrics.context import MetricContext
from ge.models.sim.league import CORE_COLUMNS, LeagueTables, build_league, save_league
from ge.models.sim.rules import game_rule
from ge.models.sim.settings import load_sim
from ge.store.holdout import Window, holdout_season

WORK_ROOT = DATA_ROOT.parent / "fit_work"
PBP_COLUMNS = [
    "game_id",
    "season",
    "week",
    "play_type",
    "posteam",
    "defteam",
    "down",
    "ydstogo",
    "yardline_100",
    "qtr",
    "game_seconds_remaining",
    "half_seconds_remaining",
    "score_differential",
    "wp",
    "posteam_timeouts_remaining",
    "defteam_timeouts_remaining",
    "xpass",
    "cp",
    "pass",
    "rush",
    "pass_attempt",
    "complete_pass",
    "sack",
    "interception",
    "fumble_lost",
    "qb_scramble",
    "qb_kneel",
    "qb_spike",
    "two_point_attempt",
    "air_yards",
    "yards_after_catch",
    "yards_gained",
    "epa",
    "pass_location",
    "field_goal_attempt",
    "field_goal_result",
    "kick_distance",
]
TABLES = (
    "weeks",
    "kicks",
    "tilt",
    "completion",
    "deep_attempt",
    "fg_make",
    "surface",
    "xpass",
    "cp",
    "wp",
    "status",
    "core",
)
LEAGUE_ROOT = DATA_ROOT.parent / "sim_league"


@dataclass(frozen=True)
class LeagueLevelFit:
    h_l: float
    losses: dict[float, float]
    weeks: int
    first_week: tuple[int, int]
    last_week: tuple[int, int]


def fit_league_level(weeks: pl.DataFrame) -> LeagueLevelFit:
    """PRJ-02 league level: h_L for one window from its training weeks."""
    h, losses = choose_league_half_life(
        weeks["points_per_team_game"].to_numpy(), weeks["team_games"].to_numpy()
    )
    return LeagueLevelFit(
        h_l=h,
        losses=losses,
        weeks=weeks.height,
        first_week=(int(weeks["season"][0]), int(weeks["week"][0])),
        last_week=(int(weeks["season"][-1]), int(weeks["week"][-1])),
    )


# ---------------------------------------------------------------- per-season extraction


def _elevations(sched: pl.DataFrame) -> dict[str, float]:
    """ENV-02: the stadium elevation (config/stadiums.yaml, city-level proxy) per game."""
    stadiums = load_stadiums()
    out: dict[str, float] = {}
    for gid, sid, name in sched.select("game_id", "stadium_id", "stadium").iter_rows():
        st = stadium_for_game(stadiums, sid, name) or {}
        if st.get("elevation_m") is not None:
            out[gid] = float(st["elevation_m"])
    return out


def _is1(col: str) -> pl.Expr:
    return (pl.col(col) == 1).fill_null(False)


def _surface_rows(plays: pl.DataFrame, sched: pl.DataFrame) -> pl.DataFrame:
    """ENV-01 (D2): qualifying plays with the game's surface class; explosive = run of 10+ or
    completed pass of 20+ (glossary; params OFF-12 and DEF-06)."""
    p = load_params()
    run_min = float(p.offense.off_12_explosive_run_min_yards.value)
    pass_min = float(p.defense.def_06_explosive_pass_min_yards.value)
    cls = sched.select(
        "game_id",
        pl.col("surface")
        .map_elements(surface_class, return_dtype=pl.String)
        .alias("surface_class"),
    )
    d = (
        plays.filter(pf.qualifying())
        .join(cls, on="game_id")
        .filter(pl.col("surface_class").is_not_null())
    )
    designed = _is1("rush") & ~_is1("qb_scramble")
    return d.select(
        pl.col("season").cast(pl.Int64),
        (pl.col("game_id") + "|" + pl.col("posteam")).alias("team_game"),
        (pl.col("surface_class") == "artificial").cast(pl.Float64).alias("artificial"),
        (
            (designed & (pl.col("yards_gained") >= run_min))
            | (_is1("complete_pass") & (pl.col("yards_gained") >= pass_min))
        )
        .cast(pl.Float64)
        .alias("explosive"),
        designed.alias("designed_run"),
        pl.col("yards_gained").cast(pl.Float64),
    )


def _status(reader: Reader, season: int) -> pl.DataFrame:
    """PLY-14 (D7) rows through the production snapshot (players crosswalk, team weeks)."""
    snap = season_view(reader, season)
    ctx = MetricContext(snap, season, None, load_registry())
    inj = ctx.table("injuries")
    snaps = ctx.snaps
    if "season" in inj.columns:
        inj = inj.filter(pl.col("season") == season)
    if "season" in snaps.columns:
        snaps = snaps.filter(pl.col("season") == season)
    team_weeks = ctx.games.select("team", pl.col("week").cast(pl.Int64)).unique()
    return game_status_rows(inj, snaps, team_weeks).with_columns(pl.lit(season).alias("season"))


def extract_sim_season(reader: Reader, season: int, out: Path) -> None:
    """Write season `season`'s Phase 5 fit inputs under `out`."""
    with use_params(ActiveParams(load_params(), None)):
        sched = reader.frame("schedules", season).filter(pl.col("season") == season)
        cols = sorted(set(PBP_COLUMNS) | set(CORE_COLUMNS))
        plays = reader.frame("pbp", season, cols)
        windows = reader.frame("era5_game_window", season)
        tables: dict[str, pl.DataFrame] = {}
        tables["weeks"] = sched.select("season", "week", "home_score", "away_score")
        tables["kicks"] = plays.filter(
            (pl.col("down") == 4) & pl.col("play_type").is_in(["field_goal", "punt"])
        ).select(
            "game_id",
            pl.col("season").cast(pl.Int64),
            pl.col("week").cast(pl.Int64),
            pl.col("yardline_100").cast(pl.Float64),
            (pl.col("play_type") == "field_goal").cast(pl.Float64).alias("fg_attempt"),
        )
        tables["tilt"] = tilt_rows(plays)
        for name, rows in weather_rows(plays, windows, _elevations(sched)).items():
            tables[name] = rows
        tables["surface"] = _surface_rows(plays, sched)
        tables["xpass"] = plays.select("season", *_feats("xpass"), "xpass").drop_nulls()
        tables["wp"] = plays.select("season", *_feats("wp"), "wp").drop_nulls()
        tables["cp"] = plays.select("season", *_feats("cp"), "cp").drop_nulls()
        tables["status"] = _status(reader, season)
        tables["core"] = plays.select(CORE_COLUMNS)  # PRJ-02 league level (E10)
    out.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.write_parquet(out / f"{name}.parquet", statistics=False)
    (out / "done.json").write_text(
        json.dumps({"season": season, "digest": reader.digest()}, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )


def _feats(model: str) -> tuple[str, ...]:
    from ge.fit.distill import DISTILL_FEATURES

    return DISTILL_FEATURES[model]


def prepare_sim(
    work: Path, seasons: Iterable[int], root: Path, as_of: dt.datetime, fresh: bool
) -> None:
    store = str(Path(root).resolve())
    for s in sorted(set(seasons)):
        d = work / f"season={s}"
        done = d / "done.json"
        if done.exists() and not fresh:
            meta = json.loads(done.read_text())
            if meta.get("data_as_of") == as_of.isoformat() and meta.get("store") == store:
                continue
        if d.exists():
            shutil.rmtree(d)
        reader = Reader(root, Window.live(), as_of)
        extract_sim_season(reader, s, d)
        meta = json.loads(done.read_text())
        meta.update({"data_as_of": as_of.isoformat(), "store": store})
        done.write_text(json.dumps(meta, sort_keys=True), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- per-window fits


@dataclass
class SimOut:
    values: dict[str, dict[str, Any]]
    missing: dict[str, str]
    no_signal: dict[str, str]
    diagnostics: dict[str, Any]

    def put(
        self, key: str, spec_id: str, value: float, method: str, seasons: list[int], n: int
    ) -> None:
        self.values[key] = {
            "spec_id": spec_id,
            "status": "fitted",
            "value": float(value),
            "method": method,
            "seasons": sorted(seasons),
            "n": int(n),
            "initial_value": None,
        }


def _cat(work: Path, name: str, seasons: Iterable[int]) -> pl.DataFrame:
    parts = [pl.read_parquet(work / f"season={s}" / f"{name}.parquet") for s in seasons]
    parts = [p for p in parts if p.height]
    return pl.concat(parts, how="diagonal_relaxed") if parts else pl.DataFrame()


@dataclass(frozen=True)
class _Coef:
    coef: float
    se: float
    no_signal: bool
    n: int


def _effect(out: SimOut, key: str, spec_id: str, f: Any, method: str, seasons: list[int]) -> None:
    """A coefficient with its clustered SE; a no-signal coefficient is listed, not used."""
    out.put(key + "/se", spec_id, f.se, method + " (SE clustered by team-game)", seasons, f.n)
    if f.no_signal:
        out.no_signal[key] = (
            f"95% interval includes 0: {f.coef:.6g} (SE {f.se:.3g}); contributes zero (BT-02)"
        )
    else:
        out.put(key, spec_id, f.coef, method, seasons, f.n)


def record_tilt(
    out: SimOut, fit: TiltFit, kind: str, seasons: list[int], *, confidence: float
) -> bool:
    """PRJ-02 rating tilt: store a slope and its SE. A slope whose interval at `confidence`
    includes 0 is listed as no-signal and contributes zero (BT-02, ruling 2026-10-24); its SE is
    still stored. Returns whether it was no-signal."""
    key = f"fit:PRJ-02/tilt/{fit.component}"
    method = (
        f"PRJ-02 rating tilt: {kind} of {fit.component} on the offense's realized "
        f"{TILT_SIDE[fit.component]} EPA/play in the game, the play itself left out (ruling "
        "2026-10-24), season intercepts"
    )
    out.put(key + "/se", "PRJ-02", fit.se, method + " (SE clustered by team-game)", seasons, fit.n)
    ns = no_signal(fit.slope, fit.se, confidence)
    if ns:
        out.no_signal[key] = (
            f"95% interval includes 0: {fit.slope:.6g} (SE {fit.se:.3g}); contributes zero "
            "(BT-02, ruling 2026-10-24)"
        )
    else:
        out.put(key, "PRJ-02", fit.slope, method, seasons, fit.n)
    return ns


def record_fourth_go(out: SimOut, fit: GoFit, seasons: list[int]) -> None:
    """Rulings 2026-10-31, 2026-11-01 and 2026-11-12: the go model's terms (A.GO_TERMS) as fit
    keys; counts and approximate SEs go to the diagnostics."""
    from ge.models.sim.arrays import GO_TERMS, go_key

    m = (
        "rulings 2026-10-31, 2026-11-01, 2026-11-12: logistic P(go for it) on every 4th-down "
        "decision (G7 garbage time included), one term per distance x field cell + "
        "score_differential + ln(ydstogo / L) in the last distance bin + one term per trailing "
        "bin x late-time bin, h_L-weighted"
    )
    coefs = (*fit.cell, fit.score_differential, fit.long_ln_togo, *fit.late)
    for t, b in zip(GO_TERMS, coefs, strict=True):
        out.put(go_key(t), "PRJ-02", b, m, seasons, fit.n)
    out.diagnostics["fourth_go"] = asdict(fit)


def record_sticks(out: SimOut, fit: SticksFit, seasons: list[int]) -> None:
    """Ruling 2026-11-12 (S-1): the spot-short q per kind (A.STICKS_KINDS) as fit keys; O, E,
    the unclamped value and the counts go to the diagnostics."""
    from ge.models.sim.arrays import STICKS_KINDS, sticks_key

    m = (
        "ruling 2026-11-12 (S-1): P(a gain exactly on the line to gain is spotted one yard "
        "short) = 1 - observed / expected gains on the line, the expected share from reference "
        "distances in the same distance bin, downs 1-3, clamped to [0, 1], h_L-weighted"
    )
    for k, q, n in zip(STICKS_KINDS, fit.q, fit.n, strict=True):
        out.put(sticks_key(k), "PRJ-02", q, m, seasons, n)
    out.diagnostics["sticks"] = {
        "raw": list(fit.raw),
        "observed": list(fit.observed),
        "expected": list(fit.expected),
        "n": list(fit.n),
        "n_eff": list(fit.n_eff),
    }


def fit_sim_window(work: Path, w: Window) -> SimOut:
    seasons = list(w.seasons)
    out = SimOut({}, {}, {}, {})
    conf = float(load_params().fitting.bt_02_no_signal_confidence.value)
    min_events = int(load_params().fitting.bt_02_min_events.value)

    # PRJ-02 league level and C8
    weeks = league_week_series(_cat(work, "weeks", seasons))
    ll = fit_league_level(weeks)
    out.put(
        "fit:PRJ-02/h_l",
        "PRJ-02",
        ll.h_l,
        "PRJ-02 league level: h_L with the smallest "
        "MSE predicting weekly league points per team-game",
        seasons,
        ll.weeks,
    )
    out.diagnostics["h_l"] = asdict(ll)
    kicks = _cat(work, "kicks", seasons).join(
        weeks.select("season", "week", "week_index"), on=["season", "week"]
    )
    fg: FgPuntFit = fit_fg_vs_punt(kicks, target_index=weeks.height, h=ll.h_l)
    m = "ruling C8: logistic P(field-goal attempt | not going for it) on yardline_100, h_L-weighted"
    out.put("fit:PRJ-02/fg_vs_punt/intercept", "PRJ-02", fg.intercept, m, seasons, fg.n)
    out.put("fit:PRJ-02/fg_vs_punt/slope", "PRJ-02", fg.slope, m, seasons, fg.n)
    out.put(
        "fit:PRJ-02/fg_vs_punt/intercept/se",
        "PRJ-02",
        fg.intercept_se,
        m + " (approx.)",
        seasons,
        fg.n,
    )
    out.put(
        "fit:PRJ-02/fg_vs_punt/slope/se", "PRJ-02", fg.slope_se, m + " (approx.)", seasons, fg.n
    )
    out.diagnostics["fg_vs_punt"] = asdict(fg)
    core = _cat(work, "core", seasons).join(
        weeks.select("season", "week", "week_index"), on=["season", "week"]
    )
    go = load_sim().fourth_go
    with use_params(ActiveParams(load_params(), None)):  # G7 bounds for COA-02's row set
        go_rows = fourth_go_rows(core)
    gf = fit_fourth_go(
        go_rows,
        target_index=weeks.height,
        h=ll.h_l,
        togo_upper=go.togo_upper.value,
        yardline_upper=go.yardline_upper.value,
        trail_upper=go.trail_upper.value,
        late_seconds_upper=go.late_seconds_upper.value,
    )
    record_fourth_go(out, gf, seasons)
    sticks = load_sim().sticks
    with use_params(ActiveParams(load_params(), None)):  # G7 bounds, as the league tables
        st_rows = sticks_rows(core)
    sf = fit_sticks(
        st_rows,
        target_index=weeks.height,
        h=ll.h_l,
        togo_min=sticks.togo_min.value,
        togo_max=sticks.togo_max.value,
        distance_upper=sticks.distance_upper.value,
        min_gap=sticks.min_gap.value,
        min_expected=sticks.min_expected.value,
    )
    record_sticks(out, sf, seasons)

    # PRJ-02 rating tilt (leave-one-out, ruling 2026-10-24) + as-written comparison
    tilt = _cat(work, "tilt", seasons)
    out.diagnostics["tilt"] = {}
    for comp, kind in TILT_COMPONENTS:
        rows = tilt.filter(pl.col("component") == comp)
        fit = fit_tilt_slope(rows, comp)
        written = fit_tilt_slope(rows.with_columns(pl.col("x_written").alias("x")), comp)
        events = fit.events if fit.events is not None else fit.n
        key = f"fit:PRJ-02/tilt/{comp}"
        if kind == "logistic" and min(events, fit.n - events) < min_events:
            out.missing[key] = f"{events} events, fewer than the {min_events}-event minimum"
            continue
        ns = record_tilt(out, fit, kind, seasons, confidence=conf)
        out.diagnostics["tilt"][comp] = {
            "slope": fit.slope,
            "no_signal": ns,
            "se": fit.se,
            "se_classical": fit.se_classical,
            "n": fit.n,
            "clusters": fit.clusters,
            "written_slope": written.slope,
            "written_se": written.se,
        }

    # PRJ-02 xpass / cp
    out.diagnostics["distill"] = {}
    for model in ("xpass", "cp", "wp"):
        X, terms, used = design(_cat(work, model, seasons), model)
        target = used[model].to_numpy().astype(np.float64)
        d = distill_fit(X, target, terms)
        dm = f"ruling D4: fractional logistic distilled from nflverse {model}"
        for t, b in zip(d.terms, d.coef, strict=True):
            out.put(f"fit:PRJ-02/{model}/{t}", "PRJ-02", float(b), dm, seasons, d.n)
        out.diagnostics["distill"][model] = asdict(d.agreement) | {"n": d.n}

    # MTC-05 / ENV weather and surface
    out.diagnostics["weather"] = {}
    for outcome in OUTCOME_FACTORS:
        rows = _cat(work, outcome, seasons)
        extra = ("distance", "altitude") if outcome == "fg_make" else ()
        fits = fit_weather_effects(rows, outcome, extra)  # raises WindGustsMasked (B4)
        for name, f in fits.items():
            if name == "distance":
                continue  # a covariate of the FG model; the baseline comes from the league level
            sid = "ENV-02" if name == "altitude" else "MTC-05"
            wm = f"MTC-05: joint logistic of {outcome}, season intercepts"
            _effect(out, f"fit:{sid}/{outcome}/{name}", sid, f, wm, seasons)
        out.diagnostics["weather"][outcome] = {
            n: {
                "coef": e.coef,
                "se": e.se,
                "se_classical": e.se_classical,
                "no_signal": e.no_signal,
                "n": e.n,
                "clusters": e.clusters,
            }
            for n, e in fits.items()
        }
        if outcome == "completion":
            out.diagnostics["factor_correlations"] = {
                f"{a}~{b}": r for (a, b), r in factor_correlations(rows).items()
            }
    surf = _cat(work, "surface", seasons)
    out.diagnostics["surface"] = {}
    for outcome, rows, fitter in (
        ("explosive", surf, logit_clustered),
        ("yards_per_carry", surf.filter(pl.col("designed_run")), ols_clustered),
    ):
        ycol = "explosive" if outcome == "explosive" else "yards_gained"
        r = rows.drop_nulls(["season", "team_game", "artificial", ycol])
        dummies, _ = season_dummies(r["season"].to_numpy())
        X = np.column_stack([dummies, r["artificial"].to_numpy()])
        sfit = fitter(X, r[ycol].to_numpy().astype(np.float64), r["team_game"].to_numpy())
        coef, se = float(sfit.coef[-1]), float(sfit.se[-1])
        ns = no_signal(coef, se, conf)
        kind = "logistic" if fitter is logit_clustered else "least squares"
        sm = f"ENV-01: {kind} of {outcome} on artificial surface, season intercepts"
        key = f"fit:ENV-01/{outcome}/artificial"
        _effect(out, key, "ENV-01", _Coef(coef, se, ns, sfit.n), sm, seasons)
        out.diagnostics["surface"][outcome] = {
            "coef": coef,
            "se": se,
            "no_signal": ns,
            "n": sfit.n,
        }

    # PLY-14 game-status play rates
    status = _cat(work, "status", seasons)
    out.diagnostics["status"] = {}
    for st in ("Questionable", "Doubtful"):
        rf = _rate(status.filter(pl.col("status") == st)["played"].to_list(), min_events)
        key = f"fit:PLY-14/game_status/{st}"
        if rf.value is None:
            out.missing[key] = rf.reason or "missing"
        else:
            out.put(
                key,
                "PLY-14",
                rf.value,
                "ruling D7: share of offensive players listed "
                f"{st} who had an offensive snap that week",
                seasons,
                rf.n,
            )
        out.diagnostics["status"][st] = {"rate": rf.value, "n": rf.n}
    return out


def run_sim_fit(
    windows: list[Window],
    as_of: dt.datetime,
    *,
    base: str = "v4",
    version: str = "v5",
    root: Path = DATA_ROOT,
    work_root: Path = WORK_ROOT,
    out_root: Path = FITTED_ROOT,
    fresh: bool = False,
    league_root: Path = LEAGUE_ROOT,
    log: Callable[[str], None] = print,
) -> dict[str, SimOut]:
    work = work_root / version / "sim"
    log(f"extracting seasons {sorted({s for w in windows for s in w.seasons})}")
    prepare_sim(work, [s for w in windows for s in w.seasons], root, as_of, fresh)
    commit = _commit()
    results: dict[str, SimOut] = {}
    for w in windows:
        log(f"fitting {w.name}")
        out = fit_sim_window(work, w)
        digest = hashlib.sha256(
            "\n".join(
                f"{s}:{json.loads((work / f'season={s}' / 'done.json').read_text())['digest']}"
                for s in w.seasons
            ).encode()
        ).hexdigest()
        write_v5(
            out_root,
            w.name,
            values=out.values,
            missing=out.missing,
            no_signal=out.no_signal,
            data_digest=digest,
            code_commit=commit,
            base=base,
            version=version,
            data_as_of=as_of,
        )
        (work / f"diagnostics_{w.name}.json").write_text(
            json.dumps(out.diagnostics, indent=1, default=str), encoding="utf-8", newline="\n"
        )
        log(f"league tables {w.name}")
        tables = window_league(work, w, out)
        save_league(tables, league_root / version / f"{w.name}.npz")
        results[w.name] = out
    return results


def window_league(work: Path, w: Window, out: SimOut) -> LeagueTables:
    """PRJ-02 league level for a window: its training plays weighted by its fitted h_L, w
    counted from the test season's first week (the live window: the week after 2024's last)."""
    seasons = list(w.seasons)
    weeks = league_week_series(_cat(work, "weeks", seasons))
    core = _cat(work, "core", seasons).join(
        weeks.select("season", "week", "week_index"), on=["season", "week"]
    )
    s = load_sim().league
    rule_season = w.test_season if w.test_season is not None else holdout_season() + 1
    return build_league(
        core,
        target_index=weeks.height,
        h_l=float(out.values["fit:PRJ-02/h_l"]["value"]),
        min_events=int(s.min_category_events.value),
        punt_bucket_yards=int(s.punt_bucket_yards.value),
        fg_miss_bucket_yards=int(s.fg_miss_bucket_yards.value),
        late_kickoff_seconds=int(s.late_kickoff_seconds.value),
        two_minute_seconds=game_rule("two_minute_warning_seconds", rule_season),
    )
