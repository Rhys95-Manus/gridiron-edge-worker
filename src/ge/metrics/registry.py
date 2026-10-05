"""Every metric by spec ID: its raw function, and for each stat the k (a params.yaml key),
the prior and the G3 half-life class. `raw(ctx, id)` and `shrunk(ctx, id, stat)` are the only
entry points later phases use.

Where the spec doesn't define something a stat needs, the stat says so in `missing` and
shrinking it raises NotImplementedError (user decisions 2026-10-02)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import polars as pl

from ge.metrics import coaching as co
from ge.metrics import defense as d
from ge.metrics import offense as o
from ge.metrics import player as pl_
from ge.metrics import skills as sk
from ge.metrics.context import MetricContext
from ge.metrics.conventions import HalfLife
from ge.metrics.engine import (
    AtPosition,
    Computed,
    Fixed,
    League,
    Parent,
    Side,
    StatDef,
    shrink_stat,
)

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


def _overall(sid: str, k: str, **stats: HalfLife) -> dict[str, StatDef]:
    """6b stats whose prior is 'his overall' (rule 1: his overall value, itself shrunk toward
    his role prior): raise until Phase 3e (ruling 2026-10-04)."""
    return _stats(
        *(
            StatDef(
                s,
                h,
                f"player.{k}",
                missing=_role_prior(sid, "his overall value, which needs a role prior"),
            )
            for s, h in stats.items()
        )
    )


def _no_k(sid: str, stat: str) -> str:
    return (
        f"{sid}: {stat} has no k in its own unit in the spec (ruling 2026-10-04: raise until it "
        "sets one)"
    )


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
        # ---- section 6b: player skills ----
        Entry("PLY-18", sk.ply_18, _overall("PLY-18", "ply_18_k_attempts", share=U, epa=E, adot=E)),
        Entry(
            "PLY-19",
            sk.ply_19,
            _stats(
                StatDef("epa_gap", E, "player.ply_19_k"),
                StatDef(
                    "play_action_rate",
                    E,
                    "player.ply_19_k",
                    missing="PLY-19: his play-action rate has no prior in the spec (k = 100 and "
                    "the league gap belong to the play-action split); raises until it sets one",
                ),
            ),
        ),
        Entry(
            "PLY-20",
            sk.ply_20,
            _stats(
                *(
                    StatDef(s, E, "player.ply_20_k", AtPosition("QB"))
                    for s in (
                        "cpoe",
                        "catchable_rate",
                        "interception_worthy_rate",
                        "throwaway_rate",
                    )
                )
            ),
        ),
        Entry(
            "PLY-21",
            sk.ply_21,
            _stats(
                *(
                    StatDef(s, E, "player.ply_21_k", AtPosition("QB"))
                    for s in ("time_to_throw", "sack_rate")
                )
            ),
        ),
        Entry(
            "PLY-22",
            sk.ply_22,
            _stats(
                StatDef("yards_per_rush", E, "player.ply_22_k", AtPosition("QB")),
                *(
                    StatDef(s, E, "player.ply_22_k", missing=_no_k("PLY-22", s))
                    for s in ("scramble_rate", "designed_runs_per_game")
                ),
            ),
        ),
        Entry("PLY-23", sk.ply_23, _overall("PLY-23", "ply_23_k", share=U, epa=E)),
        Entry("PLY-24", sk.ply_24, _overall("PLY-24", "ply_24_k", success=E, ypc=E)),
        Entry("PLY-25", sk.ply_25, _overall("PLY-25", "ply_25_k", success=E, ypc=E)),
        Entry(
            "PLY-26",
            sk.ply_26,
            _stats(
                StatDef("explosive", E, "player.ply_26_k_explosive", AtPosition("RB")),
                StatDef("stuff", E, "player.ply_26_k_stuff", AtPosition("RB")),
            ),
        ),
        Entry(
            "PLY-27",
            sk.ply_27,
            _stats(
                *(
                    _usage_role("PLY-27", s, "ply_27_k")
                    for s in ("screen_share", "target_share", "yacoe")
                )
            ),
        ),
        Entry("PLY-28", sk.ply_28, _overall("PLY-28", "ply_28_k", share=U, epa=E, adot=E)),
        Entry("PLY-29", sk.ply_29, _overall("PLY-29", "ply_29_k", share=U, epa=E)),
        Entry(
            "PLY-30",
            sk.ply_30,
            _stats(
                StatDef("drop_rate", E, "player.ply_30_k_catchable", AtPosition()),
                StatDef("contested_catch_rate", E, "player.ply_30_k_contested", AtPosition()),
                StatDef(
                    "created_reception_rate",
                    E,
                    "player.ply_30_k_catchable",
                    missing=_no_k("PLY-30", "created_reception_rate"),
                ),
            ),
        ),
        Entry(
            "PLY-31",
            sk.ply_31,
            _stats(
                *(StatDef(s, E, "player.ply_31_k", AtPosition()) for s in ("separation", "cushion"))
            ),
        ),
        Entry(
            "PLY-32",
            sk.ply_32,
            _stats(
                _usage_role("PLY-32", "end_zone_share", "ply_32_k", "his PLY-06 red-zone share")
            ),
        ),
        Entry("PLY-33", sk.ply_33, _overall("PLY-33", "ply_33_k", target_share=U)),
        Entry("PLY-34", sk.ply_34),
        # ---- section 6b: defensive counterparts ----
        Entry(
            "DEF-09",
            d.def_09,
            _stats(
                StatDef("epa", E, "defense.def_09_k", Parent("DEF-01", "epa", "pass")),
                StatDef(
                    "cpoe",
                    E,
                    "defense.def_09_k",
                    missing="DEF-09: completion over expected per cell shrinks toward the "
                    "defense's shrunk pass value, which has no team-level k (user decision "
                    "2026-10-02, OFF-13 ruling)",
                ),
            ),
            _DEF,
        ),
        Entry("DEF-10", d.def_10, _stats(StatDef("epa_gap", E, "defense.def_10_k")), _DEF),
        Entry(
            "DEF-11", d.def_11, _stats(StatDef("yacoe", E, "defense.def_11_k", Fixed(0.0))), _DEF
        ),
        Entry(
            "DEF-12",
            d.def_12,
            _stats(
                StatDef(
                    "stacked_box_share",
                    E,
                    "defense.def_12_k",
                    missing="DEF-12: the stacked-box share has no k or prior in the spec (ruling "
                    "2026-10-04: raise until it sets them)",
                ),
                StatDef("success", E, "defense.def_12_k", Parent("DEF-02", "success", "run")),
                StatDef("ypc", E, "defense.def_12_k", missing=_no_team_k("DEF-12", "yards/carry")),
            ),
            _DEF,
        ),
        Entry("DEF-13", d.def_13, _stats(StatDef("epa_gap", E, "defense.def_13_k")), _DEF),
        Entry(
            "DEF-14",
            d.def_14,
            _stats(
                *(StatDef(s, E, "defense.def_14_k") for s in ("scramble_rate", "qb_rush_yards"))
            ),
            _DEF,
        ),
        Entry(
            "DEF-15",
            d.def_15,
            _stats(
                StatDef("success", E, "defense.def_15_k", Parent("DEF-02", "success", "run")),
                StatDef("ypc", E, "defense.def_15_k", missing=_no_team_k("DEF-15", "yards/carry")),
            ),
            _DEF,
        ),
        Entry("DEF-16", d.def_16, _stats(StatDef("td_rate", E, "defense.def_16_k")), _DEF),
        Entry(
            "DEF-17",
            d.def_17,
            _stats(
                *(
                    StatDef(s, U, "defense.def_17_k_events_per_share", Computed(d.def_17_prior))
                    for s in d.DEF17_CREDITS
                )
            ),
        ),
        # ---- section 5: coaching ----
        Entry("COA-01", co.coa_01),
        Entry(
            "COA-02",
            co.coa_02,
            _stats(
                StatDef(
                    "go_over_expected",
                    E,
                    "coaching.coa_02_k",
                    Fixed(0.0),
                    missing="COA-02: going for it over expected needs the p_go logistic model, "
                    "which Phase 3e fits (user decision 2026-10-02); the raw go rate is shown",
                )
            ),
            _OFF,
        ),
        Entry("COA-03", co.coa_03, _stats(StatDef("two_point_rate", E, "coaching.coa_03_k")), _OFF),
        Entry(
            "COA-04",
            co.coa_04,
            _stats(*(StatDef(s, E, "coaching.coa_04_k") for s in ("proe", "seconds_per_play"))),
            _OFF,
        ),
        Entry("COA-05", co.coa_05),
        Entry("COA-05b", co.coa_05b, paid=True),
        Entry("COA-06", co.coa_06),
        Entry("COA-07", co.coa_07),
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
