"""Coaching profile (spec section 5). COA-01 is the hand-maintained staff and play-caller
registry, config/coaching_registry.csv: nflverse does not track coordinators or who calls
plays. One row per team, season and role, each with its own source link, supporting quote and
confidence (schema of 2026-10-07). Rows are entered from fetched sources, never from memory
(rule 2). A role with no row is blank: play-caller lookups then fall back to the G4
head-coach stand-in, and the team's other rows still count."""

from __future__ import annotations

import bisect
import csv
import datetime as dt
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import polars as pl

from ge.config import REPO_ROOT, load_params
from ge.metrics.engine import finish

if TYPE_CHECKING:
    from ge.metrics.context import MetricContext

_C = load_params().coaching

REGISTRY_PATH = REPO_ROOT / "config" / "coaching_registry.csv"
REGISTRY_COLUMNS = (
    "team",
    "season",
    "role",
    "person",
    "effective_date",
    "source_url",
    "quote",
    "confidence",
)
ROLES = (
    "head_coach",
    "offensive_coordinator",
    "defensive_coordinator",
    "offensive_play_caller",
    "defensive_play_caller",
)
# Source confidence (user decision 2026-10-07): a team site or major outlet; a local or
# team-focused outlet; or only a play-caller ranking.
CONFIDENCE = ("team_or_major", "local_or_team_focused", "ranking_only")
_URL = re.compile(r"^https?://[^\s/]+\.[^\s/]+(/\S*)?$")
_CALLER = {"offense": "offensive_play_caller", "defense": "defensive_play_caller"}


class RegistryError(ValueError):
    """COA-01: a registry row failed validation."""


@dataclass(frozen=True)
class RegistryRow:
    team: str
    season: int
    role: str
    person: str
    effective_date: dt.date
    source_url: str
    quote: str
    confidence: str


@dataclass(frozen=True)
class CoachingRegistry:
    """COA-01 rows. A row says who held a role for a team from its effective date until the
    team's next row for that role."""

    rows: tuple[RegistryRow, ...]

    def row(self, team: str, role: str, on: dt.date) -> RegistryRow | None:
        """The team's latest row for `role` effective on or before `on`."""
        mine = [
            r for r in self.rows if r.team == team and r.role == role and r.effective_date <= on
        ]
        return max(mine, key=lambda r: r.effective_date) if mine else None

    def person(self, team: str, role: str, on: dt.date) -> str | None:
        r = self.row(team, role, on)
        return None if r is None else r.person

    def current(self, team: str, on: dt.date) -> dict[str, RegistryRow]:
        """Every role with a row effective on or before `on` (blank roles are absent)."""
        out = {}
        for role in ROLES:
            r = self.row(team, role, on)
            if r is not None:
                out[role] = r
        return out

    def caller(self, team: str, side: Literal["offense", "defense"], on: dt.date) -> str | None:
        return self.person(team, _CALLER[side], on)


def load_registry(path: Path = REGISTRY_PATH) -> CoachingRegistry:
    """COA-01: read and validate the registry. Every field of a row is required: season is
    a year; role and confidence come from fixed lists; effective_date is an ISO date;
    source_url is an http(s) link. One row per team, role and effective date."""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != REGISTRY_COLUMNS:
            raise RegistryError(f"COA-01: {path} columns must be {', '.join(REGISTRY_COLUMNS)}")
        rows = []
        seen: set[tuple[str, str, dt.date]] = set()
        for i, raw in enumerate(reader, start=2):
            r = _row(raw, f"{path.name} line {i}")
            key = (r.team, r.role, r.effective_date)
            if key in seen:
                raise RegistryError(
                    f"COA-01: {path.name} line {i}: duplicate team, role, date {key}"
                )
            seen.add(key)
            rows.append(r)
    return CoachingRegistry(tuple(rows))


