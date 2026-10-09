"""Phase 3e provenance for fitted params files (approved 2026-10-08): every file under
config/params_fitted/ loads strictly, carries the attribution, uses only seasons before its test
season (never the holdout), and every value names a spec ID, the method, the seasons used and n.
The initial file stays all-initial (a fit never overwrites it)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ge.config import FITTED_ROOT, FittedFile, _check_fitted, _read_yaml, load_params
from tests.phase0.helpers import PARAMS_PATH, iter_leaves, spec_ids

HOLDOUT = int(load_params().backtest.bt_01_holdout_season.value)
FILES = sorted(p for p in FITTED_ROOT.glob("*/*.yaml"))


def test_initial_file_is_all_initial() -> None:
    data = yaml.safe_load(PARAMS_PATH.read_text(encoding="utf-8"))
    assert {e["status"] for _, _, e in iter_leaves(data)} == {"initial"}


def test_active_version_has_every_window() -> None:
    active = FITTED_ROOT / "active.yaml"
    if not active.exists():
        pytest.skip("no fit is active yet")
    version = yaml.safe_load(active.read_text(encoding="utf-8"))["fit_version"]
    names = {p.stem for p in (FITTED_ROOT / version).glob("*.yaml")}
    bt = load_params().backtest
    first, last = int(bt.bt_01_first_test_season.value), int(bt.bt_01_last_test_season.value)
    assert {f"S{s}" for s in range(first, last + 1)} | {"live"} <= names


@pytest.mark.parametrize("path", FILES, ids=[f"{p.parent.name}/{p.stem}" for p in FILES])
def test_fitted_file(path: Path) -> None:
    f = FittedFile.model_validate(_read_yaml(path))
    _check_fitted(f, path, load_params())  # attribution, window, BT-07a / BT-07b seasons
    assert HOLDOUT not in f.seasons
    if f.test_season is not None:
        assert max(f.seasons) < f.test_season
    ids = spec_ids()
    for key, v in f.values.items():
        sids = [v.spec_id] if isinstance(v.spec_id, str) else v.spec_id
        assert all(s in ids for s in sids), key
        assert v.method.strip() and v.seasons and v.n >= 0, key
        assert set(v.seasons) <= set(f.seasons), key
    for key, why in {**f.missing, **f.no_signal}.items():
        assert why.strip(), key
