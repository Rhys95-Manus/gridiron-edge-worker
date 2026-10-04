"""DATA-08: newly discovered series arrive with a rule-based proposal (user request
2026-10-04); decisions stay the user's. Live runs have no fee-schedule PDF (bot check), so that
rule is skipped and labelled (user decision 2026-10-04)."""

from __future__ import annotations

from pathlib import Path

import yaml

from ge.ingest.kalshi import (
    FEE_RULE_SKIPPED,
    apply_decisions,
    nfl_candidates,
    refresh_review,
    update_review_file,
)
from tests.phase1.test_kalshi_proposals import _series, _teams


def _rows(path: Path) -> dict:  # type: ignore[type-arg]
    return yaml.safe_load(path.read_text(encoding="utf-8"))["series"]


def test_new_series_get_a_proposal_and_stay_pending(tmp_path: Path) -> None:
    review = tmp_path / "review.yaml"
    series = _series()
    first, rest = series[:3], series[3:]
    # an existing file: three candidates already decided by the user
    update_review_file(review, nfl_candidates(first))
    decided = {c.ticker: "decided earlier" for c in nfl_candidates(first)}
    apply_decisions(review, {}, decided, decided_by="user", decided_on="2026-09-29")
    before = {t: dict(r) for t, r in _rows(review).items()}

    cands, new = refresh_review(review, series, _teams())
    rows = _rows(review)
    new_tickers = {c.ticker for c in nfl_candidates(rest)} - set(before)
    assert new == len(new_tickers) > 0
    assert {c.ticker for c in cands} == set(rows)
    for t in new_tickers:
        assert rows[t]["decision"] == "pending", t
        assert rows[t]["proposed"] in {"include", "exclude", "undecided"}, t
        assert FEE_RULE_SKIPPED in rows[t]["proposed_rules"], t
    for t, row in before.items():  # existing rows: decision and its record untouched
        for key in ("decision", "decided_by", "decided_on", "decision_basis"):
            assert rows[t][key] == row[key], (t, key)
        assert "proposed" not in rows[t], t


def test_proposals_are_not_redone(tmp_path: Path) -> None:
    """A pending row that already has a proposal keeps it; refresh only proposes for rows
    without one (so a proposal the user has read doesn't change under them)."""
    review = tmp_path / "review.yaml"
    refresh_review(review, _series(), _teams())
    data = yaml.safe_load(review.read_text(encoding="utf-8"))
    some = next(t for t, r in data["series"].items() if r["decision"] == "pending")
    data["series"][some]["proposed"] = "undecided"
    data["series"][some]["proposed_rules"] = ["kept"]
    review.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    refresh_review(review, _series(), _teams())
    assert _rows(review)[some]["proposed_rules"] == ["kept"]
