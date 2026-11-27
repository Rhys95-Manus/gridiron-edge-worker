"""PRV-08 availability gate: the injury report status seen at as_of, and the flag it carries.

PRV-08: "Out or Doubtful at as_of: unpriced. Questionable, or no final injury report: priced
and flagged. The status seen is stored on every row. Vacated targets and carries are not
redistributed in v0." Spec sync #6 (2026-11-27): the status is the report_status on the
player's row, matched by gsis_id, in his nflverse team's injury report for the target game's
week, as visible at as_of under BT-01. Stored values: Out, Doubtful, Questionable, none (listed
with no game designation), not_listed. A team's final report is in when its visible
target-week rows include at least one Out, Doubtful or Questionable designation (PLY-14 ruling
2026-10-04). Pricer v0 does not read roster status.

The caller passes the injury rows visible at as_of (the snapshot's injuries, BT-01); this module
only reads them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import polars as pl

from ge.pricer_v0.reasons import PricerUnpriced

SPEC_ID = "PRV-08"
# PRV-08 stored status values.
OUT = "Out"
DOUBTFUL = "Doubtful"
QUESTIONABLE = "Questionable"
NO_DESIGNATION = "none"
NOT_LISTED = "not_listed"
DESIGNATIONS = (OUT, DOUBTFUL, QUESTIONABLE)
INJURY_COLUMNS = ("season", "week", "team", "gsis_id", "report_status")


class AvailabilityFlag(StrEnum):
    """PRV-08: priced and flagged."""

    QUESTIONABLE = "questionable"
    NO_FINAL_REPORT = "no_final_report"


@dataclass(frozen=True)
class Availability:
    """PRV-08 verdict for one player: the status seen (stored on every row), whether his team's
    final report is in, the flag (priced rows) and the unpriced reason (Out, Doubtful)."""

    status_seen: str
    final_report_in: bool
    flag: AvailabilityFlag | None
    reason: PricerUnpriced | None


def availability(
    injuries: pl.DataFrame, *, season: int, week: int, team: str, gsis_id: str
) -> Availability:
    """PRV-08: `injuries` are the injury report rows visible at as_of (INJURY_COLUMNS); only
    the rows of `team` for `season`/`week` are read. A null or blank report_status is "listed
    with no game designation". A status outside Out/Doubtful/Questionable, or two rows for the
    player with different statuses, raises NotImplementedError: the spec doesn't say."""
    week_rows = injuries.filter(
        (pl.col("season") == season) & (pl.col("week") == week) & (pl.col("team") == team)
    )
    seen: list[str] = []
    for status in week_rows["report_status"].to_list():
        text = (status or "").strip()
        if text and text not in DESIGNATIONS:
            raise NotImplementedError(
                f"{SPEC_ID}: report_status {text!r} is not Out, Doubtful or Questionable"
            )
        seen.append(text)
    final_report_in = any(s in DESIGNATIONS for s in seen)
    mine = {
        (s or "").strip()
        for s in week_rows.filter(pl.col("gsis_id") == gsis_id)["report_status"].to_list()
    }
    if len(mine) > 1:
        raise NotImplementedError(
            f"{SPEC_ID}: {gsis_id} has rows with different statuses {sorted(mine)}"
        )
    status_seen = (mine.pop() or NO_DESIGNATION) if mine else NOT_LISTED
    if status_seen == OUT:
        return Availability(status_seen, final_report_in, None, PricerUnpriced.OUT)
    if status_seen == DOUBTFUL:
        return Availability(status_seen, final_report_in, None, PricerUnpriced.DOUBTFUL)
    if status_seen == QUESTIONABLE:
        return Availability(status_seen, final_report_in, AvailabilityFlag.QUESTIONABLE, None)
    flag = None if final_report_in else AvailabilityFlag.NO_FINAL_REPORT
    return Availability(status_seen, final_report_in, flag, None)
