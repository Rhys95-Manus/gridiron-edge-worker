"""DATA-07 ERA5 ingest (Phase 5 checklist): only outdoor stadiums, only seasons 2016-2024 and
2026 (2025 raises HoldoutReadError before any call), rate-limited by ingest.yaml, and every row
carries pulled_at, source URL and model. Schedules and stadiums here are synthetic placeholders,
not real games; the response is a captured real one (fixtures/era5_gnb_20161211.json)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import numpy as np
import polars as pl
import pytest

from ge.config import load_ingest, load_params
from ge.ingest.raw import read_latest
from ge.ingest.weather_era5 import (
    ERA5_FIELDS,
    ERA5_MODEL,
    Era5Client,
    check_era5_season,
    era5_limiter,
    game_window,
    outdoor_games,
    parse_hourly,
    run_era5,
    schedule_agreement,
)
from ge.store.holdout import HoldoutReadError
from tests.phase5.conftest import load_fixture

FIXTURE = load_fixture("era5_gnb_20161211.json")
PULLED_AT = dt.datetime(2026, 10, 23, 12, 0, tzinfo=dt.UTC)


class FakeHttp:
    """Stands in for PublicClient: records every GET and answers with the captured response."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        self.calls.append((url, params))
        return FIXTURE["response"]


def _stadiums() -> list[dict[str, Any]]:
    return [
        {"stadium_id": "OUT01", "name": "Open Air", "lat": 44.5, "lon": -88.0},
        {"stadium_id": "DOM01", "name": "Covered", "lat": 40.0, "lon": -80.0},
        {"stadium_id": "RET01", "name": "Retractable", "lat": 35.0, "lon": -90.0},
        {"stadium_id": "UNK01", "name": "Unknown Roof", "lat": 30.0, "lon": -95.0},
    ]


def _sched(season: int) -> pl.DataFrame:
    rows = [
        ("G_OUT", "OUT01", "Open Air", "outdoors"),
        ("G_DOME", "DOM01", "Covered", "dome"),
        ("G_CLOSED", "RET01", "Retractable", "closed"),
        ("G_OPEN", "RET01", "Retractable", "open"),
        ("G_UNKNOWN", "UNK01", "Unknown Roof", None),
    ]
    return pl.DataFrame(
        {
            "game_id": [f"{season}_{g}" for g, *_ in rows],
            "season": [season] * len(rows),
            "gameday": [f"{season}-12-11"] * len(rows),
            "gametime": ["16:25"] * len(rows),
            "stadium_id": [r[1] for r in rows],
            "stadium": [r[2] for r in rows],
            "roof": [r[3] for r in rows],
        },
        schema_overrides={"roof": pl.String},
    )


def test_fields_are_the_five_data07_names() -> None:
    assert set(ERA5_FIELDS) == {
        "precipitation",
        "snowfall",
        "wind_speed_10m",
        "wind_gusts_10m",
        "temperature_2m",
    }
    assert ERA5_MODEL == "era5"


@pytest.mark.parametrize("season", [2016, 2020, 2024, 2026])
def test_allowed_seasons(season: int) -> None:
    check_era5_season(season)


def test_2025_raises_holdout_before_any_call(tmp_path: Path) -> None:
    http = FakeHttp()
    with pytest.raises(HoldoutReadError):
        run_era5(
            load_ingest(),
            2025,
            http=http,
            sched=_sched(2025),
            stadiums=_stadiums(),
            pulled_at=PULLED_AT,
            root=tmp_path,
        )
    assert http.calls == []
    assert not any(tmp_path.iterdir())


@pytest.mark.parametrize("season", [2015, 2027])
def test_seasons_outside_scope_raise(season: int) -> None:
    with pytest.raises(ValueError, match="DATA-07"):
        check_era5_season(season)


def test_only_outdoor_open_and_unknown_roof_games_are_requested() -> None:
    games = outdoor_games(_sched(2016), _stadiums())
    assert sorted(games["game_id"].to_list()) == ["2016_G_OPEN", "2016_G_OUT", "2016_G_UNKNOWN"]
    unknown = games.filter(pl.col("game_id") == "2016_G_UNKNOWN")
    assert unknown["weather_status"].to_list() == ["pull_roof_unknown"]


