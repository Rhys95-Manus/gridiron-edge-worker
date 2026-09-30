"""EDG-02 / DATA-09: compare fees.yaml with the fee_type and fee_multiplier Kalshi's API
reports for each included series. fee_type meanings are from docs.kalshi.com get-series."""

import copy

from ge.config import load_fees
from ge.ingest.fees_check import api_fee_alerts, effective_multipliers
from tests.phase1.conftest import load_fixture

SERIES = {s["ticker"]: s for s in load_fixture("kalshi_series_subset.json")["response"]["series"]}


def _one(ticker: str, **changes: object) -> dict:
    s = copy.deepcopy(SERIES[ticker])
    s.update(changes)
    return s


def test_game_series_matches_fees_yaml() -> None:
    s = SERIES["KXNFLGAME"]
    assert s["fee_type"] == "quadratic_with_maker_fees", "fixture changed; re-read the docs"
    assert api_fee_alerts(load_fees(), [s]) == []


def test_changed_taker_multiplier_alerts() -> None:
    alerts = api_fee_alerts(load_fees(), [_one("KXNFLGAME", fee_multiplier=2)])
    assert len(alerts) == 1 and "KXNFLGAME" in alerts[0] and "taker" in alerts[0]


def test_changed_fee_type_alerts() -> None:
    alerts = api_fee_alerts(load_fees(), [_one("KXNFLGAME", fee_type="quadratic")])
    assert len(alerts) == 1 and "maker" in alerts[0]


def test_flat_or_unknown_fee_type_alerts() -> None:
    for fee_type in ("flat", "something_new"):
        alerts = api_fee_alerts(load_fees(), [_one("KXNFLGAME", fee_type=fee_type)])
        assert len(alerts) == 1 and fee_type in alerts[0]


def test_series_only_prefix_matching_a_row_is_flagged() -> None:
    """An unlisted series that only prefix-matches a row must be flagged, not pass silently.
    (Checked against a fees.yaml whose combos row lists only KXMVE, as before 2026-09-29.)"""
    fees = load_fees()
    old = fees.model_copy(
        update={
            "series": fees.series.model_copy(
                update={"kxmve": fees.series.kxmve.model_copy(update={"tickers": ["KXMVE"]})}
            )
        }
    )
    combo = next(t for t in SERIES if t.startswith("KXMVENFL"))
    alerts = api_fee_alerts(old, [SERIES[combo]])
    assert any(combo in a and "KXMVE" in a and "prefix" in a for a in alerts), alerts


def test_futures_series_listed_from_the_pdf_match_the_api() -> None:
    """User approval 2026-09-29: futures_and_awards holds the PDF's futures and awards tickers."""
    from ge.ingest.kalshi import fee_schedule_nfl_tickers
    from tests.phase1.conftest import FIXTURES

    fees = load_fees()
    pdf = fee_schedule_nfl_tickers((FIXTURES / "kalshi_fee_schedule.pdf").read_bytes())
    futs = [t for t in fees.series.futures_and_awards.tickers if t in SERIES and t in pdf]
    assert len(futs) == len(pdf - {"KXNFLGAME"})
    assert api_fee_alerts(fees, [SERIES[t] for t in futs]) == []


def test_combos_keep_the_costlier_maker_rate_and_alert() -> None:
    """EDG-02 (2026-09-29): where API and fees.yaml disagree, use whichever costs more."""
    fees = load_fees()
    combos = [t for t in SERIES if t.startswith("KXMVENFL")]
    assert combos and set(combos) <= set(fees.series.kxmve.tickers)
    for t in combos:
        eff = effective_multipliers(fees, SERIES[t])
        assert eff.maker == max(fees.series.kxmve.maker_multiplier, _api_maker(SERIES[t]))
        assert eff.alerts


def test_api_maker_fees_on_default_row_series_are_charged_and_alerted() -> None:
    """The five series Phase 1 found: default row says maker 0, the API says maker fees."""
    fees = load_fees()
    hits = [
        t
        for t, s in SERIES.items()
        if s.get("fee_type") == "quadratic_with_maker_fees"
        and t.startswith(("KXNFLSPREAD", "KXNFLTOTAL", "KXNFLANYTD", "KXNFLFIRSTTD", "KXNFL2TD"))
    ]
    assert hits
    for t in hits:
        eff = effective_multipliers(fees, SERIES[t])
        assert eff.row == "default"
        assert eff.maker == 1 and eff.alerts


def test_agreement_means_no_alert_and_same_multipliers() -> None:
    fees = load_fees()
    eff = effective_multipliers(fees, SERIES["KXNFLGAME"])
    assert (eff.taker, eff.maker, eff.alerts) == (1, 1, [])


def _api_maker(s: dict) -> int:
    return {"quadratic": 0, "quadratic_with_maker_fees": 1, "quadratic_with_combo_maker_fees": 2}[
        s["fee_type"]
    ]
