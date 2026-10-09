"""Section 4 role priors (spec synced 2026-10-08) and the slot data behind them.

A player stat with a role prior shrinks toward last season's shrunk value if the player has the
same team and play-caller; otherwise toward the league average for his slot (QB1, RB1, RB2, WR1,
WR2, WR3, TE1) from the season's Phase 3e fit (key role_key). Slots come from ge.metrics.slots:
usage rank within the team over the team's games before the target game, the depth chart only
without game history.

Who is ranked (ruling 2026-10-08): live, players on the team's latest visible weekly roster
with status ACT, minus those designated Out this week; in the end-of-season (prior) view and in
the Phase 3e fitter, players who played (an offensive snap). The same usage table and ranking
code serve the fitter (ge.fit.roles).

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

import polars as pl

from ge.metrics import plays as pf
from ge.metrics.slots import SLOT_COUNTS, TIEBREAK, History, rank_position, slot_labels

if TYPE_CHECKING:
    from ge.metrics.context import MetricContext

SLOT_POSITIONS = tuple(SLOT_COUNTS)


def role_key(spec_id: str, stat: str, cell: str, slot: str) -> str:
    """Phase 3e key of one slot's league-average prior."""
    return f"fit:role/{spec_id}/{stat}/{cell}/{slot}"


def usage_by_game(snaps: pl.DataFrame, plays: pl.DataFrame) -> pl.DataFrame:
    """Per (team, game_id, gsis_id): offensive snaps, the team's offensive snaps, targets and
    designed carries with the team's totals (usage definitions, garbage time kept), and the
    snap-count position."""
    s = snaps.filter(pl.col("offense_snaps").fill_null(0) > 0).select(
        "team",
        "game_id",
        "gsis_id",
        pl.col("position").fill_null(""),
        pl.col("offense_snaps").cast(pl.Float64).alias("snaps"),
        pl.col("team_offense_snaps").cast(pl.Float64).alias("team_snaps"),
    )

    def counts(mask: pl.Expr, who: str, name: str) -> tuple[pl.DataFrame, pl.DataFrame]:
        p = plays.filter(mask & pl.col("posteam").is_not_null())
        mine = (
            p.filter(pl.col(who).is_not_null())
            .group_by(pl.col("posteam").alias("team"), "game_id", pl.col(who).alias("gsis_id"))
            .agg(pl.len().cast(pl.Float64).alias(name))
        )
        team = p.group_by(pl.col("posteam").alias("team"), "game_id").agg(
            pl.len().cast(pl.Float64).alias(f"team_{name}")
        )
        return mine, team

    tg, tg_team = counts(pf.usage_target(), "receiver_player_id", "targets")
    ca, ca_team = counts(pf.usage_carry(), "rusher_player_id", "carries")
    out = (
        s.join(tg, on=["team", "game_id", "gsis_id"], how="left")
        .join(ca, on=["team", "game_id", "gsis_id"], how="left")
        .join(tg_team, on=["team", "game_id"], how="left")
        .join(ca_team, on=["team", "game_id"], how="left")
    )
    return out.with_columns(
        pl.col(c).fill_null(0.0) for c in ("targets", "carries", "team_targets", "team_carries")
    ).sort("team", "game_id", "gsis_id")


