"""Every metric by spec ID: its raw function, and for each stat the k (a params.yaml key),
the prior and the G3 half-life class. `raw(ctx, id)` and `shrunk(ctx, id, stat)` are the only
entry points later phases use.

Where the spec doesn't define something a stat needs, the stat says so in `missing` and
shrinking it raises NotImplementedError (user decisions 2026-10-02)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import polars as pl

from ge.metrics import defense as d
from ge.metrics import offense as o
from ge.metrics import player as pl_
from ge.metrics.context import MetricContext
from ge.metrics.conventions import HalfLife
from ge.metrics.engine import Computed, Fixed, League, Parent, Side, StatDef, shrink_stat

RawFn = Callable[[MetricContext], pl.DataFrame]
E: HalfLife = "efficiency"


@dataclass(frozen=True)
class Entry:
    spec_id: str
    raw: RawFn
    stats: dict[str, StatDef] = field(default_factory=dict)
    side: Side | None = None
    paid: bool = False
    proxy: bool = False  # a v1 free-data proxy (PLY-02, PLY-08)
    full: RawFn | None = None  # the full version a proxy stands in for (raises PAID)

    def param_keys(self) -> list[str]:
        keys = []
        for s in self.stats.values():
            keys += s.k_keys()
            if isinstance(s.prior, Fixed) and s.prior.key:
                keys.append(s.prior.key)
        return keys


def _stats(*defs: StatDef) -> dict[str, StatDef]:
    return {s.stat: s for s in defs}


def _no_team_k(sid: str, what: str) -> str:
    return (
        f"{sid}: {what} cells shrink toward the team's own shrunk value, but the spec gives no "
        "team-level k for it (user decision 2026-10-02: raise until the spec sets one)"
    )


def _split_k(prefix: str) -> dict[str, str]:
    return {"all": f"{prefix}_k_overall", "pass": f"{prefix}_k_pass", "run": f"{prefix}_k_run"}


def _run_grid(
    sid: str, grp: str, pre: str, epa_parent: str, success_parent: str
) -> dict[str, StatDef]:
    return _stats(
        StatDef("carries", E),
        StatDef("epa", E, f"{grp}.{pre}_k_epa_ypc", Parent(epa_parent, "epa", "run")),
        StatDef("success", E, f"{grp}.{pre}_k_success", Parent(success_parent, "success", "run")),
        StatDef("ypc", E, f"{grp}.{pre}_k_epa_ypc", missing=_no_team_k(sid, "yards/carry")),
        StatDef(
            "explosive", E, f"{grp}.{pre}_k_explosive", missing=_no_team_k(sid, "explosive-rate")
        ),
    )


def _eligible_on_off(rows: pl.DataFrame) -> pl.DataFrame:
    """DEF-08: numeric adjustment only with >= 200 plays each way."""
    return rows.filter(~pl.col("below_min_sample") & pl.col("value_w").is_not_null())


def _role_prior(sid: str, what: str = "a role prior") -> str:
    return (
        f"{sid}: shrinks toward {what}: section 4's role prior is last season's shrunk value "
        "(which itself needs a role prior) or the league average for his depth-chart slot, "
        "estimated in Phase 3e (BT-02 core); raises until then (user decision 2026-10-02)"
    )


def _usage_role(sid: str, stat: str, k: str, what: str = "a role prior") -> StatDef:
    return StatDef(stat, U, f"player.{k}", missing=_role_prior(sid, what))


def _ply_15_prior(stat: str) -> Computed:
    return Computed(lambda ctx: pl_.ply_15_prior(ctx, stat))


_OFF: Side = "offense"
_DEF: Side = "defense"
U: HalfLife = "usage"
_OVERALL = "his shrunk overall share, which needs a role prior"
REGISTRY: dict[str, Entry] = {
    e.spec_id: e
    for e in [
        # ---- section 2: team offense ----
        Entry(
            "OFF-01",
            o.off_01,
            _stats(StatDef("epa", E, {c: f"offense.{k}" for c, k in _split_k("off_01").items()})),
            _OFF,
        ),
        Entry("OFF-02", o.off_02, _stats(StatDef("success", E, "offense.off_02_k")), _OFF),
        Entry(
            "OFF-03",
            o.off_03,
            _stats(
                StatDef("epa", E, "offense.off_03_k", Parent("OFF-01", "epa", "all")),
                StatDef("success", E, "offense.off_03_k", Parent("OFF-02", "success", "all")),
            ),
            _OFF,
        ),
        Entry("OFF-04", o.off_04, _stats(StatDef("pass_rate", E, "offense.off_04_k")), _OFF),
        Entry("OFF-05", o.off_05, _stats(StatDef("proe", E, "offense.off_05_k", Fixed(0.0))), _OFF),
        Entry("OFF-06", o.off_06, _stats(StatDef("play_action_rate", E, "offense.off_06_k")), _OFF),
        Entry("OFF-07", o.off_07, _stats(StatDef("motion_rate", E, "offense.off_07_k")), _OFF),
        Entry("OFF-08", o.off_08, _stats(StatDef("rpo_rate", E, "offense.off_08_k")), _OFF),
        Entry("OFF-09", o.off_09, _stats(StatDef("shotgun_rate", E, "offense.off_09_k")), _OFF),
        Entry(
            "OFF-10",
            o.off_10,
            _stats(StatDef("seconds_per_play", E, "offense.off_10_k_pairs")),
            _OFF,
        ),
        Entry(
            "OFF-11", o.off_11, _stats(StatDef("plays_per_game", E, "offense.off_11_k_games")), _OFF
        ),
        Entry(
            "OFF-12", o.off_12, _run_grid("OFF-12", "offense", "off_12", "OFF-01", "OFF-02"), _OFF
        ),
        Entry(
            "OFF-13",
            o.off_13,
            _stats(
                StatDef("share", E, "offense.off_13_k_targets"),
                StatDef("epa", E, "offense.off_13_k_targets", Parent("OFF-01", "epa", "pass")),
                StatDef(
                    "cpoe",
                    E,
                    "offense.off_13_k_targets",
                    missing=(
                        "OFF-13: completion over expected per cell shrinks toward the team's "
                        "shrunk pass value, which has no team-level k (user decision 2026-10-02)"
                    ),
                ),
            ),
            _OFF,
        ),
        Entry(
            "OFF-14",
            o.off_14,
            _stats(
                StatDef("pass_share", E, "offense.off_14_k_plays"),
                StatDef("td_per_trip", E, "offense.off_14_k_trips"),
            ),
            _OFF,
        ),
        Entry(
            "OFF-15",
            o.off_15,
            _stats(
                StatDef("sack_rate", E, "offense.off_15_k"),
                StatDef("hit_rate", E, "offense.off_15_k"),
            ),
            _OFF,
        ),
        Entry(
            "OFF-16",
            o.off_16,
            _stats(
                StatDef("success", E, "offense.off_16_k", Parent("OFF-02", "success", "run")),
                StatDef("stuff", E, "offense.off_16_k", missing=_no_team_k("OFF-16", "stuff-rate")),
            ),
            _OFF,
        ),
        Entry("OFF-17", o.off_17, side=_OFF),
        # ---- section 3: team defense ----
        Entry(
            "DEF-01",
            d.def_01,
            _stats(StatDef("epa", E, {c: f"defense.{k}" for c, k in _split_k("def_01").items()})),
            _DEF,
        ),
        Entry("DEF-02", d.def_02, _stats(StatDef("success", E, "defense.def_02_k")), _DEF),
        Entry(
            "DEF-03", d.def_03, _run_grid("DEF-03", "defense", "def_03", "DEF-01", "DEF-02"), _DEF
        ),
        Entry(
            "DEF-04",
            d.def_04,
            _stats(
                *(
                    StatDef(
                        s, E, "defense.def_04_k_targets", Fixed(key="defense.def_04_prior_ratio")
                    )
                    for s in ("targets", "receptions", "yards", "tds")
                ),
                StatDef("epa_diff", E, "defense.def_04_k_targets", Fixed(0.0)),
            ),
            _DEF,
        ),
        Entry("DEF-04b", d.def_04b, paid=True),
        Entry(
            "DEF-05",
            d.def_05,
            _stats(
                *(
                    StatDef(s, E, "defense.def_05_k")
                    for s in ("blitz_rate", "rushers", "box", "sack_rate", "hit_rate")
                ),
            ),
            _DEF,
        ),
        Entry("DEF-05b", d.def_05b, paid=True),
        Entry(
            "DEF-06",
            d.def_06,
            _stats(
                *(
                    StatDef(s, E, "defense.def_06_k")
                    for s in ("explosive", "explosive_run", "explosive_pass")
                ),
            ),
            _DEF,
        ),
        Entry(
            "DEF-07", d.def_07, _stats(StatDef("td_per_trip", E, "defense.def_07_k_trips")), _DEF
        ),
        Entry(
            "DEF-08",
            d.def_08,
            _stats(
                StatDef("on_off", E, "defense.def_08_k", Fixed(0.0), eligible=_eligible_on_off),
            ),
            _DEF,
        ),
        # ---- section 4: player ----
        Entry("PLY-01", pl_.ply_01, _stats(_usage_role("PLY-01", "snap_share", "ply_01_k_games"))),
        Entry(
            "PLY-02",
            pl_.ply_02,
            _stats(_usage_role("PLY-02", "snap_share", "ply_01_k_games")),
            proxy=True,
            full=pl_.ply_02_full,
        ),
        Entry(
            "PLY-03",
            pl_.ply_03,
            _stats(_usage_role("PLY-03", "target_share", "ply_03_k_team_targets")),
        ),
        Entry(
            "PLY-04",
            pl_.ply_04,
            _stats(
                _usage_role("PLY-04", "air_share", "ply_04_k_team_targets"),
                _usage_role("PLY-04", "wopr", "ply_04_k_team_targets"),
            ),
        ),
        Entry(
            "PLY-05",
            pl_.ply_05,
            _stats(_usage_role("PLY-05", "carry_share", "ply_05_k_team_carries")),
        ),
        Entry(
            "PLY-06",
            pl_.ply_06,
            _stats(
                _usage_role("PLY-06", "opportunity_share", "ply_06_k_team_opportunities", _OVERALL)
            ),
        ),
        Entry(
            "PLY-07",
            pl_.ply_07,
            _stats(_usage_role("PLY-07", "opportunity_share", "ply_07_k", _OVERALL)),
        ),
        Entry(
            "PLY-08",
            pl_.ply_08,
            _stats(
                StatDef(
                    "yards_per_team_dropback",
                    E,
                    "player.ply_08_k_team_dropbacks",
                    missing=_role_prior("PLY-08"),
                )
            ),
            proxy=True,
            full=pl_.ply_08_full,
        ),
        Entry(
            "PLY-09",
            pl_.ply_09,
            _stats(StatDef("yacoe", E, "player.ply_09_k_receptions", Fixed(0.0))),
        ),
        Entry(
            "PLY-10", pl_.ply_10, _stats(StatDef("croe", E, "player.ply_10_k_targets", Fixed(0.0)))
        ),
        Entry(
            "PLY-11",
            pl_.ply_11,
            _stats(StatDef("ryoe_per_carry", E, "player.ply_11_k_carries", Fixed(0.0))),
        ),
        Entry("PLY-12", pl_.ply_12, paid=True),
        Entry("PLY-13", pl_.ply_13),
        Entry("PLY-14", pl_.ply_14),
        Entry(
            "PLY-15",
            pl_.ply_15,
            _stats(
                *(
                    StatDef(
                        s, U, "player.ply_15_k_games", _ply_15_prior(s), prior_only_below_min=True
                    )
                    for s in ("target_share", "carry_share")
                )
            ),
        ),
        Entry(
            "PLY-16",
            pl_.ply_16,
            _stats(
                StatDef(
                    "share",
                    U,
                    "player.ply_16_k_carries",
                    missing=(
                        "PLY-16: lane carry shares would shrink toward the team's shrunk OFF-12 "
                        "value, but OFF-12 has no shrunk carry-share stat (user decision "
                        "2026-10-04: raise until the spec sets it)"
                    ),
                ),
                StatDef(
                    "success",
                    E,
                    "player.ply_16_k_carries",
                    Parent("OFF-12", "success", None, "team"),
                ),
                StatDef("epa", E, "player.ply_16_k_carries", Parent("OFF-12", "epa", None, "team")),
            ),
        ),
        Entry(
            "PLY-17",
            pl_.ply_17,
            _stats(
                *(
                    StatDef(s, E, "player.ply_17_k_blitzed_dropbacks")
                    for s in ("epa_gap", "sack_gap")
                )
            ),
        ),
    ]
}


def _entry(spec_id: str) -> Entry:
    if spec_id not in REGISTRY:
        raise KeyError(f"no metric {spec_id!r} in the registry")
    return REGISTRY[spec_id]


def raw(ctx: MetricContext, spec_id: str) -> pl.DataFrame:
    """Raw rows (value, value_w, n, n_eff, min-n flag, league rows) for one metric."""
    key = ("raw", spec_id)
    if key not in ctx.cache:
        ctx.cache[key] = _entry(spec_id).raw(ctx)
    return ctx.cache[key]


def shrunk(ctx: MetricContext, spec_id: str, stat: str) -> pl.DataFrame:
    """One stat of one metric with its prior, k and G1-shrunk value."""
    key = ("shrunk", spec_id, stat)
    if key not in ctx.cache:
        e = _entry(spec_id)
        if stat not in e.stats:
            raise KeyError(f"{spec_id} has no shrinkable stat {stat!r}; has {sorted(e.stats)}")
        ctx.cache[key] = shrink_stat(
            ctx,
            spec_id,
            e.stats[stat],
            raw(ctx, spec_id),
            e.side,
            lambda sid, st: shrunk(ctx, sid, st),
        )
    return ctx.cache[key]


__all__ = ["REGISTRY", "Entry", "League", "raw", "shrunk"]
