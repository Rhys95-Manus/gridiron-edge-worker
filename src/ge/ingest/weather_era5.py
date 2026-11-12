"""DATA-07 Open-Meteo ERA5 history for the MTC-05 / ENV fits (spec synced 2026-10-23).

Hourly `precipitation`, `snowfall`, `wind_speed_10m`, `wind_gusts_10m` and `temperature_2m` at
each outdoor (or open, or unknown-roof) stadium's coordinates, one request per game covering the
UTC dates its game window touches (ruling A3). Seasons 2016-2024 and 2026 only; 2025 raises
HoldoutReadError before any request. Values keep Open-Meteo's units (the uom column); the
game-window aggregates are labelled observed_as_forecast_proxy, like schedules' temp and wind.

Game window (MTC-05, ruling A1, 2026-10-23): kickoff to kickoff + the window length.
Open-Meteo's precipitation and snowfall are totals over the hour ending at the stamp
("sum of the preceding hour"); an hour counts when (t - 1 h, t) overlaps the window by more
than an instant. Wind, gusts and temperature are values at the stamp; a stamp counts when it
lies in [kickoff, kickoff + window]. Totals for the accumulations, mean wind and temperature,
maximum gust. Data: Open-Meteo (ERA5), CC BY 4.0."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode

import numpy as np
import polars as pl

from ge.config import IngestConfig, OpenMeteoSettings, load_params
from ge.ingest.http import RateLimiter
from ge.ingest.raw import DATA_ROOT, write_raw
from ge.ingest.stadiums import stadium_for_game
from ge.ingest.weather_nws import classify_game
from ge.store.holdout import refuse_holdout
from ge.store.known_at import with_kickoff

ERA5_FIELDS = (
    "precipitation",
    "snowfall",
    "wind_speed_10m",
    "wind_gusts_10m",
    "temperature_2m",
)
ERA5_MODEL = "era5"
ACCUMULATED = ("precipitation", "snowfall")  # hour-ending totals
LABEL = "observed_as_forecast_proxy"
ATTRIBUTION = "Weather: Open-Meteo.com (ERA5 reanalysis), CC BY 4.0"
_HOUR = dt.timedelta(hours=1)


class _Http(Protocol):
    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any: ...


def check_era5_season(season: int) -> None:
    """DATA-07: seasons 2016-2024 and 2026 only. The holdout raises HoldoutReadError (BT-07b);
    any other season outside the list raises ValueError."""
    refuse_holdout(season, "DATA-07 ERA5 ingest")
    bt = load_params().backtest
    first = int(bt.bt_01_first_training_season.value)
    hold = int(bt.bt_01_holdout_season.value)
    allowed = [*range(first, hold), hold + 1]
    if season not in allowed:
        raise ValueError(
            f"DATA-07: ERA5 is ingested only for seasons {first}-{hold - 1} and {hold + 1}; "
            f"{season} refused"
        )


def era5_limiter(
    cfg: OpenMeteoSettings,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> RateLimiter:
    """DATA-07: requests spaced at the ingest.yaml rate (ruling A2, 2026-10-23)."""
    kw: dict[str, Any] = {}
    if clock is not None:
        kw["clock"] = clock
    if sleep is not None:
        kw["sleep"] = sleep
    return RateLimiter(float(cfg.requests_per_second.value), **kw)


class Era5Client:
    def __init__(self, http: _Http, cfg: OpenMeteoSettings) -> None:
        self._http = http
        self._url = cfg.archive_url.value
        self._model = cfg.model.value

    def hourly(
        self, lat: float, lon: float, start: dt.date, end: dt.date
    ) -> tuple[str, dict[str, Any]]:
        """DATA-07: one archive request; returns (full request URL, response body)."""
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": ",".join(ERA5_FIELDS),
            "models": self._model,
            "timezone": "GMT",
        }
        body = self._http.get_json(self._url, params)
        return f"{self._url}?{urlencode(params)}", dict(body)


def parse_hourly(body: Mapping[str, Any]) -> list[dict[str, Any]]:
    """DATA-07: rows {field, valid_hour (UTC), value, uom}. The request asks for GMT, so a
    response in any other time zone is refused rather than shifted."""
    if body.get("utc_offset_seconds") != 0:
        raise ValueError(f"DATA-07: expected a GMT response, got {body.get('timezone')!r}")
    hourly, units = body["hourly"], body["hourly_units"]
    times = [dt.datetime.fromisoformat(t).replace(tzinfo=dt.UTC) for t in hourly["time"]]
    rows: list[dict[str, Any]] = []
    for field in ERA5_FIELDS:
        rows.extend(
            {"field": field, "valid_hour": t, "value": v, "uom": units[field]}
            for t, v in zip(times, hourly[field], strict=True)
        )
    return rows


def window_dates(kickoff_utc: dt.datetime, hours: float) -> tuple[dt.date, dt.date]:
    """UTC dates from the first hour-ending total that can count to the window's end."""
    return kickoff_utc.date(), (kickoff_utc + dt.timedelta(hours=hours) + _HOUR).date()


