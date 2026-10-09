# Phase 3e fit v1 — notes on the results

Written by hand next to the generated REPORT.md (`ge fit --as-of 2026-10-09T00:00:00Z --window all
--fit-version v1`). REPORT.md lists every fitted value beside its initial value with seasons and
n; this file explains the values that moved more than 50% from the initial guess, and flags what
needs a decision. Data: nflverse; charting: FTN Data via nflverse.

## Why values moved more than 50%

The initial k values were "deliberately conservative guesses" (G1). The fitted ones are stable
across all five windows (each window adds a season and the values barely move), so the moves are
systematic, not noise. They fall into five groups.

1. **Shares of team opportunity shrink far less than guessed (k down 60–95%).** PLY-03 target
   share 60 → ~10, PLY-05 carry share 40 → ~2.7, PLY-04, 06, 07, 08, 16, 18 / 23 / 28 / 29 band
   shares, 27, 32, 33, OFF-13 cell share. Who gets the ball is a role: a WR1 and a WR4 differ
   by far more than any one game's noise, so a split half of a player's season already agrees
   with the other half after a few games. **Caveat:** split-half reliability is measured around
   the league mean, but section 4 shrinks these stats toward the *slot* prior, which already
   explains most of the role difference. Within a slot the true spread is smaller, so the k that
   fits G1's weighting toward a slot prior is larger than these values. Flagged below.
2. **Defense stats need much more data than guessed (k up 60–1000%).** DEF-01 EPA allowed 250 →
   ~1000, DEF-04 vs position 60 → 320–665, DEF-06 explosive allowed 300 → ~1400, DEF-09, DEF-15.
   What a defense allows depends heavily on who it faced and on offense-driven variance, so
   season halves of a defense agree much less than halves of an offense (OFF-01 stays near its
   guess, 250 → ~320). This matches the common finding that defensive efficiency is less stable
   than offensive.
3. **Efficiency splits by situation, cell or side are noisier than guessed (k up 60–230%).**
   OFF-03 down/zone cells, OFF-12 success / EPA by lane, OFF-13 EPA by cell, OFF-16 by side,
   OFF-14 red-zone pass share, PLY-10, PLY-23 EPA by side, PLY-25 formation splits. Splitting a
   team's or player's plays into cells divides the signal more than the guesses assumed.
4. **Tendencies stabilise faster than guessed (k down 50–75%).** OFF-07 motion rate, OFF-09
   shotgun rate, OFF-10 and COA-04 pace, DEF-05 blitz rate, PLY-21 time to throw, PLY-28 aDOT,
   PLY-31 separation, OFF-12 explosive rate, DEF-17 sacks share. These are scheme or style
   choices that a play-caller repeats every week, so a few dozen plays already identify them.
5. **Half-lives are longer (usage 3 → 8 games, efficiency 6 → 8, 12 in the two earliest
   windows).** With the fitted k values, next-game prediction is best when older games keep more
   weight: week-to-week changes in role and efficiency are smaller than the initial h assumed.
   Both are grid values; 8 is the grid point between 6 and 12.

Other notable values: COA-02 over-expected k 30 → ~120 (no detectable signal in S2021–S2022);
PLY-14 return factor 0.85 → ~0.93 (n 546–1161 returns); MTC-03 OL-absence factor 1.10 → 1.04–1.07
per missing starter; G6 penalty 10^2.5 ≈ 316 in every window, the same scale as OFF-01's fitted
k (~300 plays), as G1 and G6 should agree.

## Flags needing a decision

- **Share k vs slot prior (group 1).** BT-02's split-half measures reliability around the
  league, while section 4 shrinks shares toward the slot average. If the k should match the
  prior actually used, the fix is a spec choice: split-half on the residual from the slot prior
  (k would rise), or keep the league-based k. Fitted values follow the spec as written.
- **PRJ-06 QB missed-game rate ~17–18%.** The approved pool ("played the team's previous
  game", any offensive snap) includes backups who take a snap in mop-up and then sit, so the
  rate overstates a starter's risk. A starter-only pool (e.g. slot holders, or a snap-share
  floor) would need a spec rule.
- **Stats flipping between "no detectable signal" and fitted across windows** (COA-02
  over-expected, DEF-11 yacoe, OFF-13 cpoe, PLY-11 ryoe, DEF-12 ypc, DEF-04 counting stats in
  S2021): their r sits right at the edge of the 95% interval. Each window applies BT-02 as
  written; the flips are reported, not smoothed.
- **Missing by BT-02's own minimum** (2m = 50 units): per-game units can't reach it in one
  season — PLY-01/02 snap share, OFF-11 plays per game, PLY-22 designed runs per game (no spec k:
  stays unshrunk and its shrink raises), DEF-17 interceptions, PLY-30 contested catches; also
  COA-03 two-point rate and DEF-16 end-zone TD rate. Spec-k stats keep their initial k.
- **Role priors missing for thin slots** ("N player-seasons < 30"): mostly stats where a slot
  rarely holds the stat (e.g. QB-only stats by WR slots), which never apply.