def _row(raw: dict[str, str | None], where: str) -> RegistryRow:
    vals = {c: (raw.get(c) or "").strip() for c in REGISTRY_COLUMNS}
    for c, v in vals.items():
        if not v:
            raise RegistryError(f"COA-01: {where}: {c} is empty")
    if not vals["season"].isdigit():
        raise RegistryError(f"COA-01: {where}: season {vals['season']!r} is not a year")
    if vals["role"] not in ROLES:
        raise RegistryError(f"COA-01: {where}: role {vals['role']!r} not in {ROLES}")
    if vals["confidence"] not in CONFIDENCE:
        raise RegistryError(
            f"COA-01: {where}: confidence {vals['confidence']!r} not in {CONFIDENCE}"
        )
    try:
        when = dt.date.fromisoformat(vals["effective_date"])
    except ValueError as exc:
        raise RegistryError(f"COA-01: {where}: effective_date {vals['effective_date']!r}") from exc
    if not _URL.match(vals["source_url"]):
        raise RegistryError(f"COA-01: {where}: source_url {vals['source_url']!r} is not a link")
    return RegistryRow(
        team=vals["team"],
        season=int(vals["season"]),
        role=vals["role"],
        person=vals["person"],
        effective_date=when,
        source_url=vals["source_url"],
        quote=vals["quote"],
        confidence=vals["confidence"],
    )


# ---- COA-01 to COA-07 metrics (section 5) ----
# The metric modules import the context, which imports this module for the registry, so
# they are imported inside each function.


def coa_01(ctx: MetricContext) -> pl.DataFrame:
    """COA-01: staff and play-caller registry. Per team: its registry roles at as_of (blank
    roles listed as blank, or that no row covers it); whether the registry head coach matches
    the schedules data's head coach for its target or latest game; and whether a mid-season
    play-caller change reset OFF-04 to OFF-10 (registry, else the head-coach stand-in; ruling
    2026-10-05)."""
    rows: list[dict[str, object]] = []
    for team in ctx.teams["team"].to_list():
        reg = ctx.registry.current(team, ctx.as_of.date())
        games = ctx.games.filter(pl.col("team") == team).sort("g")
        latest = ctx.coach_by_game.get((team, games["game_id"][0])) if games.height else None
        sched_hc = ctx._target_coach(team) or latest
        base = {"entity_type": "team", "entity_id": team, "team": team, "cell": "staff"}
        match: float | None = None
        if not reg:
            rows.append({**base, "stat": "registry", "note": "no COA-01 row covering as_of"})
        else:
            parts = [
                f"{role}: {reg[role].person} ({reg[role].confidence}, since "
                f"{reg[role].effective_date})"
                if role in reg
                else f"{role}: blank"
                for role in ROLES
            ]
            rows.append({**base, "stat": "registry", "note": "; ".join(parts)})
            hc = reg.get("head_coach")
            match = None if sched_hc is None or hc is None else float(hc.person == sched_hc)
        rows.append(
            {
                **base,
                "stat": "hc_matches_schedules",
                "value": match,
                "note": f"schedules head coach: {sched_hc}",
            }
        )
        r = ctx.resets.get(team)
        since = 0 if r is None or r.first_game_g is None else int(r.first_game_g) + 1
        rows.append(
            {
                **base,
                "stat": "play_caller_reset",
                "value": 1.0 if r else 0.0,
                "n": since,
                "note": r.note if r else None,
            }
        )
    df = pl.DataFrame(rows, infer_schema_length=None).with_columns(
        pl.lit("COA-01").alias("spec_id")
    )
    return finish(df).sort("entity_id", "stat")


def coa_02(ctx: MetricContext) -> pl.DataFrame:
    """COA-02: 4th-down aggressiveness. Going for it = a 4th-down pass or run, against a punt
    or field goal (no-play penalties, kneels and spikes out; G7 garbage time out, since this
    is a tendency). The raw go rate is shown; the over-expected value needs the p_go model,
    which Phase 3e fits (user decision 2026-10-02), so it raises."""
    from ge.metrics import plays as pf
    from ge.metrics.offense import team_rate, team_units

    fourth = (pl.col("down") == 4) & pl.col("play_type").is_in(
        ["pass", "run", "punt", "field_goal"]
    )
    m = fourth & ~pf.garbage() & pl.col("posteam").is_not_null()
    x = pl.col("play_type").is_in(["pass", "run"]).cast(pl.Float64)
    u = team_units(ctx, m, pl.lit("all"), x, "offense")
    return team_rate(ctx, "COA-02", "go_rate", u, ["all"], _C.coa_02_min_fourth_downs.value)


