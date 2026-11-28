"""PRV-10 training windows, the PRV-05/06 compound-model yard pools, and PRV-03 μ for one game.

Fit prep only (session 7a): nothing here fits a parameter.

PRV-10: "Walk-forward: season S (2022, 2023, 2024) is scored with distribution parameters fitted
on 2021 to S - 1" and "The live model uses distribution parameters fitted on 2021-2024".

PRV-05: "Y_i are drawn with replacement from the league per-reception yards of his position group
in the training window: yards_gained on plays with complete_pass = 1 and the receiver's
receiver_player_id, from play-by-play, with the receiver's group taken from that game's
ff_opportunity row."

PRV-06: "Per-carry yards are drawn with replacement from the position group's training-window
play-by-play plays with rush_attempt = 1 (designed runs, scrambles and kneels, as official rushing
yards count them)."

Spec sync #8 (2026-11-27), PRV-06: "Yard pools for PRV-05 and PRV-06: two-point tries
(two_point_attempt = 1) are left out of both yard pools. A play whose receiver or rusher has no
ff_opportunity row for that game is dropped from the pool and counted in the fit report. The
rusher's position group comes from that game's ff_opportunity row, and the per-carry value is
yards_gained, as in PRV-05. A training window's seasons include their postseason games. Each
yard pool is ordered by game_id, then play_id. A player-game with ff_opportunity rows in two
different position groups stops the pool build. Pools read the latest pull of each window
season."

Spec sync #8, PRV-10: "Each family's distribution parameters are fitted by maximum likelihood on
the training window's player-games, each with its point-in-time μ at as_of = kickoff - 24 h
under BT-01. Each season's μ, in training and in scoring, uses that season's
params_fitted/v4/S<season>.yaml; the live model uses live.yaml. Training and calibration use
every player-game in which the player played (an offensive snap or an opportunity) and that has
at least 3 earlier qualifying games in the stint; a played game with no ff_opportunity row
counts the stat as 0, and players left unpriced are not used."

Rulings 2026-11-27 (session 7b): "unpriced" includes PRV-08 (Out, Doubtful,
injury_status_unclear at as_of); actuals are the ff_opportunity actual columns and "played" is
MetricContext.played on the end-of-season view, both from the latest pull of 2021-2024.

Data: nflverse; charting: FTN Data via nflverse; expected points: ffopportunity (ffverse) via
nflverse; data license not stated by the source.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from ge.config import load_params
from ge.ingest.raw import DATA_ROOT
from ge.metrics.expected import STATS, position_group
from ge.pricer_v0.availability import availability
from ge.pricer_v0.projection import PRV_STATS, Centring, Prv03Fit, centring, project
from ge.store import known_at as ka
from ge.store.holdout import Window
from ge.store.vintage import choose_version

POOL_PBP_COLUMNS = (
    "game_id",
    "play_id",
    "complete_pass",
    "receiver_player_id",
    "rush_attempt",
    "rusher_player_id",
    "two_point_attempt",
    "yards_gained",
)
POOL_FF_COLUMNS = ("game_id", "player_id", "position")
_WINDOW_NAME = re.compile(r"S(\d{4})")


def pricer_window(name: str) -> Window:
    """PRV-10: 'S<S>' for a scored season S (2021 to S - 1) or 'live' (2021 to 2024). Built on
    BT-07's Window, so a read of the holdout or of the test season raises HoldoutReadError."""
    pv0 = load_params().pricer_v0
    first_fit = int(pv0.prv_10_first_fit_season.value)
    if name == "live":
        last = int(pv0.prv_10_live_last_fit_season.value)
        return Window("live", None, tuple(range(first_fit, last + 1)))
    m = _WINDOW_NAME.fullmatch(name)
    first_scored = int(pv0.prv_10_first_scored_season.value)
    last_scored = int(pv0.prv_10_last_scored_season.value)
    if m is None or not first_scored <= int(m.group(1)) <= last_scored:
        raise ValueError(
            f"PRV-10: window {name!r} is not live or S<S> for S in {first_scored}..{last_scored}"
        )
    s = int(m.group(1))
    return Window(name, s, tuple(range(first_fit, s)))


