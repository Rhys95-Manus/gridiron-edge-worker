"""ENV-02: stadium elevation from Wikidata's elevation above sea level, kept in the unit
Wikidata gives. Blank, with a reason, when the item has no single usable claim."""

import copy
import functools
from typing import Any

from ge.config import load_ingest
from ge.ingest.wikidata import elevation
from tests.phase1.conftest import load_fixture


@functools.cache
def _prop() -> Any:
    return load_fixture("wikidata_elevation_property.json")["response"]["search"][0]


@functools.cache
def _parser_ents() -> Any:
    return load_fixture("wikidata_elevation_parser_entities.json")["response"]["entities"]


@functools.cache
def _venues() -> Any:
    return load_fixture("wikidata_elevation_entities.json")["response"]["entities"]


def test_property_id_was_confirmed_from_wikidata() -> None:
    assert _prop()["label"] == "elevation above sea level"
    assert load_ingest().wikidata.elevation_property.value == _prop()["id"]


def test_single_claim_gives_value_and_unit() -> None:
    ent = next(iter(_parser_ents().values()))
    claim = ent["claims"][_prop()["id"]][0]["mainsnak"]["datavalue"]["value"]
    e = elevation(ent, _prop()["id"])
    assert e.value == float(claim["amount"])
    assert e.unit == claim["unit"]
    assert e.reason


def test_item_without_claim_is_blank() -> None:
    ent = next(iter(_venues().values()))
    assert _prop()["id"] not in ent.get("claims", {})
    e = elevation(ent, _prop()["id"])
    assert e.value is None and e.unit is None and e.reason


def _with_claims(values: list[tuple[str, str]]) -> dict:
    """A real entity whose P2044 claims are replaced by copies of its real claim."""
    ent = copy.deepcopy(next(iter(_parser_ents().values())))
    base = ent["claims"][_prop()["id"]][0]
    claims = []
    for amount, rank in values:
        c = copy.deepcopy(base)
        c["mainsnak"]["datavalue"]["value"]["amount"] = amount
        c["rank"] = rank
        claims.append(c)
    ent["claims"][_prop()["id"]] = claims
    return ent


def test_preferred_rank_wins() -> None:
    e = elevation(_with_claims([("+10", "normal"), ("+20", "preferred")]), _prop()["id"])
    assert e.value == 20.0


def test_conflicting_normal_claims_are_blank() -> None:
    e = elevation(_with_claims([("+10", "normal"), ("+20", "normal")]), _prop()["id"])
    assert e.value is None and "conflict" in e.reason


def test_deprecated_claims_are_ignored() -> None:
    e = elevation(_with_claims([("+10", "deprecated"), ("+20", "normal")]), _prop()["id"])
    assert e.value == 20.0
