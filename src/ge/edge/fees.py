"""EDG-02 Kalshi taker fee, shared by the shadow track (SHD-08) and Phase 7.

EDG-02: "taker fee = ceil(M_t x 0.07 x C x P (1-P))", "P = price in dollars, C = contracts,
M = series multiplier". "The app rounds up to the cent, the conservative reading, until a real
fill confirms which rule applies." The rate, the multipliers and the rounding come from
config/fees.yaml (decision 2026-11-19: built once, in this module, implementing EDG-02 exactly).
Where fees.yaml and Kalshi's API fee fields disagree, `ge ingest fees-check` alerts and the
costlier value applies; this module reads fees.yaml only.

SHD-08: "F is the EDG-02 taker fee for one contract, rounded up to the whole cent. The
100-contract fee is shown as a sensitivity column."

Money is integer centicents (CLAUDE.md rule 7); the arithmetic is exact (fractions), so the
ceiling is never off by a float error."""

from __future__ import annotations

from fractions import Fraction

from ge.config import Fees, load_fees, load_params
from ge.ingest.prices import CENTICENTS_PER_DOLLAR

# fees.yaml rounding -> the unit (in centicents) a fee is rounded up to.
_CENTS_PER_DOLLAR = 100
CENTICENTS_PER_CENT = CENTICENTS_PER_DOLLAR // _CENTS_PER_DOLLAR
_ROUNDING_UNIT_CC = {"up_to_cent": CENTICENTS_PER_CENT, "up_to_centicent": 1}


def taker_multiplier(series_ticker: str, fees: Fees | None = None) -> int:
    """EDG-02: M_t for a series: its fees.yaml row when listed, otherwise the default row."""
    fees = fees or load_fees()
    s = fees.series
    for row in (s.kxnflgame, s.kxmve, s.futures_and_awards):
        if series_ticker in row.tickers:
            return int(row.taker_multiplier)
    return int(s.default.taker_multiplier)


def _check_int(name: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int, got {value!r}")
    return value


def _ceil_to(value: Fraction, unit: int) -> int:
    return -(-value // unit) * unit


def _raw_taker_fee_cc(price_cc: int, contracts: int, series_ticker: str, fees: Fees) -> Fraction:
    """EDG-02 before rounding, in centicents: M_t x rate x C x P x (1 - P)."""
    _check_int("price_cc", price_cc)
    _check_int("contracts", contracts)
    if not 0 < price_cc < CENTICENTS_PER_DOLLAR:
        raise ValueError(f"price_cc must be inside (0, {CENTICENTS_PER_DOLLAR}), got {price_cc}")
    if contracts <= 0:
        raise ValueError(f"contracts must be positive, got {contracts}")
    p = Fraction(price_cc, CENTICENTS_PER_DOLLAR)
    rate = Fraction(str(fees.taker_rate))
    dollars = taker_multiplier(series_ticker, fees) * rate * contracts * p * (1 - p)
    return dollars * CENTICENTS_PER_DOLLAR


def taker_fee_cc(
    price_cc: int, contracts: int, series_ticker: str, fees: Fees | None = None
) -> int:
    """EDG-02: the taker fee in centicents for `contracts` contracts at `price_cc`, rounded up
    as fees.yaml's rounding says (up_to_cent or up_to_centicent)."""
    fees = fees or load_fees()
    raw = _raw_taker_fee_cc(price_cc, contracts, series_ticker, fees)
    return _ceil_to(raw, _ROUNDING_UNIT_CC[fees.rounding])


def clv_fee_cc(price_cc: int, series_ticker: str, fees: Fees | None = None) -> int:
    """SHD-08: F, the EDG-02 taker fee for one contract, rounded up to the whole cent whatever
    fees.yaml's rounding says."""
    n = int(load_params().shadow.shd_08_fee_contracts.value)
    return _ceil_to(Fraction(taker_fee_cc(price_cc, n, series_ticker, fees)), CENTICENTS_PER_CENT)


def clv_fee_sensitivity_cc(price_cc: int, series_ticker: str, fees: Fees | None = None) -> int:
    """SHD-08: the sensitivity column, the EDG-02 taker fee for 100 contracts (total, in
    centicents, with fees.yaml's rounding)."""
    n = int(load_params().shadow.shd_08_sensitivity_fee_contracts.value)
    return taker_fee_cc(price_cc, n, series_ticker, fees)
