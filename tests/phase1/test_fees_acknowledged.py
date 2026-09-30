"""EDG-02: known fees.yaml-vs-API disagreements can be acknowledged by the user. fees-check
passes only when every disagreement matches an acknowledgement exactly; a new, changed or
resolved one fails. The costlier value is used either way."""

import copy
import functools
from typing import Any

from ge.config import load_fees
from ge.ingest.fees_check import fee_check
from tests.phase1.conftest import load_fixture


@functools.cache
def _series() -> Any:
    return {s["ticker"]: s for s in load_fixture("kalshi_series_subset.json")["response"]["series"]}


def _fees_with_acks(acks: list[dict]):  # type: ignore[no-untyped-def]
    fees = load_fees()
    raw = fees.model_dump(by_alias=True)
    raw["acknowledged"] = acks
    return type(fees).model_validate(raw)


def _ack(ticker: str, field: str, yaml_v: float, api_v: float, fee_type: str) -> dict:
    return {
        "ticker": ticker,
        "field": field,
        "fees_yaml_value": yaml_v,
        "api_value": api_v,
        "api_fee_type": fee_type,
        "value_in_use": max(yaml_v, api_v),
        "reason": "test",
        "acknowledged_by": "user",
        "acknowledged_on": "2026-09-29",
    }


def _one_disagreeing_series() -> tuple[str, dict]:
    combo = next(t for t in _series() if t.startswith("KXMVENFL"))
    return combo, _series()[combo]


def test_every_acknowledgement_in_fees_yaml_cites_the_user() -> None:
    import datetime as dt

    for a in load_fees().acknowledged:
        assert a.acknowledged_by == "user", a.ticker
        on = dt.date.fromisoformat(a.acknowledged_on)  # a real ISO date, not in the future
        assert on <= dt.datetime.now(dt.UTC).date(), a.ticker
        assert a.value_in_use == max(a.fees_yaml_value, a.api_value)
        assert a.reason.strip()


def test_unacknowledged_disagreement_fails() -> None:
    _, s = _one_disagreeing_series()
    result = fee_check(_fees_with_acks([]), [s])
    assert not result.ok and result.new and not result.acknowledged


def test_matching_acknowledgement_passes_and_still_uses_costlier_value() -> None:
    t, s = _one_disagreeing_series()
    fees = load_fees()
    ack = _ack(t, "maker", fees.series.kxmve.maker_multiplier, 0, s["fee_type"])
    result = fee_check(_fees_with_acks([ack]), [s])
    assert result.ok, result.new
    assert [e.maker for e in result.effective] == [fees.series.kxmve.maker_multiplier]


def test_changed_api_value_fails_even_when_acknowledged() -> None:
    t, s = _one_disagreeing_series()
    fees = load_fees()
    ack = _ack(t, "maker", fees.series.kxmve.maker_multiplier, 0, s["fee_type"])
    changed = copy.deepcopy(s)
    changed["fee_type"] = "quadratic_with_maker_fees"  # now maker 1, still disagrees
    result = fee_check(_fees_with_acks([ack]), [changed])
    assert not result.ok and result.new


def test_resolved_acknowledgement_is_reported_and_fails() -> None:
    fees = load_fees()
    game = _series()["KXNFLGAME"]  # agrees with fees.yaml
    ack = _ack("KXNFLGAME", "maker", 1, 0, "quadratic")
    result = fee_check(_fees_with_acks([ack]), [game])
    assert not result.ok and result.stale
    assert result.effective[0].maker == fees.series.kxnflgame.maker_multiplier
