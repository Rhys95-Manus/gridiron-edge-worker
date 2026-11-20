"""PRV-01 market scope: the strike parser for KXNFLRECYDS, KXNFLRSHYDS and KXNFLREC.

Normal markets are real (anonymised) markets from the newest 2026 kalshi_markets partition.
No 2026 partition held an edge case (cap_strike set, non-"greater" strike_type, non-whole X,
missing field: 188 partitions scanned 2026-11-19), so each edge case below is one real market
with one field changed, and says so.
"""

import copy
from typing import Any

import pytest
import yaml

from ge.pricer_v0.scope import (
    PRV01_SERIES,
    TEAM_CODES_PATH,
    ScopedMarket,
    Unpriced,
    load_team_codes,
    scope_market,
)
from tests.shadow.conftest import load_fixture

MARKETS = load_fixture("kalshi_prop_markets.json")["markets"]
CODES = load_team_codes()


def _market(series: str = "KXNFLRECYDS", i: int = 0) -> dict[str, Any]:
    return copy.deepcopy([m for m in MARKETS if m["series_ticker"] == series][i])


def _ticker_swap(m: dict[str, Any], old: str, new: str) -> dict[str, Any]:
    m["ticker"] = m["ticker"].replace(old, new)
    m["event_ticker"] = m["event_ticker"].replace(old, new)
    return m


# ---- normal markets ----


def test_fixture_covers_each_series() -> None:
    assert sorted({m["series_ticker"] for m in MARKETS}) == sorted(PRV01_SERIES)
    assert all(sum(m["series_ticker"] == s for m in MARKETS) >= 5 for s in PRV01_SERIES)


@pytest.mark.parametrize("m", MARKETS, ids=[m["ticker"] for m in MARKETS])
def test_every_fixture_market_is_priced(m: dict[str, Any]) -> None:
    out = scope_market(m, CODES)
    assert out.priced and out.reason is None
    assert out.ticker == m["ticker"] and out.event_ticker == m["event_ticker"]
    assert out.series == m["series_ticker"]
    assert out.floor_strike == m["floor_strike"] and out.strike_type == "greater"
    assert out.cap_strike is None
    assert out.x == int(m["floor_strike"] + 0.5) and out.x == int(m["ticker"].rsplit("-", 1)[1])
    assert out.player_uuid == m["custom_strike"]["football_player"]
    assert out.team_uuid == m["custom_strike"]["football_team"]
    assert out.player_name is not None and out.player_name.startswith("Player ")
    assert out.team_code is not None and m["ticker"].split("-")[2].startswith(out.team_code)


def test_one_market_exactly() -> None:
    m = next(m for m in MARKETS if m["ticker"] == "KXNFLRSHYDS-26NOV22ARIKC-KCPLAYER04-15")
    assert scope_market(m, CODES) == ScopedMarket(
        ticker="KXNFLRSHYDS-26NOV22ARIKC-KCPLAYER04-15",
        event_ticker="KXNFLRSHYDS-26NOV22ARIKC",
        series="KXNFLRSHYDS",
        x=15,
        floor_strike=14.5,
        strike_type="greater",
        cap_strike=None,
        player_uuid="00000000-0000-4000-8000-000000000004",
        team_uuid=m["custom_strike"]["football_team"],
        player_name="Player 04",
        team_code="KC",
        priced=True,
        reason=None,
    )


def test_both_sides_of_a_game_get_their_own_team_code() -> None:
    teams = {
        scope_market(m, CODES).team_code for m in MARKETS if m["event_ticker"].endswith("ARIKC")
    }
    assert teams == {"ARI", "KC"}


# ---- team codes ----


def test_team_codes_config_matches_the_fixture() -> None:
    fixture = load_fixture("kalshi_team_codes.json")
    cfg = yaml.safe_load(TEAM_CODES_PATH.read_text(encoding="utf-8"))
    assert cfg["spec_id"] == "PRV-01" and cfg["status"] == "initial"
    assert cfg["source"] == fixture["source"]
    assert frozenset(fixture["codes"]) == CODES and len(CODES) == 32


def test_two_ways_to_split_the_game_code_is_unpriced() -> None:
    """Synthetic codes: LACKC splits as LA|CKC and LAC|KC, so the team is never guessed."""
    m = _ticker_swap(_market("KXNFLRSHYDS", 3), "ARIKC", "LACKC")
    m["ticker"] = m["ticker"].replace("-KCPLAYER", "-LACPLAYER")
    out = scope_market(m, frozenset({"LA", "CKC", "LAC", "KC"}))
    assert out.reason is Unpriced.TEAM_CODE_UNPARSED and out.team_code is None
    assert scope_market(m, CODES).team_code == "LAC"


# ---- edge cases (synthetic: one real market, one field changed) ----


def _drop(key: str) -> Any:
    def f(m: dict[str, Any]) -> dict[str, Any]:
        del m[key]
        return m

    return f


def _set(key: str, value: Any) -> Any:
    def f(m: dict[str, Any]) -> dict[str, Any]:
        m[key] = value
        return m

    return f