def test_request_asks_for_era5_hourly_fields_in_gmt() -> None:
    http = FakeHttp()
    cfg = load_ingest().open_meteo
    url, body = Era5Client(http, cfg).hourly(  # type: ignore[arg-type]
        44.5, -88.0, dt.date(2016, 12, 11), dt.date(2016, 12, 12)
    )
    assert body == FIXTURE["response"]
    sent_url, params = http.calls[0]
    assert sent_url == cfg.archive_url.value
    assert params is not None
    assert params["models"] == ERA5_MODEL
    assert params["timezone"] == "GMT"
    assert params["hourly"].split(",") == list(ERA5_FIELDS)
    # The recorded source URL is the full request, so a row can be re-pulled from it.
    q = parse_qs(urlsplit(url).query)
    assert q["models"] == [ERA5_MODEL]
    assert q["start_date"] == ["2016-12-11"] and q["end_date"] == ["2016-12-12"]


def test_parse_keeps_open_meteo_units_and_hours_in_utc() -> None:
    rows = parse_hourly(FIXTURE["response"])
    resp = FIXTURE["response"]
    assert len(rows) == len(resp["hourly"]["time"]) * len(ERA5_FIELDS)
    for field in ERA5_FIELDS:
        units = {r["uom"] for r in rows if r["field"] == field}
        assert units == {resp["hourly_units"][field]}, field
    first = rows[0]
    assert first["valid_hour"] == dt.datetime(2016, 12, 11, 0, 0, tzinfo=dt.UTC)


def test_every_stored_row_carries_pulled_at_source_url_and_model(tmp_path: Path) -> None:
    http = FakeHttp()
    run_era5(
        load_ingest(),
        2016,
        http=http,
        sched=_sched(2016),
        stadiums=_stadiums(),
        pulled_at=PULLED_AT,
        root=tmp_path,
    )
    assert len(http.calls) == 3  # one request per outdoor, open or unknown-roof game
    hourly = read_latest(tmp_path, "era5_hourly", 2016)
    assert hourly.height > 0
    assert hourly["pulled_at"].null_count() == 0
    assert set(hourly["model"].unique().to_list()) == {ERA5_MODEL}
    urls = hourly["source_url"].unique().to_list()
    assert urls and all(u.startswith(load_ingest().open_meteo.archive_url.value) for u in urls)
    games = read_latest(tmp_path, "era5_game_window", 2016)
    assert sorted(games["game_id"].to_list()) == ["2016_G_OPEN", "2016_G_OUT", "2016_G_UNKNOWN"]
    assert set(games["label"].unique().to_list()) == {"observed_as_forecast_proxy"}
    assert games["pulled_at"].null_count() == 0 and games["source_url"].null_count() == 0
    assert set(games["model"].unique().to_list()) == {ERA5_MODEL}


def _window(kickoff: dt.datetime) -> dict[str, float]:
    hours = float(load_params().environment.mtc_05_game_window_hours.value)
    return game_window(parse_hourly(FIXTURE["response"]), kickoff, hours)


def test_window_on_the_hour_kickoff_hand_computed() -> None:
    """Kickoff 18:00 UTC (a test setting), window [18:00, 22:00], fixture values.
    Accumulations (hour-ending totals) count when (t - 1 h, t) overlaps the window by more than
    an instant: stamps 19:00-22:00. Precipitation 0.5 + 0.2 + 0.0 + 0.0 = 0.7 mm; snowfall
    0.35 + 0.14 + 0.07 + 0.0 = 0.56 cm. (Stamp 18:00 is the hour 17-18, wholly before kickoff;
    stamp 23:00 is 22-23, wholly after.)
    Instantaneous values count when the stamp is inside [18:00, 22:00]: stamps 18-22.
    Wind mean (9.7 + 8.2 + 7.4 + 6.0 + 3.8) / 5 = 7.02 km/h; gusts max 21.6 km/h;
    temperature mean (-2.1 - 2.3 - 2.6 - 2.7 - 2.7) / 5 = -2.48 C."""
    w = _window(dt.datetime(2016, 12, 11, 18, 0, tzinfo=dt.UTC))
    assert w["precipitation_mm"] == pytest.approx(0.7)
    assert w["snowfall_cm"] == pytest.approx(0.56)
    assert w["wind_speed_kmh"] == pytest.approx(7.02)
    assert w["wind_gusts_kmh"] == pytest.approx(21.6)
    assert w["temperature_c"] == pytest.approx(-2.48)
    assert (w["accumulation_hours"], w["instant_hours"]) == (4, 5)


