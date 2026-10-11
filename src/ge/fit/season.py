"""Phase 3e per-season extraction: everything the fitters need from one training season, read
through the production metric code (season_view + MetricContext, initial params pinned) and
written to data/fit_work/<fit_version>/season=<s>/ as Parquet.

- units/: every summarise() input (capture_units), gap arms (DEF-10, DEF-13, PLY-17, PLY-19)
  and DEF-04's per-game actual and expected totals, one file per (spec, stat, kind)
- games: (team, game_id, week, g) for the season (g = games ago from the season's end)
- g6: qualifying plays for the G6 ridge; fourth: COA-02 4th-down decisions with p_go features
- ol: dropbacks with sacks and the offense's missing OFF-17 starters (MTC-03)
- practice: injury-report rows by practice status, and whether he played that week (PLY-14)
- shares, listed: per player-team game snap shares, and weeks listed on a report or RES (PLY-14
  return factor)
- missed: player-weeks for PRJ-06 (played the team's previous game, on its roster this week)
- slots: section 4 slot per player-game (usage rank before the game; depth chart in week 1)
- wopr, def08: rows for PLY-04 WOPR and DEF-08 on/off, computed whole within each half

Window-independent: the fit for season S reads only seasons before S from here.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import polars as pl

from ge.config import ActiveParams, load_params, use_params
from ge.fit.history import Reader, season_view
from ge.metrics import plays as pf
from ge.metrics.coaching import P_GO_FEATURES, fourth_downs, load_registry
from ge.metrics.context import MetricContext
from ge.metrics.engine import CapturedUnits, capture_units
from ge.metrics.offense import OL_POSITIONS
from ge.metrics.player import _listed_weeks
from ge.metrics.registry import REGISTRY, raw
from ge.metrics.roles import assign, depth_ranks, histories, last_season_snaps, usage_by_game
from ge.metrics.slots import SLOT_COUNTS

PRACTICE_LABELS = {
    "Did Not Participate In Practice": "DNP",
    "Limited Participation in Practice": "Limited",
    "Full Participation in Practice": "Full",
}


def unit_file(spec_id: str, stat: str, kind: str) -> str:
    return f"{spec_id}__{stat}__{kind}.parquet"


def _write(df: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path, statistics=False)


def extract_season(reader: Reader, season: int, out: Path) -> None:
    """Write season `season`'s fitting inputs under `out` (see module docstring)."""
    with use_params(ActiveParams(load_params(), None)):
        snap = season_view(reader, season)
        ctx = MetricContext(snap, season, None, load_registry())
        if ctx.table("pbp").is_empty():
            # A season the store doesn't hold (e.g. a fixture slice): nothing to fit from.
            out.mkdir(parents=True, exist_ok=True)
            (out / "done.json").write_text(
                json.dumps({"season": season, "window": reader.window.name, "empty": True}),
                encoding="utf-8",
            )
            return
        with capture_units() as sink:
            for sid in sorted(REGISTRY):
                try:
                    raw(ctx, sid)
                except NotImplementedError:
                    continue  # PAID metrics
        _write_units(sink, season, out / "units")
        games = ctx.games.select("team", "game_id", "week", "g").sort("team", "week", "game_id")
        _write(games.with_columns(pl.lit(season).alias("season")), out / "games.parquet")
        _write(_g6(ctx), out / "g6.parquet")
        _write(_fourth(ctx), out / "fourth.parquet")
        _write(_ol(ctx), out / "ol.parquet")
        _write(_practice(ctx), out / "practice.parquet")
        shares, listed = _shares(ctx)
        _write(shares, out / "shares.parquet")
        _write(listed, out / "listed.parquet")
        _write(_missed(ctx, shares), out / "missed.parquet")
        _write(_slots(ctx), out / "slots.parquet")
        _write(_wopr(ctx), out / "wopr.parquet")
        _write(_def08(ctx), out / "def08.parquet")
    (out / "done.json").write_text(
        json.dumps({"season": season, "window": reader.window.name}), encoding="utf-8"
    )


