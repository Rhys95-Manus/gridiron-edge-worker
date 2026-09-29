"""BUILD_PLAN Phase 0: `ge --help` lists all six jobs, and each job is an honest placeholder."""

import pytest
from typer.testing import CliRunner

from ge.cli import app

JOBS = ["ingest", "metrics", "simulate", "price", "sync", "backtest"]
# Phase 1 built `ingest` as a command group (approved 2026-09-29); the rest are placeholders.
PLACEHOLDER_JOBS = [j for j in JOBS if j != "ingest"]

runner = CliRunner()


def test_help_lists_all_six_jobs() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    for job in JOBS:
        assert job in result.output, f"{job} missing from ge --help"


@pytest.mark.parametrize("job", PLACEHOLDER_JOBS)
def test_each_job_raises_not_implemented(job: str) -> None:
    result = runner.invoke(app, [job])
    assert isinstance(result.exception, NotImplementedError), (
        f"{job}: expected NotImplementedError, got {result.exception!r}\n{result.output}"
    )


@pytest.mark.parametrize("job", PLACEHOLDER_JOBS)
def test_each_job_accepts_season_week_as_of(job: str) -> None:
    result = runner.invoke(
        app, [job, "--season", "2024", "--week", "1", "--as-of", "2024-09-05T00:00:00+00:00"]
    )
    assert isinstance(result.exception, NotImplementedError), result.output
