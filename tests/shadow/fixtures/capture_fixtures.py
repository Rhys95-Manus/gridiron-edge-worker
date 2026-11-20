"""Save the shadow-track fixtures from the local raw store. Run once, by hand:

    uv run python tests/shadow/fixtures/capture_fixtures.py

Reads data/raw/kalshi_markets/season=2026 only (DATA-08 public market data, written by
`ge ingest`); 2025 is the holdout and is never opened. Uses polars directly (not ge code) so
fixtures don't depend on the code under test. Every file records its source and pull time
(CLAUDE.md rule 2). Player names, the name part of the ticker's player segment and Kalshi
player UUIDs are replaced with placeholders (Player 01, PLAYER01, a fixed placeholder UUID).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import polars as pl

HERE = Path(__file__).parent
REPO = HERE.parents[2]
SEASON_DIR = REPO / "data" / "raw" / "kalshi_markets" / "season=2026"
SERIES = ("KXNFLRECYDS", "KXNFLRSHYDS", "KXNFLREC")  # PRV-01
# The fields the PRV-01 parser reads, plus a few for context. Anything else is dropped so
# no unreviewed field carries a player name into the repo.
KEEP = (
    "ticker",
    "event_ticker",
    "series_ticker",
    "title",
    "yes_sub_title",
    "no_sub_title",
    "floor_strike",
    "cap_strike",
    "strike_type",
    "custom_strike",
    "market_type",
    "status",
)
GAME = re.compile(r"^[A-Z0-9]+-\d{2}[A-Z]{3}\d{2}([A-Z]+)$")
TITLE = re.compile(r"^(.+): \d+\+ ")
PER_SIDE = 3  # strikes kept per player
# Game-code length wanted per series (3+3, 2+3 and 2+2 letter team pairs), so the fixtures
# cover 2-letter team codes; the first event is used when no game has that length.
GAME_LENGTHS = (6, 5, 4)


def _game(event_ticker: str) -> str:
    g = GAME.match(event_ticker)
    assert g, event_ticker
    return g.group(1)


def _partitions() -> list[Path]:
    assert SEASON_DIR.name == "season=2026", SEASON_DIR
    return sorted(p for p in SEASON_DIR.iterdir() if p.name.startswith("pulled_at="))


def _pulled_at(df: pl.DataFrame) -> str:
    vals = df["pulled_at"].unique().to_list()
    assert len(vals) == 1, vals
    return str(vals[0].isoformat())


def _source(p: Path) -> str:
    return f"data/raw/kalshi_markets/season=2026/{p.name}/part.parquet (DATA-08, via ge ingest)"


def _save(name: str, body: dict[str, Any]) -> None:
    text = json.dumps(body, indent=1, ensure_ascii=False) + "\n"
    (HERE / name).write_text(text, encoding="utf-8", newline="\n")


def team_codes() -> tuple[list[str], str, str]:
    """Kalshi's NFL team codes: the last segment of every KXNFLGAME winner ticker in 2026."""
    parts = _partitions()
    codes: set[str] = set()
    for p in parts:
        df = pl.read_parquet(p / "part.parquet", columns=["series_ticker", "ticker"])
        codes |= {
            t.split("-")[-1] for t in df.filter(pl.col("series_ticker") == "KXNFLGAME")["ticker"]
        }
    return sorted(codes), parts[0].name, parts[-1].name


def _split(teams: str, codes: set[str]) -> tuple[str, str]:
    splits = [(teams[:i], teams[i:]) for i in range(1, len(teams))]
    ok = [s for s in splits if s[0] in codes and s[1] in codes]
    assert len(ok) == 1, (teams, ok)
    return ok[0]


