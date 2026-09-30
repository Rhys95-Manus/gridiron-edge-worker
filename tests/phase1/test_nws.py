"""DATA-06: NWS gridpoint series expand to hourly rows in NWS's own units; outdoor games are
pulled, dome/closed skipped, unknown roofs pulled and flagged, non-US points marked unknown."""

import datetime as dt
import functools
import re
from typing import Any

import pytest

from ge.ingest.weather_nws import (
    GRID_FIELDS,
    classify_game,
    expand_series,
    parse_gridpoint,
    points_status,
)
from tests.phase1.conftest import load_fixture


@functools.cache
def _grid() -> Any:
    return load_fixture("nws_gridpoint.json")["response"]


def _hours(duration: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?)?", duration)
    assert m, duration
    return int(m.group(1) or 0) * 24 + int(m.group(2) or 0)


def test_grid_fields_are_the_five_the_spec_asks_for() -> None:
    assert set(GRID_FIELDS) == {
        "temperature",
        "windSpeed",
        "windGust",
        "probabilityOfPrecipitation",
        "quantitativePrecipitation",
    }


@pytest.mark.parametrize("field", ["temperature", "windSpeed", "windGust"])
def test_intervals_expand_to_one_row_per_hour(field: str) -> None:
    series = _grid()["properties"][field]
    rows = expand_series(series)
    assert len(rows) == sum(_hours(v["validTime"].split("/")[1]) for v in series["values"])
    first = series["values"][0]
    start = dt.datetime.fromisoformat(first["validTime"].split("/")[0])
    assert rows[0] == (start, first["value"])
    # Every row of a 5-hour interval carries that interval's value, one hour apart.
    k = _hours(first["validTime"].split("/")[1])
    assert rows[:k] == [(start + dt.timedelta(hours=h), first["value"]) for h in range(k)]
    times = [t for t, _ in rows]
    assert times == sorted(set(times)), "hours must be unique and increasing"


def test_parse_keeps_nws_units() -> None:
    table = parse_gridpoint(_grid())
    for field in GRID_FIELDS:
        uom = _grid()["properties"][field]["uom"]
        units = {r["uom"] for r in table if r["field"] == field}
        assert units == {uom}, field


def test_outside_nws_coverage_is_no_weather_source() -> None:
    fx = load_fixture("nws_points_outside.json")
    assert points_status(fx["status_code"], fx["response"]) == "no_weather_source"


def test_real_us_point_is_covered() -> None:
    fx = load_fixture("nws_points.json")
    assert points_status(200, fx["response"]) == "ok"


@pytest.mark.parametrize(
    ("roof", "expected"),
    [
        ("outdoors", "pull"),
        ("open", "pull"),
        ("dome", "skip_roof"),
        ("closed", "skip_roof"),
        (None, "pull_roof_unknown"),
    ],
)
def test_roof_rules(roof: str | None, expected: str) -> None:
    assert classify_game(roof=roof, has_coordinates=True) == expected


def test_no_coordinates_means_unknown_weather() -> None:
    assert classify_game(roof="outdoors", has_coordinates=False) == "no_coordinates"