def _write_units(sink: list[CapturedUnits], season: int, folder: Path) -> None:
    """One file per (spec, stat, kind); a metric called from another (PLY-02 -> PLY-01) gives
    the same capture twice: the first is kept."""
    seen: set[tuple[str, str, str]] = set()
    for cu in sink:
        kind = (
            "gap" if cu.entity_type == "gap" else "ratio" if cu.entity_type == "ratio" else "units"
        )
        key = (cu.spec_id, cu.stat, kind)
        if key in seen:
            continue
        seen.add(key)
        u = cu.units
        for col in ("d", "c"):
            if kind == "units" and col not in u.columns:
                u = u.with_columns(pl.lit(1.0).alias(col))
        u = u.with_columns(pl.lit(season).alias("season"))
        _write(u.sort(u.columns), folder / unit_file(*key))


def _g6(ctx: MetricContext) -> pl.DataFrame:
    return (
        ctx.plays.filter(pf.qualifying() & pl.col("epa").is_not_null())
        .select(
            "game_id",
            pl.col("week").cast(pl.Int64),
            "posteam",
            "defteam",
            (pl.col("posteam") == pl.col("home_team")).cast(pl.Int64).alias("is_home"),
            pl.col("epa").cast(pl.Float64),
        )
        .sort("game_id", "posteam", "defteam", "epa")
    )


def _fourth(ctx: MetricContext) -> pl.DataFrame:
    return (
        fourth_downs(ctx.plays)
        .select(
            "game_id",
            "posteam",
            pl.col("g_off").cast(pl.Float64).alias("g"),
            "go",
            *(pl.col(f).cast(pl.Float64) for f in P_GO_FEATURES),
        )
        .sort("game_id", "posteam", "g", "go", *P_GO_FEATURES)
    )


def _team_game_order(ctx: MetricContext) -> dict[str, list[tuple[int, str]]]:
    out: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for team, gid, week in ctx.games.select("team", "game_id", "week").iter_rows():
        out[team].append((int(week), gid))
    return {t: sorted(v) for t, v in out.items()}


def _ol(ctx: MetricContext) -> pl.DataFrame:
    """MTC-03 rows: each dropback (OFF-15's dropback), sack 0/1, and the offense's missing
    starting linemen: OFF-17's starters (the n OL with the most offensive snaps over the
    team's previous `lookback` games) with no offensive snap in this game. A team's first game
    (no previous games) is left out."""
    o = load_params().offense
    n_ol, look = int(o.off_17_starting_ol_count.value), int(o.off_17_starter_lookback_games.value)
    s = ctx.snaps.filter(pl.col("position").is_in(list(OL_POSITIONS)))
    snaps: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for team, gid, pid, n in s.select(
        "team", "game_id", "gsis_id", pl.col("offense_snaps").fill_null(0).cast(pl.Float64)
    ).iter_rows():
        snaps[(team, gid)][pid] = n
    missing = []
    for team, games in _team_game_order(ctx).items():
        for i, (_, gid) in enumerate(games):
            prev = games[max(0, i - look) : i]
            if not prev:
                continue
            tot: dict[str, float] = defaultdict(float)
            for _, pg in prev:
                for pid, n in snaps.get((team, pg), {}).items():
                    tot[pid] += n
            starters = sorted(tot, key=lambda p: (-tot[p], p))[:n_ol]
            now = snaps.get((team, gid), {})
            missing.append((team, gid, sum(1 for p in starters if now.get(p, 0.0) <= 0)))
    miss = pl.DataFrame(
        missing, schema={"posteam": pl.Utf8, "game_id": pl.Utf8, "missing": pl.Int64}, orient="row"
    )
    db = ctx.plays.filter(pf.dropback() & pl.col("posteam").is_not_null()).select(
        "game_id", "posteam", "defteam", pl.col("sack").fill_null(0).cast(pl.Int64)
    )
    return (
        db.join(miss, on=["posteam", "game_id"], how="inner")
        .with_columns(pl.lit(ctx.season).alias("season"))
        .sort("game_id", "posteam", "defteam", "sack", "missing")
    )


