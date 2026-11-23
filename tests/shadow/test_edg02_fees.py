"""EDG-02 taker fee (shared ge.edge.fees) and the SHD-08 fee in CLV.

EDG-02: "taker fee = ceil(M_t x 0.07 x C x P (1-P))"; "The app rounds up to the cent, the
conservative reading, until a real fill confirms which rule applies." Expected values come from
the spec text, not from memory: "At 50¢ the taker fee is 1.75¢ per contract" and the PDF's
printed table "100 contracts at $0.05 shows $0.34, not $0.3325".
SHD-08: "F is the EDG-02 taker fee for one contract, rounded up to the whole cent. The
100-contract fee is shown as a sensitivity column."
Integer centicents (1/10,000 of a dollar) throughout (CLAUDE.md rule 7)."""

import pytest

from ge.config import load_fees
from ge.edge.fees import (
    clv_fee_cc,
    clv_fee_sensitivity_cc,
    taker_fee_cc,
    taker_multiplier,
)
from ge.pricer_v0.scope import PRV01_SERIES

FEES = load_fees()
CENTICENT = load_fees().model_copy(update={"rounding": "up_to_centicent"})


def test_prv01_series_use_the_default_taker_multiplier() -> None:
    """None of the three PRV-01 series is listed in fees.yaml, so the default row applies."""
    assert set(PRV01_SERIES) == {"KXNFLRECYDS", "KXNFLRSHYDS", "KXNFLREC"}
    for s in PRV01_SERIES:
        assert taker_multiplier(s, FEES) == FEES.series.default.taker_multiplier == 1


def test_listed_series_use_their_row() -> None:
    assert taker_multiplier("KXNFLGAME", FEES) == FEES.series.kxnflgame.taker_multiplier
    assert taker_multiplier("KXSB", FEES) == FEES.series.futures_and_awards.taker_multiplier


def test_spec_example_at_50c_is_1_75c_unrounded() -> None:
    # 0.07 x 0.5 x 0.5 = $0.0175 = 175 centicents, exactly, before rounding.
    assert taker_fee_cc(5000, 1, "KXNFLREC", CENTICENT) == 175
    assert taker_fee_cc(5000, 1, "KXNFLREC", FEES) == 200  # up to the cent


def test_spec_table_100_contracts_at_5c() -> None:
    # 0.07 x 100 x 0.05 x 0.95 = $0.3325; the printed table shows $0.34.
    assert taker_fee_cc(500, 100, "KXNFLRECYDS", FEES) == 3400
    assert taker_fee_cc(500, 100, "KXNFLRECYDS", CENTICENT) == 3325


def test_fees_yaml_rounding_is_used() -> None:
    assert FEES.rounding == "up_to_cent"
    assert taker_fee_cc(4500, 1, "KXNFLRSHYDS") == taker_fee_cc(4500, 1, "KXNFLRSHYDS", FEES)


def test_exact_cent_is_not_rounded_up_again() -> None:
    # 0.07 x 100 x 0.5 x 0.5 = $1.75 exactly: 17500 cc, already a whole cent.
    assert taker_fee_cc(5000, 100, "KXNFLREC", FEES) == 17500


def test_multiplier_scales_the_fee() -> None:
    doubled = FEES.model_copy(
        update={
            "series": FEES.series.model_copy(
                update={"default": FEES.series.default.model_copy(update={"taker_multiplier": 2})}
            )
        }
    )
    assert (
        taker_fee_cc(
            5000, 1, "KXNFLREC", doubled.model_copy(update={"rounding": "up_to_centicent"})
        )
        == 350
    )


@pytest.mark.parametrize("price", [0, 10000, -1, 10001])
def test_price_must_be_inside_the_book(price: int) -> None:
    with pytest.raises(ValueError):
        taker_fee_cc(price, 1, "KXNFLREC", FEES)


@pytest.mark.parametrize("bad", [0.5, 5000.0, True])
def test_price_must_be_integer_centicents(bad: object) -> None:
    with pytest.raises(TypeError):
        taker_fee_cc(bad, 1, "KXNFLREC", FEES)  # type: ignore[arg-type]


@pytest.mark.parametrize("contracts", [0, -1])
def test_contracts_must_be_positive(contracts: int) -> None:
    with pytest.raises(ValueError):
        taker_fee_cc(5000, contracts, "KXNFLREC", FEES)


def test_shd08_fee_is_one_contract_rounded_up_to_the_cent() -> None:
    assert clv_fee_cc(5000, "KXNFLREC", FEES) == 200
    assert clv_fee_cc(100, "KXNFLREC", FEES) == 100  # 0.07 x 0.01 x 0.99 = 6.93 cc -> 1 cent


def test_shd08_rounds_up_to_the_cent_even_if_fees_yaml_says_centicent() -> None:
    """SHD-08's cent round-up is hard: a fees.yaml rounding change does not reach it."""
    assert taker_fee_cc(5000, 1, "KXNFLREC", CENTICENT) == 175
    assert clv_fee_cc(5000, "KXNFLREC", CENTICENT) == 200
    for p in range(1, 10000, 37):
        f = clv_fee_cc(p, "KXNFLRECYDS", CENTICENT)
        assert f % 100 == 0 and f >= taker_fee_cc(p, 1, "KXNFLRECYDS", CENTICENT)


def test_shd08_sensitivity_is_the_100_contract_fee() -> None:
    assert clv_fee_sensitivity_cc(500, "KXNFLRECYDS", FEES) == 3400
    assert clv_fee_sensitivity_cc(500, "KXNFLRECYDS", FEES) == taker_fee_cc(
        500, 100, "KXNFLRECYDS", FEES
    )


def test_fees_are_ints() -> None:
    for p in (1, 2500, 5000, 9999):
        assert type(taker_fee_cc(p, 3, "KXNFLREC", FEES)) is int
        assert type(clv_fee_cc(p, "KXNFLREC", FEES)) is int
