"""DATA-13 Wikidata stadium coordinates. A stadium is matched only when every name it appears
under in the schedules resolves, by exact label or alias, to the same single item that has a
coordinate location. Otherwise it is left blank with a reason. Coordinates are never guessed."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from ge.config import WikidataSettings
from ge.ingest.http import PublicClient

Status = Literal["matched", "no_match", "ambiguous"]


@dataclass(frozen=True)
class StadiumMatch:
    status: Status
    reason: str
    qid: str | None = None
    label: str | None = None
    lat: float | None = None
    lon: float | None = None
    source_url: str | None = None


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


@dataclass(frozen=True)
class Elevation:
    value: float | None
    unit: str | None  # Wikidata unit entity URI, exactly as given; never converted here
    reason: str


def elevation(entity: Mapping[str, Any], prop: str) -> Elevation:
    """ENV-02: elevation above sea level from the item's claims. Preferred rank wins;
    deprecated claims are ignored; conflicting claims leave it blank."""
    claims = [
        c for c in (entity.get("claims") or {}).get(prop, []) if c.get("rank") != "deprecated"
    ]
    usable = [c for c in claims if (c.get("mainsnak") or {}).get("datavalue")]
    if not usable:
        return Elevation(None, None, f"item has no {prop} (elevation above sea level) claim")
    preferred = [c for c in usable if c.get("rank") == "preferred"]
    pick = preferred or usable
    values = {(v["amount"], v["unit"]) for v in (c["mainsnak"]["datavalue"]["value"] for c in pick)}
    if len(values) != 1:
        return Elevation(None, None, f"conflicting {prop} claims: {sorted(values)}")
    amount, unit = next(iter(values))
    rank = "preferred" if preferred else "normal"
    return Elevation(float(amount), unit, f"{prop} ({rank} rank)")


def coordinates(entity: Mapping[str, Any], prop: str) -> tuple[float, float] | None:
    """DATA-13: the item's coordinate location (latitude, longitude), if it has one."""
    return _coords(entity, prop)


def _coords(entity: Mapping[str, Any], prop: str) -> tuple[float, float] | None:
    for claim in (entity.get("claims") or {}).get(prop, []):
        value = (claim.get("mainsnak") or {}).get("datavalue", {}).get("value")
        if value and "latitude" in value and "longitude" in value:
            return float(value["latitude"]), float(value["longitude"])
    return None


def _exact_hits(name: str, search: Mapping[str, Any]) -> list[str]:
    hits = []
    for hit in (search.get(name) or {}).get("search", []):
        texts = [hit.get("label") or "", (hit.get("match") or {}).get("text") or ""]
        texts += list(hit.get("aliases") or [])
        if any(_norm(t) == _norm(name) for t in texts if t):
            hits.append(hit["id"])
    return hits


def match_stadium(
    names: Iterable[str],
    search: Mapping[str, Any],
    entities: Mapping[str, Any],
    coord_prop: str,
    item_url_prefix: str = "https://www.wikidata.org/wiki/",
) -> StadiumMatch:
    """DATA-13: resolve one stadium (all names it appears under) to a Wikidata item."""
    unique_names = sorted(set(names))
    per_name: dict[str, set[str]] = {}
    for name in unique_names:
        with_coords = {
            q
            for q in _exact_hits(name, search)
            if q in entities and _coords(entities[q], coord_prop)
        }
        if with_coords:
            per_name[name] = with_coords
    if not per_name:
        return StadiumMatch(
            "no_match", f"no exact label/alias hit with coordinates for {unique_names}"
        )
    items = set().union(*per_name.values())
    if len(items) != 1:
        detail = "; ".join(f"{n} -> {sorted(q)}" for n, q in sorted(per_name.items()))
        return StadiumMatch("ambiguous", f"names resolve to different items: {detail}")
    qid = next(iter(items))
    lat, lon = _coords(entities[qid], coord_prop) or (None, None)
    unmatched = [n for n in unique_names if n not in per_name]
    reason = "exact match" + (f"; no hit for other names {unmatched}" if unmatched else "")
    label = ((entities[qid].get("labels") or {}).get("en") or {}).get("value")
    return StadiumMatch("matched", reason, qid, label, lat, lon, item_url_prefix + qid)


class WikidataClient:
    def __init__(self, client: PublicClient, cfg: WikidataSettings) -> None:
        self._c = client
        self._cfg = cfg

    def search(self, name: str) -> dict[str, Any]:
        return dict(
            self._c.get_json(
                self._cfg.api_url.value,
                {
                    "action": "wbsearchentities",
                    "search": name,
                    "language": "en",
                    "type": "item",
                    "limit": self._cfg.search_limit.value,
                    "format": "json",
                },
            )
        )

    def entities(self, qids: list[str]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        n = self._cfg.entities_batch_size.value
        for i in range(0, len(qids), n):
            body = self._c.get_json(
                self._cfg.api_url.value,
                {
                    "action": "wbgetentities",
                    "ids": "|".join(qids[i : i + n]),
                    "props": "labels|aliases|claims",
                    "languages": "en",
                    "format": "json",
                },
            )
            out.update(body.get("entities") or {})
        return out