def coa_03(ctx: MetricContext) -> pl.DataFrame:
    """COA-03: 2-point attempt rate = 2-point tries / touchdowns, counting every TD the team
    scores (A20). A garbage-time TD (G7) leaves the denominator and its try leaves the
    numerator (ruling 2026-10-05). n = TDs. Min 10 TDs."""
    from ge.metrics import plays as pf
    from ge.metrics.offense import team_rate

    is_td = (pl.col("touchdown") == 1).fill_null(False) & pl.col("td_team").is_not_null()
    p = ctx.plays.sort("game_id", "play_id").with_columns(
        pl.when(is_td).then(pf.garbage()).forward_fill().over("game_id").alias("_td_garbage")
    )
    tds = (
        p.filter(is_td & ~pf.garbage())
        .group_by(pl.col("td_team").alias("team"), "game_id")
        .agg(pl.len().cast(pl.Float64).alias("d"))
    )
    try_ok = (pl.col("two_point_attempt") == 1).fill_null(False) & pl.col("posteam").is_not_null()
    tries = (
        p.filter(try_ok & pl.col("_td_garbage").eq(False).fill_null(False))
        .group_by(pl.col("posteam").alias("team"), "game_id")
        .agg(pl.len().cast(pl.Float64).alias("x"))
    )
    u = (
        tds.join(tries, on=["team", "game_id"], how="full", coalesce=True)
        .join(ctx.games.select("team", "game_id", "g"), on=["team", "game_id"], how="inner")
        .select(
            pl.col("team").alias("entity_id"),
            "team",
            pl.lit("all").alias("cell"),
            "g",
            pl.col("x").fill_null(0.0),
            pl.col("d").fill_null(0.0),
            pl.col("d").fill_null(0.0).alias("c"),
        )
    )
    return team_rate(ctx, "COA-03", "two_point_rate", u, ["all"], _C.coa_03_min_tds.value)


def coa_04(ctx: MetricContext) -> pl.DataFrame:
    """COA-04: script response: OFF-05 (pass rate over expected) and OFF-10 (pace) on plays
    with wp > 0.80 (leading) and wp < 0.20 (trailing), not garbage time (G7). For pace, the
    prior play of each pair sets the bucket. Min 40 plays (pairs) per bucket."""
    from ge.metrics import plays as pf
    from ge.metrics.offense import pace_pairs, team_rate, team_units

    wp = pl.col("wp")
    bucket = (
        pl.when(pf.garbage())
        .then(None)
        .when(wp > _C.coa_04_leading_min_wp.value)
        .then(pl.lit("leading"))
        .when(wp < _C.coa_04_trailing_max_wp.value)
        .then(pl.lit("trailing"))
    )
    cells = ["leading", "trailing"]
    mn = _C.coa_04_min_plays_per_bucket.value
    m = pf.qualifying() & pl.col("xpass").is_not_null() & bucket.is_not_null()
    proe = team_units(ctx, m, bucket, pl.col("pass") - pl.col("xpass"), "offense")
    pairs = pace_pairs(ctx, prior_ok=bucket.is_not_null(), cell=bucket).select(
        pl.col("posteam").alias("entity_id"), pl.col("posteam").alias("team"), "cell", "g", "x"
    )
    return pl.concat(
        [
            team_rate(ctx, "COA-04", "proe", proe, cells, mn),
            team_rate(ctx, "COA-04", "seconds_per_play", pairs, cells, mn),
        ]
    )


COA05_OUTSIDE = ("left_end", "left_tackle", "right_tackle", "right_end")


