"""PRJ-02 simulator settings from config/sim.yaml (strict: every key required, none extra)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import StrictBool, StrictInt

from ge.config import REPO_ROOT, IntSetting, _Entry, _Group, _Strict

SIM_PATH = REPO_ROOT / "config" / "sim.yaml"


class IntListSetting(_Entry):
    value: list[StrictInt]


class BoolSetting(_Entry):
    value: StrictBool


class RunSettings(_Group):
    chunks: IntSetting


class LeagueSettings(_Group):
    punt_bucket_yards: IntSetting
    fg_miss_bucket_yards: IntSetting
    late_kickoff_seconds: IntSetting
    timeout_drop_from_season: IntSetting  # data correction D (Rhys 2026-11-20)
    min_category_events: IntSetting


class DistillSettings(_Group):
    xpass_togo_bin_upper: IntListSetting  # ruling 2026-10-29 (P3)


class ShortYardageSettings(_Group):
    downs: IntListSetting  # ruling 2026-10-29 (P2)
    max_togo: IntSetting


class SackSettings(_Group):
    distance_upper: IntListSetting  # ruling 2026-10-30 (P5)


class PassDepthSettings(_Group):
    distance_upper: IntListSetting  # ruling 2026-11-02


class SituationYardsSettings(_Group):
    distance_upper: IntListSetting  # ruling 2026-11-03 (P6); runs only (ruling 2026-11-12)


class FourthGoSettings(_Group):
    togo_upper: IntListSetting  # ruling 2026-10-31
    yardline_upper: IntListSetting
    trail_upper: IntListSetting  # ruling 2026-11-12 (G-2)
    late_seconds_upper: IntListSetting


class SticksSettings(_Group):  # ruling 2026-11-12 (S-1)
    togo_min: IntSetting
    togo_max: IntSetting
    distance_upper: IntListSetting
    min_gap: IntSetting
    min_expected: IntSetting


class EarlyFgSettings(_Group):  # early-down field goals (Rhys 2026-11-16)
    enabled: BoolSetting
    max_seconds: IntSetting
    max_yardline: IntSetting
    q4_score_min: IntSetting
    q4_score_max: IntSetting
    periods: IntListSetting


class LateTimeoutsSettings(_Group):  # fix round 2 (Rhys 2026-11-20)
    enabled: BoolSetting
    seconds_upper: IntListSetting


class DiagnosticSettings(_Group):  # diagnostic counters approved 2026-10-30
    red_zone_max_yardline: IntSetting
    fourth_togo_upper: IntListSetting
    fourth_yardline_upper: IntListSetting
    early_deep_air_min: IntSetting
    fg_distance_lower: IntListSetting
    early_fg_seconds_upper: IntListSetting  # approved 2026-11-19 (option B)


class SimSettings(_Strict):
    runs: RunSettings
    league: LeagueSettings
    distill: DistillSettings
    short_yardage: ShortYardageSettings
    sacks: SackSettings
    pass_depth: PassDepthSettings
    situation_yards: SituationYardsSettings
    fourth_go: FourthGoSettings
    sticks: SticksSettings
    early_fg: EarlyFgSettings
    late_timeouts: LateTimeoutsSettings
    diagnostics: DiagnosticSettings


@lru_cache(maxsize=4)
def _load(path: Path, mtime_ns: int) -> SimSettings:
    return SimSettings.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_sim(path: Path = SIM_PATH) -> SimSettings:
    return _load(path, path.stat().st_mtime_ns)
