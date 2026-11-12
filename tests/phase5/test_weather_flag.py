"""MTC-05 "Weather risk not modelled (fallback only)" (Phase 5 checklist).

An outdoor (or unknown-roof) game is flagged when it has no NWS forecast at decision time, or
when an effect came out no-signal and the forecast shows that weather in the game window:
precipitation or snow no-signal with quantitativePrecipitation > 0, snowfallAmount > 0 or
probabilityOfPrecipitation >= the threshold; gusts no-signal with windGust >= the threshold.
A fitted (signal) effect never flags; a dome never. In a flagged game, passing and receiving
props (and combos with such a leg) are excluded, and every market carries the flag.

Forecast rows use the stored NWS shape (field, valid_hour, value, uom) and NWS's own units
(wmoUnit:mm, wmoUnit:percent, wmoUnit:km_h-1, as in tests/phase1/fixtures/nws_gridpoint.json).
Every forecast hour below lies strictly inside the game window, so the test does not depend on
which boundary hours belong to it."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest

from ge.config import load_params
from ge.models.sim.weather_flag import (
    PROP_FAMILIES_EXCLUDED,
    excluded_when_flagged,
    flag_factors,
    weather_risk,
)

KICKOFF = dt.datetime(2026, 12, 13, 18, 0, tzinfo=dt.UTC)
UOM = {
    "quantitativePrecipitation": "wmoUnit:mm",
    "snowfallAmount": "wmoUnit:mm",
    "probabilityOfPrecipitation": "wmoUnit:percent",
    "windGust": "wmoUnit:km_h-1",
    "windSpeed": "wmoUnit:km_h-1",
    "temperature": "wmoUnit:degC",
}
ENV = load_params().environment
POP_T = float(ENV.mtc_05_flag_precip_probability_pct.value)
GUST_T = float(ENV.mtc_05_flag_gust_kmh.value)


def _calm(**over: float) -> list[dict[str, Any]]:
    """Two forecast hours inside the window, dry and calm unless overridden."""
    base = {
        "quantitativePrecipitation": 0.0,
        "snowfallAmount": 0.0,
        "probabilityOfPrecipitation": 0.0,
        "windGust": 0.0,
        "windSpeed": 5.0,
        "temperature": 5.0,
    }
    base.update(over)
    rows = []
    for h in (1, 2):
        t = KICKOFF + dt.timedelta(hours=h)
        rows.extend(
            {"field": f, "valid_hour": t, "value": v, "uom": UOM[f]} for f, v in base.items()
        )
    return rows


ALL_NO_SIGNAL = {"precipitation", "snowfall", "wind_gusts"}


@pytest.mark.parametrize("roof", ["outdoors", "open", None])
def test_no_forecast_flags_outdoor_and_unknown_roof(roof: str | None) -> None:
    flag = weather_risk(roof=roof, forecast=None, kickoff_utc=KICKOFF, no_signal=set())
    assert flag.flagged
    assert any("no NWS forecast" in r for r in flag.reasons)


@pytest.mark.parametrize("roof", ["dome", "closed"])
def test_dome_never_flags(roof: str) -> None:
    flag = weather_risk(
        roof=roof,
        forecast=None,
        kickoff_utc=KICKOFF,
        no_signal=ALL_NO_SIGNAL,
    )
    assert not flag.flagged


@pytest.mark.parametrize(
    ("factor", "forecast"),
    [
        ("precipitation", {"quantitativePrecipitation": 0.5}),
        ("precipitation", {"probabilityOfPrecipitation": POP_T}),
        ("snowfall", {"snowfallAmount": 2.0}),
        ("snowfall", {"probabilityOfPrecipitation": POP_T + 10}),
        ("wind_gusts", {"windGust": GUST_T}),
        ("wind_gusts", {"windGust": GUST_T + 15}),
    ],
)
def test_no_signal_effect_plus_forecast_at_threshold_flags(
    factor: str, forecast: dict[str, float]
) -> None:
    flag = weather_risk(
        roof="outdoors", forecast=_calm(**forecast), kickoff_utc=KICKOFF, no_signal={factor}
    )
    assert flag.flagged
    assert flag.values, "the flag shows the forecast values that set it"


@pytest.mark.parametrize(
    "forecast",
    [
        {"quantitativePrecipitation": 3.0, "probabilityOfPrecipitation": 90.0},
        {"snowfallAmount": 20.0},
        {"windGust": GUST_T + 40},
    ],
)
def test_signal_effects_never_flag(forecast: dict[str, float]) -> None:
    flag = weather_risk(
        roof="outdoors", forecast=_calm(**forecast), kickoff_utc=KICKOFF, no_signal=set()
    )
    assert not flag.flagged


def test_below_threshold_does_not_flag() -> None:
    flag = weather_risk(
        roof="outdoors",
        forecast=_calm(probabilityOfPrecipitation=POP_T - 1, windGust=GUST_T - 1),
        kickoff_utc=KICKOFF,
        no_signal=ALL_NO_SIGNAL,
    )
    assert not flag.flagged


def test_unknown_unit_raises() -> None:
    rows = _calm(windGust=GUST_T)
    for r in rows:
        if r["field"] == "windGust":
            r["uom"] = "wmoUnit:m_s-1"
    with pytest.raises(ValueError, match="MTC-05"):
        weather_risk(roof="outdoors", forecast=rows, kickoff_utc=KICKOFF, no_signal={"wind_gusts"})


def test_flag_factors_come_from_passing_effects_only() -> None:
    """Ruling B3 (2026-10-23): a factor counts as no-signal for the flag only if its effect on a
    passing outcome (completion or deep-attempt share) is no-signal; field-goal effects never
    count."""
    no_signal = {
        ("wind_gusts", "completion"): False,
        ("wind_gusts", "deep_attempt"): True,  # one passing effect no-signal: counts
        ("wind_gusts", "fg_make"): False,
        ("precipitation", "completion"): False,
        ("precipitation", "deep_attempt"): False,
        ("snowfall", "completion"): False,
        ("snowfall", "deep_attempt"): False,
        ("snowfall", "fg_make"): True,  # field-goal only: does not count
    }
    assert flag_factors(no_signal) == {"wind_gusts"}


def test_excluded_prop_families_are_passing_and_receiving() -> None:
    assert set(PROP_FAMILIES_EXCLUDED) == {
        "passing_yards",
        "passing_tds",
        "receiving_yards",
        "receptions",
    }


@pytest.mark.parametrize(
    ("legs", "excluded"),
    [
        (["passing_yards"], True),
        (["receptions"], True),
        (["rushing_yards"], False),
        (["anytime_td"], False),
        (["rushing_yards", "receiving_yards"], True),  # a combo with such a leg
        (["rushing_yards", "anytime_td"], False),
    ],
)
def test_flagged_game_excludes_passing_and_receiving_legs(legs: list[str], excluded: bool) -> None:
    assert excluded_when_flagged(legs) is excluded
