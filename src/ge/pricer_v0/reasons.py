"""PRV-03 pricer v0 reason codes after PRV-01 and PRV-02, and the order they are checked in.

PRV-03 (spec sync #6, 2026-11-27): "Pricer v0's checks run in this order, and the first failure
is the reason: PRV-01, PRV-02, PRV-08 (out, doubtful), PRV-03 (too_few_stint_games,
no_centring_mean, mu_not_positive), then a missing fitted distribution parameter
(no_fitted_params)."
"""

from __future__ import annotations

from enum import StrEnum


class PricerUnpriced(StrEnum):
    """PRV-08 and PRV-03 to PRV-06 reason codes, in the order they are checked."""

    OUT = "out"
    DOUBTFUL = "doubtful"
    TOO_FEW_STINT_GAMES = "too_few_stint_games"
    NO_CENTRING_MEAN = "no_centring_mean"
    MU_NOT_POSITIVE = "mu_not_positive"
    NO_FITTED_PARAMS = "no_fitted_params"


_PRV08 = (PricerUnpriced.OUT, PricerUnpriced.DOUBTFUL)
_PRV03 = (
    PricerUnpriced.TOO_FEW_STINT_GAMES,
    PricerUnpriced.NO_CENTRING_MEAN,
    PricerUnpriced.MU_NOT_POSITIVE,
)


def first_reason(
    prv01: str | None,
    prv02: str | None,
    prv08: PricerUnpriced | None,
    prv03: PricerUnpriced | None,
    params: PricerUnpriced | None,
) -> str | None:
    """PRV-03: the first failure in the order PRV-01, PRV-02, PRV-08, PRV-03, then a missing
    fitted distribution parameter; None when every check passed. Each argument is that
    stage's own reason (or None); a reason passed for the wrong stage raises ValueError."""
    if prv08 is not None and prv08 not in _PRV08:
        raise ValueError(f"PRV-03: {prv08} is not a PRV-08 reason")
    if prv03 is not None and prv03 not in _PRV03:
        raise ValueError(f"PRV-03: {prv03} is not a PRV-03 reason")
    if params is not None and params is not PricerUnpriced.NO_FITTED_PARAMS:
        raise ValueError(f"PRV-03: {params} is not a fitted-parameter reason")
    for reason in (prv01, prv02, prv08, prv03, params):
        if reason is not None:
            return str(reason)
    return None
