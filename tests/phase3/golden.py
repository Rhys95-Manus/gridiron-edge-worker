"""Comparison helpers for golden tests: metric frames vs the oracle."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import polars as pl
import pytest

from tests.phase3.oracle import Agg

REL = 1e-12


def _approx(x: float | None) -> Any:
    return None if x is None else pytest.approx(x, rel=REL, abs=1e-12)


def check_raw(
    frame: pl.DataFrame,
    stat: str,
    want: dict[tuple[str, str], Agg],
    league_want: dict[str, float],
    entities: Iterable[str],
    cells: Iterable[str],
    min_n: Callable[[str], float] | None = None,
) -> None:
    """Every (entity, cell) has a row; n, value, value_w, n_eff and the min-n flag match."""
    rows = frame.filter(pl.col("stat") == stat)
    ent = rows.filter(pl.col("entity_type") != "league")
    got = {(r["entity_id"], r["cell"]): r for r in ent.iter_rows(named=True)}
    cells = list(cells)
    for e in entities:
        for c in cells:
            assert (e, c) in got, f"{stat}: no row for {e} {c}"
            r, a = got[(e, c)], want.get((e, c))
            if a is None:
                assert r["n"] == 0 and r["value"] is None, (e, c, r)
                continue
            assert r["n"] == a.n, (stat, e, c)
            assert r["value"] == _approx(a.value), (stat, e, c)
            assert r["value_w"] == _approx(a.value_w), (stat, e, c)
            assert r["n_eff"] == _approx(a.n_eff), (stat, e, c)
            if min_n is not None:
                assert r["min_n"] == min_n(c)
                assert r["below_min_sample"] == (a.n < min_n(c)), (stat, e, c)
    lg = {
        r["cell"]: r for r in rows.filter(pl.col("entity_type") == "league").iter_rows(named=True)
    }
    for c, x in league_want.items():
        assert lg[c]["value"] == _approx(x), (stat, "league", c)


def check_shrunk(
    frame: pl.DataFrame,
    want: dict[tuple[str, str], float],
    prior: dict[tuple[str, str], float],
    k: Callable[[str], float],
) -> None:
    got = {(r["entity_id"], r["cell"]): r for r in frame.iter_rows(named=True)}
    assert set(want) <= set(got), sorted(set(want) - set(got))[:5]
    for key, s in want.items():
        r = got[key]
        assert r["prior"] == _approx(prior[key]), key
        assert r["k"] == k(key[1]), key
        assert r["shrunk"] == _approx(s), key
