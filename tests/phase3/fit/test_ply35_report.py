"""BT-02 (spec synced 2026-10-16): the Phase 3e report shows PLY-35's k per window with its
split-half r for 2016-2020 and for 2021 onward, its no-signal and missing stats, and each stat's
2026 mean raw gap beside its 2024 mean."""

from __future__ import annotations

from pathlib import Path

from ge.fit.job import Out
from ge.fit.report import write_report
from ge.metrics.engine import fit_k_key
from ge.store.holdout import Window

W = Window("S2022", 2022, (2019, 2020, 2021))


def _out() -> Out:
    o = Out()
    k = fit_k_key("PLY-35", "receiving_yards", None)
    o.put(
        k, "PLY-35", 6.5, "split-half in player-games, m:r = 4:0.380", [2019, 2020, 2021], 900, None
    )
    o.notes[k] = "r 2019-2020 (inside model training data): m:r = 4:0.390; k 6.3"
    o.no_signal[fit_k_key("PLY-35", "tds", None)] = "no detectable signal; seasons 2019-2021"
    o.missing[fit_k_key("PLY-35", "rushing_yards", None)] = "fewer than 30 stints reach 2m games"
    return o


def test_report_has_a_ply35_section(tmp_path: Path) -> None:
    gap = ["| stat | group | 2024 mean gap (n) | 2026 mean gap (n) | 2026 - 2024 |", "|---|"]
    p = write_report({W.name: _out()}, [W], "tv", root=tmp_path, extra=["## PLY-35", *gap])
    text = p.read_text(encoding="utf-8")
    sec = text[text.index("## PLY-35 (expected production)") :]
    assert "| S2022 | receiving_yards | 6.5" in sec
    assert "r 2019-2020 (inside model training data)" in sec
    assert "| S2022 | tds | no signal |" in sec
    assert "| S2022 | rushing_yards | missing |" in sec
    assert "2026 mean gap (n)" in text
    assert text.rstrip().endswith(
        "expected points: ffopportunity (ffverse) via nflverse; data license not stated by the "
        "source"
    )
