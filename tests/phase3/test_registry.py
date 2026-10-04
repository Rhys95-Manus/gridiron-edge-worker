"""Metric registry: every metric row in spec sections 2 and 3 has an entry (sections 4-5 and
6b are added in 3b-3d); PAID metrics raise the PAID error; every params key exists."""

from __future__ import annotations

import pytest

from ge.config import load_params
from ge.metrics.registry import REGISTRY
from tests.phase0.helpers import spec_table_rows

PAID = {"DEF-04b", "DEF-05b"}


def _section_ids(prefixes: tuple[str, ...], numbers: range) -> set[str]:
    ids = {rid for rid, _, _ in spec_table_rows(prefixes)}
    return {i for i in ids if int(i.split("-")[1][:2]) in numbers}


def test_sections_2_and_3_are_registered() -> None:
    want = _section_ids(("OFF-",), range(1, 18)) | _section_ids(("DEF-",), range(1, 9))
    assert want <= set(REGISTRY), sorted(want - set(REGISTRY))
    assert {"OFF-01", "OFF-17", "DEF-08", *PAID} <= want


def test_paid_entries_are_marked() -> None:
    for sid in PAID:
        assert REGISTRY[sid].paid


def test_every_params_key_exists() -> None:
    params = load_params()
    for sid, entry in REGISTRY.items():
        for key in entry.param_keys():
            group, name = key.split(".")
            assert hasattr(getattr(params, group), name), f"{sid}: {key}"


def test_functions_start_with_their_spec_id() -> None:
    for sid, entry in REGISTRY.items():
        doc = (entry.raw.__doc__ or "").lstrip()
        assert doc.startswith(sid), f"{sid}: {entry.raw.__name__} docstring"


def test_half_life_class_is_declared() -> None:
    """Plan A2: every shrunk stat names its G3 class (usage or efficiency)."""
    for sid, entry in REGISTRY.items():
        for st in entry.stats.values():
            assert st.half_life in ("usage", "efficiency"), (sid, st.stat)


@pytest.mark.parametrize("sid", sorted(PAID))
def test_paid_doc(sid: str) -> None:
    assert "PAID" in (REGISTRY[sid].raw.__doc__ or "")
