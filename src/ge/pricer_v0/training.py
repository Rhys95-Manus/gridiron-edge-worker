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

Rulings 2026-11-27 (session 7a, spec wording proposed in session7a-report.md): two-point tries
(two_point_attempt = 1) are left out of both pools; a play whose receiver or rusher has no
ff_opportunity row for that game is dropped and counted; the rusher's group comes from that
game's ff_opportunity row and the per-carry value is yards_gained, as in PRV-05; a window's
seasons include their postseason games. Code choice (proposed in the report): each pool is in
(game_id, play_id) order, since the Monte Carlo index draws depend on pool order.

Data: nflverse; charting: FTN Data via nflverse; expected points: ffopportunity (ffverse) via
nflverse; data license not stated by the source.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from ge.config import load_params
from ge.ingest.raw import DATA_ROOT
from ge.metrics.expected import position_group
from ge.pricer_v0.projection import PRV_STATS, Centring, Prv03Fit, project
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
