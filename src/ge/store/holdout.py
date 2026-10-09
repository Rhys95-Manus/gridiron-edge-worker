"""BT-07b: the 2025 holdout lock, as Phase 3e enforces it.

2025 is never computed during development. The metric engine refuses a 2025 target season and
every Phase 3e fitter refuses a training window that reaches the holdout or its own test season
(user ruling 2026-10-07: the guard sits in the metric engine and the fitters; snapshot() itself
stays data access). Phase 8's frozen-tag ledger is the only future way in.

BT-07a: season S is predicted only from parameters fit on 2016 through S - 1; the live fit uses
2016-2024 for seasons after the holdout. Every season bound comes from params.yaml."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ge.config import load_params


class HoldoutReadError(RuntimeError):
    """BT-07b: a read of the holdout season, or of a season a fit must not see."""


def holdout_season() -> int:
    """BT-07b: the locked holdout season (params.yaml bt_01_holdout_season)."""
    return int(load_params().backtest.bt_01_holdout_season.value)


def refuse_holdout(season: int, what: str) -> None:
    """BT-07b: raise if `season` is the holdout."""
    if season == holdout_season():
        raise HoldoutReadError(
            f"BT-07b: {what} for season {season} refused; {season} is the locked holdout and is "
            "never computed during development (only Phase 8's frozen model tag may open it)"
        )


@dataclass(frozen=True)
class Window:
    """BT-02 / BT-07a: one fit's training seasons. `test_season` None is the live fit (for
    seasons after the holdout). Construction fails if a training season is the test season or
    later, or is the holdout or later."""

    name: str
    test_season: int | None
    seasons: tuple[int, ...]

    def __post_init__(self) -> None:
        for s in self.seasons:
            self.check_read(s)

    def check_read(self, season: int) -> None:
        """BT-07b / BT-07a: raise unless this fit may read `season`."""
        hold = holdout_season()
        if season >= hold:
            raise HoldoutReadError(
                f"BT-07b: fit {self.name} tried to read season {season}; seasons from the "
                f"{hold} holdout on are never read by a fit"
            )
        if self.test_season is not None and season >= self.test_season:
            raise HoldoutReadError(
                f"BT-07a: fit {self.name} tried to read season {season}; a fit uses only "
                f"seasons before its test season {self.test_season}"
            )

    @staticmethod
    def for_test_season(test_season: int) -> Window:
        bt = load_params().backtest
        first = int(bt.bt_01_first_training_season.value)
        return Window(f"S{test_season}", test_season, tuple(range(first, test_season)))

    @staticmethod
    def live() -> Window:
        """The fit on every training season, 2016 through the last test season."""
        bt = load_params().backtest
        first = int(bt.bt_01_first_training_season.value)
        last = int(bt.bt_01_last_test_season.value)
        return Window("live", None, tuple(range(first, last + 1)))

    @staticmethod
    def walk_forward() -> list[Window]:
        """S2021..S2024, then live."""
        bt = load_params().backtest
        first = int(bt.bt_01_first_test_season.value)
        last = int(bt.bt_01_last_test_season.value)
        return [Window.for_test_season(s) for s in range(first, last + 1)] + [Window.live()]

    @staticmethod
    def named(name: str) -> Window:
        if name == "live":
            return Window.live()
        if name.startswith("S") and name[1:].isdigit():
            return Window.for_test_season(int(name[1:]))
        raise ValueError(f"unknown fit window {name!r}: use S<season> or live")


def check_seasons(seasons: Iterable[int], window: Window) -> None:
    for s in seasons:
        window.check_read(s)
