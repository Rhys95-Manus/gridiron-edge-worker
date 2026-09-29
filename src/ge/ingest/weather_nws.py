"""DATA-06 NWS hourly forecast for outdoor games. Values keep NWS's own units (the uom column);
nothing is converted here. Dome/closed roofs are skipped; unknown roofs are pulled and flagged;
points NWS doesn't cover are recorded as no_weather_source, meaning weather is unknown and
later phases must apply no weather adjustment (decision 2026-09-29), not assume calm."""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from typing import Any, Literal

from ge.config import NwsSettings
from ge.ingest.http import PublicClient

GRID_FIELDS = (
    "temperature",
    "windSpeed",
    "windGust",
    "probabilityOfPrecipitation",
    "quantitativePrecipitation",
)

GameWeather = Literal["pull", "pull_roof_unknown", "skip_roof", "no_coordinates"]
_DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?)?$")


def _hours(duration: str) -> int:
    m = _DURATION.match(duration)
    if not m or duration in ("P", "PT"):
        raise ValueError(f"unsupported NWS duration {duration!r}")
    return int(m.group(1) or 0) * 24 + int(m.group(2) or 0)


def expand_series(series: Mapping[str, Any]) -> list[tuple[dt.datetime, Any]]:
    """DATA-06: expand NWS validTime intervals ("start/PT5H") into one row per hour."""
    rows: list[tuple[dt.datetime, Any]] = []
    for v in series.get("values") or []:
        start_s, dur = v["validTime"].split("/")
        start = dt.datetime.fromisoformat(start_s).astimezone(dt.UTC)
        rows.extend((start + dt.timedelta(hours=h), v["value"]) for h in range(_hours(dur)))
    return rows


def parse_gridpoint(grid: Mapping[str, Any]) -> list[dict[str, Any]]:
    """DATA-06: hourly rows {field, valid_hour, value, uom} for the five spec fields."""
    props = grid["properties"]
    out: list[dict[str, Any]] = []
    for field in GRID_FIELDS:
        series = props[field]
        out.extend(
            {"field": field, "valid_hour": t, "value": val, "uom": series["uom"]}
            for t, val in expand_series(series)
        )
    return out


def points_status(status_code: int, body: Mapping[str, Any]) -> Literal["ok", "no_weather_source"]:
    if status_code == 200 and (body.get("properties") or {}).get("forecastGridData"):
        return "ok"
    if status_code == 404:
        return "no_weather_source"
    raise RuntimeError(f"unexpected NWS /points response {status_code}: {body.get('title')}")


def classify_game(*, roof: str | None, has_coordinates: bool) -> GameWeather:
    """DATA-06 / MTC-05: roof dome or closed means weather is ignored."""
    if roof in ("dome", "closed"):
        return "skip_roof"
    if roof not in ("outdoors", "open", None):
        raise ValueError(f"unknown roof value {roof!r}")
    if not has_coordinates:
        return "no_coordinates"
    return "pull_roof_unknown" if roof is None else "pull"


class NwsClient:
    def __init__(self, client: PublicClient, cfg: NwsSettings) -> None:
        self._c = client
        self._base = cfg.base_url.value.rstrip("/")

    def grid_url(self, lat: float, lon: float) -> tuple[str, str | None]:
        """Returns (status, forecastGridData URL). NWS docs: resolve via /points first."""
        r = self._c.get(f"{self._base}/points/{lat},{lon}")
        if r.status_code in (301, 308):
            # NWS rounds coordinates itself by redirecting (seen 2026-09-29); follow it only
            # when it stays on the NWS API host.
            location = r.headers.get("location", "")
            if not location.startswith("/points/"):
                raise RuntimeError(f"unexpected NWS redirect to {location!r}")
            r = self._c.get(self._base + location)
        body = r.json()
        status = points_status(r.status_code, body)
        return status, (body["properties"]["forecastGridData"] if status == "ok" else None)

    def gridpoint(self, url: str) -> dict[str, Any]:
        if not url.startswith(self._base + "/"):
            raise ValueError(f"refusing non-NWS grid URL {url}")
        return dict(self._c.get_json(url))
