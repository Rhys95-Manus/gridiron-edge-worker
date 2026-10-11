"""BT-02, Phase 3e v3 (spec synced 2026-10-10): k for a stat whose prior is the player's own
parent value (PLY-06 and PLY-07 toward his overall opportunity share, PLY-33 toward his PLY-03
target share, PLY-32 toward his red-zone target share, which itself shrinks toward his PLY-03
target share).

Per split, each player's games go to half A or B at random (one draw per player-game, shared by
his cell and parent units); within each half a cell's units are taken in random order until m
are in; the half's value is his cell share from those units minus his parent share over every
parent unit in the half's games. Cell-halves short of m, or with no parent in a half, are left
out. N counts distinct players (rule 3). A cell gets its own k when it meets BT-02's minimum
alone; otherwise the pooled k applies.

Inputs: season, entity_id, team, cell, g, x, d (cell units) and the same without a needed cell
(parent units). Seeded from the caller's key (rule 6); sums are sequential (np.bincount over
sorted rows)."""

from __future__ import annotations

import numpy as np
import polars as pl

from ge.fit.splithalf import KFit, SplitHalfConfig, k_from_halves, seeded

_HV = {
    "split": pl.Int64,
    "m": pl.Int64,
    "entity": pl.Utf8,
    "cell": pl.Utf8,
    "v_a": pl.Float64,
    "v_b": pl.Float64,
    "n_a": pl.Float64,
    "n_b": pl.Float64,
    "group": pl.Utf8,
}


def _ent(df: pl.DataFrame) -> pl.Expr:
    return pl.concat_str(
        [pl.col("season").cast(pl.Utf8), pl.col("entity_id"), pl.col("team")], separator="|"
    )


def parent_half_values(
    cells: pl.DataFrame, parent: pl.DataFrame, cfg: SplitHalfConfig, seed_key: str
) -> pl.DataFrame:
    """Half values of (cell value - parent value) per player-cell, per split and m."""
    u = cells.filter(pl.col("x").is_not_null())
    p = parent.filter(pl.col("x").is_not_null())
    if u.is_empty() or p.is_empty():
        return pl.DataFrame(schema=_HV)
    u = u.with_columns(_ent(u).alias("ent")).sort("ent", "cell", "g", "x", "d")
    p = p.with_columns(_ent(p).alias("ent")).sort("ent", "g", "x", "d")
    pairs = (
        pl.concat([u.select("ent", "g"), p.select("ent", "g")])
        .unique()
        .sort("ent", "g")
        .with_row_index("pair")
    )
    u = u.join(pairs, on=["ent", "g"], how="left")
    p = p.join(pairs, on=["ent", "g"], how="left")
    ents_s = pairs["ent"].unique().sort()
    emap = pl.DataFrame({"ent": ents_s, "e": np.arange(len(ents_s))})
    ents = ents_s.to_list()
    u = u.join(emap, on="ent", how="left")
    p = p.join(emap, on="ent", how="left")
    cell_names = sorted(u["cell"].unique().to_list())
    cmap = {c: i for i, c in enumerate(cell_names)}
    uc = np.array([cmap[c] for c in u["cell"].to_list()])
    ue, upair = u["e"].to_numpy(), u["pair"].to_numpy()
    ux, ud = u["x"].to_numpy(), u["d"].to_numpy()
    pe, ppair = p["e"].to_numpy(), p["pair"].to_numpy()
    px, pd_ = p["x"].to_numpy(), p["d"].to_numpy()
    ne, nc = len(ents), len(cell_names)
    frames = []
    for b in range(cfg.splits):
        g = seeded(f"{seed_key}/split{b}")
        side = g.integers(0, 2, pairs.height)
        rk = g.random(u.height)
        pslot = pe * 2 + side[ppair]
        psx = np.bincount(pslot, weights=px, minlength=2 * ne)
        psd = np.bincount(pslot, weights=pd_, minlength=2 * ne)
        grp = (ue * nc + uc) * 2 + side[upair]
        order = np.lexsort((rk, grp))
        grp_o, x_o, d_o = grp[order], ux[order], ud[order]
        start = np.r_[True, grp_o[1:] != grp_o[:-1]]
        csum = np.cumsum(np.ones_like(x_o))
        base = np.maximum.accumulate(np.where(start, csum - 1, 0.0))
        before = csum - 1 - base
        size = ne * nc * 2
        idx = np.arange(ne * nc)
        e_of, c_of = idx // nc, idx % nc
        a, bb = idx * 2, idx * 2 + 1
        pa, pb = e_of * 2, e_of * 2 + 1
        for m in cfg.m_grid:
            keep = before < m
            gk = grp_o[keep]
            sx = np.bincount(gk, weights=x_o[keep], minlength=size)
            sd = np.bincount(gk, weights=d_o[keep], minlength=size)
            sn = np.bincount(gk, minlength=size)
            ok = (
                (sn[a] >= m) & (sn[bb] >= m) & (sd[a] != 0) & (sd[bb] != 0)
                & (psd[pa] != 0) & (psd[pb] != 0)
            )  # fmt: skip
            if not ok.any():
                continue
            frames.append(
                pl.DataFrame(
                    {
                        "split": np.full(int(ok.sum()), b, dtype=np.int64),
                        "m": np.full(int(ok.sum()), m, dtype=np.int64),
                        "entity": [
                            f"{ents[e]}|{cell_names[c]}"
                            for e, c in zip(e_of[ok], c_of[ok], strict=True)
                        ],
                        "cell": [cell_names[c] for c in c_of[ok]],
                        "v_a": sx[a][ok] / sd[a][ok] - psx[pa][ok] / psd[pa][ok],
                        "v_b": sx[bb][ok] / sd[bb][ok] - psx[pb][ok] / psd[pb][ok],
                        "n_a": sn[a][ok].astype(np.float64),
                        "n_b": sn[bb][ok].astype(np.float64),
                        "group": [ents[e] for e in e_of[ok]],
                    },
                    schema=_HV,
                )
            )
    return pl.concat(frames) if frames else pl.DataFrame(schema=_HV)


def parent_cell_fits(hv: pl.DataFrame, cfg: SplitHalfConfig) -> tuple[KFit, dict[str, KFit]]:
    """The pooled k over every cell, and each cell's own k where the cell meets BT-02's minimum
    alone (status fitted or no detectable signal; a 'missing' cell uses the pooled k)."""
    pooled = k_from_halves(hv.drop("cell"), cfg)
    per_cell = {}
    for c in sorted(hv["cell"].unique().to_list()):
        fit = k_from_halves(hv.filter(pl.col("cell") == c).drop("cell"), cfg)
        if fit.status != "missing":
            per_cell[c] = fit
    return pooled, per_cell


def season_parent_residual(cells: pl.DataFrame, parent: pl.DataFrame) -> pl.DataFrame:
    """Half-life rows (ruling 2026-10-10): each cell unit minus his parent share over the same
    season (and team) times d, so the loss predicts toward 0. Units with no parent are dropped."""
    par = parent.group_by("season", "entity_id", "team").agg(
        (pl.col("x").sum() / pl.col("d").sum()).alias("_p")
    )
    return (
        cells.join(par, on=["season", "entity_id", "team"], how="inner")
        .with_columns((pl.col("x") - pl.col("_p") * pl.col("d")).alias("x"))
        .drop("_p")
    )
