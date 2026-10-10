# Phase 3e fit v2 — notes on the results

Hand-written beside the generated REPORT.md (`ge fit --as-of 2026-10-09T00:00:00Z --window all
--fit-version v2 --compare-to v1`). v2 is the fit Phase 4 reads (decisions log 2026-10-09); v1
stays in config/params_fitted/v1 for comparison. Data: nflverse; charting: FTN Data via nflverse.

## What v2 changes (BT-02 method, spec synced 2026-10-10)

1. Every stat with a slot or role prior is split-half tested on each player's residual from the
   slot prior fitted in the same window (WOPR: half WOPR minus the team-target-weighted mean
   slot-prior WOPR). Units without a slot, or whose slot has no fitted prior, are left out.
2. Every multi-cell stat (one k over several cells) is centred on each cell's league mean in the
   same season.
3. For multi-cell stats, N in the Fisher-z interval, the 30-entity minimum and the
   inverse-variance weights counts distinct entities (n = 288 team-seasons for team stats).
4. The half-life loss predicts toward the same prior k is measured around (0 on residual or
   centred rows).
5. PRJ-06's QB pool: QBs with at least 50% of the team's dropbacks in the previous game.

## Acceptance (tests/phase3/fit/test_v2_acceptance.py, live window, real data: 7 passed)

| check | 2026-10-09 diagnostic | v2 code, diagnostic seeds and entity-cell N | v2 fit (own seeds; ruling 3 N) |
|---|---|---|---|
| PLY-03 target share k | 58.1 | 58.1 | 59.6 |
| PLY-05 carry share k | 17.6 | 17.6 | 17.3 |
| PLY-18 band share k | 207.6 | 207.6 | 204.5 |
| PLY-23 side share k | 210.6 | 210.6 | 212.0 |
| PLY-28 band share k | 45.3 | 45.3 | 45.5 |
| PLY-29 side share k | 70.6 | 70.6 | 71.2 |
| PRJ-06 QB missed-game rate | 0.0815 (n 4,589) | — | 0.0815 (n 4,589) |

The fit's own values differ from the diagnostics only by split noise (different seed keys) and,
for the four multi-cell shares, by ruling 3 changing N.

## Reading the v1 → v2 changes

- **Rule 1 raises every slot-prior k**, because the role difference is no longer counted as the
  player's own signal: target, air, carry and opportunity shares, WOPR, yards per team dropback
  and aDOT rise 4–40×; band and side shares rise the most (PLY-18 4.5 → 204.5).
- **Rule 2 removes cell base rates and season drift**: the share-type cell stats rise sharply
  (OFF-13 share 19.8 → 437.9, OFF-12 lane share 22.8 → 96.3, PLY-16 lane share 19.2 → 60.3),
  and many cell efficiency splits that passed as signal in v1 now show **no detectable signal**
  (OFF-12 and DEF-03 EPA / YPC / explosive by lane, OFF-13 and DEF-09 EPA by cell, OFF-16 and
  DEF-15 sides, PLY-18 and PLY-23 EPA by band / side, PLY-25 in the earlier windows). Their
  apparent v1 signal was largely the gap between cells.
- **Usage half-life 8 → 6** in every window (efficiency stays 8; 12 in S2021–S2022), now that
  usage stats are predicted toward the slot prior instead of the league mean.
- **Stats v2 did not change still move a few percent** (e.g. OFF-05 +4%, DEF-01 pass −8%): the
  split seeds include the fit version, so v2 draws different random splits. Stats right at the
  edge of the 95% interval can flip status on that alone (DEF-11 YACOE: no signal in v1 live,
  656 in v2 live).

## Flags needing a decision

- **PLY-06, PLY-07, PLY-32, PLY-33 shares keep small k (5–11).** They shrink toward "his
  overall" share (a parent stat), not the slot prior, so rule 1 doesn't reach them; rule 2 only
  removes the cell means. Their k likely still counts role differences as signal. A spec choice:
  extend rule 1 to stats whose prior is his own overall share (residual from the slot prior of
  that overall stat), or leave as is.
- **PRJ-06 RB / WR / TE pools** (0.13 / 0.11 / 0.09) still use "played the previous game"
  (open item in the spec).
- **Seed keys include the fit version**, so every refit redraws splits; values near the
  no-signal edge can flip between versions. Keying seeds by stat and season only would make
  versions comparable split-for-split.
