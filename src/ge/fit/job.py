"""`ge fit`: Phase 3e (BT-02 core) walk-forward fits.

For each window (S2021..S2024 on 2016..S-1, live on 2016-2024) this estimates, from that
window's seasons only, and writes config/params_fitted/<fit_version>/<window>.yaml:

- k for every shrunk stat (G1; BT-02 method incl. "No signal"): single-mean stats from their
  metric units; gaps, DEF-04's ratios, DEF-08's on/off and PLY-04 WOPR computed whole within
  each half (ruling 2026-10-08); PLY-15 keeps its initial k (a redistribution rule)
- G3 half-lives (one usage h, one efficiency h), the G6 ridge penalty, section 4 slot priors,
  COA-02's p_go coefficients, MTC-03's OL-absence factor, PLY-14's practice base rates and
  return factor, PRJ-06's missed-game rates

Every season's inputs are extracted once (ge.fit.season) through a Reader limited to 2016-2024;
each window reads only its own seasons, and the window file's seasons are checked against its
test season when written and when loaded (BT-07a / BT-07b). The holdout is never read.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import shutil
import subprocess
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import yaml

from ge.config import ATTRIBUTION, FITTED_ROOT, REPO_ROOT, Fitting, load_params
from ge.fit.availability import missed_game_rates, practice_base_rates, return_factor
from ge.fit.halflife import HLoss, choose_half_life, half_life_losses, merge
from ge.fit.history import Reader
from ge.fit.logistic import fit_logistic
from ge.fit.ol_factor import ol_absence_factor
from ge.fit.ridge_cv import choose_penalty, g6_cv_losses
from ge.fit.season import extract_season, unit_file
from ge.fit.splithalf import (
    NO_SIGNAL,
    KFit,
    SplitHalfConfig,
    half_values,
    k_from_halves,
    variance_k,
)
from ge.fit.whole import (
    ValueFn,
    diff_of_ratios_value,
    gap_value,
    ratio_value,
    whole_half_values,
    wopr_value,
)
from ge.ingest.raw import DATA_ROOT
from ge.metrics.coaching import P_GO_FEATURES, P_GO_TERMS, p_go_key
from ge.metrics.conventions import G6_PENALTY_KEY as G6_KEY
from ge.metrics.engine import FIT_ONLY, Role, StatDef, fit_k_key
from ge.metrics.registry import REGISTRY
from ge.metrics.roles import role_key
from ge.store.holdout import Window

WORK_ROOT = DATA_ROOT.parent / "fit_work"

# Stats sharing another metric's units (the metric calls the other one).
ALIASES = {
    ("PLY-02", "snap_share"): ("PLY-01", "snap_share"),
    ("PLY-27", "target_share"): ("PLY-03", "target_share"),
    ("PLY-27", "yacoe"): ("PLY-09", "yacoe"),
}
GAPS = {
    ("DEF-10", "epa_gap"),
    ("DEF-13", "epa_gap"),
    ("PLY-17", "epa_gap"),
    ("PLY-17", "sack_gap"),
    ("PLY-19", "epa_gap"),
}
DEF04 = ("targets", "receptions", "yards", "tds", "epa_diff")
# BT-02 (ruling 2026-10-08): a redistribution rule, not a stabilizing skill.
KEEP_INITIAL = {("PLY-15", "target_share"), ("PLY-15", "carry_share")}
OVERLAY = {
    "usage_h": "conventions.g3_usage_half_life_games",
    "efficiency_h": "conventions.g3_efficiency_half_life_games",
    "return": "player.ply_14_return_factor",
    "ol": "matchup.mtc_03_ol_absence_factor",
}


@dataclass(frozen=True)
class FitConfig:
    split: SplitHalfConfig
    penalties: tuple[float, ...]
    half_lives: tuple[float, ...]
    min_entities: int
    min_events: int

    @staticmethod
    def from_params(f: Fitting) -> FitConfig:
        return FitConfig(
            SplitHalfConfig.from_params(f),
            f.penalty_grid(),
            f.half_life_grid(),
            int(f.bt_02_min_entities.value),
            int(f.bt_02_min_events.value),
        )


@dataclass
class Out:
    """One window's fitted file contents and report rows."""

    values: dict[str, dict[str, Any]] = field(default_factory=dict)
    missing: dict[str, str] = field(default_factory=dict)
    no_signal: dict[str, str] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)  # key -> report note (cross-checks)

    def put(
        self,
        key: str,
        spec_id: str | list[str],
        value: float,
        method: str,
        seasons: Iterable[int],
        n: int,
        initial: float | None,
    ) -> None:
        self.values[key] = {
            "spec_id": spec_id,
            "status": "fitted",
            "value": float(value),
            "method": method,
            "seasons": sorted(set(seasons)),
            "n": int(n),
            "initial_value": initial,
        }


