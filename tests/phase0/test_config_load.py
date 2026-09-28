"""BUILD_PLAN Phase 0: config loads, and any missing, extra or malformed key makes loading fail."""

import copy
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ge.config import Fees, Params, load_fees, load_params
from tests.phase0.helpers import (
    FEES_PATH,
    PARAMS_PATH,
    get_path,
    iter_dict_nodes,
    iter_dict_paths,
    iter_leaves,
)

MODELS: dict[str, tuple[Any, Any]] = {
    "params": (PARAMS_PATH, Params),
    "fees": (FEES_PATH, Fees),
}


def _raw(name: str) -> dict[str, Any]:
    path, _ = MODELS[name]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _fails(name: str, data: dict[str, Any]) -> bool:
    _, model = MODELS[name]
    try:
        model.model_validate(data)
    except ValidationError:
        return True
    return False


def test_params_load() -> None:
    params = load_params()
    assert isinstance(params, Params)


def test_fees_load() -> None:
    fees = load_fees()
    assert isinstance(fees, Fees)


@pytest.mark.parametrize("name", ["params", "fees"])
def test_unmodified_file_validates(name: str) -> None:
    assert not _fails(name, _raw(name))


@pytest.mark.parametrize("name", ["params", "fees"])
def test_deleting_any_key_fails(name: str) -> None:
    raw = _raw(name)
    paths = list(iter_dict_paths(raw))
    assert paths, f"{name}: no keys found"
    loaded_anyway = []
    for path in paths:
        data = copy.deepcopy(raw)
        del get_path(data, path[:-1])[path[-1]]
        if not _fails(name, data):
            loaded_anyway.append(".".join(path))
    assert not loaded_anyway, f"{name}: still loads with these keys deleted: {loaded_anyway}"


@pytest.mark.parametrize("name", ["params", "fees"])
def test_extra_key_at_any_level_fails(name: str) -> None:
    raw = _raw(name)
    loaded_anyway = []
    for path in iter_dict_nodes(raw):
        data = copy.deepcopy(raw)
        get_path(data, path)["unexpected_key"] = 1
        if not _fails(name, data):
            loaded_anyway.append(".".join(path) or "<root>")
    assert not loaded_anyway, f"{name}: accepts an extra key at: {loaded_anyway}"


def test_bad_status_fails() -> None:
    raw = _raw("params")
    group, name, _ = next(iter_leaves(raw))
    raw[group][name]["status"] = "guess"
    assert _fails("params", raw)


def test_every_param_status_is_initial_or_fitted() -> None:
    for group, name, entry in iter_leaves(_raw("params")):
        assert entry["status"] in {"initial", "fitted"}, f"{group}.{name}"


def test_centicent_fields_reject_floats() -> None:
    raw = _raw("params")
    cc_leaves = [(g, n) for g, n, _ in iter_leaves(raw) if n.endswith("_cc")]
    assert cc_leaves, "no _cc (centicent) entries found in params.yaml"
    loaded_anyway = []
    for group, name in cc_leaves:
        data = copy.deepcopy(raw)
        data[group][name]["value"] = float(data[group][name]["value"]) + 0.5
        if not _fails("params", data):
            loaded_anyway.append(f"{group}.{name}")
    assert not loaded_anyway, f"float accepted in centicent fields: {loaded_anyway}"


def test_centicent_values_are_ints() -> None:
    for group, name, entry in iter_leaves(_raw("params")):
        if name.endswith("_cc"):
            assert type(entry["value"]) is int, f"{group}.{name}"


def test_numeric_value_rejects_string() -> None:
    raw = _raw("params")
    group, name, _ = next(iter_leaves(raw))
    raw[group][name]["value"] = "250"
    assert _fails("params", raw)
