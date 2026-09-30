import json
from pathlib import Path
from typing import Any

import polars as pl
import pytest

_HERE = Path(__file__).parent
FIXTURES = _HERE / "fixtures"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if _HERE in Path(item.fspath).parents:
            item.add_marker(pytest.mark.phase2)


def load_parquet_fixture(name: str) -> pl.DataFrame:
    """A slice of real downloaded data, with <name>.meta.json recording source and pull time."""
    meta = json.loads((FIXTURES / f"{name}.meta.json").read_text(encoding="utf-8"))
    assert meta["source"] and meta["pulled_at"], f"{name}: fixture must record source and pull date"
    return pl.read_parquet(FIXTURES / f"{name}.parquet")


def load_json_fixture(name: str) -> dict[str, Any]:
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    assert data["source"] and data["pulled_at"], f"{name}: fixture must record source and pull date"
    return data
