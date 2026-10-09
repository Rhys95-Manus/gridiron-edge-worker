"""Phase 3e report (BUILD_PLAN 3e): every fitted value beside its initial value with seasons
and n; values that moved more than 50% from the initial guess; every "no detectable signal"
stat by window; everything left missing. Written next to the fits as REPORT.md.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ge.config import ATTRIBUTION, FITTED_ROOT
from ge.store.holdout import Window

MOVE_FLAG = 0.5  # the user's report rule (2026-10-08): flag moves of more than 50%


def _fmt(v: float | None) -> str:
    if v is None:
        return "—"
    a = abs(v)
    if a == 0:
        return "0"
    if a >= 1000:
        return f"{v:,.0f}"
    if a >= 10:
        return f"{v:.1f}"
    if a >= 0.01:
        return f"{v:.4f}"
    return f"{v:.3g}"


def _change(fitted: float, initial: float | None) -> float | None:
    if initial is None or initial == 0:
        return None
    return (fitted - initial) / abs(initial)


def _seasons(s: list[int]) -> str:
    return f"{min(s)}-{max(s)}" if len(s) > 1 else str(s[0])


def write_report(
    results: Mapping[str, Any], windows: list[Window], fit_version: str, root: Path = FITTED_ROOT
) -> Path:
    lines = [
        f"# Phase 3e fit report — {fit_version}",
        "",
        "Every fitted value beside its initial value (— = the spec gives none), the seasons "
        "used and n (entities for k and priors; rows or events otherwise). Change is relative "
        "to the initial value; **bold** = moved more than 50%.",
        "",
    ]
    moved: list[str] = []
    for w in windows:
        out = results[w.name]
        lines += [f"## {w.name} (seasons {_seasons(list(w.seasons))})", ""]
        lines += [
            "| key | spec | initial | fitted | change | n | seasons | method |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for key, v in out.values.items():
            ch = _change(v["value"], v["initial_value"])
            big = ch is not None and abs(ch) > MOVE_FLAG
            chs = "" if ch is None else f"{ch:+.0%}"
            if big:
                chs = f"**{chs}**"
                moved.append(
                    f"| {w.name} | `{key}` | {_fmt(v['initial_value'])} "
                    f"| {_fmt(v['value'])} | {chs} | {v['n']} |"
                )
            note = out.notes.get(key, "")
            method = v["method"] + (f"; {note}" if note else "")
            sid = v["spec_id"] if isinstance(v["spec_id"], str) else ", ".join(v["spec_id"])
            lines.append(
                f"| `{key}` | {sid} | {_fmt(v['initial_value'])} | {_fmt(v['value'])} | {chs} "
                f"| {v['n']} | {_seasons(v['seasons'])} | {method} |"
            )
        lines.append("")
    lines += [
        "## Moved more than 50% from the initial guess",
        "",
        "| window | key | initial | fitted | change | n |",
        "|---|---|---|---|---|---|",
        *moved,
        "",
        "## No detectable signal (BT-02): shrunk value = prior, matchup terms contribute zero",
        "",
    ]
    for w in windows:
        ns = results[w.name].no_signal
        lines.append(f"**{w.name}** ({len(ns)}): " + (", ".join(f"`{k}`" for k in ns) or "none"))
        lines.append("")
    lines += ["## Left missing", ""]
    for w in windows:
        lines.append(f"### {w.name}")
        lines.append("")
        for k, why in results[w.name].missing.items():
            lines.append(f"- `{k}`: {why}")
        lines.append("")
    lines.append(ATTRIBUTION)
    path = root / fit_version / "REPORT.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path