def coa_05(ctx: MetricContext) -> pl.DataFrame:
    """COA-05: scheme tendency cluster, shown as percentiles among the teams (not a scheme
    label): outside-run share (end + tackle cells of OFF-12; raw, since OFF-12 has no shrunk
    share), under-center rate (1 - shrunk OFF-09), play-action rate (shrunk OFF-06) and
    motion rate (shrunk OFF-07). Percentile = (teams below + half the ties) / teams with a
    value. The inputs' samples and shrinkage apply."""
    from ge.metrics.registry import raw, shrunk

    vals: dict[str, dict[str, float]] = {}
    car = raw(ctx, "OFF-12").filter(
        (pl.col("stat") == "carries") & (pl.col("entity_type") == "team")
    )
    tot = car.group_by("entity_id").agg(pl.col("n").sum().alias("t"))
    outside = (
        car.filter(pl.col("cell").is_in(list(COA05_OUTSIDE)))
        .group_by("entity_id")
        .agg(pl.col("n").sum().alias("o"))
    )
    j = tot.join(outside, on="entity_id", how="left").filter(pl.col("t") > 0)
    vals["outside_run_share"] = {
        e: o / t for e, t, o in j.select("entity_id", "t", pl.col("o").fill_null(0)).iter_rows()
    }
    for stat, sid, s, flip in (
        ("under_center_rate", "OFF-09", "shotgun_rate", True),
        ("play_action_rate", "OFF-06", "play_action_rate", False),
        ("motion_rate", "OFF-07", "motion_rate", False),
    ):
        sh = shrunk(ctx, sid, s).filter(pl.col("shrunk").is_not_null())
        vals[stat] = {
            e: (1 - v if flip else v) for e, v in sh.select("entity_id", "shrunk").iter_rows()
        }
    rows: list[dict[str, object]] = []
    for stat, by in vals.items():
        xs = sorted(by.values())
        for team, x in sorted(by.items()):
            below = bisect.bisect_left(xs, x)
            ties = bisect.bisect_right(xs, x) - below
            base = {
                "entity_type": "team",
                "entity_id": team,
                "team": team,
                "cell": "all",
                "n": len(xs),
            }
            rows.append({**base, "stat": stat, "value": x})
            rows.append({**base, "stat": f"{stat}_pctl", "value": (below + 0.5 * ties) / len(xs)})
    df = pl.DataFrame(rows, infer_schema_length=None).with_columns(
        pl.lit("COA-05").alias("spec_id")
    )
    return finish(df).sort("entity_id", "stat")


def coa_05b(ctx: MetricContext) -> pl.DataFrame:
    """COA-05b: defensive coverage family. PAID: needs coverage charting (DATA-11)."""
    raise NotImplementedError("PAID: DATA-11")


def coa_06(ctx: MetricContext) -> pl.DataFrame:
    """COA-06: coordinator history vs this opponent's staff; display only (no numeric
    adjustment in v1). For each side of the target game: past games in the snapshot window
    (plan A21) where this team's current offensive play-caller called plays against a defense
    whose play-caller was the opponent's current one (COA-01 rows at each game's date), and
    EPA per qualifying play of his offense in those games. Min 2 games."""
    from ge.metrics import plays as pf

    tg = ctx.snap.collect("target_game")
    if not tg.height:
        return finish(pl.DataFrame(schema={"spec_id": pl.Utf8}))
    t = tg.row(0, named=True)
    sched = ctx.snap.collect("schedules")
    day = {g: dt.date.fromisoformat(d) for g, d in sched.select("game_id", "gameday").iter_rows()}
    plays = ctx.snap.collect("pbp").filter(pf.qualifying() & pl.col("posteam").is_not_null())
    games = plays.select("game_id", "posteam", "defteam").unique().sort("game_id", "posteam")
    min_games = _C.coa_06_min_games.value
    rows: list[dict[str, object]] = []
    for off, dfn in ((t["away_team"], t["home_team"]), (t["home_team"], t["away_team"])):
        base = {
            "entity_type": "team",
            "entity_id": off,
            "team": off,
            "cell": f"vs {dfn}",
            "stat": "epa_vs_coordinator",
            "min_n": float(min_games),
        }
        oc = ctx.registry.caller(off, "offense", ctx.as_of.date())
        dc = ctx.registry.caller(dfn, "defense", ctx.as_of.date())
        if oc is None or dc is None:
            note = "no COA-01 rows naming both play-callers (display only)"
            rows.append({**base, "n": 0, "below_min_sample": True, "note": note})
            continue
        hit = [
            (g, a)
            for g, a, b in games.iter_rows()
            if g in day
            and ctx.registry.caller(a, "offense", day[g]) == oc
            and ctx.registry.caller(b, "defense", day[g]) == dc
        ]
        mine = plays.join(
            pl.DataFrame(hit, schema={"game_id": pl.Utf8, "posteam": pl.Utf8}, orient="row"),
            on=["game_id", "posteam"],
            how="semi",
        )
        epa = mine.sort("game_id", "play_id")["epa"].to_list()
        names = ", ".join(sorted({g for g, _ in hit})) or "none"
        rows.append(
            {
                **base,
                "n": len(hit),
                "value": math.fsum(epa) / len(epa) if epa else None,
                "below_min_sample": len(hit) < min_games,
                "note": f"{oc} vs {dc}; games: {names} (display only)",
            }
        )
    df = pl.DataFrame(rows, infer_schema_length=None).with_columns(
        pl.lit("COA-06").alias("spec_id")
    )
    return finish(df)


