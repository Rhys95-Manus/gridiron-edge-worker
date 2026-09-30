"""DATA-09 / EDG-02: compare the Kalshi fee schedule PDF's "Last updated and effective" date
with config/fees.yaml. A mismatch is an alert: the fee table may have changed."""

from __future__ import annotations

import datetime as dt
import io
import re
from dataclasses import dataclass
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ge.config import AcknowledgedFee, Fees

_PHRASE = re.compile(
    r"Last\s+updated\s+and\s+effective\W*([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", re.IGNORECASE
)


def parse_effective_date(pdf: bytes) -> dt.date:
    """DATA-09: read the date after "Last updated and effective" in the fee schedule PDF."""
    try:
        text = " ".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)
    except (PdfReadError, ValueError, OSError) as exc:
        raise ValueError(f"cannot read fee schedule PDF: {exc}") from exc
    m = _PHRASE.search(text)
    if not m:
        raise ValueError('"Last updated and effective <date>" not found in the PDF text')
    month, day, year = m.groups()
    return dt.datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()


@dataclass(frozen=True)
class FeeCheckResult:
    ok: bool
    pdf_date: dt.date
    config_date: dt.date

    @property
    def message(self) -> str:
        if self.ok:
            return f"fee schedule unchanged: effective {self.pdf_date}"
        return (
            f"ALERT: Kalshi fee schedule date {self.pdf_date} differs from fees.yaml "
            f"{self.config_date}. Review the PDF and update EDG-02 before trading."
        )


def check_fee_schedule(fees: Fees, pdf_date: dt.date) -> FeeCheckResult:
    """EDG-02: fees.yaml is only valid for the schedule date it was built from."""
    return FeeCheckResult(
        pdf_date == fees.schedule_effective_date, pdf_date, fees.schedule_effective_date
    )


def _fees_row(fees: Fees, ticker: str) -> tuple[str, int, int, str | None]:
    """(row name, taker M, maker M, row a ticker only prefix-matches) for one series."""
    rows = {
        "KXNFLGAME": fees.series.kxnflgame,
        "KXMVE": fees.series.kxmve,
        "futures_and_awards": fees.series.futures_and_awards,
    }
    for name, row in rows.items():
        if ticker in row.tickers:
            return name, row.taker_multiplier, row.maker_multiplier, None
    prefix = next((t for row in rows.values() for t in row.tickers if ticker.startswith(t)), None)
    d = fees.series.default
    return "default", d.taker_multiplier, d.maker_multiplier, prefix


@dataclass(frozen=True)
class Disagreement:
    ticker: str
    field: str  # taker | maker
    fees_yaml_value: float
    api_value: float
    api_fee_type: str
    value_in_use: float
    message: str


@dataclass(frozen=True)
class EffectiveFees:
    ticker: str
    row: str
    taker: float
    maker: float
    known: bool  # False when Kalshi's fee_type isn't modelled: no fee can be trusted
    alerts: list[str]
    disagreements: tuple[Disagreement, ...] = ()


def effective_multipliers(fees: Fees, series: dict[str, Any]) -> EffectiveFees:
    """EDG-02: multipliers for one series. Where fees.yaml and Kalshi's API disagree, the
    costlier value is used and the difference is alerted (decisions log 2026-09-29)."""
    ticker = series["ticker"]
    row, taker, maker, prefix = _fees_row(fees, ticker)
    alerts = []
    if prefix:
        alerts.append(
            f"{ticker}: not listed in fees.yaml, so the {row} row applies, but it starts "
            f"with {prefix} (prefix match only): confirm which EDG-02 row covers it"
        )
    by_type = {
        name: getattr(fees.api_fee_types, name).maker_multiplier
        for name in type(fees.api_fee_types).model_fields
    }
    fee_type, mult = series.get("fee_type"), series.get("fee_multiplier")
    if fee_type not in by_type or not isinstance(mult, int | float):
        alerts.append(
            f"{ticker}: Kalshi fee_type {fee_type!r} / fee_multiplier {mult!r} is not modelled "
            "in fees.yaml; fees for this series cannot be trusted"
        )
        return EffectiveFees(ticker, row, taker, maker, False, alerts)
    api_maker = by_type[fee_type]
    diffs = []
    if mult != taker:
        msg = (
            f"{ticker}: Kalshi taker multiplier {mult} != fees.yaml {row} {taker}; "
            f"using {max(mult, taker)}"
        )
        diffs.append(Disagreement(ticker, "taker", taker, mult, fee_type, max(mult, taker), msg))
    if api_maker != maker:
        msg = (
            f"{ticker}: Kalshi fee_type {fee_type} means maker {api_maker}, fees.yaml {row} "
            f"row says maker {maker}; using {max(api_maker, maker)}"
        )
        diffs.append(
            Disagreement(ticker, "maker", maker, api_maker, fee_type, max(api_maker, maker), msg)
        )
    alerts += [d.message for d in diffs]
    return EffectiveFees(
        ticker, row, max(mult, taker), max(api_maker, maker), True, alerts, tuple(diffs)
    )


@dataclass(frozen=True)
class FeeCheck:
    effective: list[EffectiveFees]
    acknowledged: list[str]  # disagreements matching an acknowledgement exactly
    new: list[str]  # anything else that alerts: new or changed disagreements, unknown fees
    stale: list[str]  # acknowledgements for disagreements no longer seen

    @property
    def ok(self) -> bool:
        return not self.new and not self.stale


def fee_check(fees: Fees, series: list[dict[str, Any]]) -> FeeCheck:
    """EDG-02: split every alert into acknowledged (exact match on ticker, field, both values,
    fee_type and value in use) and new. The costlier value is used either way."""
    acks: dict[tuple[str, str], AcknowledgedFee] = {
        (a.ticker, a.field): a for a in fees.acknowledged
    }
    effective = [effective_multipliers(fees, s) for s in series]
    acknowledged, new, seen = [], [], set()
    for e in effective:
        diff_msgs = {d.message for d in e.disagreements}
        new += [a for a in e.alerts if a not in diff_msgs]  # prefix / unknown fee_type
        for d in e.disagreements:
            a = acks.get((d.ticker, d.field))
            match = a is not None and (
                a.fees_yaml_value,
                a.api_value,
                a.api_fee_type,
                a.value_in_use,
            ) == (d.fees_yaml_value, d.api_value, d.api_fee_type, d.value_in_use)
            if match:
                seen.add((d.ticker, d.field))
                acknowledged.append(d.message)
            else:
                new.append(d.message + ("" if a is None else " (differs from acknowledgement)"))
    checked = {s["ticker"] for s in series}
    stale = [
        f"{t} {f}: acknowledged disagreement no longer seen (fee fields changed?)"
        for (t, f) in sorted(acks)
        if t in checked
        and (t, f) not in seen
        and not any(d.ticker == t and d.field == f for e in effective for d in e.disagreements)
    ]
    return FeeCheck(effective, acknowledged, new, stale)


def api_fee_alerts(fees: Fees, series: list[dict[str, Any]]) -> list[str]:
    """EDG-02: every difference between fees.yaml and what Kalshi's API reports per series."""
    return [a for s in series for a in effective_multipliers(fees, s).alerts]
