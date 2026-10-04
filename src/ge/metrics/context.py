"""MetricContext: what every metric reads, built from one BT-01 snapshot (rule 5).

Current-season rows give values; the prior season (also in the snapshot) gives G4 priors
through `prior_context()`. Nothing else is read except the COA-01 registry, filtered to rows
effective on or before as_of.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import datetime as dt
from functools import cached_property
from typing import Any

import polars as pl

from ge.metrics.coaching import CoachingRegistry, load_registry
from ge.metrics.engine import Side
from ge.metrics.plays import scrimmage
from ge.store.snapshot import Snapshot


class MetricContext:
    """One season's view of a snapshot. `week` is the target game's week for the current
    season, None for the prior-season view (its end-of-season values, no G4 recursion)."""

    def __init__(
        self,
        snap: Snapshot,
        season: int,
        week: int | None,
        registry: CoachingRegistry,
    ) -> None:
        self.snap = snap
        self.season = season
        self.week = week
        self.as_of = snap.as_of
        self.registry = registry
        self.cache: dict[Any, pl.DataFrame] = {}
        self._prior: MetricContext | None = None

    # ---- tables ----

    def table(self, name: str) -> pl.DataFrame:
        df = self.snap.collect(name)
        if "season" in df.columns:
            return df.filter(pl.col("season") == self.season)
        return df

    @cached_property
    def games(self) -> pl.DataFrame:
        """Visible games this season with each team's games-ago index (G3: g = 0 for the most
        recent game)."""
        pbp = self.table("pbp")
        if pbp.is_empty():
            return pl.DataFrame(
                schema={"team": pl.Utf8, "game_id": pl.Utf8, "week": pl.Int64, "g": pl.Float64}
            )
        g = pbp.select("game_id", "week", "home_team", "away_team").unique()
        both = pl.concat(
            [
                g.select("game_id", "week", pl.col(s).alias("team"))
                for s in ("home_team", "away_team")
            ]
        )
        return (
            both.with_columns(pl.col("week").cast(pl.Int64))
            .sort(["team", "week", "game_id"], descending=[False, True, True])
            .with_columns(pl.int_range(pl.len()).over("team").cast(pl.Float64).alias("g"))
        )

    @cached_property
    def opponents(self) -> pl.DataFrame:
        """(team, game_id, opponent) for every visible game."""
        pbp = self.table("pbp").select("game_id", "home_team", "away_team").unique()
        return pl.concat(
            [
                pbp.select(
                    "game_id",
                    pl.col("home_team").alias("team"),
                    pl.col("away_team").alias("opponent"),
                ),
                pbp.select(
                    "game_id",
                    pl.col("away_team").alias("team"),
                    pl.col("home_team").alias("opponent"),
                ),
            ]
        )

    @cached_property
    def plays(self) -> pl.DataFrame:
        """This season's play-by-play with games-ago for the offense (g_off) and defense
        (g_def), and FTN charting joined on (game_id, play_id)."""
        pbp = self.table("pbp")
        gm = self.games.select("team", "game_id", "g")
        out = pbp.join(
            gm.rename({"team": "posteam", "g": "g_off"}), on=["posteam", "game_id"], how="left"
        ).join(gm.rename({"team": "defteam", "g": "g_def"}), on=["defteam", "game_id"], how="left")
        ftn = self.table("ftn_charting")
        if ftn.height:
            keep = [c for c in ftn.columns if c.startswith(("is_", "n_"))]
            f = ftn.select(
                pl.col("nflverse_game_id").alias("game_id"),
                pl.col("nflverse_play_id").cast(pl.Float64).alias("_pid"),
                *keep,
                pl.lit(True).alias("ftn_charted"),
            ).unique(["game_id", "_pid"], keep="first")
            out = (
                out.with_columns(pl.col("play_id").cast(pl.Float64).alias("_pid"))
                .join(f, on=["game_id", "_pid"], how="left")
                .drop("_pid")
            )
        return out

    @cached_property
    def teams(self) -> pl.DataFrame:
        """entity_id/team for every team, including teams that haven't played yet this season
        (n = 0, shrunk = prior): this season's visible teams and the target game's, plus any
        franchise seen only last season (under last season's abbreviation)."""
        cur = set(self.games["team"].to_list())
        tg = self.snap.collect("target_game")
        if self.season == self.snap.season and tg.height:
            cur |= {tg["home_team"][0], tg["away_team"][0]}
        prev = self.snap.collect("pbp").filter(pl.col("season") == self.season - 1)
        seen = {self.franchise(x) for x in cur}
        for x in sorted(set(prev["home_team"].to_list()) | set(prev["away_team"].to_list())):
            if self.franchise(x) not in seen:
                cur.add(x)
                seen.add(self.franchise(x))
        t = sorted(cur)
        return pl.DataFrame(
            {"entity_id": t, "team": t}, schema={"entity_id": pl.Utf8, "team": pl.Utf8}
        )

    @cached_property
    def crosswalk(self) -> dict[str, str]:
        """DATA-04 pfr_id -> gsis_id."""
        x = self.snap.collect("players")
        return dict(x.select("pfr_id", "gsis_id").iter_rows()) if x.height else {}

    def gsis(self, pfr: pl.Expr) -> pl.Expr:
        """pfr id -> gsis id; unmatched players keep a visible "pfr:<id>" key."""
        xw = self.crosswalk
        return pfr.replace_strict(xw, default=None, return_dtype=pl.Utf8).fill_null(
            pl.lit("pfr:") + pfr
        )

    def injuries_now(self) -> pl.DataFrame:
        """This week's injury report rows visible at as_of (current season only)."""
        inj = self.table("injuries")
        if self.week is None or inj.is_empty():
            return inj.clear()
        return inj.filter(pl.col("week") == self.week)

    # ---- G4 ----

    def prior_context(self) -> MetricContext:
        if self._prior is None:
            self._prior = MetricContext(self.snap, self.season - 1, None, self.registry)
        return self._prior

    def _top_qb(self, season: int) -> dict[str, str]:
        pbp = self.snap.collect("pbp").filter(pl.col("season") == season)
        if pbp.is_empty():
            return {}
        c = (
            pbp.filter(
                (pl.col("qb_dropback") == 1).fill_null(False)
                & scrimmage()
                & pl.col("passer_player_id").is_not_null()
            )
            .group_by("posteam", "passer_player_id")
            .len()
            .sort(["posteam", "len", "passer_player_id"], descending=[False, True, True])
        )
        return dict(
            c.group_by("posteam", maintain_order=True)
            .first()
            .select("posteam", "passer_player_id")
            .iter_rows()
        )

    @cached_property
    def _franchises(self) -> dict[str, str]:
        t = self.snap.collect("teams")
        return dict(t.select("team_abbr", "team_id").iter_rows()) if t.height else {}

    def franchise(self, abbr: str) -> str:
        """G4: a team abbreviation's franchise (nflverse teams table team_id), so a relocated
        team keeps its history. An abbreviation missing from the table raises KeyError."""
        fr = self._franchises
        if abbr not in fr:
            raise KeyError(f"G4: {abbr!r} is not in the nflverse teams table (DATA-04)")
        return fr[abbr]

    def by_franchise(self, values: dict[str, Any]) -> dict[str, Any]:
        """Re-key a {team_abbr: value} map by franchise."""
        return {self.franchise(t): v for t, v in values.items()}

    @cached_property
    def _qb_now(self) -> dict[str, str]:
        return self.by_franchise(self._top_qb(self.season))

    @cached_property
    def _qb_then(self) -> dict[str, str]:
        return self.by_franchise(self._top_qb(self.season - 1))

    def _last_games(self, season: int) -> dict[str, tuple[dt.date, str, str]]:
        """Per franchise, its latest visible game in `season`: (date, abbreviation, head
        coach from the schedules data)."""
        s = self.snap.collect("schedules").filter(pl.col("season") == season)
        out: dict[str, tuple[dt.date, str, str]] = {}
        for r in s.sort("gameday", "game_id").iter_rows(named=True):
            d = dt.date.fromisoformat(r["gameday"])
            for side in ("home", "away"):
                t = r[f"{side}_team"]
                out[self.franchise(t)] = (d, t, r[f"{side}_coach"])
        return out

    @cached_property
    def _now(self) -> dict[str, tuple[dt.date, str, str]]:
        """This season's latest visible game per franchise; a team with none yet uses the
        target game, whose head coaches are known before kickoff."""
        out = self._last_games(self.season)
        tg = self.snap.collect("target_game")
        if tg.height and self.season == self.snap.season:
            r = tg.row(0, named=True)
            for side in ("home", "away"):
                t = r[f"{side}_team"]
                out.setdefault(
                    self.franchise(t), (dt.date.fromisoformat(r["gameday"]), t, r[f"{side}_coach"])
                )
        return out

    @cached_property
    def _then(self) -> dict[str, tuple[dt.date, str, str]]:
        return self._last_games(self.season - 1)

    def _caller_changed(self, team: str, side: Side) -> tuple[bool | None, str]:
        """G4 play-caller change: from COA-01 when it has a caller at both dates; until then a
        head-coach change in the schedules data stands in (spec G4, docs synced 2026-10-04)."""
        fr = self.franchise(team)
        now, then = self._now.get(fr), self._then.get(fr)
        if now is None or then is None:
            return None, ""
        c_now = self.registry.caller(now[1], side, self.as_of.date())
        c_then = self.registry.caller(then[1], side, then[0])
        if c_now is not None and c_then is not None:
            return c_now != c_then, "new play-caller"
        if now[2] is None or then[2] is None:
            return None, ""
        return now[2] != then[2], "new head coach (stands in for play-caller)"

    def g4_changed(self, team: str, side: Side) -> tuple[bool | None, str]:
        """G4: (changed, note). Offense: new offensive play-caller or new QB (most dropbacks
        this season vs last); defense: new defensive play-caller. Any known change -> True;
        all known and unchanged -> False; otherwise None (user decision 2026-10-02)."""
        caller, label = self._caller_changed(team, side)
        checks: dict[str, bool | None] = {label or "new play-caller": caller}
        if side == "offense":
            fr = self.franchise(team)
            q_now, q_then = self._qb_now.get(fr), self._qb_then.get(fr)
            checks["new QB"] = None if q_now is None or q_then is None else q_now != q_then
        hits = [k for k, v in checks.items() if v]
        if hits:
            return True, "; " + ", ".join(hits)
        if all(v is False for v in checks.values()):
            return False, ""
        return None, ""


def build_context(snap: Snapshot, registry: CoachingRegistry | None = None) -> MetricContext:
    """Phase 3 entry point: metrics for the snapshot's season, as of its as_of."""
    return MetricContext(snap, snap.season, snap.week, registry or load_registry())
