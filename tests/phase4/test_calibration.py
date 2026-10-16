"""PRJ-01a calibration (decision log 2026-10-13, Phase 4b).

Per window, from every training-season game that can be rated point-in-time: actual home
margin = a x 1[non-neutral] + b x raw spread and actual total = a_t + b_t x raw total, by
least squares on actual results only (never closing lines). a applies only at non-neutral
sites. Calibrated spread and total are PRJ-01a's outputs; raw values are kept.

- calibrate() equals the closed-form OLS with the indicator design and recovers planted
  values within 3 standard errors (synthetic; every number here is a test setting);
- game_lines applies a, b, a_t, b_t with delta-method standard errors;
- season S's calibration reads no game from S or later, and deleting those seasons changes
  nothing (fixture store, window narrowed to 2023, weeks 9-10 to keep the test short);
- the holdout is refused; the r2 file round-trips the calibration with its provenance."""

from __future__ import annotations

import datetime as dt
import math
import shutil
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import ge.store.snapshot as snapshot_module
from ge.config import FittedFile, _check_fitted, _read_yaml, load_params
from ge.metrics.coaching import CoachingRegistry
from ge.models.ratings import (
    CALIB_KEYS,
    Calibration,
    WindowConsts,
    calibrate,
    fit_ratings,
    game_lines,
    load_window_consts,
)
from ge.models.ratings_window import fit_calibration, fit_window, write_window_file
from ge.store.holdout import HoldoutReadError, Window
from tests.phase3.conftest import STORE
from tests.phase4 import synth

AS_OF = dt.datetime(2026, 10, 12, tzinfo=dt.UTC)
FIXTURE_WINDOW = Window("S2024", 2024, (2023,))
WEEKS = (9, 10)


def _games(key: str, n: int = 2000) -> tuple[pl.DataFrame, dict[str, float]]:
    """Synthetic rated games with a planted compression and home edge (test settings)."""
    g = synth.rng(key)
    planted = {"a": 2.0, "b": 1.8, "a_t": 4.0, "b_t": 0.9}
    raw_spread = g.normal(0.0, 3.0, n)
    raw_total = g.normal(44.0, 3.0, n)
    neutral = g.random(n) < 0.15
    margin = planted["a"] * (~neutral) + planted["b"] * raw_spread + g.normal(0.0, 13.0, n)
    total = planted["a_t"] + planted["b_t"] * raw_total + g.normal(0.0, 13.0, n)
    df = pl.DataFrame(
        {
            "raw_spread": raw_spread,
            "raw_total": raw_total,
            "neutral": neutral,
            "margin": margin,
            "total": total,
        }
    )
    return df, planted