def histories(usage: pl.DataFrame, games: Iterable[str]) -> dict[str, History]:
    """History over the given team games (one team's rows): snap share = his snaps / the team's
    snaps over all those games (a game he missed counts 0); tiebreak share likewise for targets
    (WR, TE) or carries (RB, QB). Only players with a snap in those games have a history."""
    g = set(games)
    u = usage.filter(pl.col("game_id").is_in(list(g)))
    if u.is_empty():
        return {}
    team_tot = u.select("game_id", "team_snaps", "team_targets", "team_carries").unique("game_id")
    ts = float(team_tot["team_snaps"].sum())
    tt = float(team_tot["team_targets"].sum())
    tc = float(team_tot["team_carries"].sum())
    out: dict[str, History] = {}
    agg = u.group_by("gsis_id", "position").agg(
        pl.col("snaps").sum(), pl.col("targets").sum(), pl.col("carries").sum()
    )
    for pid, pos, sn, tgt, car in agg.sort("gsis_id", "position").iter_rows():
        tb = TIEBREAK.get(pos)
        share = (tgt / tt if tt else 0.0) if tb == "target" else (car / tc if tc else 0.0)
        prev = out.get(pid)
        h = History(sn / ts if ts else 0.0, share)
        if prev is None or (h.snap_share, h.tiebreak_share) > (
            prev.snap_share,
            prev.tiebreak_share,
        ):
            out[pid] = h
    return out


def depth_ranks(depth: pl.DataFrame, team: str, week: int | None) -> dict[str, tuple[str, float]]:
    """gsis_id -> (position, depth rank) from a depth chart: the week-numbered format (before
    2025: depth_team, offense formation, that week or the latest earlier one) or the ESPN
    format (2025 on: pos_abb, pos_rank, already the latest chart by as_of)."""
    if depth.is_empty():
        return {}
    if "pos_rank" in depth.columns:
        d = depth.filter((pl.col("team") == team) & pl.col("pos_abb").is_in(SLOT_POSITIONS))
        rows = d.select("gsis_id", "pos_abb", pl.col("pos_rank").cast(pl.Float64)).iter_rows()
    else:
        d = depth.filter(
            (pl.col("club_code") == team)
            & pl.col("depth_position").is_in(SLOT_POSITIONS)
            & (pl.col("formation") == "Offense")
        )
        if week is not None and d.height:
            wk = d.filter(pl.col("week") <= week)["week"].max()
            d = d.filter(pl.col("week") == wk) if wk is not None else d.head(0)
        rows = d.select(
            "gsis_id", "depth_position", pl.col("depth_team").cast(pl.Float64)
        ).iter_rows()
    out: dict[str, tuple[str, float]] = {}
    for pid, pos, rank in sorted(rows, key=lambda r: (str(r[0]), r[2], str(r[1]))):
        if pid is not None and rank is not None and pid not in out:
            out[str(pid)] = (str(pos), float(rank))
    return out


def assign(
    candidates: Mapping[str, str],
    history: Mapping[str, History],
    depth: Mapping[str, tuple[str, float]],
    last_snaps: Mapping[str, float],
) -> dict[str, str]:
    """gsis_id -> slot for one team-game: candidates (gsis_id -> position) ranked per position
    by the section 4 rule."""
    by_pos: dict[str, list[str]] = defaultdict(list)
    for pid, pos in candidates.items():
        if pos in SLOT_COUNTS:
            by_pos[pos].append(pid)
    out: dict[str, str] = {}
    for pos, pids in sorted(by_pos.items()):
        ranks = {p: r for p, (dp, r) in depth.items() if dp == pos}
        ranked = rank_position(pos, pids, history, ranks, last_snaps)
        out.update(slot_labels(pos, ranked))
    return out


def last_season_snaps(ctx: MetricContext) -> dict[str, float]:
    """Offensive snaps per player last season, on any team (depth-chart tiebreak)."""
    s = ctx.snap.collect("snap_counts")
    if s.is_empty():
        return {}
    s = s.filter(pl.col("season") == ctx.season - 1)
    if s.is_empty():
        return {}
    g = (
        s.with_columns(ctx.gsis(pl.col("pfr_player_id")).alias("gsis_id"))
        .group_by("gsis_id")
        .agg(pl.col("offense_snaps").fill_null(0).sum().cast(pl.Float64))
    )
    return dict(g.iter_rows())


