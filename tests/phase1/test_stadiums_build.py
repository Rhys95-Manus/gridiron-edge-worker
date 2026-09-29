"""DATA-13: stadiums are keyed by (stadium_id, stadium name), so one ID filed under two
venues (a London game under a US team's ID) gets each venue's own coordinates. Approved
overrides pick a Wikidata item; coordinates still come only from Wikidata."""

from pathlib import Path
from typing import Any

import polars as pl
import pytest
import yaml

from ge.config import load_ingest
from ge.ingest.stadiums import build_stadiums, load_overrides, stadium_for_game
from tests.phase1.conftest import load_fixture

SEARCH = load_fixture("wikidata_search.json")["response"]
ENTITIES = load_fixture("wikidata_entities.json")["response"]["entities"]
REAL = [n for n, r in SEARCH.items() if r.get("search")]
NO_HIT = next(n for n, r in SEARCH.items() if not r.get("search"))
CFG = load_ingest().wikidata


class FakeWiki:
    """Serves the captured real Wikidata responses."""

    def search(self, name: str) -> dict[str, Any]:
        return SEARCH.get(name, {"search": []})

    def entities(self, qids: list[str]) -> dict[str, Any]:
        return {q: ENTITIES[q] for q in qids if q in ENTITIES}


def _sched(rows: list[tuple[str, str, int, str | None]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=["stadium_id", "stadium", "season", "roof"], orient="row")


def _coords(qid: str) -> tuple[float, float]:
    v = ENTITIES[qid]["claims"][CFG.coordinate_property.value][0]["mainsnak"]["datavalue"]["value"]
    return v["latitude"], v["longitude"]


def test_one_id_two_venues_gets_two_rows_with_their_own_coordinates() -> None:
    sched = _sched([("TEST00", REAL[0], 2026, "outdoors"), ("TEST00", REAL[1], 2026, "outdoors")])
    rows = build_stadiums(sched, FakeWiki(), CFG, 2026, overrides=[])
    by_name = {r["name"]: r for r in rows}
    assert set(by_name) == {REAL[0], REAL[1]}
    for name in REAL[:2]:
        r = by_name[name]
        assert r["stadium_id"] == "TEST00"
        assert r["match_status"] == "matched"
        qid = SEARCH[name]["search"][0]["id"]
        assert (r["lat"], r["lon"]) == _coords(qid)
    assert (by_name[REAL[0]]["lat"], by_name[REAL[0]]["lon"]) != (
        by_name[REAL[1]]["lat"],
        by_name[REAL[1]]["lon"],
    )


def test_game_lookup_uses_id_and_name() -> None:
    sched = _sched([("TEST00", REAL[0], 2026, "outdoors"), ("TEST00", REAL[1], 2026, "dome")])
    rows = build_stadiums(sched, FakeWiki(), CFG, 2026, overrides=[])
    assert stadium_for_game(rows, "TEST00", REAL[1])["name"] == REAL[1]
    assert stadium_for_game(rows, "TEST00", "not a venue") is None


def test_override_takes_coordinates_from_wikidata_and_cites_approval(tmp_path: Path) -> None:
    qid = SEARCH[REAL[2]]["search"][0]["id"]
    path = tmp_path / "stadium_overrides.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "overrides": [
                    {
                        "stadium_id": "TEST01",
                        "name": NO_HIT,
                        "qid": qid,
                        "approved_by": "user",
                        "approved_on": "2026-09-29",
                        "reason": "unit test",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    sched = _sched([("TEST01", NO_HIT, 2026, "outdoors")])
    rows = build_stadiums(sched, FakeWiki(), CFG, 2026, overrides=load_overrides(path))
    (r,) = rows
    assert r["match_status"] == "override"
    assert (r["lat"], r["lon"]) == _coords(qid)
    assert r["source_url"] == CFG.item_url_prefix.value + qid
    assert "user" in r["match_reason"] and "2026-09-29" in r["match_reason"]


def test_override_must_be_approved(tmp_path: Path) -> None:
    path = tmp_path / "stadium_overrides.yaml"
    path.write_text(
        yaml.safe_dump({"overrides": [{"stadium_id": "X", "name": "Y", "qid": "Q1"}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_overrides(path)


def test_override_item_without_coordinates_is_an_error(tmp_path: Path) -> None:
    qid = SEARCH[REAL[0]]["search"][0]["id"]
    ents = {**ENTITIES, qid: {**ENTITIES[qid], "claims": {}}}

    class NoCoords(FakeWiki):
        def entities(self, qids: list[str]) -> dict[str, Any]:
            return {q: ents[q] for q in qids if q in ents}

    ov = [
        {
            "stadium_id": "T",
            "name": NO_HIT,
            "qid": qid,
            "approved_by": "user",
            "approved_on": "2026-09-29",
            "reason": "t",
        }
    ]
    with pytest.raises(ValueError):
        build_stadiums(_sched([("T", NO_HIT, 2026, None)]), NoCoords(), CFG, 2026, overrides=ov)