def read_window_frames(window: Window, root: Path = DATA_ROOT) -> tuple[pl.DataFrame, pl.DataFrame]:
    """PRV-05/06: play-by-play (POOL_PBP_COLUMNS) and ff_opportunity (POOL_FF_COLUMNS) for the
    window's seasons only, each from its latest pull. Every season is checked against the
    window (BT-07a/b) before its path is opened; a season with no pull raises
    FileNotFoundError."""
    latest = dt.datetime.max.replace(tzinfo=dt.UTC)
    out: dict[str, list[pl.DataFrame]] = {"pbp": [], "ff_opportunity": []}
    cols = {"pbp": list(POOL_PBP_COLUMNS), "ff_opportunity": list(POOL_FF_COLUMNS)}
    for s in window.seasons:
        window.check_read(s)
        for ds, frames in out.items():
            v = choose_version(root, ds, s, latest)
            if v is None:
                raise FileNotFoundError(f"PRV-10: no {ds} pull for season {s} under {root}")
            frames.append(pl.read_parquet(v.path, columns=cols[ds]))
    return (
        pl.concat(out["pbp"], how="diagonal_relaxed"),
        pl.concat(out["ff_opportunity"], how="diagonal_relaxed"),
    )


@dataclass(frozen=True)
class YardsPools:
    """PRV-05/06 league pools per position group for one training window, in (game_id,
    play_id) order, and the plays dropped for having no ff_opportunity row that game."""

    window: str
    seasons: tuple[int, ...]
    per_reception: Mapping[str, tuple[float, ...]]
    per_carry: Mapping[str, tuple[float, ...]]
    dropped_receptions: int
    dropped_carries: int


def _groups(ff: pl.DataFrame, spec_id: str) -> pl.DataFrame:
    """(game_id, player_id) -> PLY-35 group from that game's ff_opportunity row. Identical rows
    collapse; a player with two groups in one game raises ValueError."""
    g = (
        ff.filter(pl.col("player_id").is_not_null())
        .select("game_id", "player_id", position_group(pl.col("position")))
        .unique()
    )
    clash = g.group_by("game_id", "player_id").len().filter(pl.col("len") > 1)
    if clash.height:
        raise ValueError(
            f"{spec_id}: {clash.height} player-games have ff_opportunity rows in two position "
            "groups"
        )
    return g


def _pool(
    plays: pl.DataFrame, groups: pl.DataFrame, player_col: str
) -> tuple[dict[str, tuple[float, ...]], int]:
    plays = plays.filter(pl.col(player_col).is_not_null())
    joined = plays.join(
        groups, left_on=["game_id", player_col], right_on=["game_id", "player_id"], how="inner"
    ).sort("game_id", "play_id", maintain_order=True)
    pools = {
        str(grp): tuple(float(y) for y in part["yards_gained"].to_list())
        for (grp,), part in joined.group_by("group", maintain_order=True)
    }
    return dict(sorted(pools.items())), plays.height - joined.height


def yards_pools(pbp: pl.DataFrame, ff: pl.DataFrame, window: Window) -> YardsPools:
    """PRV-05/06 per-reception and per-carry yard pools for `window`. Rows outside the
    window's seasons are ignored; two-point tries never enter (ruling 2026-11-27)."""
    prefixes = [f"{s}_" for s in window.seasons]

    def in_window(df: pl.DataFrame) -> pl.DataFrame:
        season = pl.col("game_id").str.slice(0, 5)
        return df.filter(season.is_in(prefixes))

    plays = in_window(pbp).filter(pl.col("two_point_attempt").fill_null(0) != 1)
    groups = _groups(in_window(ff), "PRV-05, PRV-06")
    rec, dropped_rec = _pool(
        plays.filter(pl.col("complete_pass") == 1), groups, "receiver_player_id"
    )
    rush, dropped_rush = _pool(
        plays.filter(pl.col("rush_attempt") == 1), groups, "rusher_player_id"
    )
    return YardsPools(
        window=window.name,
        seasons=window.seasons,
        per_reception=rec,
        per_carry=rush,
        dropped_receptions=dropped_rec,
        dropped_carries=dropped_rush,
    )


