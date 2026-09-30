"""ENV-02: every elevation stored in metres, with the original value and unit beside it.
Unit factors live in config/ingest.yaml; foot = 0.3048 m exactly (NIST)."""

import pytest

from ge.config import load_ingest
from ge.ingest.wikidata import to_metres
from tests.phase1.conftest import load_fixture

UNITS = load_ingest().wikidata_units
LABELS = {
    q: e["labels"]["en"]["value"]
    for q, e in load_fixture("wikidata_units.json")["response"]["entities"].items()
}
PREFIX = "http://www.wikidata.org/entity/"


def test_unit_items_match_wikidata_labels() -> None:
    assert LABELS[UNITS.metre.unit_qid] == "metre"
    assert LABELS[UNITS.foot.unit_qid] == "foot"


def test_foot_factor_is_nist_exact() -> None:
    assert UNITS.foot.value == 0.3048
    assert "nist.gov" in UNITS.foot.source and "0.3048" in UNITS.foot.source.replace(" ", "")
    assert UNITS.metre.value == 1


def test_conversion() -> None:
    assert to_metres(1609.0, PREFIX + UNITS.metre.unit_qid, UNITS) == 1609.0
    assert to_metres(1000.0, PREFIX + UNITS.foot.unit_qid, UNITS) == pytest.approx(304.8, abs=1e-9)


def test_unknown_unit_is_an_error() -> None:
    with pytest.raises(ValueError):
        to_metres(1.0, PREFIX + "Q1", UNITS)
