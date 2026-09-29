"""DATA-13 check (BUILD_PLAN Phase 1 item 2): fails if any 2026 game's stadium lacks
coordinates or a source_url. Reads the generated config/stadiums.yaml, so it runs in CI.
Rows are keyed by (stadium_id, name)."""

import re
from pathlib import Path

import yaml
from timezonefinder import TimezoneFinder

from ge.ingest.stadiums import STADIUMS_PATH, missing_for_2026

ITEM_URL = re.compile(r"^https://www\.wikidata\.org/wiki/Q\d+$")


def _rows() -> list[dict]:
    assert STADIUMS_PATH.exists(), "run `uv run ge ingest stadiums` to generate it"
    data = yaml.safe_load(Path(STADIUMS_PATH).read_text(encoding="utf-8"))
    assert data["generated_by"] == "ge ingest stadiums", (
        "stadiums.yaml must be generated, not typed"
    )
    return data["stadiums"]


def test_rows_are_unique_by_id_and_name() -> None:
    keys = [(r["stadium_id"], r["name"]) for r in _rows()]
    assert len(keys) == len(set(keys))


def test_every_2026_stadium_has_coordinates_and_source() -> None:
    problems = missing_for_2026(_rows())
    assert not problems, "2026 stadiums missing coordinates or source_url:\n" + "\n".join(problems)


def test_located_rows_are_complete_and_consistent() -> None:
    tf = TimezoneFinder()
    for r in _rows():
        key = (r["stadium_id"], r["name"])
        if r["match_status"] not in ("matched", "override"):
            assert r["lat"] is None and r["lon"] is None and r["source_url"] is None, key
            continue
        assert ITEM_URL.match(r["source_url"]), key
        assert tf.timezone_at(lng=r["lon"], lat=r["lat"]) == r["timezone"], key


def test_elevation_fields_are_present_and_consistent() -> None:
    """ENV-02: value and unit together or not at all; always a reason."""
    for r in _rows():
        key = (r["stadium_id"], r["name"])
        assert {"elevation", "elevation_unit", "elevation_reason"} <= set(r), key
        assert (r["elevation"] is None) == (r["elevation_unit"] is None), key
        assert r["elevation_reason"], key
        if r["elevation"] is not None:
            assert r["source_url"], key


def test_overrides_file_cites_approval() -> None:
    from ge.ingest.stadiums import OVERRIDES_PATH, load_overrides

    rows = {(r["stadium_id"], r["name"]): r for r in _rows()}
    for o in load_overrides(OVERRIDES_PATH):
        r = rows[(o["stadium_id"], o["name"])]
        assert r["match_status"] == "override"
        assert r["source_url"].endswith("/" + o["qid"])


def test_roof_values_come_from_schedules() -> None:
    allowed = {"outdoors", "open", "dome", "closed", None}
    for r in _rows():
        assert set(r["roof_values_seen"]) <= allowed, (r["stadium_id"], r["name"])
