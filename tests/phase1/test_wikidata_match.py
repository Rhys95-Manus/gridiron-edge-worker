"""DATA-13: a stadium gets coordinates only from one exact label/alias match that has a
coordinate location. No match or conflicting matches leave it blank, with a reason."""

from ge.ingest.wikidata import match_stadium
from tests.phase1.conftest import load_fixture

SEARCH = load_fixture("wikidata_search.json")["response"]
ENTITIES = load_fixture("wikidata_entities.json")["response"]["entities"]
COORD_PROP = load_fixture("wikidata_coordinate_property.json")["response"]["search"][0]["id"]
REAL_NAMES = [n for n, r in SEARCH.items() if r.get("search")]
NO_HIT_NAME = next(n for n, r in SEARCH.items() if not r.get("search"))


def test_coordinate_property_was_confirmed_from_wikidata() -> None:
    hit = load_fixture("wikidata_coordinate_property.json")["response"]["search"][0]
    assert hit["label"] == "coordinate location"


def test_exact_label_match_gets_coordinates_and_item_url() -> None:
    name = REAL_NAMES[0]
    m = match_stadium([name], SEARCH, ENTITIES, COORD_PROP)
    assert m.status == "matched", m.reason
    hit = SEARCH[name]["search"][0]
    assert m.qid == hit["id"]
    assert m.source_url == f"https://www.wikidata.org/wiki/{hit['id']}"
    claim = ENTITIES[hit["id"]]["claims"][COORD_PROP][0]["mainsnak"]["datavalue"]["value"]
    assert (m.lat, m.lon) == (claim["latitude"], claim["longitude"])


def test_no_search_hit_is_blank() -> None:
    m = match_stadium([NO_HIT_NAME], SEARCH, ENTITIES, COORD_PROP)
    assert m.status == "no_match"
    assert m.lat is None and m.lon is None and m.source_url is None
    assert m.reason


def test_names_pointing_to_different_items_are_ambiguous_and_blank() -> None:
    """One stadium_id listed under two names that resolve to two different items."""
    m = match_stadium(REAL_NAMES[:2], SEARCH, ENTITIES, COORD_PROP)
    assert m.status == "ambiguous"
    assert m.lat is None and m.source_url is None
    assert m.reason


def test_same_name_twice_is_still_one_match() -> None:
    m = match_stadium([REAL_NAMES[0], REAL_NAMES[0]], SEARCH, ENTITIES, COORD_PROP)
    assert m.status == "matched"


def test_hit_without_exact_text_is_not_accepted() -> None:
    """A search hit whose label/alias differs from the stadium name is not a match."""
    name = REAL_NAMES[0]
    altered = name + " Annex"
    search = {altered: SEARCH[name]}
    m = match_stadium([altered], search, ENTITIES, COORD_PROP)
    assert m.status == "no_match"


def test_item_without_coordinates_is_not_accepted() -> None:
    name = REAL_NAMES[0]
    qid = SEARCH[name]["search"][0]["id"]
    ents = {k: dict(v) for k, v in ENTITIES.items()}
    ents[qid] = {**ents[qid], "claims": {}}
    m = match_stadium([name], SEARCH, ents, COORD_PROP)
    assert m.status == "no_match"
