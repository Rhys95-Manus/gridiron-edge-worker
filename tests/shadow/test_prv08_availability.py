"""PRV-08 availability gate and the PRV-03 check order, on synthetic data only."""

from __future__ import annotations

from typing import Any

import polars as pl
import pytest

from ge.pricer_v0.availability import Availability, AvailabilityFlag, availability
from ge.pricer_v0.reasons import PricerUnpriced, first_reason

SCHEMA = {
    "season": pl.Int64,
    "week": pl.Int64,
    "team": pl.Utf8,
    "gsis_id": pl.Utf8,
    "report_status": pl.Utf8,
}


def inj(*rows: tuple[str, str, str | None], week: int = 5, season: int = 2024) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {"season": season, "week": week, "team": t, "gsis_id": g, "report_status": s}
            for t, g, s in rows
        ],
        schema=SCHEMA,
    )


def check(frame: pl.DataFrame, gsis_id: str = "P1", team: str = "TMA") -> Availability:
    return availability(frame, season=2024, week=5, team=team, gsis_id=gsis_id)


@pytest.mark.parametrize(
    ("status", "reason"), [("Out", PricerUnpriced.OUT), ("Doubtful", PricerUnpriced.DOUBTFUL)]
)
def test_out_and_doubtful_are_unpriced(status: str, reason: PricerUnpriced) -> None:
    a = check(inj(("TMA", "P1", status)))
    assert a.reason is reason
    assert a.status_seen == status
    assert a.final_report_in is True


def test_questionable_is_priced_and_flagged() -> None:
    a = check(inj(("TMA", "P1", "Questionable")))
    assert a.reason is None and a.flag is AvailabilityFlag.QUESTIONABLE
    assert a.status_seen == "Questionable"


@pytest.mark.parametrize("blank", [None, "", "  "])
def test_listed_without_designation_and_final_report_in(blank: Any) -> None:
    a = check(inj(("TMA", "P1", blank), ("TMA", "P2", "Out")))
    assert a == Availability(status_seen="none", final_report_in=True, flag=None, reason=None)


def test_listed_without_designation_and_no_final_report() -> None:
    a = check(inj(("TMA", "P1", None), ("TMA", "P2", None)))
    assert a == Availability(
        status_seen="none",
        final_report_in=False,
        flag=AvailabilityFlag.NO_FINAL_REPORT,
        reason=None,
    )


def test_not_listed_with_final_report_in_is_unflagged() -> None:
    a = check(inj(("TMA", "P2", "Questionable")))
    assert a == Availability(status_seen="not_listed", final_report_in=True, flag=None, reason=None)


def test_not_listed_and_no_report_rows_is_flagged() -> None:
    a = check(inj())
    assert a == Availability(
        status_seen="not_listed",
        final_report_in=False,
        flag=AvailabilityFlag.NO_FINAL_REPORT,
        reason=None,
    )


def test_only_his_team_and_the_target_week_are_read() -> None:
    other_team = inj(("TMB", "P1", "Out"), ("TMB", "P9", "Out"))
    assert check(other_team).status_seen == "not_listed"
    assert check(other_team).final_report_in is False
    other_week = inj(("TMA", "P1", "Out"), week=4)
    assert check(other_week).reason is None
    other_season = inj(("TMA", "P1", "Out"), season=2023)
    assert check(other_season).reason is None


def test_unknown_status_on_his_own_row_is_injury_status_unclear() -> None:
    # Sync #7: unpriced, no crash; the raw text seen is stored (ruling 2026-11-27).
    a = check(inj(("TMA", "P1", "Probable"), ("TMA", "P2", "Out")))
    assert a == Availability(
        status_seen="Probable",
        final_report_in=True,
        flag=None,
        reason=PricerUnpriced.INJURY_STATUS_UNCLEAR,
    )


def test_conflicting_rows_are_injury_status_unclear() -> None:
    a = check(inj(("TMA", "P1", "Out"), ("TMA", "P1", "Questionable")))
    assert a.reason is PricerUnpriced.INJURY_STATUS_UNCLEAR and a.flag is None
    # distinct statuses, sorted, joined with '|'; a blank row reads 'none'
    assert a.status_seen == "Out|Questionable"
    b = check(inj(("TMA", "P1", "Doubtful"), ("TMA", "P1", None)))
    assert b.reason is PricerUnpriced.INJURY_STATUS_UNCLEAR
    assert b.status_seen == "Doubtful|none"


