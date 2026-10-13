"""BUILD_PLAN Phase 4 live check, on the fixture store: `ge ratings --season S --through-week
W` prints all 32 teams ranked by implied neutral-site margin, each with its four ratings and
their standard errors, the fit sources and the attribution."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ge.cli import app
from ge.config import ATTRIBUTION
from tests.phase3.conftest import STORE

ROW = re.compile(
    r"^\s*(\d+)\s+(\S+)\s+([+-]\d+\.\d+)\s+(\d+\.\d+)\s+(\d\.\d+)"
    + r"\s+[+-]\d\.\d+ \(\d\.\d+\)" * 4
    + r"\s*$"
)


@pytest.mark.usefixtures("fit_env")
def test_ratings_prints_all_teams_ranked_with_errors(ratings_root: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "ratings",
            "--season",
            "2024",
            "--through-week",
            "7",
            "--data-root",
            str(STORE),
            "--ratings-root",
            str(ratings_root),
        ],
    )
    assert result.exit_code == 0, result.output
    rows = [m.groups() for line in result.output.splitlines() if (m := ROW.match(line))]
    assert [int(r[0]) for r in rows] == list(range(1, 33))
    assert len({r[1] for r in rows}) == 32
    margins = [float(r[2]) for r in rows]
    assert margins == sorted(margins, reverse=True)
    assert "S2024" in result.output and "approximate" in result.output
    assert result.output.rstrip().endswith(ATTRIBUTION)
