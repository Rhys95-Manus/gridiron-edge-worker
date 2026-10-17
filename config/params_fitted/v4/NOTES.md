# Phase 3e fit v4 — notes on the results

Hand-written beside the generated REPORT.md (`ge fit --as-of 2026-10-09T00:00:00Z --window all
--fit-version v4 --compare-to v3`, run 2026-10-17 17:04-17:39 UTC, exit 0). v4 is v3 plus PLY-35's
k (Phase 3f). It is **not** the active fit: config/params_fitted/active.yaml stays v3 until the user
switches it. Data: nflverse; charting: FTN Data via nflverse; expected points: ffopportunity
(ffverse) via nflverse; data license not stated by the source.

## What v4 adds (spec synced 2026-10-16, decisions log)

- `fit:k/PLY-35/<stat>` for receptions, receiving_yards, rushing_yards and tds: split-half on
  per-game centred gaps (unit player-game, entity player-team stint in a season, prior 0) on
  PLY-35's own grid m ∈ {4, 6, 8} games; BT-02's other rules unchanged.
- PLY-35 is left out of the G3 half-life fit, so no other fitted value can move.
- The report adds a PLY-35 section (k per window, split-half r for 2016-2020, inside
  ffopportunity's stated training data, and for 2021 onward) and the 2026-vs-2024 gap check.

## v3 vs v4

Every key other than PLY-35's is identical in every window: same value, n, seasons, method, and the
same no-signal and missing entries (checked key by key, and REPORT.md's comparison lists only the
20 PLY-35 keys). File metadata differs only in `attribution` (the extended line), `code_commit`
and `data_digest` (the fit now also reads ff_opportunity, which the digest records).

## PLY-35 k (player-games)

| window | receptions | receiving_yards | rushing_yards | tds |
|---|---|---|---|---|
| S2021 (2016-2020) | 31.7 | 49.1 | 28.8 | no signal |
| S2022 (2016-2021) | 32.2 | 37.2 | 26.4 | no signal |
| S2023 (2016-2022) | 37.7 | 40.4 | 29.6 | no signal |
| S2024 (2016-2023) | 40.9 | 37.9 | 28.0 | no signal |
| live (2016-2024) | 41.3 | 36.7 | 24.4 | no signal |

k of 25-50 games means heavy shrinkage: after 8 games a player keeps roughly 8 / (8 + k), about
15-25%, of his centred gap. TDs over expected show no detectable signal in any window, so PLY-35's
TD value shrinks fully to 0.