MU_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "game_id": pl.Utf8,
    "as_of": pl.Datetime("us", "UTC"),
    "team": pl.Utf8,
    "gsis_id": pl.Utf8,
    "stat": pl.Utf8,
    "n_games": pl.Int64,
    "group": pl.Utf8,
    "e": pl.Float64,
    "m": pl.Float64,
    "g": pl.Float64,
    "g_n_eff": pl.Float64,
    "mu": pl.Float64,
    "carries_mean": pl.Float64,
    "reason": pl.Utf8,
    "centring_label": pl.Utf8,
    "fit_window": pl.Utf8,
}


def game_mu(
    ff: pl.DataFrame,
    games: pl.DataFrame,
    *,
    target_game_id: str,
    teams: tuple[str, ...],
    fit: Prv03Fit,
    centring_means: Centring,
    as_of: dt.datetime,
) -> pl.DataFrame:
    """PRV-03 μ at as_of for every player with a visible target-season ff_opportunity row on
    either team of the game, for each PRV stat (MU_SCHEMA, sorted by team, gsis_id, stat).
    `ff` and `games` are the snapshot's visible rows, as project() takes them."""
    season = f"{target_game_id.split('_', 1)[0]}_"
    seen = ff.filter(
        pl.col("game_id").str.starts_with(season)
        & (pl.col("game_id") != target_game_id)
        & pl.col("player_id").is_not_null()
    )
    rows = []
    for team in sorted(teams):
        players = sorted(seen.filter(pl.col("posteam") == team)["player_id"].unique().to_list())
        for gsis_id in players:
            for stat in sorted(PRV_STATS):
                p = project(
                    ff,
                    games,
                    target_game_id=target_game_id,
                    gsis_id=str(gsis_id),
                    team=team,
                    stat=stat,
                    centring_means=centring_means,
                    fit=fit,
                )
                rows.append(
                    {
                        "game_id": target_game_id,
                        "as_of": as_of,
                        "team": team,
                        "gsis_id": str(gsis_id),
                        "stat": stat,
                        "n_games": p.n_games,
                        "group": p.group,
                        "e": p.e,
                        "m": p.m,
                        "g": p.g,
                        "g_n_eff": p.g_n_eff,
                        "mu": p.mu,
                        "carries_mean": p.carries_mean,
                        "reason": None if p.reason is None else p.reason.value,
                        "centring_label": p.centring_label,
                        "fit_window": fit.window,
                    }
                )
    return pl.DataFrame(rows, schema=MU_SCHEMA)


# ---- PRV-10 labels: every played player-game, actuals from ff_opportunity ----

LABEL_STATS = PRV_STATS
LABELS_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "game_id": pl.Utf8,
    "team": pl.Utf8,
    "gsis_id": pl.Utf8,
    "has_ff_row": pl.Boolean,
    "receptions": pl.Float64,
    "receiving_yards": pl.Float64,
    "rushing_yards": pl.Float64,
    "carries": pl.Float64,
}
# PRV-06 compound model: the carries count is ff_opportunity's rush_attempt.
_CARRIES_COLUMN = "rush_attempt"


def _season_prefix(season: int) -> str:
    return f"{season}_"


