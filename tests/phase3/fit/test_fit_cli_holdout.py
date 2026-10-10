"""BT-07b (spec synced 2026-10-10): `ge fit --window live` through the command line, twice, with
and without a planted 2025 partition in every dataset of a copy of the Phase 3 fixture store:
byte-identical output, no requested season above 2024, and a live window configured to include
2025 raises HoldoutReadError before any read. The hidden --data-root / --work-root / --out-root
options go through the same Window and Reader checks as the defaults.

The fixture store holds 2023 and 2024 weeks 1-8 (its partial 2021 slice is removed in the copies);
the live window's other seasons are absent and extract as empty."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ge.cli import app
from ge.config import load_params
from ge.store.holdout import HoldoutReadError
from tests.phase3.conftest import STORE

AS_OF = "2026-10-09T00:00:00Z"
HOLDOUT = int(load_params().backtest.bt_01_holdout_season.value)
runner = CliRunner()


def _plant_holdout(store: Path) -> None:
    """A 2025 partition in every dataset that has seasons, copied from its latest season."""
    for ds in sorted(p for p in store.iterdir() if p.is_dir()):
        seasons = sorted(
            int(s.name.split("=")[1])
            for s in ds.glob("season=*")
            if s.name.split("=")[1].isdigit() and int(s.name.split("=")[1]) > 0
        )
        if not seasons:
            continue
        src = next((ds / f"season={seasons[-1]}").glob("pulled_at=*"))
        shutil.copytree(src, ds / f"season={HOLDOUT}" / src.name)


def _run(tmp: Path, store: Path, tag: str, reads: list[tuple[str, int]], monkeypatch) -> bytes:  # type: ignore[no-untyped-def]
    import ge.fit.history as history

    real = history.choose_version

    def recording(root, dataset, season, as_of):  # type: ignore[no-untyped-def]
        reads.append((dataset, season))
        return real(root, dataset, season, as_of)

    monkeypatch.setattr(history, "choose_version", recording)
    result = runner.invoke(
        app,
        [
            "fit",
            "--as-of", AS_OF,
            "--window", "live",
            "--fit-version", "t",
            "--data-root", str(store),
            "--work-root", str(tmp / f"work_{tag}"),
            "--out-root", str(tmp / f"out_{tag}"),
        ],
    )  # fmt: skip
    assert result.exit_code == 0, (result.output, result.exception)
    return (tmp / f"out_{tag}" / "t" / "live.yaml").read_bytes()


@pytest.fixture(scope="module")
def stores(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, Path]:
    tmp = tmp_path_factory.mktemp("cli")
    clean = tmp / "store_clean"
    planted = tmp / "store_2025"
    shutil.copytree(STORE, clean)
    shutil.copytree(STORE, planted)
    # The fixture's 2021 slice is deliberately partial (schedules and pbp only, for the no-FTN
    # test); a season without weekly rosters can't be extracted, and real seasons always have
    # them. Both copies drop it identically, so the live window fits from 2023 and 2024.
    for store in (clean, planted):
        for part in store.glob("*/season=2021"):
            shutil.rmtree(part)
    _plant_holdout(planted)
    assert any(planted.glob(f"*/season={HOLDOUT}"))
    return tmp, clean, planted


def test_live_fit_ignores_a_planted_holdout(stores, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    tmp, clean, planted = stores
    reads_clean: list[tuple[str, int]] = []
    reads_planted: list[tuple[str, int]] = []
    a = _run(tmp, clean, "clean", reads_clean, monkeypatch)
    b = _run(tmp, planted, "planted", reads_planted, monkeypatch)
    assert a == b
    assert (tmp / "out_clean" / "t" / "REPORT.md").read_bytes() == (
        tmp / "out_planted" / "t" / "REPORT.md"
    ).read_bytes()
    assert reads_planted, "no reads recorded"
    assert max(s for _, s in reads_planted) <= HOLDOUT - 1
    assert sorted(set(reads_clean)) == sorted(set(reads_planted))


def test_live_window_including_holdout_refuses_before_any_read(stores, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import ge.fit.history as history
    import ge.store.holdout as holdout

    tmp, _, planted = stores
    real = holdout.load_params()
    bt = real.backtest
    bad_bt = bt.model_copy(
        update={
            "bt_01_last_test_season": bt.bt_01_last_test_season.model_copy(
                update={"value": HOLDOUT}
            )
        }
    )
    monkeypatch.setattr(
        holdout, "load_params", lambda: real.model_copy(update={"backtest": bad_bt})
    )
    reads: list[tuple[str, int]] = []
    monkeypatch.setattr(
        history,
        "choose_version",
        lambda *a: reads.append((a[1], a[2])),  # type: ignore[func-returns-value]
    )
    result = runner.invoke(
        app,
        [
            "fit",
            "--as-of", AS_OF,
            "--window", "live",
            "--fit-version", "t",
            "--data-root", str(planted),
            "--work-root", str(tmp / "work_bad"),
            "--out-root", str(tmp / "out_bad"),
        ],
    )  # fmt: skip
    assert isinstance(result.exception, HoldoutReadError), (result.output, result.exception)
    assert "BT-07b" in str(result.exception)
    assert reads == []
    assert not (tmp / "out_bad").exists()
