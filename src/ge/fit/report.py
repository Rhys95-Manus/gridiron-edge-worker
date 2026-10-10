"""Phase 3e report (BUILD_PLAN 3e): every fitted value beside its initial value with seasons
and n; values that moved more than 50% from the initial guess; every "no detectable signal"
stat by window; everything left missing. Written next to the fits as REPORT.md.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

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


def _load_version(root: Path, version: str, windows: list[Window]) -> dict[str, dict[str, Any]]:
    out = {}
    for w in windows:
        p = root / version / f"{w.name}.yaml"
        if p.exists():
            out[w.name] = yaml.safe_load(p.read_text(encoding="utf-8"))
    return out


def _status(body: Mapping[str, Any], key: str) -> tuple[str, float | None]:
    if key in body.get("values", {}):
        return "fitted", float(body["values"][key]["value"])
    if key in body.get("no_signal", {}):
        return "no signal", None
    if key in body.get("missing", {}):
        return "missing", None
    return "absent", None


def _comparison(
    results: Mapping[str, Any],
    windows: list[Window],
    old: Mapping[str, Mapping[str, Any]],
    compare_to: str,
    fit_version: str,
) -> list[str]:
    """Every key whose value or status differs between the two versions, per window."""
    lines = [
        f"## {compare_to} vs {fit_version}: every changed value or status",
        "",
        f"| window | key | {compare_to} | {fit_version} | change |",
        "|---|---|---|---|---|",
    ]
    for w in windows:
        prev = old.get(w.name)
        if prev is None:
            continue
        cur = results[w.name]
        now = {"values": cur.values, "no_signal": cur.no_signal, "missing": cur.missing}
        keys = sorted(
            set(prev.get("values", {})) | set(prev.get("no_signal", {}))
            | set(prev.get("missing", {})) | set(cur.values) | set(cur.no_signal)
            | set(cur.missing)
        )  # fmt: skip
        for k in keys:
            (s0, v0), (s1, v1) = _status(prev, k), _status(now, k)
            same = s0 == s1 and (
                v0 is None or v1 is None or abs(v0 - v1) <= 1e-12 * max(1, abs(v0))
            )
            if same:
                continue
            a = _fmt(v0) if s0 == "fitted" else s0
            b = _fmt(v1) if s1 == "fitted" else s1
            ch = _change(v1, v0) if s0 == s1 == "fitted" and v1 is not None else None
            lines.append(f"| {w.name} | `{k}` | {a} | {b} | {'' if ch is None else f'{ch:+.0%}'} |")
    lines.append("")
    return lines


def write_report(
    results: Mapping[str, Any],
    windows: list[Window],
    fit_version: str,
    root: Path = FITTED_ROOT,
    compare_to: str | None = None,
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
    old = _load_version(root, compare_to, windows) if compare_to else {}
    for w in windows:
        ns = results[w.name].no_signal
        prev = set(old.get(w.name, {}).get("no_signal", {}))
        items = [f"`{k}`" + (" **(new)**" if compare_to and k not in prev else "") for k in ns]
        lines.append(f"**{w.name}** ({len(ns)}): " + (", ".join(items) or "none"))
        if compare_to:
            gone = sorted(prev - set(ns))
            lines.append(
                f"  departed since {compare_to} ({len(gone)}): "
                + (", ".join(f"`{k}`" for k in gone) or "none")
            )
        lines.append("")
    if compare_to:
        lines += _comparison(results, windows, old, compare_to, fit_version)
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