class Anonymiser:
    def __init__(self) -> None:
        self.by_uuid: dict[str, int] = {}
        self.real: set[str] = set()

    def number(self, uuid: str) -> int:
        return self.by_uuid.setdefault(uuid, len(self.by_uuid) + 1)

    def market(self, j: dict[str, Any], team: str) -> dict[str, Any]:
        m = TITLE.match(j["title"])
        assert m, j["title"]
        name = m.group(1)
        n = self.number(j["custom_strike"]["football_player"])
        series, game, player, x = j["ticker"].split("-")
        assert player.startswith(team), (player, team)
        self.real |= {name, player[len(team) :], j["custom_strike"]["football_player"]}
        self.real |= set(name.split())
        out = {k: j[k] for k in KEEP if k in j}
        for k in ("title", "yes_sub_title", "no_sub_title"):
            out[k] = out[k].replace(name, f"Player {n:02d}")
        out["ticker"] = f"{series}-{game}-{team}PLAYER{n:02d}-{x}"
        out["custom_strike"] = {
            **j["custom_strike"],
            "football_player": f"00000000-0000-4000-8000-{n:012d}",
        }
        return out

    def rules(self, j: dict[str, Any]) -> dict[str, str]:
        m = TITLE.match(j["title"])
        assert m
        name = m.group(1)
        n = self.number(j["custom_strike"]["football_player"])
        self.real |= {name, *name.split()}
        return {
            "rules_primary": j["rules_primary"].replace(name, f"Player {n:02d}"),
            "rules_secondary": j["rules_secondary"].replace(name, f"Player {n:02d}"),
        }

    def check(self, text: str) -> None:
        # Short tokens (initials, "Jr") would match ordinary words, so check names of 3+ letters.
        leaks = sorted(r for r in self.real if len(r) >= 3 and r in text)
        assert not leaks, f"real player data left in a fixture: {len(leaks)} tokens"


def main() -> None:
    codes, first, last = team_codes()
    code_set = set(codes)
    newest = _partitions()[-1]
    df = pl.read_parquet(newest / "part.parquet").filter(pl.col("series_ticker").is_in(SERIES))
    pulled_at = _pulled_at(df)
    anon = Anonymiser()
    markets: list[dict[str, Any]] = []
    rules: dict[str, dict[str, str]] = {}
    for series, game_len in zip(SERIES, GAME_LENGTHS, strict=True):
        rows = [json.loads(r) for r in df.filter(pl.col("series_ticker") == series)["raw_json"]]
        rows.sort(key=lambda j: (j["event_ticker"], j["ticker"]))
        events = sorted({j["event_ticker"] for j in rows})
        event = next((e for e in events if len(_game(e)) == game_len), events[0])
        g = GAME.match(event)
        assert g, event
        away, home = _split(g.group(1), code_set)
        in_event = [j for j in rows if j["event_ticker"] == event]
        for team in (away, home):
            side = [j for j in in_event if j["ticker"].split("-")[2].startswith(team)]
            uuid = side[0]["custom_strike"]["football_player"]
            mine = sorted(
                (j for j in side if j["custom_strike"]["football_player"] == uuid),
                key=lambda j: j["floor_strike"],
            )
            markets += [anon.market(j, team) for j in mine[:PER_SIDE]]
        rules[series] = {
            "ticker": anon.market(in_event[0], _team(in_event[0], away, home))["ticker"]
        }
        rules[series] |= anon.rules(in_event[0])

    common = {
        "pulled_at": pulled_at,
        "anonymised": "player names -> 'Player NN', ticker player segment -> <team>PLAYERNN, "
        "Kalshi player UUID -> placeholder; everything else as downloaded",
    }
    m_body = {"source": _source(newest), **common, "markets": markets}
    r_body = {"source": _source(newest), **common, "rules": rules}
    for body in (m_body, r_body):
        anon.check(json.dumps(body, ensure_ascii=False))
    _save("kalshi_prop_markets.json", m_body)
    _save("kalshi_prop_rules.json", r_body)
    _save(
        "kalshi_team_codes.json",
        {
            "source": "last segment of every KXNFLGAME ticker in data/raw/kalshi_markets/"
            f"season=2026, partitions {first} to {last} (DATA-08, via ge ingest)",
            "pulled_at": pulled_at,
            "codes": codes,
        },
    )
    print(f"{len(markets)} markets, {len(rules)} rules, {len(codes)} team codes from {newest.name}")


def _team(j: dict[str, Any], away: str, home: str) -> str:
    player = j["ticker"].split("-")[2]
    hits = [t for t in (away, home) if player.startswith(t)]
    assert len(hits) == 1, hits
    return hits[0]


if __name__ == "__main__":
    main()