def labels_from(played: pl.DataFrame, ff: pl.DataFrame, season: int) -> pl.DataFrame:
    """PRV-10: one row per played (gsis_id, team, game_id) of `season` (MetricContext.played:
    an offensive snap or an opportunity) with the PRV stats' actual values from that game's
    ff_opportunity row; "a played game with no ff_opportunity row counts the stat as 0", and a
    null actual counts as 0 (as in PRV-03). ff rows with no player_id are ignored; two rows for
    one played player-game raise ValueError. Sorted by game_id, team, gsis_id."""
    prefix = _season_prefix(season)
    plays = played.filter(pl.col("game_id").str.starts_with(prefix)).select(
        "game_id", "team", "gsis_id"
    )
    rows = ff.filter(pl.col("game_id").str.starts_with(prefix) & pl.col("player_id").is_not_null())
    dup = (
        rows.group_by("game_id", "player_id")
        .len()
        .filter(pl.col("len") > 1)
        .join(plays, left_on=["game_id", "player_id"], right_on=["game_id", "gsis_id"])
    )
    if dup.height:
        raise ValueError(
            f"PRV-10: {dup.height} played player-games have two or more ff_opportunity rows"
        )
    actual = {stat: STATS[stat][0] for stat in LABEL_STATS}
    values = rows.select(
        "game_id",
        pl.col("player_id").alias("gsis_id"),
        pl.lit(True).alias("has_ff_row"),
        *[
            pl.sum_horizontal(pl.col(c).fill_null(0.0) for c in cols).cast(pl.Float64).alias(s)
            for s, cols in actual.items()
        ],
        pl.col(_CARRIES_COLUMN).fill_null(0.0).cast(pl.Float64).alias("carries"),
    )
    out = plays.join(values, on=["game_id", "gsis_id"], how="left").with_columns(
        pl.col("has_ff_row").fill_null(False),
        *[pl.col(c).fill_null(0.0) for c in (*LABEL_STATS, "carries")],
    )
    return (
        out.select(list(LABELS_SCHEMA))
        .cast(pl.Schema(LABELS_SCHEMA))
        .sort("game_id", "team", "gsis_id")
    )


def season_labels(season: int, root: Path = DATA_ROOT) -> pl.DataFrame:
    """PRV-10 labels for one season from the latest pull: MetricContext.played on the
    end-of-season view (ge.fit.history.season_view) and that view's ff_opportunity. Reads go
    through the live pricer window, so 2025 (BT-07b) is refused before any file is opened."""
    from ge.fit.history import Reader, season_view
    from ge.metrics.coaching import load_registry
    from ge.metrics.context import MetricContext
    from ge.store.snapshot import FF

    window = pricer_window("live")
    window.check_read(season)
    reader = Reader(root, window, dt.datetime.max.replace(tzinfo=dt.UTC))
    view = season_view(reader, season)
    ctx = MetricContext(view, season, None, load_registry())
    return labels_from(ctx.played, view.collect(FF), season)


# ---- PRV-10 point-in-time mu for a season ----

SCHEDULE_COLUMNS = ("game_id", "kickoff_utc", "home_team", "away_team", "week")


def read_schedule(season: int, root: Path = DATA_ROOT) -> pl.DataFrame:
    """The season's games (regular and postseason) from the latest schedules pull, with
    kickoff_utc, in kickoff order. The live pricer window is checked first (BT-07b)."""
    pricer_window("live").check_read(season)
    v = choose_version(root, "schedules", season, dt.datetime.max.replace(tzinfo=dt.UTC))
    if v is None:
        raise FileNotFoundError(f"PRV-10: no schedules pull for season {season} under {root}")
    sched = ka.with_kickoff(pl.read_parquet(v.path))
    return sched.select(SCHEDULE_COLUMNS).sort("kickoff_utc", "game_id")


@dataclass(frozen=True)
class GameInputs:
    """What PRV-03 and PRV-08 read for one game at as_of: the visible ff_opportunity rows, the
    target season's visible team games (MetricContext.games), the visible injury reports and
    the target game's week."""

    ff: pl.DataFrame
    games: pl.DataFrame
    injuries: pl.DataFrame
    week: int


OpenGame = Callable[[str, dt.datetime], GameInputs]


def open_game(game_id: str, as_of: dt.datetime) -> GameInputs:
    """BT-01 snapshot of one game at as_of (rule 5), as PRV-03 and PRV-08 read it."""
    from ge.metrics.context import build_context
    from ge.store.snapshot import FF, snapshot

    snap = snapshot(game_id, as_of)
    ctx = build_context(snap)
    return GameInputs(
        ff=snap.collect(FF), games=ctx.games, injuries=snap.collect("injuries"), week=snap.week
    )