def _played_weeks(ctx: MetricContext) -> pl.DataFrame:
    s = ctx.snaps
    if s.is_empty():
        return pl.DataFrame(schema={"gsis_id": pl.Utf8, "team": pl.Utf8, "week": pl.Int64})
    snaps = (
        pl.col("offense_snaps").fill_null(0)
        + pl.col("defense_snaps").fill_null(0)
        + pl.col("st_snaps").fill_null(0)
    )
    return s.filter(snaps > 0).select("gsis_id", "team", pl.col("week").cast(pl.Int64)).unique()


def _practice(ctx: MetricContext) -> pl.DataFrame:
    """PLY-14 base-rate rows (ruling 2026-10-08): every injury-report row with a DNP / Limited
    / Full practice status, whatever its game designation, in a week the team played; played =
    any snap that week."""
    inj = ctx.table("injuries")
    if inj.is_empty():
        return pl.DataFrame(schema={"practice": pl.Utf8, "played": pl.Boolean})
    team_weeks = ctx.games.select("team", pl.col("week").cast(pl.Int64)).unique()
    rows = (
        inj.filter(pl.col("gsis_id").is_not_null())
        .with_columns(
            pl.col("practice_status")
            .replace_strict(PRACTICE_LABELS, default=None, return_dtype=pl.Utf8)
            .alias("practice"),
            pl.col("week").cast(pl.Int64),
        )
        .filter(pl.col("practice").is_not_null())
        .select("gsis_id", "team", "week", "practice")
        .unique()
        .join(team_weeks, on=["team", "week"], how="semi")
    )
    played = _played_weeks(ctx).with_columns(pl.lit(True).alias("played"))
    return (
        rows.join(played, on=["gsis_id", "team", "week"], how="left")
        .with_columns(pl.col("played").fill_null(False))
        .select("practice", "played", "gsis_id", "team", "week")
        .sort("team", "week", "gsis_id", "practice")
    )


