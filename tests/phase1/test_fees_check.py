"""DATA-09 / EDG-02: `ge ingest fees-check` reads the fee PDF's "Last updated and effective"
date and fails loudly when it differs from config/fees.yaml.

The PDF fixture must be the real file, saved by hand (the download is behind a bot check)."""

import datetime as dt
from pathlib import Path

from ge.config import load_fees
from ge.ingest.fees_check import FeeCheckResult, check_fee_schedule, parse_effective_date

PDF = Path(__file__).parent / "fixtures" / "kalshi_fee_schedule.pdf"


def test_real_pdf_date_matches_fees_yaml() -> None:
    assert PDF.exists(), f"save the real fee schedule PDF to {PDF} (see phase report)"
    assert parse_effective_date(PDF.read_bytes()) == load_fees().schedule_effective_date


def test_matching_date_passes() -> None:
    fees = load_fees()
    result = check_fee_schedule(fees, fees.schedule_effective_date)
    assert result == FeeCheckResult(
        ok=True, pdf_date=fees.schedule_effective_date, config_date=fees.schedule_effective_date
    )


def test_changed_date_fails_with_both_dates_in_the_message() -> None:
    fees = load_fees()
    newer = fees.schedule_effective_date + dt.timedelta(days=1)
    result = check_fee_schedule(fees, newer)
    assert not result.ok
    assert str(newer) in result.message and str(fees.schedule_effective_date) in result.message


def test_text_without_the_phrase_raises() -> None:
    try:
        parse_effective_date(b"%PDF-1.4 not a fee schedule")
    except ValueError:
        return
    raise AssertionError("an unreadable or unrelated PDF must raise, not guess a date")