AVAILABILITY_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "team": pl.Utf8,
    "gsis_id": pl.Utf8,
    "status_seen": pl.Utf8,
    "availability_flag": pl.Utf8,
    "availability_reason": pl.Utf8,
}


def with_availability(
    mu: pl.DataFrame, injuries: pl.DataFrame, *, season: int, week: int
) -> pl.DataFrame:
    """PRV-08 for every (team, gsis_id) in `mu`: the status seen, the flag and the unpriced
    reason, from the injury rows visible at as_of for the target season and week."""
    players = mu.select("team", "gsis_id").unique().sort("team", "gsis_id")
    rows = []
    for team, gsis_id in players.iter_rows():
        a = availability(injuries, season=season, week=week, team=team, gsis_id=gsis_id)
        rows.append(
            {
                "team": team,
                "gsis_id": gsis_id,
                "status_seen": a.status_seen,
                "availability_flag": None if a.flag is None else a.flag.value,
                "availability_reason": None if a.reason is None else a.reason.value,
            }
        )
    avail = pl.DataFrame(rows, schema=AVAILABILITY_SCHEMA)
    return mu.join(avail, on=["team", "gsis_id"], how="left", maintain_order="left")


SEASON_MU_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    **MU_SCHEMA,
    **{k: v for k, v in AVAILABILITY_SCHEMA.items() if k not in ("team", "gsis_id")},
}


def season_mu(
    season: int,
    schedule: pl.DataFrame,
    *,
    fit: Prv03Fit,
    open_game: OpenGame = open_game,
    on_game: Callable[[int, str], None] | None = None,
) -> pl.DataFrame:
    """PRV-10: point-in-time μ for every game of `season` in kickoff order, each at as_of =
    kickoff - 24 h (BT-01 decision time), with `fit` (the season's own v4 S<season> file) and
    PRV-08 at the same as_of. Rows follow game_mu's order within each game
    (SEASON_MU_SCHEMA)."""
    bt = load_params().backtest
    games = schedule.select(SCHEDULE_COLUMNS).sort("kickoff_utc", "game_id")
    wrong = games.filter(~pl.col("game_id").str.starts_with(_season_prefix(season)))
    if wrong.height:
        raise ValueError(
            f"PRV-10: schedule for season {season} holds other seasons' games: "
            f"{wrong['game_id'].to_list()[:3]}"
        )
    parts = []
    for i, (gid, kickoff, home, away, week) in enumerate(games.iter_rows()):
        as_of = ka.default_as_of(kickoff, "decision", bt)
        inp = open_game(gid, as_of)
        mu = game_mu(
            inp.ff,
            inp.games,
            target_game_id=gid,
            teams=(home, away),
            fit=fit,
            centring_means=centring(inp.ff, inp.games, season),
            as_of=as_of,
        )
        parts.append(with_availability(mu, inp.injuries, season=season, week=int(week)))
        if on_game is not None:
            on_game(i, gid)
    if not parts:
        return pl.DataFrame(schema=SEASON_MU_SCHEMA)
    return pl.concat(parts).select(list(SEASON_MU_SCHEMA)).cast(pl.Schema(SEASON_MU_SCHEMA))


# ---- PRV-10 training / calibration rows ----


def training_rows(mu: pl.DataFrame, labels: pl.DataFrame, stat: str) -> pl.DataFrame:
    """PRV-10: the player-games used for `stat`: priced at as_of (no PRV-03 reason and no PRV-08
    reason, ruling 2026-11-27) and played for the same team that game. `actual` is the stat's
    label; `carries` the game's rush_attempt. Sorted by game_id, team, gsis_id."""
    if stat not in PRV_STATS:
        raise ValueError(f"PRV-10: stat {stat!r} is not one of {PRV_STATS}")
    priced = mu.filter(
        (pl.col("stat") == stat)
        & pl.col("reason").is_null()
        & pl.col("availability_reason").is_null()
    )
    return priced.join(
        labels.select(
            "game_id", "team", "gsis_id", "has_ff_row", pl.col(stat).alias("actual"), "carries"
        ),
        on=["game_id", "team", "gsis_id"],
        how="inner",
    ).sort("game_id", "team", "gsis_id")