def _shares(ctx: MetricContext) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Per player-team and team game (in week order): his offensive snap share (0 when he had
    no offensive snap) and his weekly-roster position; plus the weeks he was listed (injury
    report or RES, as PLY-14's return flag requires)."""
    s = ctx.snaps.filter(pl.col("offense_snaps").fill_null(0) > 0).select(
        "gsis_id",
        "team",
        "game_id",
        (pl.col("offense_snaps") / pl.col("team_offense_snaps")).cast(pl.Float64).alias("share"),
    )
    pos = ctx.positions
    order = _team_game_order(ctx)
    rows = []
    mine: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for pid, team, gid, sh in s.iter_rows():
        mine[(pid, team)][gid] = sh
    for (pid, team), got in sorted(mine.items()):
        for i, (week, gid) in enumerate(order.get(team, [])):
            rows.append((pid, team, i, week, gid, got.get(gid, 0.0), gid in got, pos.get(pid)))
    shares = pl.DataFrame(
        rows,
        schema={
            "gsis_id": pl.Utf8,
            "team": pl.Utf8,
            "t": pl.Int64,
            "week": pl.Int64,
            "game_id": pl.Utf8,
            "share": pl.Float64,
            "played": pl.Boolean,
            "position": pl.Utf8,
        },
        orient="row",
    )
    listed = pl.DataFrame(
        sorted(_listed_weeks(ctx)),
        schema={"gsis_id": pl.Utf8, "team": pl.Utf8, "week": pl.Int64},
        orient="row",
    )
    return shares, listed


def _missed(ctx: MetricContext, shares: pl.DataFrame) -> pl.DataFrame:
    """PRJ-06 rows: per team game after its first, players who played the previous team game
    (an offensive snap) and are on the team's weekly roster that week (any status), at QB / RB /
    WR / TE by roster position; missed = no offensive snap in this game. Byes don't count as
    games; a player cut or traded is off the roster and left out. prev_dropback_share: his share
    of the team's dropbacks in that previous game (PRJ-06's QB pool, spec synced 2026-10-10:
    plays from scrimmage, garbage time kept, credited to the dropback QB)."""
    schema = {
        "position": pl.Utf8,
        "missed": pl.Boolean,
        "prev_dropback_share": pl.Float64,
        "prev_snap_share": pl.Float64,
    }
    rw = ctx.table("rosters_weekly")
    if rw.is_empty() or shares.is_empty():
        return pl.DataFrame(schema=schema)
    roster = (
        rw.filter(pl.col("gsis_id").is_not_null() & pl.col("position").is_in(list(SLOT_COUNTS)))
        .select("gsis_id", "team", pl.col("week").cast(pl.Int64), "position")
        .unique(["gsis_id", "team", "week"], keep="first", maintain_order=True)
    )
    prev = shares.filter(pl.col("played")).select(
        "gsis_id",
        "team",
        (pl.col("t") + 1).alias("t"),
        pl.col("game_id").alias("prev_game"),
        pl.col("share").alias("prev_snap_share"),  # his offensive snap share there (PRJ-06)
    )
    now = shares.select("gsis_id", "team", "t", "week", "game_id", "played")
    return (
        prev.join(now, on=["gsis_id", "team", "t"], how="inner")
        .join(roster, on=["gsis_id", "team", "week"], how="inner")
        .join(
            _dropback_shares(ctx).rename({"game_id": "prev_game"}),
            on=["team", "prev_game", "gsis_id"],
            how="left",
        )
        .select(
            "position",
            (~pl.col("played")).alias("missed"),
            pl.col("prev_dropback_share").fill_null(0.0),
            "prev_snap_share",
            "gsis_id",
            "team",
            "week",
        )
        .sort("team", "week", "gsis_id")
    )


def _dropback_shares(ctx: MetricContext) -> pl.DataFrame:
    """(team, game_id, gsis_id, prev_dropback_share): each QB's share of his team's dropbacks
    in a game (qb_dropback on plays from scrimmage, garbage time kept, the dropback QB)."""
    db = (
        ctx.plays.filter(
            (pl.col("qb_dropback") == 1).fill_null(False)
            & pf.scrimmage()
            & pl.col("posteam").is_not_null()
        )
        .with_columns(pf.dropback_qb().alias("gsis_id"))
        .filter(pl.col("gsis_id").is_not_null())
    )
    return (
        db.group_by(pl.col("posteam").alias("team"), "game_id", "gsis_id")
        .len()
        .with_columns(
            (pl.col("len") / pl.col("len").sum().over("team", "game_id"))
            .cast(pl.Float64)
            .alias("prev_dropback_share")
        )
        .select("team", "game_id", "gsis_id", "prev_dropback_share")
    )


def _slots(ctx: MetricContext) -> pl.DataFrame:
    """Section 4 slot of every player-game (fitter pool, ruling 2026-10-08: players with an
    offensive snap in that game), ranked on the team's games before it; the week's depth chart
    with no history (week 1 or new signing)."""
    usage = usage_by_game(ctx.snaps, ctx.plays) if ctx.snaps.height else pl.DataFrame()
    if usage.is_empty():
        return pl.DataFrame(
            schema={"team": pl.Utf8, "game_id": pl.Utf8, "gsis_id": pl.Utf8, "slot": pl.Utf8}
        )
    depth = ctx.snap.collect("depth_charts")
    last = last_season_snaps(ctx)
    rows = []
    for team, games in _team_game_order(ctx).items():
        mine = usage.filter(pl.col("team") == team)
        for i, (week, gid) in enumerate(games):
            here = mine.filter(pl.col("game_id") == gid)
            cands = dict(here.select("gsis_id", "position").sort("gsis_id").iter_rows())
            hist = histories(mine, [g for _, g in games[:i]])
            dr = depth_ranks(depth, team, week) if any(p not in hist for p in cands) else {}
            for pid, slot in sorted(assign(cands, hist, dr, last).items()):
                rows.append((team, gid, pid, slot))
    return pl.DataFrame(
        rows,
        schema={"team": pl.Utf8, "game_id": pl.Utf8, "gsis_id": pl.Utf8, "slot": pl.Utf8},
        orient="row",
    ).with_columns(pl.lit(ctx.season).alias("season"))


def _wopr(ctx: MetricContext) -> pl.DataFrame:
    """PLY-04 WOPR rows: one per team target (PLY-03's usage target) per player of that team who
    played the game: his target 0/1, his air yards, the target's air yards (null = 0)."""
    air = pl.col("air_yards").fill_null(0.0).cast(pl.Float64)
    tg = ctx.plays.filter(pf.usage_target() & pl.col("posteam").is_not_null()).select(
        pl.col("posteam").alias("team"),
        "game_id",
        pl.col("g_off").cast(pl.Float64).alias("g"),
        pl.col("receiver_player_id").alias("_who"),
        air.alias("team_air"),
    )
    return (
        tg.join(ctx.played, on=["team", "game_id"], how="inner")
        .select(
            pl.col("gsis_id").alias("entity_id"),
            "team",
            "g",
            (pl.col("_who") == pl.col("gsis_id")).cast(pl.Float64).alias("his_target"),
            pl.when(pl.col("_who") == pl.col("gsis_id"))
            .then(pl.col("team_air"))
            .otherwise(0.0)
            .alias("his_air"),
            "team_air",
        )
        .with_columns(pl.lit(ctx.season).alias("season"))
        .sort("entity_id", "team", "g", "his_target", "his_air", "team_air")
    )


def _def08(ctx: MetricContext) -> pl.DataFrame:
    """DEF-08 on/off rows: for each defensive starter over the season (>= the starter snap
    share of the team's defensive snaps) who missed at least one team game, the team's
    qualifying plays against, arm = 1 in games he played, x = EPA allowed."""
    d = load_params().defense
    min_share = d.def_08_starter_min_snap_share.value
    s = ctx.table("snap_counts").select(
        "team", "game_id", "pfr_player_id", "defense_snaps", "defense_pct"
    )
    if s.is_empty():
        return pl.DataFrame(
            schema={"entity_id": pl.Utf8, "team": pl.Utf8, "game_id": pl.Utf8, "x": pl.Float64}
        )
    team_snaps = (
        s.filter(pl.col("defense_pct") > 0)
        .group_by("team", "game_id")
        .agg((pl.col("defense_snaps") / pl.col("defense_pct")).max().alias("t"))
    )
    tot = dict(team_snaps.group_by("team").agg(pl.col("t").sum()).iter_rows())
    n_games = dict(team_snaps.group_by("team").len().iter_rows())
    mine = (
        s.filter(pl.col("defense_snaps").fill_null(0) > 0)
        .group_by("team", "pfr_player_id")
        .agg(pl.col("defense_snaps").sum().alias("snaps"), pl.col("game_id").alias("games"))
    )
    q = ctx.plays.filter(pf.qualifying() & pl.col("defteam").is_not_null()).select(
        pl.col("defteam").alias("team"), "game_id", pl.col("epa").cast(pl.Float64).alias("x")
    )
    frames = []
    for team, pfr, sn, games in mine.sort("team", "pfr_player_id").iter_rows():
        if not tot.get(team) or sn / tot[team] < min_share or len(games) >= n_games[team]:
            continue
        frames.append(
            q.filter(pl.col("team") == team).with_columns(
                pl.lit(f"{team}|{pfr}").alias("entity_id"),
                pl.col("game_id").is_in(list(games)).cast(pl.Int64).alias("arm"),
            )
        )
    if not frames:
        return pl.DataFrame(
            schema={"entity_id": pl.Utf8, "team": pl.Utf8, "game_id": pl.Utf8, "x": pl.Float64}
        )
    return (
        pl.concat(frames)
        .filter(pl.col("x").is_not_null())
        .with_columns(pl.lit(ctx.season).alias("season"))
        .sort("entity_id", "game_id", "x")
    )