def _ols(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ b
    return b, (r @ r) / (len(y) - X.shape[1]) * np.linalg.inv(X.T @ X)


def test_calibrate_matches_closed_form_ols() -> None:
    df, _ = _games("calib/closed")
    got = calibrate(df)
    nn = (~df["neutral"].to_numpy()).astype(float)
    bs, cs = _ols(np.column_stack([nn, df["raw_spread"].to_numpy()]), df["margin"].to_numpy())
    bt, ct = _ols(
        np.column_stack([np.ones(df.height), df["raw_total"].to_numpy()]), df["total"].to_numpy()
    )
    assert (got.a, got.b) == pytest.approx((bs[0], bs[1]), rel=1e-10)
    assert (got.a_se, got.b_se, got.ab_cov) == pytest.approx(
        (math.sqrt(cs[0, 0]), math.sqrt(cs[1, 1]), cs[0, 1]), rel=1e-8
    )
    assert (got.a_t, got.b_t) == pytest.approx((bt[0], bt[1]), rel=1e-10)
    assert (got.a_t_se, got.b_t_se, got.ab_t_cov) == pytest.approx(
        (math.sqrt(ct[0, 0]), math.sqrt(ct[1, 1]), ct[0, 1]), rel=1e-8
    )
    assert got.n == df.height


def test_calibrate_recovers_planted_values() -> None:
    df, planted = _games("calib/recover", 4000)
    got = calibrate(df)
    for name in ("a", "b", "a_t", "b_t"):
        est, se = getattr(got, name), getattr(got, f"{name}_se")
        assert abs(est - planted[name]) <= 3 * se, (name, est, se)


def test_home_edge_never_applies_at_a_neutral_site() -> None:
    """Planted: neutral games carry no a. A fit that put a on every game would be biased;
    the indicator design recovers a and b."""
    df, planted = _games("calib/neutral", 4000)
    got = calibrate(df)
    assert abs(got.a - planted["a"]) <= 3 * got.a_se
    neutral_only = df.filter(pl.col("neutral"))
    resid = neutral_only["margin"] - got.b * neutral_only["raw_spread"]
    assert abs(float(resid.mean())) < 3 * 13.0 / math.sqrt(neutral_only.height)


def _consts(calib: Calibration | None) -> WindowConsts:
    coefs = {"home": 0.0, "rest": 0.0, "travel": 0.0, "tz": 0.0}
    return WindowConsts(
        "S3001", "rt", coefs, dict(coefs), c=6.0, c_se=0.1, league_epa=0.01,
        league_ppd=2.0, league_drives=11.0, calib=calib,
    )  # fmt: skip


@pytest.mark.parametrize("neutral", [False, True])
def test_game_lines_apply_the_calibration(neutral: bool) -> None:
    s = synth.make("calib/lines", synth.Settings(teams=6, seasons=1, weeks=5, plays_per_offense=30))
    plays = synth.season_frame(s, s.settings.first_season)
    table = fit_ratings(plays, s.teams, penalty=40.0, h=3.0, prior=None)
    home, away = s.teams[0], s.teams[1]
    h = 0.0 if neutral else 1.0
    terms = pl.DataFrame(
        {
            "game_id": ["g", "g"],
            "posteam": [home, away],
            "defteam": [away, home],
            "home": [h, -h],
            "d_rest": [0.0, 0.0],
            "d_travel": [0.0, 0.0],
            "d_tz": [0.0, 0.0],
        }
    )
    p = {home: 0.6, away: 0.55}
    cal = Calibration(
        a=2.0, b=1.8, a_t=4.0, b_t=0.9, a_se=0.3, b_se=0.1, a_t_se=2.0, b_t_se=0.05,
        ab_cov=-0.004, ab_t_cov=-0.09, n=1000,
    )  # fmt: skip
    raw = game_lines(table, "g", home, away, p, terms, _consts(None))
    got = game_lines(table, "g", home, away, p, terms, _consts(cal))
    assert (got.raw_spread, got.raw_total) == (raw.spread, raw.total)
    assert (got.raw_spread_se, got.raw_total_se) == (raw.spread_se, raw.total_se)
    assert got.neutral is neutral
    ind = 0.0 if neutral else 1.0
    assert got.spread == pytest.approx(ind * 2.0 + 1.8 * raw.spread, abs=1e-12)
    assert got.total == pytest.approx(4.0 + 0.9 * raw.total, abs=1e-12)
    var_s = 1.8**2 * raw.spread_se**2 + (
        ind * ind * 0.3**2 + raw.spread**2 * 0.1**2 + 2 * ind * raw.spread * -0.004
    )
    var_t = 0.9**2 * raw.total_se**2 + (2.0**2 + raw.total**2 * 0.05**2 + 2 * raw.total * -0.09)
    assert got.spread_se == pytest.approx(math.sqrt(var_s), rel=1e-12)
    assert got.total_se == pytest.approx(math.sqrt(var_t), rel=1e-12)


@pytest.fixture(scope="module")
def fixture_fit(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    from ge.config import use_fitted_root
    from tests.phase4.conftest import FIT_SETTINGS, write_fitted_root

    root = write_fitted_root(tmp_path_factory.mktemp("fitted_calib"), FIT_SETTINGS)
    with use_fitted_root(root):
        yield root, fit_window(FIXTURE_WINDOW, AS_OF, root=STORE)


def test_calibration_reads_only_earlier_seasons(
    fixture_fit, registry: CoachingRegistry, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    from ge.config import use_fitted_root

    root, fit = fixture_fit
    seen: list[str] = []
    orig = snapshot_module.snapshot

    def spy(game_id: str, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        seen.append(game_id)
        return orig(game_id, *args, **kwargs)  # type: ignore[arg-type]

    with use_fitted_root(root):
        monkeypatch.setattr(snapshot_module, "snapshot", spy)
        cal, rated = fit_calibration(
            FIXTURE_WINDOW, fit, root=STORE, registry=registry, weeks=WEEKS
        )
        monkeypatch.setattr(snapshot_module, "snapshot", orig)
        assert seen and all(int(g[:4]) < 2024 for g in seen), sorted(set(g[:4] for g in seen))
        assert cal.n == rated.filter(pl.col("skip_reason").is_null()).height > 0
        ok = rated.filter(pl.col("skip_reason").is_null())
        want = calibrate(ok.select("raw_spread", "raw_total", "neutral", "margin", "total"))
        assert cal == want
        copy = tmp_path / "store"
        shutil.copytree(STORE, copy)
        for ds in copy.iterdir():
            for later in ds.glob("season=2024"):
                shutil.rmtree(later)
        cal2, rated2 = fit_calibration(
            FIXTURE_WINDOW, fit, root=copy, registry=registry, weeks=WEEKS
        )
        assert cal2 == cal
        assert rated2.equals(rated)


def test_calibration_refuses_the_holdout(fixture_fit, registry: CoachingRegistry) -> None:  # type: ignore[no-untyped-def]
    _, fit = fixture_fit
    holdout = int(load_params().backtest.bt_01_holdout_season.value)
    with pytest.raises(HoldoutReadError):
        fit_calibration(Window.for_test_season(holdout), fit, root=STORE, registry=registry)


def test_window_file_round_trips_the_calibration(
    fixture_fit, registry: CoachingRegistry, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    from dataclasses import replace

    from ge.config import use_fitted_root

    root, fit = fixture_fit
    with use_fitted_root(root):
        cal, _ = fit_calibration(FIXTURE_WINDOW, fit, root=STORE, registry=registry, weeks=WEEKS)
    path = write_window_file(
        replace(fit, calib=cal, calib_skipped={"G4: test": 1}), "rtest", tmp_path
    )
    (tmp_path / "active.yaml").write_text("fit_version: rtest\n", encoding="utf-8", newline="\n")
    f = FittedFile.model_validate(_read_yaml(path))
    _check_fitted(f, path, load_params())
    for key in CALIB_KEYS.values():
        assert key in f.values and f.values[key].n == cal.n, key
    got = load_window_consts(2024, tmp_path)
    assert got.calib == cal


def test_unrated_training_games_read_back_from_the_window_file(
    fixture_fit, registry: CoachingRegistry, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    """The report's per-window unrated table reads the counts the window file records."""
    from dataclasses import replace

    from ge.config import use_fitted_root
    from ge.models.ratings_report import unrated_training_games

    root, fit = fixture_fit
    with use_fitted_root(root):
        cal, _ = fit_calibration(FIXTURE_WINDOW, fit, root=STORE, registry=registry, weeks=WEEKS)
    skipped = {"COA-07: travel origin unknown (no earlier season in the store)": 3, "G4: other": 1}
    write_window_file(replace(fit, calib=cal, calib_skipped=skipped), "rtest", tmp_path)
    got = unrated_training_games(tmp_path, "rtest", ["S2024"])
    assert got.rows() == [
        ("S2024", cal.n, "(rated)", cal.n),
        (
            "S2024",
            cal.n,
            "COA-07: travel origin unknown (no earlier season in the store)",
            3,
        ),
        ("S2024", cal.n, "G4: other", 1),
    ]