def game_window(
    rows: Iterable[Mapping[str, Any]], kickoff_utc: dt.datetime, hours: float
) -> dict[str, float]:
    """MTC-05 game-window values (ruling A1). Raises when the rows do not cover the window."""
    end = kickoff_utc + dt.timedelta(hours=hours)
    by_field: dict[str, dict[dt.datetime, Any]] = {f: {} for f in ERA5_FIELDS}
    for r in rows:
        if r["field"] in by_field:
            by_field[r["field"]][r["valid_hour"]] = r["value"]

    def stamps_acc() -> list[dt.datetime]:
        t = kickoff_utc.replace(minute=0, second=0, microsecond=0) + _HOUR
        out = []
        while t - _HOUR < end:
            out.append(t)
            t += _HOUR
        return out

    def stamps_inst() -> list[dt.datetime]:
        t = kickoff_utc.replace(minute=0, second=0, microsecond=0)
        if t < kickoff_utc:
            t += _HOUR
        out = []
        while t <= end:
            out.append(t)
            t += _HOUR
        return out

    def values(field: str, stamps: list[dt.datetime]) -> list[float]:
        got = by_field[field]
        missing = [t for t in stamps if got.get(t) is None]
        if missing:
            raise ValueError(
                f"MTC-05: {field} has no value for {len(missing)} hour(s) of the game window "
                f"starting {kickoff_utc.isoformat()} (first {missing[0].isoformat()})"
            )
        return [float(got[t]) for t in stamps]

    acc, inst = stamps_acc(), stamps_inst()
    wind = values("wind_speed_10m", inst)
    temp = values("temperature_2m", inst)
    return {
        "precipitation_mm": sum(values("precipitation", acc)),
        "snowfall_cm": sum(values("snowfall", acc)),
        "wind_speed_kmh": sum(wind) / len(wind),
        "wind_gusts_kmh": max(values("wind_gusts_10m", inst)),
        "temperature_c": sum(temp) / len(temp),
        "accumulation_hours": len(acc),
        "instant_hours": len(inst),
    }


def outdoor_games(sched: pl.DataFrame, stadiums: list[dict[str, Any]]) -> pl.DataFrame:
    """MTC-05: games whose weather counts (roof outdoors, open, or unknown) and whose stadium
    has coordinates, with kickoff_utc."""
    rows = []
    for g in with_kickoff(sched).iter_rows(named=True):
        st = stadium_for_game(stadiums, g["stadium_id"], g["stadium"]) or {}
        has_xy = st.get("lat") is not None and st.get("lon") is not None
        status = classify_game(roof=g["roof"], has_coordinates=has_xy)
        if status in ("pull", "pull_roof_unknown"):
            rows.append(
                {
                    "game_id": g["game_id"],
                    "kickoff_utc": g["kickoff_utc"],
                    "stadium_id": g["stadium_id"],
                    "roof": g["roof"],
                    "lat": float(st["lat"]),
                    "lon": float(st["lon"]),
                    "weather_status": status,
                }
            )
    schema = pl.Schema(
        {
            "game_id": pl.String(),
            "kickoff_utc": pl.Datetime("us", "UTC"),
            "stadium_id": pl.String(),
            "roof": pl.String(),
            "lat": pl.Float64(),
            "lon": pl.Float64(),
            "weather_status": pl.String(),
        }
    )
    return pl.DataFrame(rows, schema=schema)