EDGE_CASES: list[tuple[str, Any, Unpriced]] = [
    (
        "protected series",
        lambda m: (
            _ticker_swap(m, "KXNFLRECYDS-", "KXNFLRECYDSPROT-")
            | {"series_ticker": "KXNFLRECYDSPROT"}
        ),
        Unpriced.SERIES_OUT_OF_SCOPE,
    ),
    ("no series_ticker", _drop("series_ticker"), Unpriced.SERIES_MISSING),
    ("strike_type less", _set("strike_type", "less"), Unpriced.STRIKE_TYPE_NOT_GREATER),
    ("strike_type between", _set("strike_type", "between"), Unpriced.STRIKE_TYPE_NOT_GREATER),
    ("no strike_type", _drop("strike_type"), Unpriced.STRIKE_TYPE_MISSING),
    ("cap_strike set", _set("cap_strike", 120.5), Unpriced.CAP_STRIKE_SET),
    ("no floor_strike", _drop("floor_strike"), Unpriced.FLOOR_STRIKE_MISSING),
    ("null floor_strike", _set("floor_strike", None), Unpriced.FLOOR_STRIKE_MISSING),
    ("text floor_strike", _set("floor_strike", "4.5"), Unpriced.FLOOR_STRIKE_NOT_NUMERIC),
    ("bool floor_strike", _set("floor_strike", True), Unpriced.FLOOR_STRIKE_NOT_NUMERIC),
    ("X not whole (.0)", _set("floor_strike", 5.0), Unpriced.STRIKE_NOT_WHOLE),
    ("X not whole (.25)", _set("floor_strike", 4.25), Unpriced.STRIKE_NOT_WHOLE),
    ("no ticker", _drop("ticker"), Unpriced.TICKER_UNPARSED),
    (
        "ticker 3 parts",
        lambda m: m | {"ticker": m["ticker"].rsplit("-", 1)[0]},
        Unpriced.TICKER_UNPARSED,
    ),
    (
        "ticker series differs",
        lambda m: m | {"ticker": "KXNFLREC" + m["ticker"][11:]},
        Unpriced.TICKER_UNPARSED,
    ),
    (
        "event ticker differs",
        lambda m: m | {"event_ticker": m["event_ticker"] + "X"},
        Unpriced.TICKER_UNPARSED,
    ),
    (
        "ticker X differs",
        lambda m: m | {"ticker": m["ticker"].rsplit("-", 1)[0] + "-6"},
        Unpriced.X_MISMATCH,
    ),
    (
        "title X differs",
        lambda m: m | {"title": m["title"].replace("5+", "6+")},
        Unpriced.X_MISMATCH,
    ),
    (
        "title other shape",
        lambda m: m | {"title": "Player 01 over 4.5 receiving yards"},
        Unpriced.TITLE_UNPARSED,
    ),
    (
        "title other stat",
        lambda m: m | {"title": m["title"].replace("receiving", "rushing")},
        Unpriced.TITLE_UNPARSED,
    ),
    ("no title", _drop("title"), Unpriced.TITLE_UNPARSED),
    ("no custom_strike", _drop("custom_strike"), Unpriced.PLAYER_UUID_MISSING),
    (
        "empty player uuid",
        lambda m: m | {"custom_strike": {**m["custom_strike"], "football_player": ""}},
        Unpriced.PLAYER_UUID_MISSING,
    ),
    (
        "unknown team in game",
        lambda m: _ticker_swap(m, "INDHOU", "INDXYZ"),
        Unpriced.TEAM_CODE_UNPARSED,
    ),
    (
        "player of neither team",
        lambda m: m | {"ticker": m["ticker"].replace("-IND", "-DAL")},
        Unpriced.TEAM_CODE_UNPARSED,
    ),
]


@pytest.mark.parametrize(
    ("change", "reason"), [(c, r) for _, c, r in EDGE_CASES], ids=[n for n, _, _ in EDGE_CASES]
)
def test_edge_case_is_unpriced_with_its_reason(change: Any, reason: Unpriced) -> None:
    m = change(_market("KXNFLRECYDS", 0))
    out = scope_market(m, CODES)
    assert not out.priced and out.reason is reason


def test_null_cap_strike_is_no_cap_strike() -> None:
    out = scope_market(_market() | {"cap_strike": None}, CODES)
    assert out.priced and out.cap_strike is None


def test_first_failing_check_names_the_reason() -> None:
    m = _ticker_swap(_market(), "KXNFLRECYDS-", "KXNFLRECYDSPROT-") | {
        "series_ticker": "KXNFLRECYDSPROT",
        "cap_strike": 120.5,
        "strike_type": "less",
    }
    assert scope_market(m, CODES).reason is Unpriced.SERIES_OUT_OF_SCOPE


def test_unpriced_market_keeps_what_parses_exactly() -> None:
    out = scope_market(_market() | {"cap_strike": 120.5}, CODES)
    assert out.reason is Unpriced.CAP_STRIKE_SET
    assert (out.x, out.player_name, out.team_code, out.cap_strike) == (5, "Player 01", "IND", 120.5)
    out = scope_market(_market() | {"floor_strike": 4.25}, CODES)
    assert out.x is None


def test_reason_codes() -> None:
    assert [r.value for r in Unpriced] == [
        "series_missing",
        "series_out_of_scope",
        "strike_type_missing",
        "strike_type_not_greater",
        "cap_strike_set",
        "floor_strike_missing",
        "floor_strike_not_numeric",
        "strike_not_whole",
        "ticker_unparsed",
        "x_mismatch",
        "title_unparsed",
        "player_uuid_missing",
        "team_code_unparsed",
    ]


# ---- rules text (open question: inactive-player settlement) ----


@pytest.mark.parametrize("series", PRV01_SERIES)
def test_rules_cover_active_no_play_but_not_inactive(series: str) -> None:
    rules = load_fixture("kalshi_prop_rules.json")["rules"][series]
    text = rules["rules_primary"] + "\n" + rules["rules_secondary"]
    assert (
        "is active but does not appear in any live play, the market settles to the fair "
        "market price before game start" in text
    )
    assert "inactive" not in text.lower()
