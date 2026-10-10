"""Phase 3e v2 acceptance on real data (realdata: needs `ge fit --fit-version v2` run first, so
data/fit_work/v2 and config/params_fitted/v2 exist). Live window, against the 2026-10-09
diagnostics:

- residual share k with the diagnostics' seed keys and their entity-cell N reproduces them to
  one decimal: PLY-03 58.1, PLY-05 17.6, PLY-18 207.6, PLY-23 210.6, PLY-28 45.3, PLY-29 70.6
  (ruling 3 then counts distinct entities for the multi-cell ones; the fit reports those)
- PRJ-06 QB missed-game rate 0.0815 with n 4589"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ge.config import FITTED_ROOT
from ge.fit.job import WORK_ROOT, FitConfig, Fitter, Out, Work
from ge.store.holdout import Window

pytestmark = pytest.mark.realdata

WORK = WORK_ROOT / "v2"
LIVE = FITTED_ROOT / "v2" / "live.yaml"
DIAG = {
    ("PLY-03", "target_share"): 58.1,
    ("PLY-05", "carry_share"): 17.6,
    ("PLY-18", "share"): 207.6,
    ("PLY-23", "share"): 210.6,
    ("PLY-28", "share"): 45.3,
    ("PLY-29", "share"): 70.6,
}


@pytest.fixture(scope="module")
def fitter() -> tuple[Fitter, Out]:
    if not (WORK / "season=2024" / "done.json").exists() or not LIVE.exists():
        pytest.fail("run `ge fit --fit-version v2` first (data/fit_work/v2, params_fitted/v2)")
    from ge.config import load_params

    f = Fitter(Work(Path(WORK)), FitConfig.from_params(load_params().fitting), "v2")
    out = Out()
    body = yaml.safe_load(LIVE.read_text(encoding="utf-8"))
    out.values = body["values"]
    return f, out


@pytest.mark.parametrize(("sid", "stat"), sorted(DIAG))
def test_residual_k_reproduces_diagnostics(fitter, sid: str, stat: str) -> None:  # type: ignore[no-untyped-def]
    f, out = fitter
    fit = f.residual_k_like_diagnostic(sid, stat, Window.live(), out)
    assert fit.k is not None and round(fit.k, 1) == DIAG[(sid, stat)], fit


def test_prj06_qb_rate_reproduces_diagnostic() -> None:
    body = yaml.safe_load(LIVE.read_text(encoding="utf-8"))
    v = body["values"]["fit:PRJ-06/missed/QB"]
    assert round(v["value"], 4) == 0.0815 and v["n"] == 4589, v
