"""Phase 3e v3 (BT-02 method and decisions log "Phase 3e v3 rulings", spec synced 2026-10-10):

- PLY-06, PLY-07, PLY-32, PLY-33 (and PLY-32's new red-zone target share): k from each cell's
  value minus the player's own parent value in the same half; a separate k per cell that meets
  the minimum alone, the pooled k otherwise; N = distinct players
- their half-life rows: each cell unit minus his season parent share x d (ruling 2026-10-10)
- PLY-32's prior is his red-zone target share (targets inside the 20 / team targets inside 20)
- PRJ-06 RB / WR / TE pools: at least 25% of team offensive snaps in the previous game
- split seeds keyed by stat key and season only
Planted values and tolerances are test settings."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl

from ge.config import ActiveParams, load_params, use_params
from ge.fit.availability import prj06_pool
from ge.fit.job import FitConfig, Fitter, Work
from ge.fit.parent import parent_cell_fits, parent_half_values, season_parent_residual
from ge.fit.splithalf import SplitHalfConfig
from ge.metrics.engine import fit_k_key
from ge.metrics.registry import REGISTRY
from tests.phase3.fit.synth import rng

LEVEL = float(load_params().fitting.bt_02_no_signal_confidence.value)
CFG = SplitHalfConfig(m_grid=(25, 50, 100), splits=20, min_entities=30, confidence=LEVEL)
REL_TOL = 0.15
PRJ = load_params().projection


def _parent_units(*, tau: float, sigma: float, key: str, ents: int = 800, thin: int = 0):
    """Players with very different overall shares p (the parent); each cell's true value is
    p + delta, delta ~ N(0, tau^2) independent by cell; units N(true, sigma^2). Parent units
    are plentiful so the half's parent value carries little noise. k (cell vs parent) =
    sigma^2 / tau^2. `thin` players get the second cell only, too few for it alone."""
    g = rng(key)
    p = g.uniform(0.0, 10.0, ents)
    cells, parent = [], []
    for e in range(ents):
        for cell in ("c1", "c2"):
            if cell == "c2" and e >= thin:
                continue
            mu = p[e] + g.normal(0.0, tau)
            for j in range(20):
                for v in g.normal(mu, sigma, 8):
                    cells.append(("2001", f"e{e:04d}", "T", cell, float(j), float(v)))
        for j in range(20):
            for v in g.normal(p[e], sigma / 4, 30):
                parent.append(("2001", f"e{e:04d}", "T", "all", float(j), float(v)))
    schema = {
        "season": pl.Utf8, "entity_id": pl.Utf8, "team": pl.Utf8, "cell": pl.Utf8,
        "g": pl.Float64, "x": pl.Float64,
    }  # fmt: skip
    cu = pl.DataFrame(cells, schema=schema, orient="row").with_columns(pl.lit(1.0).alias("d"))
    pu = pl.DataFrame(parent, schema=schema, orient="row").with_columns(pl.lit(1.0).alias("d"))
    return cu, pu, sigma**2 / tau**2


def test_parent_residual_recovers_planted_k() -> None:
    cu, pu, k = _parent_units(tau=0.3, sigma=0.3 * 40**0.5, key="par")
    hv = parent_half_values(cu, pu, CFG, "t/par")
    pooled, per_cell = parent_cell_fits(hv, CFG)
    assert pooled.k is not None and abs(pooled.k - k) / k < REL_TOL, (pooled.k, k)
    for c in ("c1",):
        assert per_cell[c].k is not None and abs(per_cell[c].k - k) / k < REL_TOL
    # N counts distinct players, not player-cells
    assert pooled.entities == cu["entity_id"].n_unique()


def test_thin_cell_falls_back_to_pooled() -> None:
    cu, pu, _ = _parent_units(tau=0.3, sigma=0.3 * 40**0.5, key="thin", ents=400, thin=20)
    hv = parent_half_values(cu, pu, CFG, "t/thin")
    pooled, per_cell = parent_cell_fits(hv, CFG)
    assert "c1" in per_cell and "c2" not in per_cell  # 20 players < 30: not alone
    assert pooled.k is not None


def test_season_parent_residual_arithmetic() -> None:
    cu = pl.DataFrame(
        {
            "season": ["1"] * 2,
            "entity_id": ["e"] * 2,
            "team": ["T"] * 2,
            "x": [1.0, 0.0],
            "d": [1.0, 1.0],
        }
    )
    pu = pl.DataFrame(
        {
            "season": ["1"] * 4,
            "entity_id": ["e"] * 4,
            "team": ["T"] * 4,
            "x": [1.0, 0.0, 0.0, 0.0],
            "d": [1.0] * 4,
        }
    )
    got = season_parent_residual(cu, pu)["x"].to_list()
    assert got == [0.75, -0.25]  # his season parent share is 1/4


def test_engine_uses_a_cells_own_k_else_pooled() -> None:
    sd = REGISTRY["PLY-06"].stats["opportunity_share"]
    base = load_params()
    from ge.config import FittedFile

    f = FittedFile.model_validate(
        {
            "fit_version": "t", "window": "S2024", "test_season": 2024, "seasons": [2023],
            "data_as_of": "x", "data_digest": "x", "code_commit": "x",
            "attribution": "Data: nflverse; charting: FTN Data via nflverse",
            "values": {
                fit_k_key("PLY-06", "opportunity_share", "inside_20"): {
                    "spec_id": "PLY-06", "status": "fitted", "value": 164.0, "method": "t",
                    "seasons": [2023], "n": 1, "initial_value": None,
                },
                fit_k_key("PLY-06", "opportunity_share", None): {
                    "spec_id": "PLY-06", "status": "fitted", "value": 131.0, "method": "t",
                    "seasons": [2023], "n": 1, "initial_value": None,
                },
            },
            "missing": {}, "no_signal": {},
        }
    )  # fmt: skip
    with use_params(ActiveParams(base, f)):
        assert sd.k_value("PLY-06", "inside_20")[0] == 164.0
        assert sd.k_value("PLY-06", "inside_5")[0] == 131.0


def test_prj06_pools() -> None:
    qb_min = float(PRJ.prj_06_qb_min_prev_dropback_share.value)
    snap_min = float(PRJ.prj_06_min_prev_snap_share.value)
    rows = pl.DataFrame(
        {
            "position": ["QB", "QB", "RB", "RB", "WR", "TE", "TE"],
            "missed": [True, False, True, False, True, False, True],
            "prev_dropback_share": [0.6, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0],
            "prev_snap_share": [0.9, 0.9, 0.24, snap_min, 0.8, 0.1, 0.3],
        }
    )
    kept = prj06_pool(rows, qb_min, snap_min)
    assert kept["position"].to_list() == ["QB", "RB", "WR", "TE"]
    assert kept.filter(pl.col("position") == "RB")["prev_snap_share"].to_list() == [snap_min]


def test_split_seeds_are_keyed_by_stat_and_season_only(tmp_path: Path) -> None:
    seeds: list[str] = []
    cfg = FitConfig.from_params(load_params().fitting)
    for version in ("vA", "vB"):
        f = Fitter(Work(tmp_path / version), cfg, version)
        f._half("fit:k/X/y", 2020, lambda seed: seeds.append(seed) or pl.DataFrame())  # type: ignore[func-returns-value]
    assert seeds == ["fit:k/X/y/2020", "fit:k/X/y/2020"]


def test_ply32_red_zone_target_share(ctx) -> None:  # type: ignore[no-untyped-def]
    """His targets inside the 20 / team targets inside the 20, over the games he played."""
    from ge.metrics import plays as pf
    from ge.metrics.registry import raw

    zone = load_params().player.ply_06_zone_20_yardline_100.value
    out = raw(ctx, "PLY-32").filter(
        (pl.col("stat") == "red_zone_target_share") & (pl.col("entity_type") == "player")
    )
    assert out.height > 0
    rz = ctx.plays.filter(pf.usage_target() & (pl.col("yardline_100") <= zone))
    played = ctx.played
    row = out.filter(pl.col("n") > 0).sort("entity_id", "team").row(0, named=True)
    games = played.filter(
        (pl.col("gsis_id") == row["entity_id"]) & (pl.col("team") == row["team"])
    )["game_id"].to_list()
    team_rz = rz.filter((pl.col("posteam") == row["team"]) & pl.col("game_id").is_in(games))
    mine = team_rz.filter(pl.col("receiver_player_id") == row["entity_id"])
    assert row["n"] == team_rz.height
    assert np.isclose(row["value"], mine.height / team_rz.height)
