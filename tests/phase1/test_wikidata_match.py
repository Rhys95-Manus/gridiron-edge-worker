"""DATA-13: a stadium gets coordinates only from one exact label/alias match that has a
coordinate location. No match or conflicting matches leave it blank, with a reason."""

import functools
from typing import Any

from ge.ingest.wikidata import match_stadium
from tests.phase1.conftest import load_fixture


@functools.cache
def _search() -> Any:
    return load_fixture("wikidata_search.json")["response"]


@functools.cache
def _entities() -> Any:
    return load_fixture("wikidata_entities.json")["response"]["entities"]


@functools.cache
def _coord_prop() -> Any:
    return load_fixture("wikidata_coordinate_property.json")["response"]["search"][0]["id"]


@functools.cache
def _real_names() -> Any:
    return [n for n, r in _search().items() if r.get("search")]


@functools.cache
def _no_hit_name() -> Any:
    return next(n for n, r in _search().items() if not r.get("search"))


def test_coordinate_property_was_confirmed_from_wikidata() -> None:
    hit = load_fixture("wikidata_coordinate_property.json")["response"]["search"][0]
    assert hit["label"] == "coordinate location"


def test_exact_label_match_gets_coordinates_and_item_url() -> None:
    name = _real_names()[0]
    m = match_stadium([name], _search(), _entities(), _coord_prop())
    assert m.status == "matched", m.reason
    hit = _search()[name]["search"][0]
    assert m.qid == hit["id"]
    assert m.source_url == f"https://www.wikidata.org/wiki/{hit['id']}"
    claim = _entities()[hit["id"]]["claims"][_coord_prop()][0]["mainsnak"]["datavalue"]["value"]
    assert (m.lat, m.lon) == (claim["latitude"], claim["longitude"])


def test_no_search_hit_is_blank() -> None:
    m = match_stadium([_no_hit_name()], _search(), _entities(), _coord_prop())
    assert m.status == "no_match"
    assert m.lat is None and m.lon is None and m.source_url is None
    assert m.reason


def test_names_pointing_to_different_items_are_ambiguous_and_blank() -> None:
    """One stadium_id listed under two names that resolve to two different items."""
    m = match_stadium(_real_names()[:2], _search(), _entities(), _coord_prop())
    assert m.status == "ambiguous"
    assert m.lat is None and m.source_url is None
    assert m.reason


def test_same_name_twice_is_still_one_match() -> None:
    m = match_stadium([_real_names()[0], _real_names()[0]], _search(), _entities(), _coord_prop())
    assert m.status == "matched"


def test_hit_without_exact_text_is_not_accepted() -> None:
    """A search hit whose label/alias differs from the stadium name is not a match."""
    name = _real_names()[0]
    altered = name + " Annex"
    search = {altered: _search()[name]}
    m = match_stadium([altered], search, _entities(), _coord_prop())
    assert m.status == "no_match"


def test_item_without_coordinates_is_not_accepted() -> None:
    name = _real_names()[0]
    qid = _search()[name]["search"][0]["id"]
    ents = {k: dict(v) for k, v in _entities().items()}
    ents[qid] = {**ents[qid], "claims": {}}
    m = match_stadium([name], _search(), ents, _coord_prop())
    assert m.status == "no_match"