def test_unknown_and_known_status_on_his_rows_is_unclear() -> None:
    a = check(inj(("TMA", "P1", "Out"), ("TMA", "P1", "Probable")))
    assert a.reason is PricerUnpriced.INJURY_STATUS_UNCLEAR
    assert a.status_seen == "Out|Probable"


def test_unknown_status_on_a_teammates_row_is_ignored_for_the_final_report() -> None:
    a = check(inj(("TMA", "P1", None), ("TMA", "P2", "Probable")))
    assert a == Availability(
        status_seen="none",
        final_report_in=False,
        flag=AvailabilityFlag.NO_FINAL_REPORT,
        reason=None,
    )
    b = check(inj(("TMA", "P2", "Probable"), ("TMA", "P3", "Questionable")))
    assert b == Availability(status_seen="not_listed", final_report_in=True, flag=None, reason=None)
    c = check(inj(("TMA", "P1", "Questionable"), ("TMA", "P2", "Probable")))
    assert c.reason is None and c.flag is AvailabilityFlag.QUESTIONABLE


def test_duplicate_identical_rows_are_one_status() -> None:
    assert check(inj(("TMA", "P1", "Out"), ("TMA", "P1", "Out"))).reason is PricerUnpriced.OUT


# ---- PRV-03 check order ----


def test_first_reason_follows_the_spec_order() -> None:
    assert first_reason(None, None, None, None, None) is None
    assert first_reason("x_mismatch", "unmapped", PricerUnpriced.OUT, None, None) == "x_mismatch"
    assert first_reason(None, "unmapped", PricerUnpriced.OUT, None, None) == "unmapped"
    assert (
        first_reason(None, None, PricerUnpriced.DOUBTFUL, PricerUnpriced.TOO_FEW_STINT_GAMES, None)
        == "doubtful"
    )
    assert (
        first_reason(
            None, None, None, PricerUnpriced.MU_NOT_POSITIVE, PricerUnpriced.NO_FITTED_PARAMS
        )
        == "mu_not_positive"
    )
    assert (
        first_reason(None, None, None, None, PricerUnpriced.NO_FITTED_PARAMS) == "no_fitted_params"
    )
    assert (
        first_reason(
            None,
            None,
            PricerUnpriced.INJURY_STATUS_UNCLEAR,
            PricerUnpriced.DUPLICATE_FF_ROWS,
            None,
        )
        == "injury_status_unclear"
    )
    assert (
        first_reason(
            None, None, None, PricerUnpriced.DUPLICATE_FF_ROWS, PricerUnpriced.NO_FITTED_PARAMS
        )
        == "duplicate_ff_rows"
    )


def test_reason_codes_are_listed_in_the_spec_order() -> None:
    # Sync #7: PRV-08 (out, doubtful, injury_status_unclear), PRV-03 (duplicate_ff_rows,
    # too_few_stint_games, no_centring_mean, mu_not_positive), then no_fitted_params.
    assert [r.value for r in PricerUnpriced] == [
        "out",
        "doubtful",
        "injury_status_unclear",
        "duplicate_ff_rows",
        "too_few_stint_games",
        "no_centring_mean",
        "mu_not_positive",
        "no_fitted_params",
    ]


@pytest.mark.parametrize(
    "args",
    [
        (None, None, PricerUnpriced.TOO_FEW_STINT_GAMES, None, None),
        (None, None, None, PricerUnpriced.OUT, None),
        (None, None, PricerUnpriced.DUPLICATE_FF_ROWS, None, None),
        (None, None, None, PricerUnpriced.INJURY_STATUS_UNCLEAR, None),
        (None, None, None, None, PricerUnpriced.MU_NOT_POSITIVE),
    ],
)
def test_a_reason_in_the_wrong_stage_raises(args: tuple[Any, ...]) -> None:
    with pytest.raises(ValueError):
        first_reason(*args)