def context_slots(ctx: MetricContext) -> dict[tuple[str, str], str]:
    """(gsis_id, team) -> slot as of the context's target game (live view), or over the whole
    season (end-of-season view, week None)."""
    usage = usage_by_game(ctx.snaps, ctx.plays) if ctx.snaps.height else pl.DataFrame()
    last = last_season_snaps(ctx)
    depth = ctx.snap.collect("depth_charts") if ctx.week is not None else pl.DataFrame()
    out: dict[tuple[str, str], str] = {}
    for team in ctx.teams["team"].to_list():
        mine = usage.filter(pl.col("team") == team) if usage.height else usage
        games = mine["game_id"].unique().to_list() if mine.height else []
        hist = histories(mine, games) if mine.height else {}
        if ctx.week is None:
            cands = (
                {
                    pid: pos
                    for pid, pos in mine.select("gsis_id", "position")
                    .unique()
                    .sort("gsis_id")
                    .iter_rows()
                }
                if mine.height
                else {}
            )
        else:
            cands = _live_candidates(ctx, team)
            # A candidate's position comes from the roster; history keeps his best position row.
        for pid, slot in assign(cands, hist, depth_ranks(depth, team, ctx.week), last).items():
            out[(pid, team)] = slot
    return out


def _live_candidates(ctx: MetricContext, team: str) -> dict[str, str]:
    """Latest visible weekly roster for the team (status ACT, slotted positions), minus players
    designated Out this week (ruling 2026-10-08)."""
    rw = ctx.table("rosters_weekly")
    if rw.is_empty() or "gsis_id" not in rw.columns:
        return {}
    mine = rw.filter((pl.col("team") == team) & pl.col("gsis_id").is_not_null())
    if ctx.week is not None:
        mine = mine.filter(pl.col("week") <= ctx.week)
    if mine.is_empty():
        return {}
    wk = mine["week"].max()
    mine = mine.filter((pl.col("week") == wk) & (pl.col("status") == "ACT"))
    inj = ctx.injuries_now()
    out_ids = (
        set(inj.filter((pl.col("team") == team) & (pl.col("report_status") == "Out"))["gsis_id"])
        if inj.height
        else set()
    )
    return {
        str(pid): str(pos)
        for pid, pos in mine.select("gsis_id", "position").sort("gsis_id").iter_rows()
        if pos in SLOT_COUNTS and pid not in out_ids
    }


def role_priors(ctx: MetricContext, spec_id: str, stat: str) -> pl.DataFrame:
    """Per (entity_id, team, cell) of the stat: the section 4 prior, or null (no slot, or no
    fitted value for his slot). Raises NotImplementedError when the season has no Phase 3e fit."""
    from ge.config import current_params
    from ge.metrics.registry import raw, shrunk

    a = current_params()
    if a.fitted is None:
        raise NotImplementedError(
            f"{spec_id}: section 4 role prior (slot league average) needs the season's Phase 3e "
            f"fit; there is none for season {ctx.snap.season}"
        )
    rows = (
        raw(ctx, spec_id)
        .filter((pl.col("stat") == stat) & (pl.col("entity_type") == "player"))
        .select("entity_id", "team", "cell")
        .unique()
        .sort("entity_id", "team", "cell")
    )
    last: dict[tuple[str, str, str], float] = {}
    if ctx.week is not None:
        prev = shrunk(ctx.prior_context(), spec_id, stat).filter(pl.col("shrunk").is_not_null())
        for eid, tm, cell, v in prev.select("entity_id", "team", "cell", "shrunk").iter_rows():
            last[(eid, ctx.franchise(tm), cell)] = v
    slots = ctx.slots
    priors = []
    for eid, tm, cell in rows.iter_rows():
        prior = None
        if last:
            changed, _ = ctx._caller_changed(tm, "offense")
            if changed is False:
                prior = last.get((eid, ctx.franchise(tm), cell))
        if prior is None:
            slot = slots.get((eid, tm))
            if slot is not None:
                status, v, _ = a.fit_status(role_key(spec_id, stat, cell, slot))
                prior = v if status == "fitted" else None
        priors.append(prior)
    return rows.with_columns(pl.Series("prior", priors, dtype=pl.Float64))
