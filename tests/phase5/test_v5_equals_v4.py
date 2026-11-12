"""Phase 5 checklist: every value fit v4 holds is unchanged in fit v5 (v5 only adds the Phase 5
fits), key by key, in every window: same value, n, seasons, method and initial value, and the
same missing and no-signal entries."""

from __future__ import annotations

import pytest
import yaml

from ge.config import FITTED_ROOT

WINDOWS = ("S2021", "S2022", "S2023", "S2024", "live")


def _load(version: str, window: str) -> dict[str, object]:
    path = FITTED_ROOT / version / f"{window}.yaml"
    assert path.exists(), f"{path} is missing"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.mark.parametrize("window", WINDOWS)
def test_every_v4_value_is_identical_in_v5(window: str) -> None:
    v4, v5 = _load("v4", window), _load("v5", window)
    assert v5["seasons"] == v4["seasons"]
    v4_values = v4["values"]
    v5_values = v5["values"]
    assert isinstance(v4_values, dict) and isinstance(v5_values, dict)
    changed = [k for k, v in v4_values.items() if v5_values.get(k) != v]
    assert not changed, f"{window}: v4 values changed in v5: {changed[:20]}"
    for section in ("missing", "no_signal"):
        old, new = v4.get(section) or {}, v5.get(section) or {}
        assert isinstance(old, dict) and isinstance(new, dict)
        lost = [k for k, v in old.items() if new.get(k) != v]
        assert not lost, f"{window}: v4 {section} entries changed in v5: {lost[:20]}"
