"""PRJ-02 overtime: the format in force for a season and game type, from config/overtime.yaml
(rulings 2026-10-23). The simulator raises for a season with no entry."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StringConstraints

from ge.config import REPO_ROOT, SpecId

OVERTIME_PATH = REPO_ROOT / "config" / "overtime.yaml"
_Text = Annotated[str, StringConstraints(min_length=1)]


class OvertimeRuleMissing(NotImplementedError):
    """PRJ-02: no overtime entry for this season and game type."""


class OvertimeRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    season: StrictInt
    postseason: StrictBool
    spec_id: SpecId
    status: Literal["initial"]
    quote: _Text
    text_read_from: Literal["archive", "live"]
    archive_url: _Text | None
    original_url: _Text
    capture_date: Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    period_minutes: Annotated[StrictInt, Field(gt=0)]
    max_periods: Annotated[StrictInt, Field(gt=0)] | None
    ties_allowed: StrictBool
    timeouts_per_team: Annotated[StrictInt, Field(gt=0)]
    timeouts_reset_periods: Annotated[StrictInt, Field(gt=0)] | None
    opening_touchdown_ends_game: StrictBool
    opening_safety_ends_game: StrictBool


class _OvertimeFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entries: list[OvertimeRule]


@lru_cache(maxsize=4)
def _load(path: Path, mtime_ns: int) -> tuple[OvertimeRule, ...]:
    data = _OvertimeFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    keys = [(e.season, e.postseason) for e in data.entries]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{path}: duplicate overtime entry for a season and game type")
    for e in data.entries:
        if (e.text_read_from == "archive") != (e.archive_url is not None):
            raise ValueError(f"{path}: {e.season}: archive_url must be set exactly for archive")
    return tuple(data.entries)


def load_overtime(path: Path = OVERTIME_PATH) -> tuple[OvertimeRule, ...]:
    return _load(path, path.stat().st_mtime_ns)


def overtime_rule(season: int, *, postseason: bool, path: Path = OVERTIME_PATH) -> OvertimeRule:
    """PRJ-02: the overtime format for `season`; raises OvertimeRuleMissing with no entry."""
    for e in load_overtime(path):
        if e.season == season and e.postseason == postseason:
            return e
    kind = "postseason" if postseason else "regular season"
    raise OvertimeRuleMissing(
        f"PRJ-02: no {kind} overtime entry for season {season} in {path.name}; the simulator "
        "runs only seasons with a sourced overtime format"
    )
