"""DATA-13: stadiums are keyed by (stadium_id, stadium name), so one ID filed under two
venues (a London game under a US team's ID) gets each venue's own coordinates. Approved
overrides pick a Wikidata item; coordinates still come only from Wikidata."""

import functools
from pathlib import Path
from typing import Any

import polars as pl
import pytest
import yaml

from ge.config import load_ingest
from ge.ingest.stadiums import build_stadiums, load_overrides, stadium_for_game
from tests.phase1.conftest import load_fixture


@functools.cache
def _search() -> Any:
    return load_fixture("wikidata_search.json")["response"]


@functools.cache
def _entities() -> Any:
    return load_fixture("wikidata_entities.json")["response"]["entities"]


@functools.cache
def _real() -> Any:
    return [n for n, r in _search().items() if r.get("search")]


@functools.cache
def _no_hit() -> Any:
    return next(n for n, r in _search().items() if not r.get("search"))


CFG = load_ingest().wikidata


class FakeWiki:
    """Serves the captured real Wikidata responses."""

    def search(self, name: str) -> dict[str, Any]:
        return _search().get(name, {"search": []})

    def entities(self, qids: list[str]) -> dict[str, Any]:
        return {q: _entities()[q] for q in qids if q in _entities()}


def _sched(rows: list[tuple[str, str, int, str | None]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=["stadium_id", "stadium", "season", "roof"], orient="row")


def _coords(qid: str) -> tuple[float, float]:
    v = _entities()[qid]["claims"][CFG.coordinate_property.value][0]["mainsnak"]["datavalue"][
        "value"
    ]
    return v["latitude"], v["longitude"]


def test_one_id_two_venues_gets_two_rows_with_their_own_coordinates() -> None:
    sched = _sched(
        [("TEST00", _real()[0], 2026, "outdoors"), ("TEST00", _real()[1], 2026, "outdoors")]
    )
    rows = build_stadiums(sched, FakeWiki(), CFG, 2026, overrides=[])
    by_name = {r["name"]: r for r in rows}
    assert set(by_name) == {_real()[0], _real()[1]}
    for name in _real()[:2]:
        r = by_name[name]
        assert r["stadium_id"] == "TEST00"
        assert r["match_status"] == "matched"
        qid = _search()[name]["search"][0]["id"]
        assert (r["lat"], r["lon"]) == _coords(qid)
    assert (by_name[_real()[0]]["lat"], by_name[_real()[0]]["lon"]) != (
        by_name[_real()[1]]["lat"],
        by_name[_real()[1]]["lon"],
    )


def test_game_lookup_uses_id_and_name() -> None:
    sched = _sched([("TEST00", _real()[0], 2026, "outdoors"), ("TEST00", _real()[1], 2026, "dome")])
    rows = build_stadiums(sched, FakeWiki(), CFG, 2026, overrides=[])
    assert stadium_for_game(rows, "TEST00", _real()[1])["name"] == _real()[1]
    assert stadium_for_game(rows, "TEST00", "not a venue") is None


def test_override_takes_coordinates_from_wikidata_and_cites_approval(tmp_path: Path) -> None:
    qid = _search()[_real()[2]]["search"][0]["id"]
    path = tmp_path / "stadium_overrides.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "overrides": [
                    {
                        "stadium_id": "TEST01",
                        "name": _no_hit(),
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
    sched = _sched([("TEST01", _no_hit(), 2026, "outdoors")])
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
    qid = _search()[_real()[0]]["search"][0]["id"]
    ents = {**_entities(), qid: {**_entities()[qid], "claims": {}}}

    class NoCoords(FakeWiki):
        def entities(self, qids: list[str]) -> dict[str, Any]:
            return {q: ents[q] for q in qids if q in ents}

    ov = [
        {
            "stadium_id": "T",
            "name": _no_hit(),
            "qid": qid,
            "approved_by": "user",
            "approved_on": "2026-09-29",
            "reason": "t",
        }
    ]
    with pytest.raises(ValueError):
        build_stadiums(_sched([("T", _no_hit(), 2026, None)]), NoCoords(), CFG, 2026, overrides=ov)
