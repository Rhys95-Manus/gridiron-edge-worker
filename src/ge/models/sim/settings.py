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


class RunSettings(_Group):
    chunks: IntSetting


class LeagueSettings(_Group):
    punt_bucket_yards: IntSetting
    fg_miss_bucket_yards: IntSetting
    late_kickoff_seconds: IntSetting
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


class BoolSetting(_Entry):
    value: StrictBool


class SituationYardsSettings(_Group):
    distance_upper: IntListSetting  # ruling 2026-11-03 (P6)
    yac_by_situation: BoolSetting  # ruling 2026-11-11 (P6s)


class FourthGoSettings(_Group):
    togo_upper: IntListSetting  # ruling 2026-10-31
    yardline_upper: IntListSetting


class DiagnosticSettings(_Group):  # diagnostic counters approved 2026-10-30
    red_zone_max_yardline: IntSetting
    fourth_togo_upper: IntListSetting
    fourth_yardline_upper: IntListSetting
    early_deep_air_min: IntSetting
    fg_distance_lower: IntListSetting


class SimSettings(_Strict):
    runs: RunSettings
    league: LeagueSettings
    distill: DistillSettings
    short_yardage: ShortYardageSettings
    sacks: SackSettings
    pass_depth: PassDepthSettings
    situation_yards: SituationYardsSettings
    fourth_go: FourthGoSettings
    diagnostics: DiagnosticSettings


@lru_cache(maxsize=4)
def _load(path: Path, mtime_ns: int) -> SimSettings:
    return SimSettings.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_sim(path: Path = SIM_PATH) -> SimSettings:
    return _load(path, path.stat().st_mtime_ns)
