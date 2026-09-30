"""ENV-02 city_elevation_proxy (user decisions 2026-09-29/30): start at the most specific
place the stadium is located in (Wikidata P131). If that place has no elevation (P2044),
walk up its own P131 chain to the first place that has one, and cite the item used. When a
place lists several parents, the most specific wins: any parent that another listed parent
is itself located in is dropped. Blank, with a reason, only if the whole chain has none."""

import copy
from typing import Any

from ge.config import load_ingest
from ge.ingest.wikidata import city_elevation
from tests.phase1.conftest import load_fixture

CFG = load_ingest().wikidata
LOC = load_fixture("wikidata_located_in_property.json")["response"]["search"][0]
STADIUM = load_fixture("wikidata_elevation_entities.json")["response"]["entities"]["Q1046135"]
PLACES: dict[str, Any] = {
    **load_fixture("wikidata_elevation_parser_entities.json")["response"]["entities"],
    **load_fixture("wikidata_chain_parent.json")["response"]["entities"],
}
LOCATED = CFG.located_in_property.value
ELEV = CFG.elevation_property.value


def _fetch(places: dict[str, Any]):  # type: ignore[no-untyped-def]
    def fetch(qids: list[str]) -> dict[str, Any]:
        return {q: places[q] for q in qids if q in places}

    return fetch


def _located_in(ent: dict) -> list[str]:
    """Non-deprecated located-in claims (Denver's link to Denver County is deprecated)."""
    return [
        c["mainsnak"]["datavalue"]["value"]["id"]
        for c in ent["claims"].get(LOCATED, [])
        if c.get("rank") != "deprecated"
    ]


def _elev(qid: str) -> dict:
    return PLACES[qid]["claims"][ELEV][0]["mainsnak"]["datavalue"]["value"]


def _most_specific(qids: list[str], places: dict[str, Any]) -> str:
    """Independent reading of the rule, for the test's expected value."""
    left = [q for q in qids if not any(q in _located_in(places[o]) for o in qids if o != q)]
    assert len(left) == 1, left
    return left[0]


def test_located_in_property_was_confirmed_from_wikidata() -> None:
    assert LOC["label"] == "located in the administrative territorial entity"
    assert LOC["id"] == LOCATED


def test_first_place_with_elevation_is_used() -> None:
    start = _most_specific(_located_in(STADIUM), PLACES)
    e = city_elevation(STADIUM, _fetch(PLACES), LOCATED, ELEV)
    assert e.place_qid == start
    assert e.value == float(_elev(start)["amount"]) and e.unit == _elev(start)["unit"]
    assert e.chain == [start]
    assert e.method == "city_elevation_proxy"


def test_walks_up_the_chain_when_the_place_has_no_elevation() -> None:
    places = copy.deepcopy(PLACES)
    start = _most_specific(_located_in(STADIUM), places)
    places[start]["claims"].pop(ELEV)
    step1 = _most_specific(_located_in(places[start]), places)
    assert ELEV in places[step1]["claims"]
    e = city_elevation(STADIUM, _fetch(places), LOCATED, ELEV)
    assert e.chain == [start, step1]
    assert e.place_qid == step1
    assert e.value == float(_elev(step1)["amount"])
    assert step1 in e.reason and start in e.reason


def test_blank_only_when_the_whole_chain_has_none() -> None:
    places = copy.deepcopy(PLACES)
    for q in places:
        places[q]["claims"].pop(ELEV, None)
    e = city_elevation(STADIUM, _fetch(places), LOCATED, ELEV)
    assert e.value is None and e.place_qid is None and len(e.chain) >= 2 and e.reason


def test_no_located_in_claim_is_blank() -> None:
    ent = copy.deepcopy(STADIUM)
    ent["claims"].pop(LOCATED)
    e = city_elevation(ent, _fetch(PLACES), LOCATED, ELEV)
    assert e.value is None and e.place_qid is None and e.reason


def test_two_unrelated_places_are_ambiguous() -> None:
    places = copy.deepcopy(PLACES)
    for q in places:
        places[q]["claims"][LOCATED] = []  # neither listed place is inside the other
    e = city_elevation(STADIUM, _fetch(places), LOCATED, ELEV)
    assert e.value is None and "ambiguous" in e.reason


def test_a_cycle_in_the_chain_stops_and_is_blank() -> None:
    places = copy.deepcopy(PLACES)
    start = _most_specific(_located_in(STADIUM), places)
    places[start]["claims"].pop(ELEV)
    step1 = _most_specific(_located_in(places[start]), places)
    loop = copy.deepcopy(places[step1]["claims"][LOCATED][0])
    loop["mainsnak"]["datavalue"]["value"]["id"] = start
    places[step1]["claims"][LOCATED] = [loop]  # step1 now says it is located in start
    places[step1]["claims"].pop(ELEV, None)
    stadium = copy.deepcopy(STADIUM)  # list only `start`, so the first step isn't ambiguous
    stadium["claims"][LOCATED] = [
        c for c in stadium["claims"][LOCATED] if c["mainsnak"]["datavalue"]["value"]["id"] == start
    ]
    e = city_elevation(stadium, _fetch(places), LOCATED, ELEV)
    assert e.value is None and "cycle" in e.reason and e.chain == [start, step1]
