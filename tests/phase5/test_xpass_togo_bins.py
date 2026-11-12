"""PRJ-02 xpass(state) distance bins (ruling 2026-10-29, P3): an indicator for each distance bin
within each down (ydstogo 1, 2, 3, 4-6, 7-10; 11+ the reference; edges in config/sim.yaml), on
top of the per-down linear and squared distance terms (ruling 2026-10-25). wp and cp are
unchanged. Synthetic placeholder states; the last test compares the S2024 window's fitted xpass
with nflverse xpass on 2024 plays (realdata)."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from ge.fit.distill import design, distill_fit, predict, togo_bin_index
from ge.models.sim import arrays as A
from ge.models.sim.settings import load_sim

FEATS = {
    "qtr": 2.0,
    "yardline_100": 60.0,
    "half_seconds_remaining": 900.0,
    "score_differential": 0.0,
    "wp": 0.5,
    "posteam_timeouts_remaining": 3.0,
    "defteam_timeouts_remaining": 3.0,
}
TOGOS = (1.0, 2.0, 3.0, 5.0, 8.0, 12.0)  # one per bin: 1, 2, 3, 4-6, 7-10, 11+


def _grid() -> pl.DataFrame:
    rows = [{"down": float(d), "ydstogo": t, **FEATS, "xpass": 0.5, "cp": 0.6,
             "air_yards": 8.0, "pass_location": "left", "game_seconds_remaining": 2700.0}
            for d in (1, 2, 3, 4) for t in TOGOS]  # fmt: skip
    return pl.DataFrame(rows)


def test_bin_edges_come_from_config() -> None:
    assert load_sim().distill.xpass_togo_bin_upper.value == [1, 2, 3, 6, 10]


@pytest.mark.parametrize(
    ("togo", "k"),
    [(0.5, 0), (1.0, 0), (2.0, 1), (3.0, 2), (4.0, 3), (6.0, 3), (7.0, 4), (10.0, 4),
     (11.0, 5), (30.0, 5)],
)  # fmt: skip
def test_bin_boundaries(togo: float, k: int) -> None:
    assert togo_bin_index(np.array([togo])).tolist() == [k]


def test_xpass_design_has_an_indicator_per_bin_and_down() -> None:
    X, names, d = design(_grid(), "xpass")
    bins = [n for n in names if n.startswith("ydstogo_bin=")]
    want = [f"ydstogo_bin={k}|down={dn}.0" for dn in (1, 2, 3, 4) for k in range(5)]
    assert sorted(bins) == sorted(want)  # 11+ (bin 5) is the reference
    assert "ydstogo|down=3.0" in names and "ydstogo^2|down=3.0" in names  # quadratic kept
    col = {n: X[:, i] for i, n in enumerate(names)}
    for i, r in enumerate(d.iter_rows(named=True)):
        on = [n for n in bins if col[n][i] == 1.0]
        k = TOGOS.index(r["ydstogo"])
        assert on == ([] if k == 5 else [f"ydstogo_bin={k}|down={r['down']}"])


def test_wp_and_cp_have_no_bins() -> None:
    for model in ("wp", "cp"):
        _, names, _ = design(_grid(), model)
        assert not [n for n in names if "ydstogo_bin" in n]


def test_planted_third_and_one_step_is_reproduced() -> None:
    """A step a quadratic cannot follow: on 3rd down the pass logit is -0.8 at 1 yard and +1.0
    from 2 yards on; the binned design fits it exactly and predict() reproduces it."""
    rng = np.random.default_rng(29)
    n = 20_000
    d = pl.DataFrame({
        "down": rng.integers(1, 5, n).astype(float),
        "ydstogo": rng.integers(1, 21, n).astype(float),
        "yardline_100": rng.integers(5, 95, n).astype(float),
        "qtr": rng.integers(1, 5, n).astype(float),
        "half_seconds_remaining": rng.uniform(0, 1800, n),
        "score_differential": rng.integers(-14, 15, n).astype(float),
        "wp": rng.uniform(0.05, 0.95, n),
        "posteam_timeouts_remaining": rng.integers(0, 4, n).astype(float),
        "defteam_timeouts_remaining": rng.integers(0, 4, n).astype(float),
    })  # fmt: skip
    step = np.where(
        (d["down"] == 3.0).to_numpy(), np.where(d["ydstogo"].to_numpy() <= 1, -0.8, 1.0), 0.0
    )
    target = 1 / (1 + np.exp(-(0.1 + step - 0.003 * d["yardline_100"].to_numpy())))
    d = d.with_columns(pl.Series("xpass", target))
    X, names, used = design(d, "xpass")
    fit = distill_fit(X, used["xpass"].to_numpy(), names)
    assert fit.agreement.mae < 1e-4
    coef = dict(zip(names, fit.coef.tolist(), strict=True))
    np.testing.assert_allclose(predict(coef, used), target, atol=1e-4)


def test_engine_bin_matches_the_fit_bin() -> None:
    from ge.models.sim.engine import xpass_bin

    edges = np.array(load_sim().distill.xpass_togo_bin_upper.value, dtype=np.float64)
    togos = np.arange(1, 31, dtype=np.float64)
    want = togo_bin_index(togos)
    assert [xpass_bin(t, edges) for t in togos] == want.tolist()


def test_compiled_logit_matches_predict_with_bins() -> None:
    from ge.models.sim.arrays import compile_logit
    from ge.models.sim.engine import _eta, _logit_arrays

    coef = {
        "intercept": 0.3,
        "down=3.0": 0.5,
        "ydstogo|down=3.0": 0.15,
        "ydstogo^2|down=3.0": -0.004,
        "ydstogo_bin=0|down=3.0": -1.2,
        "ydstogo_bin=3|down=3.0": 0.8,
        "ydstogo_bin=1|down=4.0": 0.5,
        "yardline_100": -0.01,
    }
    m = _logit_arrays(compile_logit(coef))
    rng = np.random.default_rng(6)
    rows = pl.DataFrame({
        "down": rng.integers(1, 5, 80).astype(float),
        "ydstogo": rng.integers(1, 15, 80).astype(float),
        "yardline_100": rng.integers(1, 99, 80).astype(float),
    })  # fmt: skip
    want = predict(coef, rows)
    bins = togo_bin_index(rows["ydstogo"].to_numpy())
    for i, r in enumerate(rows.iter_rows(named=True)):
        x = np.zeros(A.NF)
        x[A.F_DOWN], x[A.F_YDSTOGO], x[A.F_YL] = r["down"], r["ydstogo"], r["yardline_100"]
        x[A.F_TOGO_BIN] = bins[i]
        got = 1 / (1 + np.exp(-_eta(x, m)))
        assert got == pytest.approx(want[i], rel=1e-12)


@pytest.mark.realdata
def test_s2024_xpass_agrees_with_nflverse_on_2024_by_down_and_distance() -> None:
    """Out of sample: the S2024 window's distilled xpass against nflverse xpass on 2024 plays.
    Every down x distance cell with at least 100 plays within 0.03 (ruling 2026-10-29)."""
    import yaml

    from ge.config import FITTED_ROOT
    from ge.fit.distill import DISTILL_FEATURES
    from ge.ingest.raw import DATA_ROOT, read_latest

    vals = yaml.safe_load((FITTED_ROOT / "v5" / "S2024.yaml").read_text(encoding="utf-8"))["values"]
    pre = "fit:PRJ-02/xpass/"
    coef = {k[len(pre):]: float(v["value"]) for k, v in vals.items()
            if k.startswith(pre) and not k.endswith("/se")}  # fmt: skip
    try:
        pbp = read_latest(DATA_ROOT, "pbp", 2024)
    except FileNotFoundError as exc:
        pytest.fail(f"realdata test needs the local store: {exc}")
    rows = pbp.select(*DISTILL_FEATURES["xpass"], "xpass").drop_nulls()
    bins = togo_bin_index(rows["ydstogo"].to_numpy())
    rows = rows.with_columns(pl.Series("fit", predict(coef, rows)), pl.Series("bin", bins))
    g = (
        rows.group_by("down", "bin")
        .agg(pl.len().alias("n"), (pl.col("fit").mean() - pl.col("xpass").mean()).alias("diff"))
        .filter(pl.col("n") >= 100)
    )
    bad = g.filter(pl.col("diff").abs() > 0.03).sort("down", "bin")
    assert bad.height == 0, bad.rows()
