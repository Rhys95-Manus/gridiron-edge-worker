"""Phase 3e training data: one training season as the live engine's prior-season view sees it.

season_view(s) is a BT-01 Snapshot of season s after its last game: every game of s (and of
s - 1, which some metrics read for context), the weekly reports in full, participation and
seasonal rosters of s, Next Gen Stats of seasons <= s, combine years <= s, the whole season's
depth charts (the slot rule needs each week's chart), and no target game, weather or market
data. A MetricContext(view, s, week=None) is then the same end-of-season view the engine's
prior_context() gives, so fitters read metric units from the production metric code.

Every read goes through the fit's Window, so a season at or after the test season, or the
holdout, raises HoldoutReadError (BT-07a / BT-07b). Each dataset reads the latest version
pulled at or before the fit's data_as_of; the digest covers every version read.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from ge.ingest.nflverse import SEASONLESS
from ge.ingest.raw import seasons_stored
from ge.store.holdout import Window
from ge.store.snapshot import (
    COMBINE_COLUMNS,
    CROSSWALK_COLUMNS,
    FF,
    FF_OPPORTUNITY_COLUMNS,
    FRANCHISE_COLUMNS,
    GAME_KEYED,
    NGS,
    PRIOR_SEASON_ONLY,
    TABLES,
    WEEKLY_REPORTS,
    Loader,
    Snapshot,
    empty_ff_schema,
)
from ge.store.vintage import Version, choose_version


@dataclass
class Reader:
    """Guarded, vintage-pinned reads for one fit. Records every version it reads."""

    root: Path
    window: Window
    as_of: dt.datetime
    read: set[str] = field(default_factory=set)

    def version(self, dataset: str, season: int) -> Version | None:
        if season != SEASONLESS:
            self.window.check_read(season)
        v = choose_version(self.root, dataset, season, self.as_of)
        if v is not None:
            stored = v.path.parent / "content.sha256"
            digest = (
                stored.read_text(encoding="ascii").strip()
                if stored.exists()
                else hashlib.sha256(v.path.read_bytes()).hexdigest()  # e.g. test fixture slices
            )
            self.read.add(f"{v.label} {digest}")
        return v

    def frame(self, dataset: str, season: int, columns: list[str] | None = None) -> pl.DataFrame:
        v = self.version(dataset, season)
        if v is None:
            return pl.DataFrame()
        lf = pl.scan_parquet(v.path)
        return (lf.select(columns) if columns else lf).collect()

    def frames(self, dataset: str, seasons: list[int]) -> pl.DataFrame:
        got = [f for s in seasons if (f := self.frame(dataset, s)).height]
        return pl.concat(got, how="diagonal_relaxed") if got else pl.DataFrame()

    def digest(self) -> str:
        """sha256 over every version read (label and content hash), sorted."""
        return hashlib.sha256("\n".join(sorted(self.read)).encode()).hexdigest()


def _seasons(reader: Reader, season: int) -> list[int]:
    first = min(reader.window.seasons)
    return [s for s in (season - 1, season) if s >= first]


def season_view(reader: Reader, season: int) -> Snapshot:
    """The end-of-season view of one training season (see module docstring)."""
    reader.window.check_read(season)
    seasons = _seasons(reader, season)
    loaders: dict[str, Loader] = {}
    loaders["target_game"] = pl.DataFrame
    loaders["schedules"] = lambda: reader.frames("schedules", seasons)

    def frames(ds: str, which: list[int]) -> Loader:
        return lambda: reader.frames(ds, which)

    upto = [s for s in reader.window.seasons if s <= season]
    for ds in (*GAME_KEYED, *WEEKLY_REPORTS):
        loaders[ds] = frames(ds, seasons)
    for ds in NGS:
        loaders[ds] = frames(ds, upto)
    for ds in PRIOR_SEASON_ONLY:
        loaders[ds] = frames(ds, [season])

    def ff() -> pl.DataFrame:
        """PLY-35's ff_opportunity columns for s - 1 and s, every game (end of season)."""
        cols = list(FF_OPPORTUNITY_COLUMNS)
        got = [f for s in seasons if (f := reader.frame(FF, s, cols)).height]
        return pl.concat(got, how="diagonal_relaxed") if got else pl.DataFrame(empty_ff_schema())

    loaders[FF] = ff

    def ids(ds: str, cols: tuple[str, ...]) -> pl.DataFrame:
        f = reader.frame(ds, SEASONLESS, list(cols))
        if f.is_empty():
            return pl.DataFrame(schema=dict.fromkeys(cols, pl.Utf8))
        return f.drop_nulls(list(cols)).unique().sort(list(cols))

    loaders["players"] = lambda: ids("players", CROSSWALK_COLUMNS)
    loaders["teams"] = lambda: ids("teams", FRANCHISE_COLUMNS)

    def combine() -> pl.DataFrame:
        years = [y for y in seasons_stored(reader.root, "combine") if y <= season]
        got = [f for y in years if (f := reader.frame("combine", y, list(COMBINE_COLUMNS))).height]
        if not got:
            return pl.DataFrame(schema=dict.fromkeys(COMBINE_COLUMNS, pl.Utf8))
        return pl.concat(got, how="diagonal_relaxed").sort(
            "season", "pfr_id", "pos", nulls_last=True
        )

    loaders["combine"] = combine
    loaders["depth_charts"] = lambda: reader.frame("depth_charts", season)
    for t in TABLES:
        loaders.setdefault(t, pl.DataFrame)
    cache: dict[str, pl.DataFrame] = {}
    when = reader.as_of
    return Snapshot(
        game_id=f"{season}_FIT",
        season=season,
        week=0,
        kickoff_utc=when,
        as_of=when,
        pass_="decision",
        closing_line_backtest=False,
        labels=(f"Phase 3e training view of season {season} (fit {reader.window.name})",),
        vintages=(),
        _loaders=loaders,
        _cache=cache,
    )
