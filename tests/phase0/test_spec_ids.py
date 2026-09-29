"""BUILD_PLAN Phase 0: every spec_id in params.yaml and fees.yaml appears in docs/MODEL_SPEC.md,
and every value traces to a verbatim quote from the spec."""

import datetime as dt
import re
from typing import Any

import yaml

from tests.phase0.helpers import (
    FEES_PATH,
    PARAMS_PATH,
    iter_leaves,
    normalize_md,
    numbers_in,
    spec_ids,
    spec_table_rows,
    spec_text,
    value_in_source,
)


def _load(path: Any) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _entry_ids(entry: dict[str, Any]) -> list[str]:
    sid = entry["spec_id"]
    return [sid] if isinstance(sid, str) else list(sid)


def test_spec_has_ids() -> None:
    ids = spec_ids()
    assert {"G1", "OFF-01", "EDG-02", "BT-07e"} <= ids


def test_every_params_spec_id_is_in_spec() -> None:
    ids = spec_ids()
    missing = [
        f"{g}.{n}: {sid}"
        for g, n, e in iter_leaves(_load(PARAMS_PATH))
        for sid in _entry_ids(e)
        if sid not in ids
    ]
    assert not missing, f"spec_ids not in MODEL_SPEC.md: {missing}"


def test_fees_spec_id_is_in_spec() -> None:
    assert _load(FEES_PATH)["spec_id"] in spec_ids()


def test_every_params_source_is_verbatim_spec_text() -> None:
    """Verbatim after normalize_md on both sides, so a re-export's Markdown styling doesn't
    break provenance while any change to words, numbers or symbols still does."""
    text = normalize_md(spec_text())
    missing = [
        f"{g}.{n}"
        for g, n, e in iter_leaves(_load(PARAMS_PATH))
        if normalize_md(e["source"]) not in text
    ]
    assert not missing, f"source is not a verbatim quote from MODEL_SPEC.md: {missing}"


def test_every_params_value_appears_in_its_source() -> None:
    bad = [
        f"{g}.{n}: value {e['value']!r} not in {e['source']!r}"
        for g, n, e in iter_leaves(_load(PARAMS_PATH))
        if not value_in_source(e["value"], e["source"])
    ]
    assert not bad, "\n".join(bad)


def test_param_source_sits_on_a_line_naming_its_spec_id() -> None:
    """A table-row ID (OFF-/DEF-/PLY-/COA-) must be quoted from its own row, or from prose
    that names it (e.g. "What PLY-15 cannot do")."""
    row_ids = {row_id for row_id, _, _ in spec_table_rows(("OFF-", "DEF-", "PLY-", "COA-"))}
    lines = normalize_md(spec_text()).splitlines()
    bad = []
    for g, n, e in iter_leaves(_load(PARAMS_PATH)):
        source = normalize_md(e["source"])
        for sid in _entry_ids(e):
            if sid not in row_ids:
                continue
            naming = [ln for ln in lines if re.search(rf"\b{re.escape(sid)}\b", ln)]
            if not any(source in ln for ln in naming):
                bad.append(f"{g}.{n}: source not on any line naming {sid}")
    assert not bad, bad


def test_fees_match_edg02_table() -> None:
    fees = _load(FEES_PATH)
    rows = []
    in_table = False
    for line in spec_text().splitlines():
        if line.startswith("| Series (NFL)"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            if set(line) <= set("|-: "):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append((cells[0], int(cells[1]), int(cells[2])))
    assert len(rows) == 4, rows
    keys = ["default", "KXNFLGAME", "KXMVE", "futures_and_awards"]
    for key, (label, taker, maker) in zip(keys, rows, strict=True):
        series = fees["series"][key]
        assert (series["taker_multiplier"], series["maker_multiplier"]) == (taker, maker), label
    assert fees["series"]["KXNFLGAME"]["tickers"] == ["KXNFLGAME"]
    assert fees["series"]["KXMVE"]["tickers"] == ["KXMVE"]


def test_fee_rates_match_edg02_formula() -> None:
    fees = _load(FEES_PATH)
    lines = spec_text().splitlines()
    formula = next(line for line in lines if line.startswith("\\text{taker fee}"))
    nums = numbers_in(formula)
    assert fees["taker_rate"] in nums
    assert fees["maker_rate"] in nums


def test_fee_schedule_date_and_url() -> None:
    fees = _load(FEES_PATH)
    assert fees["schedule_effective_date"] == dt.date(2026, 7, 7)
    assert "effective July 7, 2026" in spec_text()
    url = fees["source_url"]
    assert url is None or url in re.findall(r"\((https?://[^)\s]+)\)", spec_text())


def test_fee_rounding_is_conservative_cent() -> None:
    assert _load(FEES_PATH)["rounding"] == "up_to_cent"