def schedule_agreement(
    sched: pl.DataFrame, windows: pl.DataFrame, *, mph_to_kmh: float
) -> pl.DataFrame:
    """MTC-05 cross-check (Phase 5 report): per season, ERA5 game-window values against
    schedules' temp and wind (kept as a cross-check only). Wind: schedules give mph (nflverse
    dictionary), converted explicitly; correlation, mean and SD of (ERA5 - schedules) in km/h.
    Temperature: the dictionary states no unit, so only the correlation and the least-squares
    line schedules temp = a + b x ERA5 C are reported, which show the unit without assuming it."""
    j = sched.select("game_id", "season", "temp", "wind").join(
        windows.select("game_id", "temperature_c", "wind_speed_kmh"), on="game_id", how="inner"
    )
    rows = []
    for season in sorted(j["season"].unique().to_list()):
        g = j.filter(pl.col("season") == season)
        w = g.drop_nulls(["wind", "wind_speed_kmh"])
        t = g.drop_nulls(["temp", "temperature_c"])
        diff = w["wind_speed_kmh"].to_numpy() - w["wind"].to_numpy() * mph_to_kmh
        tx, ty = t["temperature_c"].to_numpy(), t["temp"].to_numpy()
        slope, intercept = np.polyfit(tx, ty, 1) if t.height > 1 else (np.nan, np.nan)
        rows.append(
            {
                "season": season,
                "games": g.height,
                "wind_games": w.height,
                "wind_corr": float(np.corrcoef(w["wind_speed_kmh"], w["wind"])[0, 1])
                if w.height > 1
                else None,
                "wind_mean_diff_kmh": float(diff.mean()) if w.height else None,
                "wind_sd_diff_kmh": float(diff.std(ddof=1)) if w.height > 1 else None,
                "temp_games": t.height,
                "temp_corr": float(np.corrcoef(tx, ty)[0, 1]) if t.height > 1 else None,
                "temp_fit_intercept": float(intercept),
                "temp_fit_slope": float(slope),
            }
        )
    return pl.DataFrame(rows)


def run_era5(
    cfg: IngestConfig,
    season: int,
    *,
    http: _Http,
    sched: pl.DataFrame,
    stadiums: list[dict[str, Any]],
    pulled_at: dt.datetime,
    root: Path = DATA_ROOT,
    progress: Callable[[str], None] = lambda s: None,
) -> int:
    """DATA-07: pull one season's outdoor games and store the hourly values (era5_hourly) and
    the game-window aggregates (era5_game_window). Games whose window has not ended are not
    requested; a game the archive has not filled yet (ERA5 runs days behind) is reported and
    stored nowhere, never partly. Returns the number of games stored."""
    check_era5_season(season)  # before any request (BT-07b)
    hours = float(load_params().environment.mtc_05_game_window_hours.value)
    client = Era5Client(http, cfg.open_meteo)
    games = outdoor_games(sched.filter(pl.col("season") == season), stadiums).filter(
        pl.col("kickoff_utc") + dt.timedelta(hours=hours) + _HOUR <= pulled_at
    )
    hourly: list[dict[str, Any]] = []
    windows: list[dict[str, Any]] = []
    for i, g in enumerate(games.iter_rows(named=True), 1):
        start, end = window_dates(g["kickoff_utc"], hours)
        url, body = client.hourly(g["lat"], g["lon"], start, end)
        rows = parse_hourly(body)
        try:
            agg = game_window(rows, g["kickoff_utc"], hours)
        except ValueError as e:
            progress(f"era5 {season}: {g['game_id']} not stored: {e}")
            continue
        meta = {
            "game_id": g["game_id"],
            "model": cfg.open_meteo.model.value,
            "source_url": url,
            "request_lat": g["lat"],
            "request_lon": g["lon"],
            "grid_lat": float(body["latitude"]),
            "grid_lon": float(body["longitude"]),
        }
        hourly.extend({**r, **meta} for r in rows)
        windows.append(
            {
                **meta,
                "kickoff_utc": g["kickoff_utc"],
                "weather_status": g["weather_status"],
                "window_hours": hours,
                "label": LABEL,
                **agg,
            }
        )
        if i % 25 == 0:
            progress(f"era5 {season}: {i}/{games.height} games")
    if windows:
        model = cfg.open_meteo.model.value
        source = f"Open-Meteo archive API (DATA-07), model {model}; {ATTRIBUTION}"
        for name, data in (("era5_hourly", hourly), ("era5_game_window", windows)):
            write_raw(
                pl.DataFrame(data), name, season, source=source, root=root, pulled_at=pulled_at
            )
    return len(windows)
