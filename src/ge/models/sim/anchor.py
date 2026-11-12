"""PRJ-01b market-anchored mode: one offset added to each team's offensive ratings (pass and run
alike, so the pass/run mix from 01a is held), solved so the simulation's interpolated median
margin and median total are within the params tolerance (0.25 points) of the consensus spread
and total. Every iteration uses the game's fixed seed (common random numbers).

The solver takes Newton steps on the two offsets with a finite-difference Jacobian re-estimated
at every point (the medians carry Monte Carlo noise, so updated slopes drift), each step at most
`max_step` EPA per play and halved while it makes the miss worse; it raises AnchorFailed when
the targets are not reached within `max_iter` simulations (never a near miss reported as
success)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ge.config import load_params
from ge.models.sim import arrays as A
from ge.models.sim.arrays import GameArrays
from ge.models.sim.engine import SimResult, simulate
from ge.models.sim.league import LeagueTables
from ge.models.sim.median import interpolated_median


class AnchorFailed(RuntimeError):
    """PRJ-01b: the targets were not reached."""


@dataclass(frozen=True)
class AnchorResult:
    d_home: float
    d_away: float
    iterations: int
    median_margin: float
    median_total: float
    result: SimResult


def anchor(
    make: Callable[[float, float], GameArrays],
    league: LeagueTables,
    *,
    target_margin: float,
    target_total: float,
    n_runs: int,
    game_id: str,
    model_version: str,
    max_iter: int = 40,
    probe: float = 0.1,
    max_step: float = 0.3,
    trace: list[tuple[float, float, float, float]] | None = None,
) -> AnchorResult:
    """PRJ-01b: `make(d_home, d_away)` gives the game with those offensive offsets (EPA per
    play) applied; target_margin is the home margin (home minus away)."""
    tol = float(load_params().projection.prj_01_anchor_tolerance_points.value)
    target = np.array([target_margin, target_total])
    sims = 0

    def run(x: np.ndarray) -> tuple[np.ndarray, SimResult]:
        nonlocal sims
        sims += 1
        r = simulate(make(float(x[0]), float(x[1])), league, n_runs, game_id=game_id,
                     model_version=model_version)  # fmt: skip
        pts = r.team[:, :, A.R_POINTS].astype(np.int64)
        f = np.array(
            [interpolated_median(pts[:, 0] - pts[:, 1]), interpolated_median(pts.sum(axis=1))]
        )
        if trace is not None:
            trace.append((float(x[0]), float(x[1]), float(f[0]), float(f[1])))
        return f, r

    def jacobian(x: np.ndarray, f: np.ndarray) -> np.ndarray:
        jac = np.zeros((2, 2))
        for j in range(2):
            e = np.zeros(2)
            e[j] = probe
            fj, _ = run(x + e)
            jac[:, j] = (fj - f) / probe
        return jac

    x = np.zeros(2)
    f, r = run(x)
    if np.all(np.abs(f - target) <= tol):
        return AnchorResult(0.0, 0.0, sims, float(f[0]), float(f[1]), r)
    jac = jacobian(x, f)
    while sims < max_iter:
        if abs(np.linalg.det(jac)) < 1e-9:
            break
        step = np.linalg.solve(jac, target - f)
        size = float(np.max(np.abs(step)))
        if size > max_step:
            step *= max_step / size
        res = float(np.max(np.abs(f - target)))
        accepted = False
        for _halving in range(4):  # backtracking: a step that makes things worse is halved
            x_new = x + step
            f_new, r = run(x_new)
            if np.all(np.abs(f_new - target) <= tol):
                return AnchorResult(float(x_new[0]), float(x_new[1]), sims, float(f_new[0]),
                                    float(f_new[1]), r)  # fmt: skip
            if float(np.max(np.abs(f_new - target))) < res or sims >= max_iter:
                accepted = True
                break
            step = step / 2.0
        if accepted:
            x, f = x_new, f_new
        jac = jacobian(x, f)  # fresh slopes at the current point (noise-robust)
    raise AnchorFailed(
        f"PRJ-01b {game_id}: targets margin {target_margin:+.2f}, total {target_total:.2f} not "
        f"reached in {sims} simulations (last margin {f[0]:+.2f}, total {f[1]:.2f}, offsets "
        f"{x[0]:+.3f} / {x[1]:+.3f})"
    )