def test_window_off_the_hour_kickoff_hand_computed() -> None:
    """Kickoff 19:25 UTC (a test setting), window [19:25, 23:25].
    Accumulations: stamps 20:00-00:00 (the hour 23-00 overlaps 23:00-23:25):
    precipitation 0.2 + 0 + 0 + 0 + 0 = 0.2 mm; snowfall 0.14 + 0.07 = 0.21 cm.
    Instantaneous: stamps 20:00-23:00 (19:00 is before kickoff, 00:00 after the window):
    wind (7.4 + 6.0 + 3.8 + 4.0) / 4 = 5.3; gusts max 17.6; temperature
    (-2.6 - 2.7 - 2.7 - 3.3) / 4 = -2.825."""
    w = _window(dt.datetime(2016, 12, 11, 19, 25, tzinfo=dt.UTC))
    assert w["precipitation_mm"] == pytest.approx(0.2)
    assert w["snowfall_cm"] == pytest.approx(0.21)
    assert w["wind_speed_kmh"] == pytest.approx(5.3)
    assert w["wind_gusts_kmh"] == pytest.approx(17.6)
    assert w["temperature_c"] == pytest.approx(-2.825)
    assert (w["accumulation_hours"], w["instant_hours"]) == (5, 4)


def test_window_missing_hours_raise() -> None:
    """A window the response does not cover is an error, never a partial aggregate."""
    with pytest.raises(ValueError, match="MTC-05"):
        _window(dt.datetime(2016, 12, 12, 22, 0, tzinfo=dt.UTC))


def test_schedule_agreement_hand_computed() -> None:
    """Phase 5 report: ERA5 vs schedules temp and wind per season. Three synthetic games:
    schedule wind 10, 20, 30 mph -> 16.09344, 32.18688, 48.28032 km/h; ERA5 wind 17, 30, 50.
    Differences (ERA5 - schedules): 0.90656, -2.18688, 1.71968; mean 0.14645...; correlation of
    (17, 30, 50) with (10, 20, 30) = 0.99587... Schedule temp = 32 + 1.8 x ERA5 exactly for the
    three games, so the fitted line has intercept 32 and slope 1.8 (no unit is assumed: the fit
    shows it)."""
    sched = pl.DataFrame(
        {
            "game_id": ["a", "b", "c"],
            "season": [2016] * 3,
            "temp": [50.0, 68.0, 86.0],
            "wind": [10.0, 20.0, 30.0],
        }
    )
    windows = pl.DataFrame(
        {
            "game_id": ["a", "b", "c"],
            "temperature_c": [10.0, 20.0, 30.0],
            "wind_speed_kmh": [17.0, 30.0, 50.0],
        }
    )
    out = schedule_agreement(sched, windows, mph_to_kmh=1.609344).row(0, named=True)
    diffs = [17 - 16.09344, 30 - 32.18688, 50 - 48.28032]
    assert out["games"] == 3
    assert out["wind_mean_diff_kmh"] == pytest.approx(sum(diffs) / 3)
    mean = sum(diffs) / 3
    sd = (sum((d - mean) ** 2 for d in diffs) / 2) ** 0.5
    assert out["wind_sd_diff_kmh"] == pytest.approx(sd)
    assert out["wind_corr"] == pytest.approx(float(np.corrcoef([17, 30, 50], [10, 20, 30])[0, 1]))
    assert out["temp_corr"] == pytest.approx(1.0)
    assert out["temp_fit_intercept"] == pytest.approx(32.0)
    assert out["temp_fit_slope"] == pytest.approx(1.8)


def test_rate_comes_from_ingest_yaml_and_stays_below_the_free_tier() -> None:
    cfg = load_ingest().open_meteo
    limiter = era5_limiter(cfg)
    assert limiter.rate == cfg.requests_per_second.value
    # DATA-07 terms: "Less than 10'000 API calls per day, 5'000 per hour and 600 per minute".
    assert limiter.rate * 60 < 600
    assert limiter.rate * 3600 < 5000


def test_limiter_spaces_requests_at_the_configured_rate() -> None:
    cfg = load_ingest().open_meteo
    now = [0.0]
    slept: list[float] = []

    def sleep(s: float) -> None:
        slept.append(s)
        now[0] += s

    limiter = era5_limiter(cfg, clock=lambda: now[0], sleep=sleep)
    for _ in range(10):
        limiter.wait()
    assert now[0] == pytest.approx(9 / cfg.requests_per_second.value)