# ---------------------------------------------------------------- data


class Work:
    """The extracted seasons of one fit version."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self._cache: dict[tuple[str, int], pl.DataFrame] = {}

    def season_dir(self, s: int) -> Path:
        return self.folder / f"season={s}"

    def table(self, name: str, s: int) -> pl.DataFrame:
        key = (name, s)
        if key not in self._cache:
            p = self.season_dir(s) / f"{name}.parquet"
            self._cache[key] = pl.read_parquet(p) if p.exists() else pl.DataFrame()
        return self._cache[key]

    def units(self, spec_id: str, stat: str, kind: str, s: int) -> pl.DataFrame:
        p = self.season_dir(s) / "units" / unit_file(spec_id, stat, kind)
        return pl.read_parquet(p) if p.exists() else pl.DataFrame()

    def digest(self, s: int) -> str:
        return str(json.loads((self.season_dir(s) / "done.json").read_text())["digest"])


def prepare(
    work: Work, seasons: Iterable[int], root: Path, as_of: dt.datetime, fresh: bool
) -> None:
    """Extract every needed season once (Reader limited to 2016-2024: the live window)."""
    for s in sorted(set(seasons)):
        d = work.season_dir(s)
        done = d / "done.json"
        if done.exists() and not fresh:
            meta = json.loads(done.read_text())
            if meta.get("data_as_of") == as_of.isoformat():
                continue
        if d.exists():
            shutil.rmtree(d)
        reader = Reader(root, Window.live(), as_of)
        extract_season(reader, s, d)
        meta = json.loads(done.read_text())
        meta.update({"data_as_of": as_of.isoformat(), "digest": reader.digest()})
        done.write_text(json.dumps(meta, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------- k


def _ent(df: pl.DataFrame, cols: list[str]) -> pl.Expr:
    return pl.concat_str(
        [pl.col("season").cast(pl.Utf8), *(pl.col(c) for c in cols)], separator="|"
    )


def _initial(key: str | None) -> float | None:
    if key is None or key == FIT_ONLY:
        return None
    group, name = key.split(".")
    return float(getattr(getattr(load_params(), group), name).value)


def _k_targets() -> list[tuple[str, StatDef, str | None, str | None]]:
    """(spec_id, statdef, cell group or None, params key or FIT_ONLY) for every shrunk stat."""
    out: list[tuple[str, StatDef, str | None, str | None]] = []
    for sid, e in sorted(REGISTRY.items()):
        for st, sd in sorted(e.stats.items()):
            if sd.k is None or (sid, st) in KEEP_INITIAL:
                continue
            if isinstance(sd.k, str):
                out.append((sid, sd, None, sd.k))
            else:
                for cell, key in sorted(sd.k.items()):
                    out.append((sid, sd, cell, key))
    return out


class Fitter:
    def __init__(self, work: Work, cfg: FitConfig, fit_version: str) -> None:
        self.work = work
        self.cfg = cfg
        self.fit_version = fit_version
        self.ftn_first = int(load_params().backtest.bt_01_ftn_first_season.value)
        self._hv: dict[tuple[str, int], pl.DataFrame] = {}

    def _cat(self, name: str, w: Window) -> pl.DataFrame:
        got = [f for s in w.seasons if (f := self.work.table(name, s)).height]
        return pl.concat(got, how="diagonal_relaxed") if got else pl.DataFrame()

    # Each source gives one season's half values (window-independent, cached).
    def _half(self, key: str, s: int, make: Callable[[str], pl.DataFrame]) -> pl.DataFrame:
        k = (key, s)
        if k not in self._hv:
            self._hv[k] = make(f"{self.fit_version}/{key}/{s}")
        return self._hv[k]

    def unit_rows(self, sid: str, stat: str, cell: str | None, s: int) -> pl.DataFrame:
        src = ALIASES.get((sid, stat), (sid, stat))
        u = self.work.units(src[0], src[1], "units", s)
        if u.is_empty():
            return u
        if cell is not None:
            u = u.filter(pl.col("cell") == cell)
        return u.filter(pl.col("x").is_not_null())

    def half_values(
        self, sid: str, sd: StatDef, cell: str | None, s: int, key: str
    ) -> pl.DataFrame:
        stat = sd.stat
        sp = self.cfg.split
        if (sid, stat) in GAPS:
            g = self.work.units(sid, stat, "gap", s)
            if g.is_empty():
                return g
            rows = g.select(
                _ent(g, ["entity_id", "team"]).alias("entity"),
                pl.concat_str(["team", pl.col("g").cast(pl.Utf8)], separator="|").alias("game"),
                pl.col("arm").cast(pl.Int64),
                pl.col("x").cast(pl.Float64),
                pl.lit(1.0).alias("c"),
            ).filter(pl.col("x").is_not_null())
            return self._half(
                key, s, lambda seed: whole_half_values(rows, sp, seed, gap_value, "arm")
            )
        if sid == "DEF-04":
            r = self.work.units("DEF-04", "per_game", "ratio", s)
            if r.is_empty():
                return r
            base = [
                _ent(r, ["entity_id", "cell"]).alias("entity"),
                pl.col("game_id").alias("game"),
                pl.col("a_targets").alias("c"),
            ]
            if stat == "epa_diff":
                rows = r.select(
                    *base,
                    pl.col("a_epa"),
                    pl.col("a_targets").alias("a_tg"),
                    pl.col("e_epa"),
                    pl.col("e_targets").alias("e_tg"),
                )
                fn: ValueFn = diff_of_ratios_value
            else:
                rows = r.select(
                    *base, pl.col(f"a_{stat}").alias("num"), pl.col(f"e_{stat}").alias("den")
                )
                fn = ratio_value
            return self._half(key, s, lambda seed: whole_half_values(rows, sp, seed, fn))
        if (sid, stat) == ("DEF-08", "on_off"):
            r = self.work.table("def08", s)
            if r.is_empty():
                return r
            rows = r.select(
                _ent(r, ["entity_id"]).alias("entity"),
                pl.col("game_id").alias("game"),
                "arm",
                "x",
                pl.lit(1.0).alias("c"),
            )
            return self._half(
                key, s, lambda seed: whole_half_values(rows, sp, seed, gap_value, "arm")
            )
        if (sid, stat) == ("PLY-04", "wopr"):
            r = self.work.table("wopr", s)
            if r.is_empty():
                return r
            p = load_params().player
            fn = wopr_value(
                float(p.ply_04_wopr_target_weight.value), float(p.ply_04_wopr_air_weight.value)
            )
            rows = r.select(
                _ent(r, ["entity_id", "team"]).alias("entity"),
                pl.concat_str(["team", pl.col("g").cast(pl.Utf8)], separator="|").alias("game"),
                "his_target",
                "his_air",
                "team_air",
                pl.lit(1.0).alias("c"),
            )
            return self._half(key, s, lambda seed: whole_half_values(rows, sp, seed, fn))
        u = self.unit_rows(sid, stat, cell, s)
        if u.is_empty():
            return u
        rows = u.select(
            _ent(u, ["entity_id", "team", "cell"]).alias("entity"),
            pl.concat_str(["team", pl.col("g").cast(pl.Utf8)], separator="|").alias("game"),
            "x",
            "d",
            "c",
        )
        return self._half(key, s, lambda seed: half_values(rows, sp, seed))

    def fit_k(self, w: Window, out: Out) -> dict[str, float]:
        """Every k; returns the fitted k per key (for the half-life fit)."""
        got: dict[str, float] = {}
        for sid, sd, cell, pkey in _k_targets():
            if (sid, sd.stat) == ("COA-02", "go_over_expected"):
                continue  # needs the window's p_go: fit_coa02
            key = fit_k_key(sid, sd.stat, cell)
            parts = [(s, self.half_values(sid, sd, cell, s, key)) for s in w.seasons]
            used = [s for s, hv in parts if hv.height]
            hvs = [hv for _, hv in parts if hv.height]
            initial = _initial(pkey)
            if not hvs:
                if max(w.seasons) < self.ftn_first and not self._has_rows(sid, sd, cell, w):
                    why = "no FTN training data"
                elif self._has_rows(sid, sd, cell, w):
                    m0 = min(self.cfg.split.m_grid)
                    why = (
                        f"fewer than {self.cfg.split.min_entities} entities reach 2m = {2 * m0} "
                        "units at any m (BT-02 minimum)"
                    )
                else:
                    why = "no units in the window"
                out.missing[key] = why + ("" if initial is None else "; initial k kept")
                continue
            fit = k_from_halves(pl.concat(hvs, how="diagonal_relaxed"), self.cfg.split)
            self._record_k(out, key, sid, fit, used, initial, sd)
            if fit.status == "fitted" and fit.k is not None:
                got[key] = fit.k
                if (
                    sid not in {g[0] for g in GAPS}
                    and (sid, sd.stat)
                    not in {
                        ("DEF-08", "on_off"),
                        ("PLY-04", "wopr"),
                    }
                    and sid != "DEF-04"
                ):
                    vk = self._variance_k(sid, sd.stat, cell, used)
                    if vk is not None:
                        out.notes[key] = f"variance-components cross-check k = {vk:.1f}"
        return got

    def _has_rows(self, sid: str, sd: StatDef, cell: str | None, w: Window) -> bool:
        """Whether the stat has any input rows in the window (before the m minimum)."""
        stat = sd.stat
        for s in w.seasons:
            if (sid, stat) in GAPS:
                rows = self.work.units(sid, stat, "gap", s)
            elif sid == "DEF-04":
                rows = self.work.units("DEF-04", "per_game", "ratio", s)
            elif (sid, stat) == ("DEF-08", "on_off"):
                rows = self.work.table("def08", s)
            elif (sid, stat) == ("PLY-04", "wopr"):
                rows = self.work.table("wopr", s)
            else:
                rows = self.unit_rows(sid, stat, cell, s)
            if rows.height:
                return True
        return False

    def _variance_k(
        self, sid: str, stat: str, cell: str | None, seasons: list[int]
    ) -> float | None:
        frames = []
        for s in seasons:
            u = self.unit_rows(sid, stat, cell, s)
            if u.height:
                frames.append(
                    u.select(
                        _ent(u, ["entity_id", "team", "cell"]).alias("entity"),
                        pl.concat_str(["team", pl.col("g").cast(pl.Utf8)], separator="|").alias(
                            "game"
                        ),
                        "x",
                        "d",
                        "c",
                    )
                )
        return variance_k(pl.concat(frames)) if frames else None

    def _record_k(
        self,
        out: Out,
        key: str,
        sid: str,
        fit: KFit,
        used: list[int],
        initial: float | None,
        sd: StatDef,
    ) -> None:
        if fit.status == "fitted" and fit.k is not None:
            used_m = ", ".join(f"{p.m}:{p.r:.3f}" for p in fit.per_m if p.signal)
            out.put(
                key,
                sid,
                fit.k,
                f"split-half (BT-02), m:r = {used_m}",
                used,
                fit.entities,
                initial,
            )
        elif fit.status == "no_signal":
            out.no_signal[key] = (fit.reason or NO_SIGNAL) + f"; seasons {min(used)}-{max(used)}"
        else:
            out.missing[key] = (fit.reason or "missing") + (
                "" if initial is None else "; initial k kept"
            )

    # ---------------------------------------------------------- G3 half-lives

    def fit_half_lives(self, w: Window, ks: dict[str, float], out: Out) -> dict[str, float]:
        per_class: dict[str, list[dict[float, HLoss]]] = defaultdict(list)
        for sid, sd, cell, _ in _k_targets():
            key = fit_k_key(sid, sd.stat, cell)
            if key not in ks or (sid, sd.stat) in GAPS or sid in ("DEF-04", "DEF-08"):
                continue
            if (sid, sd.stat) in (("PLY-04", "wopr"), *ALIASES):
                continue
            losses = []
            for s in w.seasons:
                u = self.unit_rows(sid, sd.stat, cell, s)
                if u.is_empty():
                    continue
                gu = u.with_columns(
                    _ent(u, ["entity_id", "team", "cell"]).alias("entity"),
                    (-pl.col("g")).rank("dense").over(["entity_id", "team", "cell"]).alias("gi"),
                ).select("entity", "gi", "x", "d", "c")
                losses.append(half_life_losses(gu, ks[key], self.cfg.half_lives))
            if losses:
                m = merge(losses)
                if all(v.base > 0 for v in m.values()):
                    per_class[sd.half_life].append(m)
        got: dict[str, float] = {}
        for cls, name in (("usage", "usage_h"), ("efficiency", "efficiency_h")):
            stats = per_class.get(cls, [])
            key = OVERLAY[name]
            if len(stats) == 0:
                out.missing[key] = "no stat with a fitted k in this class"
                continue
            h = choose_half_life(stats)
            got[cls] = h
            out.put(
                key,
                "G3",
                h,
                f"next-game n-weighted squared error / prior-only, mean over {len(stats)} "
                f"{cls} stats (ruling 2026-10-08)",
                w.seasons,
                len(stats),
                _initial(key),
            )
        return got

    # ---------------------------------------------------------- the rest

    def fit_g6(self, w: Window, h: float | None, out: Out) -> None:
        if h is None:
            out.missing[G6_KEY] = "no fitted efficiency half-life"
            return
        losses = []
        for s in w.seasons:
            p = self.work.table("g6", s)
            if p.height:
                losses.append(g6_cv_losses(p, self.cfg.penalties, h))
        if not losses:
            out.missing[G6_KEY] = "no plays"
            return
        best = choose_penalty(losses)
        n = sum(lo[best].plays for lo in losses)
        out.put(
            G6_KEY,
            "G6",
            best,
            f"forward-chaining CV within each season (BT-02), efficiency h = {h:g}",
            w.seasons,
            n,
            None,
        )

    def fit_p_go(self, w: Window, out: Out) -> dict[str, float] | None:
        rows = self._cat("fourth", w)
        events = int(rows["go"].sum()) if rows.height else 0
        if events < self.cfg.min_events:
            for t in P_GO_TERMS:
                out.missing[p_go_key(t)] = f"{events} go decisions < {self.cfg.min_events}"
            return None
        X = np.column_stack([np.ones(rows.height), *(rows[f].to_numpy() for f in P_GO_FEATURES)])
        fit = fit_logistic(X, rows["go"].to_numpy())
        coef = {}
        for i, t in enumerate(P_GO_TERMS):
            coef[t] = float(fit.coef[i])
            out.put(
                p_go_key(t),
                "COA-02",
                coef[t],
                f"logistic, four fields as linear terms (se {fit.se[i]:.3g})",
                w.seasons,
                fit.n,
                None,
            )
        return coef

    def fit_coa02(self, w: Window, coef: dict[str, float] | None, out: Out) -> None:
        key = fit_k_key("COA-02", "go_over_expected", None)
        initial = _initial("coaching.coa_02_k")
        if coef is None:
            out.missing[key] = "no p_go fit; initial k kept"
            return
        hvs, used = [], []
        for s in w.seasons:
            f = self.work.table("fourth", s)
            if f.is_empty():
                continue
            eta = coef["intercept"] + sum(coef[t] * f[t].to_numpy() for t in P_GO_FEATURES)
            r = f["go"].to_numpy() - 1.0 / (1.0 + np.exp(-eta))
            r = r - math.fsum(r.tolist()) / len(r)  # centered on the season's league mean
            rows = pl.DataFrame(
                {
                    "entity": (str(s) + "|" + f["posteam"]).to_list(),
                    "game": f["game_id"].to_list(),
                    "x": r,
                }
            )
            hvs.append(half_values(rows, self.cfg.split, f"{self.fit_version}/{key}/{w.name}/{s}"))
            used.append(s)
        hv = [h for h in hvs if h.height]
        if not hv:
            out.missing[key] = "no 4th downs; initial k kept"
            return
        fit = k_from_halves(pl.concat(hv), self.cfg.split)
        sd = REGISTRY["COA-02"].stats["go_over_expected"]
        self._record_k(out, key, "COA-02", fit, used, initial, sd)

    def fit_ol(self, w: Window, out: Out) -> None:
        rows = self._cat("ol", w)
        key = OVERLAY["ol"]
        if rows.is_empty():
            out.missing[key] = "no dropbacks"
            return
        fit = ol_absence_factor(rows, self.cfg.min_events)
        if fit.value is None:
            out.missing[key] = fit.reason or "missing"
            return
        out.put(
            key,
            "MTC-03",
            fit.value,
            f"offset logistic on dropbacks, exp(coef) per missing OFF-17 starter (se of log "
            f"{fit.se:.3g}); undamped",
            w.seasons,
            fit.sacks,
            _initial(key),
        )

    def fit_availability(self, w: Window, usage_h: float | None, out: Out) -> None:
        def cat(name: str) -> pl.DataFrame:
            got = [f for s in w.seasons if (f := self.work.table(name, s)).height]
            return pl.concat(got, how="diagonal_relaxed") if got else pl.DataFrame()

        prac = cat("practice")
        for status, rf in practice_base_rates(prac, self.cfg.min_events).items():
            key = f"fit:PLY-14/practice/{status}"
            if rf.value is None:
                out.missing[key] = rf.reason or "missing"
            else:
                out.put(key, "PLY-14", rf.value, f"P(played | {status})", w.seasons, rf.n, None)
        miss = cat("missed")
        for pos, rf in missed_game_rates(miss, self.cfg.min_events).items():
            key = f"fit:PRJ-06/missed/{pos}"
            if rf.value is None:
                out.missing[key] = rf.reason or "missing"
            else:
                out.put(
                    key,
                    "PRJ-06",
                    rf.value,
                    f"P(no snap | played last game), {pos}",
                    w.seasons,
                    rf.n,
                    None,
                )
        key = OVERLAY["return"]
        if usage_h is None:
            out.missing[key] = "no fitted usage half-life"
            return
        ev = pl.concat([self._returns(s, usage_h) for s in w.seasons])
        rf = return_factor(ev, self.cfg.min_events)
        if rf.value is None:
            out.missing[key] = rf.reason or "missing"
        else:
            out.put(
                key,
                "PLY-14",
                rf.value,
                f"sum first-game-back snap share / sum baseline (usage h = {usage_h:g})",
                w.seasons,
                rf.n,
                _initial(key),
            )

    def _returns(self, s: int, h: float) -> pl.DataFrame:
        """PLY-14 return events: a game played after missing >= the minimum run of team games,
        listed (injury report or RES) during the run, by a QB / RB / WR / TE; baseline = his
        recency-weighted snap share over his games played on the team before the run."""
        need = int(load_params().player.ply_14_return_min_missed_games.value)
        sh = self.work.table("shares", s)
        listed = {tuple(r) for r in self.work.table("listed", s).iter_rows()}
        rows = []
        for (pid, team), grp in sh.sort("gsis_id", "team", "t").group_by(
            ["gsis_id", "team"], maintain_order=True
        ):
            pos = grp["position"][0]
            if pos not in ("QB", "RB", "WR", "TE"):
                continue
            played = grp["played"].to_list()
            share = grp["share"].to_list()
            weeks = grp["week"].to_list()
            for r in range(len(played)):
                if not played[r]:
                    continue
                run = 0
                while r - run - 1 >= 0 and not played[r - run - 1]:
                    run += 1
                start = r - run
                before = [i for i in range(start) if played[i]]
                if run < need or not before:
                    continue
                if not any((pid, team, weeks[i]) in listed for i in range(start, r)):
                    continue
                ws = [0.5 ** (j / h) for j in range(len(before))]
                vals = [share[i] for i in reversed(before)]
                base = math.fsum(w * v for w, v in zip(ws, vals, strict=True)) / math.fsum(ws)
                rows.append((base, share[r]))
        return pl.DataFrame(
            rows, schema={"baseline": pl.Float64, "return_share": pl.Float64}, orient="row"
        )

    def fit_roles(self, w: Window, out: Out) -> None:
        """Section 4 slot priors: per stat, cell and slot, the league average over the slot's
        occupants in the window: usage stats = mean over player-games of his game value;
        efficiency stats = pooled sum x / sum d. Needs BT-02's minimum of player-seasons."""
        for sid, e in sorted(REGISTRY.items()):
            for st, sd in sorted(e.stats.items()):
                if not isinstance(sd.prior, Role):
                    continue
                per: dict[tuple[str, str], list[tuple[str, float, float]]] = defaultdict(list)
                used: set[int] = set()
                for s in w.seasons:
                    g = self._game_values(sid, st, s)
                    if g.is_empty():
                        continue
                    used.add(s)
                    for cell, slot, ent, x, d in g.iter_rows():
                        per[(cell, slot)].append((ent, x, d))
                if not per:
                    why = (
                        "no FTN training data"
                        if max(w.seasons) < self.ftn_first
                        else "no player-games"
                    )
                    out.missing[f"fit:role/{sid}/{st}"] = why
                    continue
                for (cell, slot), vals in sorted(per.items()):
                    key = role_key(sid, st, cell, slot)
                    ents = len({v[0] for v in vals})
                    if ents < self.cfg.min_entities:
                        out.missing[key] = f"{ents} player-seasons < {self.cfg.min_entities}"
                        continue
                    if sd.half_life == "usage":
                        v = math.fsum(x / d for _, x, d in vals if d) / sum(
                            1 for *_, d in vals if d
                        )
                        how = "mean over slot occupants' games of his game share"
                    else:
                        v = math.fsum(x for _, x, _ in vals) / math.fsum(d for *_, d in vals)
                        how = "pooled over slot occupants' units"
                    out.put(key, sid, v, f"section 4 slot prior: {how}", used, ents, None)

    def _game_values(self, sid: str, stat: str, s: int) -> pl.DataFrame:
        """(cell, slot, player-season, sum x, sum d) per player-game, joined to its slot."""
        games = self.work.table("games", s)
        slots = self.work.table("slots", s)
        if games.is_empty() or slots.is_empty():
            return pl.DataFrame()
        if (sid, stat) == ("PLY-04", "wopr"):
            p = load_params().player
            wt, wa = float(p.ply_04_wopr_target_weight.value), float(p.ply_04_wopr_air_weight.value)
            r = self.work.table("wopr", s)
            if r.is_empty():
                return r
            u = (
                r.group_by("entity_id", "team", "g")
                .agg(
                    pl.col("his_target").sum().alias("t"),
                    pl.len().cast(pl.Float64).alias("tt"),
                    pl.col("his_air").sum().alias("a"),
                    pl.col("team_air").sum().alias("ta"),
                )
                .with_columns(
                    pl.lit("all").alias("cell"),
                    (
                        wt * pl.col("t") / pl.col("tt")
                        + wa
                        * pl.when(pl.col("ta") != 0).then(pl.col("a") / pl.col("ta")).otherwise(0.0)
                    ).alias("x"),
                    pl.lit(1.0).alias("d"),
                )
            )
        else:
            u = self.unit_rows(sid, stat, None, s)
            if u.is_empty():
                return u
            u = u.group_by("entity_id", "team", "cell", "g").agg(
                pl.col("x").sum(), pl.col("d").sum()
            )
        return (
            u.join(games.select("team", "g", "game_id"), on=["team", "g"], how="inner")
            .join(
                slots.select("team", "game_id", pl.col("gsis_id").alias("entity_id"), "slot"),
                on=["team", "game_id", "entity_id"],
                how="inner",
            )
            .select(
                "cell",
                "slot",
                (pl.lit(f"{s}|") + pl.col("entity_id") + "|" + pl.col("team")).alias("ent"),
                "x",
                "d",
            )
            .sort("cell", "slot", "ent", "x", "d")
        )


