"""Phase 3e engine wiring: with a season's fitted file in force, stats that raised in Phase 3
compute (fitted k, role priors, p_go, G6 penalty, PLY-14 base rates), a "no detectable signal"
k leaves the prior, and without a fit they still raise. Fitted values here are planted test
settings in a temporary fitted root, not fit results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import pytest
import yaml

from ge.config import ATTRIBUTION, load_params, use_fitted_root
from ge.metrics.coaching import P_GO_TERMS, p_go_key
from ge.metrics.engine import NO_SIGNAL, fit_k_key
from ge.metrics.registry import shrunk
from ge.metrics.roles import role_key
from ge.metrics.slots import SLOTS

FIRST = int(load_params().backtest.bt_01_first_training_season.value)
SEASONS = list(range(FIRST, 2024))


def _v(value: float, sid: str) -> dict[str, Any]:
    return {
        "spec_id": sid,
        "status": "fitted",
        "value": value,
        "method": "planted by test",
        "seasons": SEASONS,
        "n": 100,
        "initial_value": None,
    }


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    r = tmp_path_factory.mktemp("pf")
    values = {
        fit_k_key("OFF-12", "ypc_team", None): _v(321.0, "OFF-12"),
        fit_k_key("OFF-12", "explosive_team", None): _v(222.0, "OFF-12"),
        fit_k_key("OFF-12", "share", None): _v(111.0, "OFF-12"),
        fit_k_key("PLY-03", "target_share", None): _v(77.0, "PLY-03"),
        "fit:G6/penalty": _v(300.0, "G6"),
        **{p_go_key(t): _v(0.0, "COA-02") for t in P_GO_TERMS},
        **{
            role_key("PLY-03", "target_share", "all", s): _v(0.1 + i / 100, "PLY-03")
            for i, s in enumerate(SLOTS)
        },
    }
    body = {
        "fit_version": "tv",
        "window": "S2024",
        "test_season": 2024,
        "seasons": SEASONS,
        "data_as_of": "2026-10-08T00:00:00+00:00",
        "data_digest": "0" * 64,
        "code_commit": "test",
        "attribution": ATTRIBUTION,
        "values": values,
        "missing": {},
        "no_signal": {fit_k_key("OFF-16", "stuff_team", None): NO_SIGNAL},
    }
    (r / "tv").mkdir()
    (r / "tv" / "S2024.yaml").write_text(yaml.safe_dump(body), encoding="utf-8")
    (r / "active.yaml").write_text("fit_version: tv\n", encoding="utf-8")
    return r


def _fresh(ctx):  # type: ignore[no-untyped-def]
    """The session ctx caches shrunk frames; a fitted root needs a clean cache."""
    from ge.metrics.context import build_context

    return build_context(ctx.snap)


def test_team_parent_uses_fitted_k(ctx, root: Path) -> None:  # type: ignore[no-untyped-def]
    with use_fitted_root(root):
        c = _fresh(ctx)
        team = shrunk(c, "OFF-12", "ypc_team")
        assert set(team["k"].to_list()) == {321.0}
        cells = shrunk(c, "OFF-12", "ypc")
        assert cells["shrunk"].null_count() == 0
        # Spec k for the cells (no fitted per-stat k planted): initial value kept.
        assert set(cells["k"].to_list()) == {float(load_params().offense.off_12_k_epa_ypc.value)}


def test_no_detectable_signal_leaves_the_prior(ctx, root: Path) -> None:  # type: ignore[no-untyped-def]
    with use_fitted_root(root):
        s = shrunk(_fresh(ctx), "OFF-16", "stuff_team")
    assert (s["shrunk"] == s["prior"]).all()
    assert all(NO_SIGNAL in (n or "") for n in s["note"].to_list())


def test_role_prior_from_slot(ctx, root: Path) -> None:  # type: ignore[no-untyped-def]
    with use_fitted_root(root):
        c = _fresh(ctx)
        s = shrunk(c, "PLY-03", "target_share")
        slots = c.slots
    assert set(s["k"].drop_nulls().to_list()) == {77.0}
    planted = {slot: 0.1 + i / 100 for i, slot in enumerate(SLOTS)}
    with_slot = [
        (r["entity_id"], r["team"], r["prior"])
        for r in s.iter_rows(named=True)
        if (r["entity_id"], r["team"]) in slots
    ]
    assert with_slot
    for eid, team, prior in with_slot:
        # last season's value (same team and caller) or the slot's planted average
        assert prior is not None
        if prior in planted.values():
            assert prior == planted[slots[(eid, team)]]
    no_slot = s.filter(
        ~pl.struct("entity_id", "team").map_elements(
            lambda r: (r["entity_id"], r["team"]) in slots, return_dtype=pl.Boolean
        )
    )
    # No slot: no prior at all, unless last season's value applies (same team and caller);
    # never a slot average.
    for prior, sh in no_slot.select("prior", "shrunk").iter_rows():
        assert (prior is None and sh is None) or prior not in planted.values()
    assert no_slot["shrunk"].null_count() > 0


def test_coa_02_and_g6_compute_with_a_fit(ctx, root: Path) -> None:  # type: ignore[no-untyped-def]
    from ge.metrics.offense import off_01_adjusted

    with use_fitted_root(root):
        c = _fresh(ctx)
        s = shrunk(c, "COA-02", "go_over_expected")
        adj = off_01_adjusted(c)
    assert s.height and s["shrunk"].null_count() == 0
    assert adj.height == c.teams.height and adj["value"].null_count() == 0


def test_without_a_fit_they_still_raise(ctx) -> None:  # type: ignore[no-untyped-def]
    from ge.metrics.offense import off_01_adjusted

    c = _fresh(ctx)
    for sid, stat in (
        ("OFF-12", "ypc"),
        ("PLY-03", "target_share"),
        ("COA-02", "go_over_expected"),
    ):
        with pytest.raises(NotImplementedError, match=sid):
            shrunk(c, sid, stat)
    with pytest.raises(NotImplementedError, match="G6"):
        off_01_adjusted(c)
