import json
from pathlib import Path
from typing import Any

import pytest

_HERE = Path(__file__).parent
FIXTURES = _HERE / "fixtures"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if _HERE in Path(item.fspath).parents:
            item.add_marker(pytest.mark.phase1)


def load_fixture(name: str) -> dict[str, Any]:
    """A captured real response: {"source", "pulled_at", ..., "response"}."""
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    assert data["source"] and data["pulled_at"], f"{name}: fixture must record source and pull date"
    return data
