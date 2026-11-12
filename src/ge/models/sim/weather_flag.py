"""MTC-05 "Weather risk not modelled (fallback only)" (spec synced 2026-10-23).

An outdoor game, or one whose roof the data does not settle, is flagged when it has no NWS
forecast at decision time, or when a weather factor came out no-signal and the forecast shows
that weather in any hour of the game window: precipitation or snow no-signal with
quantitativePrecipitation > 0, snowfallAmount > 0 or probabilityOfPrecipitation >= the
threshold; gusts no-signal with windGust >= the threshold. A factor counts as no-signal only
through its passing effects (completion or deep-attempt share), never its field-goal effect
(ruling B3). NWS values cover the hour starting at valid_hour; an hour counts when it overlaps
the game window by more than an instant (ruling A1). Units are checked explicitly.

In a flagged game, passing and receiving props (and any combo with such a leg) are excluded
from the shadow log and from recommendations; every market in the game shows the flag."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from ge.config import load_params
from ge.fit.weather import PASSING_OUTCOMES

PROP_FAMILIES_EXCLUDED = ("passing_yards", "passing_tds", "receiving_yards", "receptions")
_PRECIP_FACTORS = ("precipitation", "snowfall")
# NWS field -> the unit the thresholds are written in (MTC-05: precipitation and snowfall in
# mm-based amounts only compared with 0; probability in percent; gusts in km/h).
_UNITS = {
    "quantitativePrecipitation": "wmoUnit:mm",
    "snowfallAmount": "wmoUnit:mm",
    "probabilityOfPrecipitation": "wmoUnit:percent",
    "windGust": "wmoUnit:km_h-1",
}
_HOUR = dt.timedelta(hours=1)


@dataclass(frozen=True)
class WeatherFlag:
    flagged: bool
    reasons: list[str] = field(default_factory=list)
    values: dict[str, float] = field(default_factory=dict)  # forecast values that set it


def flag_factors(no_signal: Mapping[tuple[str, str], bool]) -> set[str]:
    """Ruling B3: factors no-signal on at least one passing outcome. Field-goal effects never
    count."""
    return {f for (f, outcome), ns in no_signal.items() if ns and outcome in PASSING_OUTCOMES}


def _window_maxima(
    forecast: Iterable[Mapping[str, Any]], kickoff_utc: dt.datetime, hours: float
) -> dict[str, float]:
    end = kickoff_utc + dt.timedelta(hours=hours)
    out: dict[str, float] = {}
    for r in forecast:
        f = r["field"]
        if f not in _UNITS:
            continue
        if r["uom"] != _UNITS[f]:
            raise ValueError(f"MTC-05: NWS {f} in {r['uom']!r}, expected {_UNITS[f]!r}")
        start = r["valid_hour"]
        if not (start < end and start + _HOUR > kickoff_utc) or r["value"] is None:
            continue
        out[f] = max(out.get(f, float("-inf")), float(r["value"]))
    return out


def weather_risk(
    *,
    roof: str | None,
    forecast: Iterable[Mapping[str, Any]] | None,
    kickoff_utc: dt.datetime,
    no_signal: set[str],
) -> WeatherFlag:
    """MTC-05 fallback flag for one game. `no_signal` holds the factors from flag_factors."""
    if roof in ("dome", "closed"):
        return WeatherFlag(False)
    if roof not in ("outdoors", "open", None):
        raise ValueError(f"MTC-05: unknown roof value {roof!r}")
    rows = list(forecast) if forecast is not None else []
    if not rows:
        return WeatherFlag(True, ["no NWS forecast at decision time"])
    env = load_params().environment
    hours = float(env.mtc_05_game_window_hours.value)
    pop_t = float(env.mtc_05_flag_precip_probability_pct.value)
    gust_t = float(env.mtc_05_flag_gust_kmh.value)
    mx = _window_maxima(rows, kickoff_utc, hours)
    reasons: list[str] = []
    values: dict[str, float] = {}
    precip_ns = sorted(set(_PRECIP_FACTORS) & no_signal)
    if precip_ns:
        hit = {
            k: v
            for k, v in mx.items()
            if (k in ("quantitativePrecipitation", "snowfallAmount") and v > 0)
            or (k == "probabilityOfPrecipitation" and v >= pop_t)
        }
        if hit:
            reasons.append(f"{' and '.join(precip_ns)} no-signal; forecast shows precipitation")
            values.update(hit)
    if "wind_gusts" in no_signal and mx.get("windGust", float("-inf")) >= gust_t:
        reasons.append(f"gusts no-signal; forecast gusts >= {gust_t:g} km/h")
        values["windGust"] = mx["windGust"]
    return WeatherFlag(bool(reasons), reasons, values)


def excluded_when_flagged(legs: Iterable[str]) -> bool:
    """MTC-05: a market (or combo) with any passing or receiving leg is excluded in a flagged
    game."""
    return any(leg in PROP_FAMILIES_EXCLUDED for leg in legs)