# ---------------------------------------------------------------- run


def fit_window(fitter: Fitter, w: Window) -> Out:
    out = Out()
    ks = fitter.fit_k(w, out)
    hs = fitter.fit_half_lives(w, ks, out)
    fitter.fit_g6(w, hs.get("efficiency"), out)
    coef = fitter.fit_p_go(w, out)
    fitter.fit_coa02(w, coef, out)
    fitter.fit_ol(w, out)
    fitter.fit_availability(w, hs.get("usage"), out)
    fitter.fit_roles(w, out)
    return out


def _commit() -> str:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True
        ).stdout.strip()
        return head + ("+uncommitted" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_window(
    out: Out,
    w: Window,
    fit_version: str,
    as_of: dt.datetime,
    digest: str,
    commit: str,
    folder: Path,
) -> Path:
    body = {
        "fit_version": fit_version,
        "window": w.name,
        "test_season": w.test_season,
        "seasons": list(w.seasons),
        "data_as_of": as_of.isoformat(),
        "data_digest": digest,
        "code_commit": commit,
        "attribution": ATTRIBUTION,
        "values": dict(sorted(out.values.items())),
        "missing": dict(sorted(out.missing.items())),
        "no_signal": dict(sorted(out.no_signal.items())),
    }
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{w.name}.yaml"
    path.write_text(
        "# Phase 3e (BT-02 core) fit. Generated by `ge fit`; do not edit by hand.\n"
        + yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
        newline="\n",
    )
    return path


def run_fit(
    windows: list[Window],
    fit_version: str,
    as_of: dt.datetime,
    *,
    root: Path = DATA_ROOT,
    work_root: Path = WORK_ROOT,
    out_root: Path = FITTED_ROOT,
    fresh: bool = False,
    commit: str | None = None,
) -> dict[str, Out]:
    """Fit every window; write each file and return the results (for the report)."""
    cfg = FitConfig.from_params(load_params().fitting)
    work = Work(work_root / fit_version)
    prepare(work, [s for w in windows for s in w.seasons], root, as_of, fresh)
    fitter = Fitter(work, cfg, fit_version)
    commit = commit if commit is not None else _commit()
    results = {}
    for w in windows:
        out = fit_window(fitter, w)
        digest = hashlib.sha256(
            "\n".join(f"{s}:{work.digest(s)}" for s in w.seasons).encode()
        ).hexdigest()
        write_window(out, w, fit_version, as_of, digest, commit, out_root / fit_version)
        results[w.name] = out
    return results
