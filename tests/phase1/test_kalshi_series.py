"""DATA-08: NFL series discovery proposes candidates with reasons; only approved are ingested."""

from pathlib import Path

import yaml

from ge.ingest.kalshi import approved_series, nfl_candidates, update_review_file
from tests.phase1.conftest import load_fixture


def _series() -> list[dict]:
    return load_fixture("kalshi_series_subset.json")["response"]["series"]


def test_every_candidate_has_a_reason() -> None:
    cands = nfl_candidates(_series())
    assert cands
    assert all(c.reasons for c in cands)


def test_combo_and_game_series_are_candidates() -> None:
    tickers = {c.ticker for c in nfl_candidates(_series())}
    real = {s["ticker"] for s in _series()}
    combos = {t for t in real if t.startswith("KXMVENFL")}
    assert combos and combos <= tickers
    assert "KXNFLGAME" in tickers


def test_netflix_is_not_nfl() -> None:
    tickers = {c.ticker for c in nfl_candidates(_series())}
    nflx = {s["ticker"] for s in _series() if "NFLX" in s["ticker"]}
    assert nflx, "fixture should contain an NFLX series to test against"
    assert not (nflx & tickers)


def test_football_tagged_without_nfl_in_name_is_a_candidate() -> None:
    """Catches series like a team's week-1 QB market whose ticker never says NFL."""
    cands = {c.ticker: c for c in nfl_candidates(_series())}
    tagged_only = [
        s["ticker"]
        for s in _series()
        if "Football" in (s.get("tags") or [])
        and "NFL" not in (s["ticker"] + (s.get("title") or "")).upper()
    ]
    assert tagged_only
    assert all(t in cands for t in tagged_only)


def test_review_file_keeps_decisions_and_marks_new_as_pending(tmp_path: Path) -> None:
    review = tmp_path / "kalshi_nfl_series.yaml"
    cands = nfl_candidates(_series())
    update_review_file(review, cands)
    data = yaml.safe_load(review.read_text(encoding="utf-8"))
    assert {row["decision"] for row in data["series"].values()} == {"pending"}
    assert approved_series(review) == set()

    first, second = sorted(data["series"])[:2]
    data["series"][first]["decision"] = "include"
    data["series"][second]["decision"] = "exclude"
    review.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")

    new_count = update_review_file(review, cands)  # rerun: nothing new
    assert new_count == 0
    again = yaml.safe_load(review.read_text(encoding="utf-8"))
    assert again["series"][first]["decision"] == "include"
    assert again["series"][second]["decision"] == "exclude"
    assert approved_series(review) == {first}


def test_apply_decisions_records_who_and_when(tmp_path: Path) -> None:
    from ge.ingest.kalshi import apply_decisions

    review = tmp_path / "kalshi_nfl_series.yaml"
    update_review_file(review, nfl_candidates(_series()))
    tickers = sorted(yaml.safe_load(review.read_text(encoding="utf-8"))["series"])
    inc, exc = {tickers[0]: "rule"}, {tickers[1]: "explicit"}
    apply_decisions(review, inc, exc, decided_by="user", decided_on="2026-09-29")
    rows = yaml.safe_load(review.read_text(encoding="utf-8"))["series"]
    assert rows[tickers[0]]["decision"] == "include"
    assert rows[tickers[1]]["decision"] == "exclude"
    assert rows[tickers[0]]["decided_by"] == "user"
    assert rows[tickers[0]]["decided_on"] == "2026-09-29"
    assert rows[tickers[1]]["decision_basis"] == "explicit"
    assert rows[tickers[2]]["decision"] == "pending"
    assert approved_series(review) == {tickers[0]}


def test_apply_decisions_rejects_unknown_or_double_listed(tmp_path: Path) -> None:
    from ge.ingest.kalshi import apply_decisions

    review = tmp_path / "kalshi_nfl_series.yaml"
    update_review_file(review, nfl_candidates(_series()))
    first = sorted(yaml.safe_load(review.read_text(encoding="utf-8"))["series"])[0]
    for inc, exc in (({"KXNOTASERIES": "x"}, {}), ({first: "x"}, {first: "y"})):
        try:
            apply_decisions(review, inc, exc, decided_by="user", decided_on="2026-09-29")
        except ValueError:
            continue
        raise AssertionError(f"should reject include={inc} exclude={exc}")


def test_bad_decision_value_is_rejected(tmp_path: Path) -> None:
    review = tmp_path / "kalshi_nfl_series.yaml"
    update_review_file(review, nfl_candidates(_series()))
    data = yaml.safe_load(review.read_text(encoding="utf-8"))
    key = sorted(data["series"])[0]
    data["series"][key]["decision"] = "yes"
    review.write_text(yaml.safe_dump(data), encoding="utf-8")
    try:
        approved_series(review)
    except ValueError:
        return
    raise AssertionError("decision 'yes' should be rejected; only include/exclude/pending")
