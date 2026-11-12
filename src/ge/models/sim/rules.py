"""PRJ-02 game-rule constants from config/game_rules.yaml (ruling E2, 2026-10-24): points per
score, the line to gain, downs per series, field length, periods, timeouts and the two-minute
warning, each sourced to the official rulebook for the seasons it covers; and the kickoff eras
(K1, rulings 2026-11-01 and 2026-11-02): seasons with the same free-kick touchback spot text."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

from ge.config import REPO_ROOT, SpecId

GAME_RULES_PATH = REPO_ROOT / "config" / "game_rules.yaml"
_Text = Annotated[str, StringConstraints(min_length=1)]


class GameRuleMissing(NotImplementedError):
    """PRJ-02: no sourced value of this rule for the season."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuleSource(_Strict):
    text_read_from: Literal["archive", "live"]
    archive_url: _Text | None
    original_url: _Text
    capture_date: Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]


class GameRule(_Strict):
    spec_id: SpecId
    status: Literal["initial"]
    value: StrictInt
    quotes: Annotated[list[_Text], Field(min_length=1)]
    seasons: Annotated[list[StrictInt], Field(min_length=1)]


class KickoffEra(_Strict):
    spec_id: SpecId
    status: Literal["initial"]
    quotes: Annotated[list[_Text], Field(min_length=1)]
    seasons: Annotated[list[StrictInt], Field(min_length=1)]
    absent_in: list[StrictInt]  # captured seasons whose text was checked and has no quote


class GameRulesFile(_Strict):
    sources: dict[int, RuleSource]
    rules: dict[str, GameRule]
    kickoff_eras: dict[str, KickoffEra]


MAX_QUOTE_WORDS = 14  # quotes are under 15 words (game_rules.yaml header)


@lru_cache(maxsize=4)
def _load(path: Path, mtime_ns: int) -> GameRulesFile:
    f = GameRulesFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    for key, r in f.rules.items():
        missing = sorted(set(r.seasons) - set(f.sources))
        if missing:
            raise ValueError(f"{path}: {key} covers seasons {missing} with no source")
    seen: dict[int, str] = {}
    for key, e in f.kickoff_eras.items():
        missing = sorted((set(e.seasons) | set(e.absent_in)) - set(f.sources))
        if missing:
            raise ValueError(f"{path}: kickoff era {key} names seasons {missing} with no source")
        if set(e.seasons) & set(e.absent_in):
            raise ValueError(f"{path}: kickoff era {key} lists a season as both found and absent")
        if any(len(q.split()) > MAX_QUOTE_WORDS for q in e.quotes):
            raise ValueError(f"{path}: kickoff era {key} has a quote of 15 words or more")
        for s in e.seasons:
            if s in seen:
                raise ValueError(f"{path}: season {s} is in kickoff era {seen[s]} and {key}")
            seen[s] = key
    return f


def load_game_rules(path: Path = GAME_RULES_PATH) -> GameRulesFile:
    return _load(path, path.stat().st_mtime_ns)


def game_rule(key: str, season: int, path: Path = GAME_RULES_PATH) -> int:
    """PRJ-02: a rule value for `season`; raises GameRuleMissing when not sourced for it."""
    f = load_game_rules(path)
    r = f.rules.get(key)
    if r is None or season not in r.seasons:
        raise GameRuleMissing(
            f"PRJ-02: game rule {key!r} has no sourced value for season {season} in {path.name}"
        )
    return r.value


def kickoff_era(season: int, path: Path = GAME_RULES_PATH) -> str:
    """PRJ-02 (K1, ruling 2026-11-01): the kickoff era of `season`; raises GameRuleMissing when
    no era lists it."""
    for key, e in load_game_rules(path).kickoff_eras.items():
        if season in e.seasons:
            return key
    raise GameRuleMissing(f"PRJ-02: season {season} is in no kickoff era in {path.name}")
