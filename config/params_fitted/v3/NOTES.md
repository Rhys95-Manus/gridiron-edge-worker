# Phase 3e fit v3 — notes on the results

Hand-written beside the generated REPORT.md (`ge fit --as-of 2026-10-09T00:00:00Z --window all
--fit-version v3 --compare-to v2`). v3 replaces v2 as the fit the engine reads; v1 and v2 stay for
comparison. Data: nflverse; charting: FTN Data via nflverse.

## What v3 changes (spec synced 2026-10-10, decisions log "Phase 3e v3 rulings")

1. PLY-06 and PLY-07 (toward his overall opportunity share), PLY-33 (toward his PLY-03 target
   share) and PLY-32 (toward his red-zone target share) get k from each cell's value minus the
   player's own parent value in the same half; a cell that meets BT-02's minimum alone gets its
   own k (`fit:k/<spec>/<stat>/<cell>`), otherwise the pooled k applies; N = distinct players.
2. PLY-32's prior is his red-zone target share (his targets inside the 20 / team targets inside
   the 20), a new stat `red_zone_target_share` that shrinks toward his PLY-03 target share with a
   fitted k, also measured as a parent residual (ruling 2026-10-10).
3. Parent-residual stats enter the half-life fit as each cell unit minus his season parent share,
   predicted toward 0 (ruling 2026-10-10).
4. PRJ-06 RB / WR / TE pools: at least 25% of team offensive snaps in the previous game.
5. Split seeds keyed by stat key and season only, so v3 and later fits share splits stat for
   stat. That redraws every split once relative to v2: stats v3 doesn't otherwise change move by
   split noise this one time (e.g. DEF-01 all 1,059 → 926, PLY-11 −12%).

## Acceptance (tests/phase3/fit/test_v3_acceptance.py, live window, real data: 11 passed)

| check | 2026-10-09 diagnostic | v3 code with that diagnostic's v2 seed keys | v3 fit (own seeds) |
|---|---|---|---|
| PLY-06 inside_20 | 164.2 | 164.2 | 168.3 |
| PLY-06 inside_10 | 72.5 | 72.5 | 69.1 |
| PLY-06 inside_5 | 29.7 | 29.7 | 32.3 |
| PLY-07 third_down | 18.7 | 18.7 | 18.7 |
| PLY-07 two_minute | 31.5 | 31.5 | 31.1 |
| PLY-33 play_action | 84.7 | 84.7 | 84.2 |
| PLY-33 motion | 611.4 | 611.4 | 641.7 |
| PRJ-06 QB | 0.0815 (n 4,589) | — | 0.0815 (n 4,589) |
| PRJ-06 RB | 0.0616 (n 8,085) | — | 0.0616 (n 8,085) |
| PRJ-06 WR | 0.0641 (n 15,627) | — | 0.0641 (n 15,627) |
| PRJ-06 TE | 0.0477 (n 9,081) | — | 0.0477 (n 9,081) |

## PLY-32 by window (single cell `all`; no per-cell keys)

| window | end_zone_share k (prior: red-zone target share) | red_zone_target_share k (prior: PLY-03) |
|---|---|---|
| S2021 | 26.5 (n 290) | 118.7 (n 2,169) |
| S2022 | 27.7 (n 335) | 183.5 (n 2,624) |
| S2023 | 28.4 (n 363) | 184.1 (n 3,018) |
| S2024 | 27.8 (n 403) | 183.7 (n 3,440) |
| live | 27.9 (n 432) | 193.0 (n 3,859) |

v2's end-zone share k was 5.3 against PLY-06's red-zone opportunity share, which counts carries;
against a targets-only parent it is about 28, stable across windows.

## Flags

- PLY-33's motion cell is borderline: no detectable signal alone in S2023, fitted (≈640) in the
  others; the pooled PLY-33 k (≈187) applies only where a cell is below the minimum alone.
- DEF-04 epa_diff became "no detectable signal" in S2022, S2023 and live after the reseed (it was
  ≈685 in v2 live): an edge case the seed change exposed, not a method change.
