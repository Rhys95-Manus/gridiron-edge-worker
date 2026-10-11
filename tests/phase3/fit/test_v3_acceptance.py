"""Phase 3e v3 acceptance on real data (realdata: needs `ge fit --fit-version v3` run first).
Live window, against the 2026-10-09 diagnostics:

- parent-residual k per cell, run with that diagnostic's v2 seed keys ("v2/<k key>/<season>"):
  PLY-06 inside_20 164.2, inside_10 72.5, inside_5 29.7; PLY-07 third_down 18.7, two_minute
  31.5; PLY-33 play_action 84.7, motion 611.4
- PRJ-06: RB 0.0616 n 8085, WR 0.0641 n 15627, TE 0.0477 n 9081; QB 0.0815 n 4589"""

from __future__ import annotations

import pytest
import yaml

from ge.config import FITTED_ROOT, load_params
from ge.fit.job import WORK_ROOT, FitConfig, Fitter, Work
from ge.store.holdout import Window

pytestmark = pytest.mark.realdata

WORK = WORK_ROOT / "v3"
LIVE = FITTED_ROOT / "v3" / "live.yaml"
DIAG = {
    ("PLY-06", "opportunity_share", "inside_20"): 164.2,
    ("PLY-06", "opportunity_share", "inside_10"): 72.5,
    ("PLY-06", "opportunity_share", "inside_5"): 29.7,
    ("PLY-07", "opportunity_share", "third_down"): 18.7,
    ("PLY-07", "opportunity_share", "two_minute"): 31.5,
    ("PLY-33", "target_share", "play_action"): 84.7,
    ("PLY-33", "target_share", "motion"): 611.4,
}
PRJ06 = {"RB": (0.0616, 8085), "WR": (0.0641, 15627), "TE": (0.0477, 9081), "QB": (0.0815, 4589)}


@pytest.fixture(scope="module")
def fitter() -> Fitter:
    if not (WORK / "season=2024" / "done.json").exists() or not LIVE.exists():
        pytest.fail("run `ge fit --fit-version v3` first (data/fit_work/v3, params_fitted/v3)")
    return Fitter(Work(WORK), FitConfig.from_params(load_params().fitting), "v3")


@pytest.mark.parametrize(("sid", "stat", "cell"), sorted(DIAG))
def test_parent_residual_reproduces_diagnostic(fitter, sid: str, stat: str, cell: str) -> None:  # type: ignore[no-untyped-def]
    _, per_cell = fitter.parent_fits(sid, stat, Window.live(), seed_prefix="v2/")
    fit = per_cell[cell]
    assert fit.k is not None and round(fit.k, 1) == DIAG[(sid, stat, cell)], fit


@pytest.mark.parametrize("pos", sorted(PRJ06))
def test_prj06_pools_reproduce_diagnostic(pos: str) -> None:
    v = yaml.safe_load(LIVE.read_text(encoding="utf-8"))["values"][f"fit:PRJ-06/missed/{pos}"]
    rate, n = PRJ06[pos]
    assert round(v["value"], 4) == rate and v["n"] == n, v