def coa_07(ctx: MetricContext) -> pl.DataFrame:
    """COA-07: situational features for the target game's two teams: rest days (schedules),
    travel (great-circle km from the previous game's stadium, or the home stadium after a
    bye; A22) and time-zone change (UTC-offset hours, this stadium minus the origin, at
    kickoff; ruling 2026-10-05). The coefficients are league-wide and estimated in PRJ-01
    (Phase 4); team situation records wait for thresholds the spec doesn't give."""
    from zoneinfo import ZoneInfo

    from ge.config import load_ingest
    from ge.ingest.stadiums import load_stadiums

    tg = ctx.snap.collect("target_game")
    if not tg.height:
        return finish(pl.DataFrame(schema={"spec_id": pl.Utf8}))
    t = tg.row(0, named=True)
    stadia = {str(s["stadium_id"]): s for s in load_stadiums()}
    radius = load_ingest().geo.earth_mean_radius_km.value
    sched = ctx.snap.collect("schedules").sort("gameday", "game_id")
    dest = stadia[t["stadium_id"]]
    kickoff = dt.datetime.combine(
        dt.date.fromisoformat(t["gameday"]),
        dt.time.fromisoformat(t["gametime"]),
        ZoneInfo("America/New_York"),
    )

    def offset(s: dict[str, Any]) -> float:
        off = kickoff.astimezone(ZoneInfo(str(s["timezone"]))).utcoffset()
        assert off is not None
        return off.total_seconds() / 3600

    rows: list[dict[str, object]] = []
    for side in ("home", "away"):
        team = t[f"{side}_team"]
        mine = sched.filter((pl.col("home_team") == team) | (pl.col("away_team") == team))
        cur = mine.filter(pl.col("season") == ctx.season)
        if cur.is_empty() or cur["week"][-1] < t["week"] - 1:
            origin_id = str(mine.filter(pl.col("home_team") == team)["stadium_id"][-1])
            why = "home stadium after a bye"
        else:
            origin_id = str(cur["stadium_id"][-1])
            why = "previous game's stadium"
        origin = stadia[origin_id]
        km = _haversine_km(origin["lat"], origin["lon"], dest["lat"], dest["lon"], radius)
        base = {"entity_type": "team", "entity_id": team, "team": team, "cell": t["game_id"]}
        rows += [
            {**base, "stat": "rest_days", "value": float(t[f"{side}_rest"]), "note": "schedules"},
            {
                **base,
                "stat": "travel_km",
                "value": km,
                "note": f"from {origin_id} ({why}) to {t['stadium_id']}",
            },
            {
                **base,
                "stat": "tz_change_hours",
                "value": offset(dest) - offset(origin),
                "note": f"UTC offset at kickoff, {origin['timezone']} to {dest['timezone']}",
            },
        ]
    df = pl.DataFrame(rows, infer_schema_length=None).with_columns(
        pl.lit("COA-07").alias("spec_id")
    )
    return finish(df).sort("entity_id", "stat")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float, radius: float) -> float:
    """Great-circle distance by the haversine formula."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(min(1.0, a)))
