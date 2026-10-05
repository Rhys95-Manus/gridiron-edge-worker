# Gridiron Edge — Model Spec v1

Sep 27, 2026 · @Rhys

## 0. How to use this spec

No metric goes into Base44 until it has a row here with a definition, formula, source, minimum sample and shrinkage rule. Attach this doc to every Base44 prompt and cite the metric ID (for example `OFF-07`) the prompt implements.

**Status of every metric starts at SPEC.** A metric moves to BUILT when deterministic backend code computes it, and to VERIFIED only after an acceptance test passes on real nflverse data for at least one full past season. Anything Base44 reports as done but that has not passed its test stays BUILT.

**v1 scope.** NFL regular season and playoffs. Modeled: game winner, spread, total, anytime TD, first TD, 2+ TDs, yardage and passing-TD props, same-game and multi-game combos, season futures. Tracked but not modeled: mentions and novelty markets.

**Hard rules the code enforces, not the model.** All math runs in backend functions or scripts. The LLM layer only writes the matchup story from numbers the code hands it, and every claim in that story must reference a metric ID and its sample size. If a number is missing, the story says so.

**Metric ID prefixes.** `DATA` sources, `OFF` team offense, `DEF` team defense, `PLY` player, `COA` coaching, `MTC` matchup, `PRJ` projection, `EDG` edge/decision, `BT` backtest.

## Global conventions (every metric uses these)

**G1. Shrinkage toward league average.** Every rate or per-play average is blended with a prior (the league average, or a more specific prior noted in the metric) weighted by a pseudo-sample of k plays. With n real plays, the observed rate counts n and the prior counts k.

```latex
\text{shrunk} = \frac{n \cdot \text{observed} + k \cdot \text{prior}}{n + k}
```

k is the metric's *stabilization point*: the sample size at which a split-half correlation of the metric reaches 0.5, estimated from 2016–2024 nflverse data in Phase 3e (BT-02 core; 2025 is the BT-07b holdout). Until BT-02 runs, the k values in this spec are labelled **initial** and are deliberately conservative guesses, not published facts. At n = k the estimate is exactly halfway between observed and league average.

**G2. Minimum sample.** Below the listed minimum, the metric is still computed (fully shrunk) but the UI shows it greyed out and the matchup story may not cite it as a strength or weakness.

**G3. Recency weighting.** Each play gets weight w by how many games ago it happened (g = 0 for the most recent game). Half-life h is set per metric; initial values: usage metrics h = 3 games, efficiency metrics h = 6 games. Weighted sample size n\_eff = (Σw)² / Σw² replaces n in G1.

```latex
w = 0.5^{\,g/h}
```

**G4. Prior-season carryover.** Weeks 1–4 use last season's shrunk value as the prior instead of league average, regressed a further 1/3 toward league average for teams with a new play-caller or quarterback (COA-01, PLY-01). Until COA-01 has rows for a season, a head-coach change in the schedules data stands in for a play-caller change; a new quarterback means the team's most-dropback passer differs from last season's. Relocated teams keep their history, matched by franchise using the nflverse teams table.

**G5. Neutral game script.** A play is neutral when nflverse `wp` (win probability for the offense) is between 0.20 and 0.80, and it is not inside the final 2:00 of either half. Tendency metrics (pass rate, pace) use neutral plays only.

**G6. Opponent adjustment.** Team efficiency is adjusted with a weighted ridge regression over all plays: EPA of each play = league intercept + offense rating + defense rating + home term + error. Ridge penalty is tuned by cross-validation in BT-02. Offense and defense ratings are the adjusted numbers.

**G7. Garbage time and kneels.** Excluded from all efficiency and tendency metrics: kneels, spikes, plays with `wp` < 0.05 or > 0.95 in the 4th quarter, and penalties with no play (`play_type` = no\_play) unless the metric says otherwise.

### Glossary (plain English)

| Term | What it means |
| --- | --- |
| EPA (expected points added) | How many points a play added to the offense's expected score, given down, distance, field position and time. A 3-yard gain on 3rd-and-2 is worth more than a 3-yard gain on 3rd-and-10. nflverse computes it per play. |
| Success rate | Share of plays with EPA > 0. Less noisy than EPA because one 70-yard play can't dominate it. |
| Explosive play | Our definition: run of 10+ yards or completed pass of 20+ yards. |
| PROE (pass rate over expected) | Actual pass rate minus what a model expects given down, distance, field position, score and time. nflverse provides `xpass` per play; PROE = mean(pass − xpass). Positive = passes more than situation dictates. |
| aDOT | Average depth of target: mean air yards per target. |
| YPRR (yards per route run) | Receiving yards ÷ routes run. Best single efficiency number for receivers. |
| CROE (catch rate over expected) | Catches minus expected catches based on throw difficulty, per target. |
| RYOE (rushing yards over expected) | Rushing yards minus what Next Gen Stats expects from defender positions at handoff. |
| Closing line value (CLV) | Our entry price vs the last traded price before kickoff. Buying YES at 40¢ when it closes at 45¢ is +5¢ CLV. |
| Kelly criterion | Formula for the stake that maximizes long-run growth given your edge; we use one quarter of it. |
| Brier score / log loss | Accuracy scores for probability forecasts. Lower is better. |

## 1. Data sources

The free stack (nflverse + Kalshi public API + National Weather Service) covers team, coaching and most player metrics, but **three things the spec asks for are not in free data in-season: routes run, receiver alignment (slot/wide), and man vs zone coverage.** Those metrics are marked PAID below and replaced with free proxies in v1 until you decide to license a charting feed.

| ID | Source | What we pull | Access and license | Cost | Freshness | Gaps and cautions |
| --- | --- | --- | --- | --- | --- | --- |
| DATA-01 | [nflverse play-by-play](https://nflreadr.nflverse.com/) via nflreadr (R) or [nflreadpy](https://pypi.org/project/nflreadpy/) (Python) | `down`, `ydstogo`, `yardline_100`, `qtr`, `game_seconds_remaining`, `score_differential`, `wp`, `epa`, `success`, `pass`, `rush`, `run_location`, `run_gap`, `pass_location`, `pass_length`, `air_yards`, `yards_after_catch`, `cp`, `xpass`, `xyac_mean_yardage`, `receiver_player_id`, `rusher_player_id`, `touchdown`, `shotgun`, `no_huddle`, `posteam`, `defteam` | Open download from GitHub releases; nflverse data is broadly CC-BY 4.0 (attribution required) | Free | Updated after games (check the nflverse automation status page) | Use nflreadpy, the maintained Python port of nflreadr; treat nfl\_data\_py as legacy. `run_location`/`run_gap` are scorer-charted and noisy: gap is blank on middle runs |
| DATA-02 | [FTN charting via nflverse](https://nflreadr.nflverse.com/reference/load_ftn_charting.html) | `is_play_action`, `is_rpo`, `is_motion`, `is_screen_pass`, `n_blitzers`, `n_pass_rushers`, `n_defense_box`, `n_offense_backfield`, `is_drop`, `is_catchable_ball`, `is_contested_ball` | CC-BY-SA 4.0, attribution to "FTN Data via nflverse" required; 2022 onward | Free | Charted within about 48 hours after each game | No routes, no receiver alignment, no coverage shell. Share-alike: if you ever publish derived data, it must carry the same license |
| DATA-03 | nflverse participation (personnel) | Offensive and defensive personnel per play | CC-BY-SA 4.0 via FTN; [FTN now provides it only after each season ends](https://cran.r-project.org/web/packages/nflreadr/news/news.html) | Free | **Post-season only** | Usable for backtests and priors, not live weekly personnel |
| DATA-04 | nflverse snap counts, rosters, depth charts, schedules, injuries | Offense/defense snap %, roster positions, depth order by date, game times and stadiums, injury report status and practice participation, and the nflverse players table as a player ID crosswalk (gsis\_id ↔ pfr\_id; snapshots expose only the IDs), and the nflverse teams table for franchise IDs (team\_abbr ↔ team\_id; snapshots expose only the IDs), and nflverse combine data for PLY-34 (height, weight, 40-yard dash, vertical, broad jump, 3-cone, shuttle) | CC-BY 4.0 | Free | Snaps after games; depth charts by date; injuries on NFL report days | Depth charts now sourced from ESPN, per nflreadr release notes. Verify the injury feed is updating in-season before relying on it |
| DATA-05 | Next Gen Stats via nflverse | Weekly player aggregates: time to throw, average separation, cushion, rushing yards over expected | CC-BY 4.0 as distributed by nflverse | Free | Weekly | Player-week aggregates only, not per play, so no RYOE by gap |
| DATA-06 | Weather: National Weather Service API (primary) | Hourly forecast wind speed, gusts, precipitation probability and amount, temperature at stadium coordinates | US government data, public domain; requires a User-Agent header | Free | Hourly | US stadiums only. International games need DATA-07 |
| DATA-07 | Weather: [Open-Meteo](https://open-meteo.com/en/terms) (backup, international games) | Same fields, plus historical weather for backtests | Free tier is non-commercial only; [commercial use needs a paid plan](https://open-meteo.com/en/terms) | Paid if commercial | Hourly | A personal-use tool is arguably non-commercial, but anything run under AI Wealth Builders or sold to others is commercial. Decide before building |
| DATA-08 | [Kalshi public market data API](https://docs.kalshi.com/getting_started/quick_start_market_data) | Series, events, markets, prices, `orderbook` (bids on YES and NO), trades, candlesticks, historical markets and trades | Public read endpoints need no API key | Free | Real time (REST poll; WebSocket for live book) | The order book lists **bids only** on each side; the YES ask = $1 − best NO bid. Prices return as dollar strings in `_dollars` fields |
| DATA-09 | Kalshi fee schedule | Taker and maker multipliers by series | [Official fee schedule PDF](https://kalshi.com/docs/kalshi-fee-schedule.pdf), effective July 7, 2026 | Free | Re-check weekly | Multipliers differ by series (see EDG-02) |
| DATA-10 | Sportsbook consensus odds (optional) | Main lines, player props, closing lines | Licensed APIs, for example [The Odds API](https://the-odds-api.com/sports/nfl-odds.html) (historical props from May 2023 on paid plans) | Paid for history | Minutes | Used as a sanity check and a CLV benchmark, never scraped from sportsbook sites |
| DATA-11 | Charting feed with routes, alignment, coverage (optional) | Routes run, slot/wide/inline alignment, man/zone per play | Commercial licenses (PFF, FTN Data, Sports Info Solutions); pricing not verified | PAID | Weekly | Needed for PLY-03, PLY-05, DEF-05 at full fidelity |
| DATA-12 | Inactives and breaking news | Official inactives (about 90 minutes before kickoff), late scratches, weather updates | No free, terms-clean real-time feed identified | Open question | Minutes | This is the "fast news" edge. v1 relies on you entering news manually into the app with a timestamp |
| DATA-13 | Wikidata | Stadium coordinates (coordinate location), for every stadium in the nflverse schedules | Open data, CC0 (public domain); each row keeps its Wikidata item URL as source\_url | Free | Re-run when a new stadium appears in schedules | Community-edited, so you spot-check three stadiums on a map. Roof type comes from nflverse schedules per game; time zone is computed from the coordinates |

**Rules.** No scraping of any site whose terms forbid it, including sportsbooks and PFF. Every nflverse-derived screen shows the attribution line "Data: nflverse; charting: FTN Data via nflverse." All raw pulls are stored with a pull timestamp so backtests can reconstruct what was known at the time.

## 2. Team offense profile

Every offense metric is computed per team from DATA-01/02 play-by-play, season to date, recency-weighted (G3), with garbage time removed (G7). "Qualifying play" means `pass == 1` or `rush == 1` (sacks and scrambles count as pass plays). Minimum samples are the point below which the metric is greyed out (G2); k is the shrinkage pseudo-sample (G1), all **initial** until BT-02.

| ID | Metric and plain meaning | Formula | Data fields | Min n | Shrink (k, prior) | Feeds |
| --- | --- | --- | --- | --- | --- | --- |
| OFF-01 | EPA per play, overall / pass / run. Points added per snap | mean(`epa`) over qualifying plays; pass and run subsets; opponent-adjusted by G6 | `epa`, `pass`, `rush` | 150 plays (100 pass, 80 run) | k = 250 overall, 200 pass, 300 run; prior league mean | Winner, spread, total, all props via PRJ-01 |
| OFF-02 | Success rate, overall / pass / run. How often a play keeps the offense on schedule | mean(`success`) | `success` | 150 plays | k = 150; prior league mean | Winner, spread, total |
| OFF-03 | EPA and success by down and field zone | OFF-01/02 within cells: downs {1, 2, 3–4} × zones {own 1–20: `yardline_100` ≥ 80; open field; red zone ≤ 20; goal-to-go} | + `down`, `yardline_100`, `goal_to_go` | 30 plays per cell | k = 100; prior = team's shrunk OFF-01/02 | Total, TD markets |
| OFF-04 | Early-down pass rate (neutral). How often they throw on 1st and 2nd down when the game is close | mean(`pass`) on downs 1–2, neutral (G5) | `pass`, `down`, `wp` | 80 plays | k = 60; prior league mean | Pass/rush yardage props, total |
| OFF-05 | Pass rate over expected (neutral) | mean(`pass` − `xpass`), neutral plays | `pass`, `xpass` | 100 plays | k = 100; prior 0 | Passing and receiving props |
| OFF-06 | Play-action rate | mean(`is_play_action`) over dropbacks | FTN | 60 dropbacks | k = 80; prior league mean | Passing yards, MTC-02 |
| OFF-07 | Pre-snap motion rate | mean(`is_motion`) over qualifying plays | FTN | 80 plays | k = 80 | Context for MTC-02 |
| OFF-08 | RPO rate | mean(`is_rpo`) over qualifying plays | FTN | 80 plays | k = 80 | Context for rush/pass mix |
| OFF-09 | Shotgun rate (under center = 1 − shotgun) | mean(`shotgun`) | `shotgun` | 80 plays | k = 60 | Run-scheme context, MTC-01 |
| OFF-10 | Neutral pace. Seconds from one snap to the next when the clock is running | mean of Δ`game_seconds_remaining` between consecutive plays in the same drive and quarter; drop pairs where the prior play was incomplete, out of bounds, a timeout, penalty or turnover; cap Δ at 45 s | `game_seconds_remaining`, `drive`, `incomplete_pass`, `out_of_bounds`, `timeout`, `penalty` | 60 pairs | k = 80 pairs; prior league mean | Play count in PRJ-02, total |
| OFF-11 | Plays per game | qualifying plays ÷ games | as above | 3 games | k = 4 games; prior league mean | Total, all volume props |
| OFF-12 | **Directional run grid.** Carries, yards/carry, EPA/carry, success rate, explosive rate (10+ yds) in 7 cells: left end, left tackle, left guard, middle, right guard, right tackle, right end | Group designed runs (`rush == 1`, `qb_scramble == 0`, no kneels) by `run_location` × `run_gap`; middle has no gap. Left/right are from the offense's view | `run_location`, `run_gap`, `yards_gained`, `epa`, `success` | 25 carries per cell | k = 60 (success), 100 (EPA, YPC), 150 (explosive); prior = team's own shrunk run value, which is itself shrunk to league | Rushing yards, RB anytime TD, MTC-01 |
| OFF-13 | **Pass map.** Target share, EPA/target, completion over expected in 12 cells: `pass_location` {left, middle, right} × depth {behind line: `air_yards` < 0; short 0–9; intermediate 10–19; deep 20+} | Per cell: targets ÷ team targets; mean(`epa`); mean(`complete_pass` − `cp`) | `pass_location`, `air_yards`, `epa`, `complete_pass`, `cp` | 20 targets per cell | k = 60 targets; prior = team's shrunk pass value | Receiving yards, MTC-02 |
| OFF-14 | Red zone and goal-to-go. Run/pass split and TD rate per trip inside the 20, 10 and 5 | pass share of plays in each zone; TDs ÷ drives reaching the zone | `yardline_100`, `goal_to_go`, `drive`, `touchdown` | 20 plays; 10 trips | k = 25 plays; k = 20 trips; prior league | Anytime/first TD, total |
| OFF-15 | Pass protection. **True pressure rate is not in free data.** v1 proxy: sack rate and QB-hit rate allowed per dropback | (sacks) ÷ dropbacks; `dropbacks with a sack or QB hit ÷ dropbacks (nflverse sets qb_hit on most sacks)`; shown beside NGS time to throw because quick-throwing QBs hide weak lines | `sack`, `qb_hit`, NGS time to throw | 100 dropbacks | k = 200; prior league | Passing props, MTC-03 |
| OFF-16 | Run blocking by side. Proxy: success rate and stuff rate (gain ≤ 0) on left vs right runs. Mixes blocking with the runner's skill; labelled as a proxy | per side: mean(`success`); share with `yards_gained` ≤ 0 | `run_location`, `yards_gained`, `success` | 40 carries per side | k = 80; prior team's overall | MTC-01 |
| OFF-17 | Offensive-line continuity and injuries | Starters = 5 OL with most offensive snaps in the last 3 games; continuity = share of the team's games this season in which all 5 played ≥ 50% of offensive snaps (per-snap participation is post-season only); plus current injury-report status for each | Snap counts, rosters, injuries (DATA-04) | none (a count) | none | Adjusts OFF-15/16 in MTC-03 |

**Build order.** OFF-01, 02, 04, 05, 10, 11 first: they drive the game simulation. OFF-12 and OFF-13 second: they are the matchup edges. Everything else is context.

## 3. Team defense profile

Defense metrics mirror offense: same play filters, recency weights and shrinkage, computed on plays where the team is `defteam`. **All directions are stored in the offense's frame** ("runs to the offense's left"), so a defense's number lines up directly against the opponent's OFF-12 cell without flipping sides by hand.

| ID | Metric and plain meaning | Formula | Data fields | Min n | Shrink (k, prior) | Feeds |
| --- | --- | --- | --- | --- | --- | --- |
| DEF-01 | EPA per play allowed, overall / pass / run | mean(`epa`) against; opponent-adjusted by G6 | `epa`, `defteam` | 150 plays | k = 250 / 200 / 300; prior league | Winner, spread, total, PRJ-01 |
| DEF-02 | Success rate allowed | mean(`success`) against | `success` | 150 plays | k = 150 | Winner, spread, total |
| DEF-03 | **Directional run defense.** Carries, yards/carry, EPA, success and explosive rate allowed in the same 7 cells as OFF-12 | OFF-12 formula on runs against | `run_location`, `run_gap` | 25 carries per cell | k = 60 / 100 / 150; prior = defense's shrunk overall run value | Rushing yards, RB TD, MTC-01 |
| DEF-04 | **Defense vs position** (RB, TE, WR) receiving targets, receptions, yards, TDs and EPA/target allowed, opponent-adjusted | For each stat: ratio = Σ actual allowed ÷ Σ expected, where expected = what each opponent's players at that position average in their other games. Ratio 1.20 = allows 20% more than those offenses usually produce. EPA/target is reported as a difference (allowed − expected), shrunk toward 0 with the same k | `receiver_player_id` joined to roster position | 4 games and 40 targets to the position | k = 60 targets; prior ratio 1.00 | Receiving yards, receptions, TD props, MTC-02 |
| DEF-04b | Slot WR vs wide WR split | Needs receiver alignment per play | DATA-11 only | — | — | **PAID; not in v1** |
| DEF-05 | Pass rush and blitz | Blitz rate = share of dropbacks with `n_blitzers` ≥ 1; mean rushers; mean box count; sack rate and QB-hit rate forced (dropbacks with a sack or QB hit ÷ dropbacks) (true pressure rate is not in free data) | FTN `n_blitzers`, `n_pass_rushers`, `n_defense_box`; pbp `sack`, `qb_hit` | 100 dropbacks | k = 150; prior league | MTC-03, passing props |
| DEF-05b | Man vs zone tendency | Needs coverage charting | DATA-11 only | — | — | **PAID; not in v1** |
| DEF-06 | Explosive plays allowed | share of runs 10+ yds and completions 20+ yds against | `yards_gained`, `complete_pass` | 150 plays | k = 300; prior league | Yardage props (right tail), total |
| DEF-07 | Red-zone TD rate allowed | TDs ÷ opponent drives reaching the 20 | `yardline_100`, `drive`, `touchdown` | 10 trips | k = 20 trips; prior league | TD markets, total |
| DEF-08 | Missing defenders | Display flag for any starter (≥ 60% defensive snaps over the last 3 games) listed Out or Doubtful. Numeric adjustment only when the team has ≥ 200 defensive plays with and without him this season: adj = shrunk(EPA without − EPA with), k = 400 plays toward 0 | Snap counts, injuries, pbp | 200 plays each way | k = 400; prior 0 effect | MTC context, story |

**Honest caution on DEF-04.** Defense-vs-position numbers are among the noisiest in football: a single big game by one tight end can swing a defense's TE ratio by 30% or more early in the season. The ratio's opponent adjustment and the k = 60 shrinkage exist for exactly this reason. The app must never describe a defense as "weak against TEs" until the 4-game, 40-target minimum is met.

**Honest caution on DEF-08.** On/off numbers for one defender are confounded by who the defense played in those games. Most absences will stay display-only in v1, which is correct: an unproven adjustment is worse than none.

## 4. Player profile

Usage drives props far more than efficiency, so usage metrics get short half-lives (h = 3 games) and efficiency metrics get heavy shrinkage. **Player metrics shrink toward a role prior, not the league average:** last season's shrunk value if the player has the same team and play-caller; otherwise the league average for his depth-chart slot (WR1, WR2, WR3, TE1, RB1, RB2), computed from 2016–2024 data in Phase 3e (BT-02 core).

| ID | Metric and plain meaning | Formula | Data fields | Min n | Shrink (k, prior) | Feeds |
| --- | --- | --- | --- | --- | --- | --- |
| PLY-01 | Snap share. Share of team offensive snaps he played | player offense snaps ÷ team offense snaps | Snap counts (DATA-04) | 2 games | k = 2 games; role prior | All props |
| PLY-02 | Route participation. Share of team dropbacks where he ran a route | Needs routes (DATA-11). **v1 proxy:** snap share (PLY-01), flagged as proxy | — | — | — | Receiving props |
| PLY-03 | Target share | targets ÷ team targets; targets = pass plays with his `receiver_player_id` | `receiver_player_id` | 3 games | k = 60 team targets; role prior | Receiving yards, receptions, TD |
| PLY-04 | Air-yards share and WOPR. WOPR (weighted opportunity rating) combines targets and depth into one usage number | air share = Σ his `air_yards` ÷ team Σ `air_yards`; WOPR = 1.5 × target share + 0.7 × air share | `air_yards` | 3 games | k = 60 team targets | Receiving yards |
| PLY-05 | Carry share | designed carries ÷ team designed carries | `rusher_player_id`, `qb_scramble` | 3 games | k = 40 team carries; role prior | Rushing yards, TD |
| PLY-06 | Red-zone and goal-line share. His share of team carries + targets inside the 20, 10 and 5 | per zone: (his carries + targets) ÷ team (carries + targets) | `yardline_100` | 8 team opportunities in zone | k = 20 team opportunities; prior = his overall opportunity share (carries + targets) | Anytime, first and 2+ TD |
| PLY-07 | Third-down and two-minute role | his share of team targets + carries on 3rd down, and in the last 2:00 of each half | `down`, `half_seconds_remaining` | 15 team opportunities | k = 30; prior = his overall share | Receiving props for pass-catching RBs |
| PLY-08 | Yards per route run | Needs routes (DATA-11). **v1 proxy:** receiving yards ÷ team dropbacks in games he played | `yards_gained`, dropbacks | 3 games | k = 150 team dropbacks; role prior | Receiving yards |
| PLY-09 | Yards after catch over expected | mean(`yards_after_catch` − `xyac_mean_yardage`) per reception | pbp | 30 receptions | k = 60 receptions; prior 0 | Receiving yards tail |
| PLY-10 | Catch rate over expected. Also reflects QB accuracy, so it is context, not a driver | mean(`complete_pass` − `cp`) per target | `cp` | 40 targets | k = 80 targets; prior 0 | Receptions |
| PLY-11 | Rushing yards over expected per carry | NGS weekly value, carry-weighted | NGS (DATA-05) | 50 carries | k = 100 carries; prior 0 | Rushing yards |
| PLY-12 | Alignment (slot / wide / inline / backfield) | Needs alignment (DATA-11). v1 uses roster position only | — | — | — | **PAID; not in v1** |
| PLY-13 | Trend and role-change flag | L3 and L5 values of PLY-01/03/05/06 vs season. Flag a role change when \|L3 − season\| > 2 × √(p(1 − p) ÷ n), with p = season share and n = team opportunities in the last 3 games | derived | 3 games | none (it is a test) | Every prop; shortens h to 1.5 games when flagged |
| PLY-14 | Injury and practice status, return-from-injury limit | Game status (Out / Doubtful / Questionable) and Wed–Fri practice (DNP / Limited / Full). A player on the practice report with no game designation is expected to play once his team's final report is in the feed. If a team's final report has not reached the feed by decision time (the nflverse feed can lag the league's report), its listed players' availability comes from practice participation using base rates fit in BT-02, the player is flagged "status unknown", and no recommendation is made on his props until a status or a ManualNews entry arrives. First game back after missing 2+ games: projected snap share × return factor (**initial 0.85**, estimated in BT-02) | Injuries (DATA-04) | none | none | Every prop; PRJ-02 |
| PLY-15 | Opportunity redistribution when a teammate is out | If the team has ≥ 2 games this season without player X under the same QB and play-caller: observed shares in those games, shrunk (k = 2 games) toward the default rule. Default rule: X's vacated share goes to remaining players in proportion to their current shares, with players at X's position weighted 2× | pbp, injuries | 2 games without X | k = 2 games toward default rule | All props on that team |
| PLY-16 | Running back directional profile. Where this back runs and how well he does it, in the same 7 lanes as OFF-12. The cutback skill itself needs tracking data; PLY-11 is the closest free signal | Per back: share of his designed carries in each cell; success rate and EPA/carry in each cell | rusher\_player\_id, run\_location, run\_gap, success, epa | 15 carries per cell | k = 40 carries; prior = his team's shrunk OFF-12 value for that cell | Rushing yards, RB TD; MTC-01 uses his shares and values instead of the team's when he is the projected ball carrier |
| PLY-17 | Quarterback vs the blitz. How much better or worse this QB is when the defense sends extra rushers | Blitz gap = EPA per dropback with n\_blitzers ≥ 1 minus EPA per dropback with n\_blitzers = 0; same for sack rate | FTN n\_blitzers; pbp epa, sack, passer\_player\_id | 60 blitzed dropbacks | k = 120 blitzed dropbacks; prior = league-average blitz gap | Passing props; MTC-03 applies his shrunk blitz gap in proportion to the opponent's blitz rate (DEF-05) |

**What PLY-15 cannot do.** It cannot tell you how a backup who has never played will be used. When a vacated role goes to someone with under 50 career snaps, the app shows the projection but marks it "low confidence" and caps the stake at 0.5%.

## 5. Coaching profile

nflverse has head coaches in its schedules but **does not track coordinators or who calls plays**, so COA-01 is a hand-maintained registry where every row needs a source link and a date. Coaching samples are tiny (one team plays about 17 games a season), so most coaching effects are estimated league-wide and applied to every team, with team-specific numbers shown for context only.

| ID | Metric and plain meaning | Formula | Data fields | Min n | Shrink (k, prior) | Feeds |
| --- | --- | --- | --- | --- | --- | --- |
| COA-01 | Staff and play-caller registry | Manual rows: team, HC, OC, DC, offensive play-caller, defensive play-caller, effective date, source URL. A play-caller change resets OFF-04 through OFF-10 to the new caller's prior (his history elsewhere, or league average); efficiency metrics are not reset | Manual; HC from schedules | every row sourced | — | All tendency metrics |
| COA-02 | 4th-down aggressiveness over expected | mean(went for it − p\_go) on 4th downs, where p\_go comes from a logistic model fit on league data using `ydstogo`, `yardline_100`, `score_differential`, `game_seconds_remaining` | pbp `down == 4`, `play_type` | 20 fourth downs | k = 30; prior 0 | Total, TD markets, drive sim in PRJ-02 |
| COA-03 | 2-point attempt rate | 2-point tries ÷ touchdowns | `two_point_attempt` | 10 TDs | k = 30; prior league | Total (exact-score effects), PRJ-02 |
| COA-04 | Script response. Pass rate over expected and pace when leading vs trailing | OFF-05 and OFF-10 on plays with `wp` > 0.80 (leading) and < 0.20 (trailing), not garbage time | `wp` | 40 plays per bucket | k = 80; prior league value for that bucket | Play-by-play sim in PRJ-02, props in lopsided games |
| COA-05 | Scheme tendency cluster. Not a scheme label, which free data can't give | outside-run share (end + tackle cells of OFF-12), under-center rate, play-action rate, motion rate, shown as percentiles | OFF-06/07/09/12 | same as inputs | as inputs | Story context, MTC-01 |
| COA-05b | Defensive coverage family | Needs coverage charting | DATA-11 | — | — | **PAID; not in v1** |
| COA-06 | Coordinator history vs this opponent's staff | Registry lookup of past meetings; EPA in those games | COA-01, pbp | 2 games | display only; no numeric adjustment in v1 | Story context |
| COA-07 | Situational: after bye, short week, long road trip, time-zone change | League-wide coefficients on rest days, travel distance and time-zone change, estimated in PRJ-01. Team-specific records shown but never used as inputs | schedules `home_rest`, `away_rest`, `div_game`, stadium coordinates | league-wide: 2016–2025 | league coefficient; team value display only | Spread, winner, total |

**Why COA-06 is display-only.** Two or three prior meetings between coordinators can never produce a statistically meaningful edge. It stays in the story as color and never moves a number.

## 6. Matchup engine

The matchup engine only adds what the team ratings **don't already know**. A strong offense against a weak defense is already priced by PRJ-01; the engine adds the *interaction*, such as a team that runs outside a lot facing a defense that leaks outside. Every adjustment is a residual, is further damped by λ (initial 0.5) until BT-03 proves it predicts anything, and the combined adjustment to any player's projected mean is capped at ±15% in v1.

**MTC-01 Directional run matchup.** For each of the 7 run cells c, with dev = shrunk value minus league average in EPA per carry:

```latex
\Delta_{\text{run}} = \lambda \left[ \sum_{c} s_c \left( \text{dev}^{\text{off}}_c + \text{dev}^{\text{def}}_c \right) - \left( \text{dev}^{\text{off}}_{\text{all}} + \text{dev}^{\text{def}}_{\text{all}} \right) \right]
```

s\_c is the offense's shrunk share of carries in cell c (we assume it doesn't change its run direction for this opponent). The subtraction removes what overall ratings already count. The same formula runs on yards per carry to adjust rushing-yard projections. Inputs: OFF-12, DEF-03. Minimum: a cell contributes only when both sides have 25 carries there; otherwise its dev terms are set to the overall values, so it adds nothing.

**MTC-02 Positional passing matchup.** For each pass-catcher at position p (RB, TE, WR) facing a defense with opponent-adjusted ratio r\_p (DEF-04), his projected yards per target and TD rate are multiplied by r\_p^β, with β initial 0.5 and tuned in BT-03. His target share is **not** changed by the matchup in v1, because evidence that teams re-route targets toward a weak defensive position is thin.

**MTC-03 Pressure matchup.** Expected sack rate uses the odds-ratio (log5) method: each side's deviation from league is multiplied in odds space.

```latex
\text{odds}_{\text{game}} = \frac{\text{odds}_{\text{off}} \times \text{odds}_{\text{def}}}{\text{odds}_{\text{league}}}, \quad \text{odds} = \frac{p}{1-p}
```

Each missing starting lineman (OFF-17) multiplies odds\_off by an OL-absence factor (initial 1.10, estimated in BT-02). The result feeds the sack and drive-stall rates inside the simulation.

**MTC-04 Pace and script.** Not a separate adjustment. The simulation (PRJ-02) plays out game script itself using both teams' neutral pace (OFF-10), pass tendency (OFF-05) and script response (COA-04). The engine reports the simulated median plays and pass rate per team so you can sanity-check them.

**MTC-05 Context.** Roof `dome` or `closed`: weather ignored. Outdoors: sustained wind and precipitation enter as league-wide coefficients on pass EPA, completion rate and field-goal make rate, fit on 2016–2025 games with historical weather in BT-02. The spec does not assume a size for the 15 mph wind effect; it is measured. Rest, travel, time zone and divisional games use COA-07.

**MTC-06 Matchup story (the only LLM step).** Code assembles a JSON of every metric value, its sample size and its adjustment. The LLM writes the story from that JSON only. A validator function then extracts every number from the text and rejects the story if any number is not in the JSON, or any sentence lacks a metric ID. A sample line: "Offense runs 38% of carries to the left end and tackle (OFF-12, n = 61); this defense allows +0.09 EPA/carry there vs league (DEF-03, n = 44) → run adjustment +0.02 EPA/carry after damping."

## 6b. Skill-vs-skill matchup catalog

Every player skill here is paired with the opposing defense's matching weakness or strength, and a learned model (MTC-07) measures from 2016–2024 data how much each pairing actually moves a player's output. **A skill matchup is allowed to change a projection only after it proves, on seasons the model never saw, that it predicts better than leaving it out.** That rule is what makes a large catalog safe: splitting the same plays into more slices makes every slice smaller and noisier, and without the proof step detail becomes confident nonsense.

Four rules apply to every row below:

1. **Same conventions.** Shrinkage (G1), recency (G3), garbage-time removal (G7) and the minimum-sample greying (G2) apply exactly as in sections 2–5. Player skills shrink toward the player's own overall value, which is itself shrunk toward his role prior.
2. **Pairs, not singles.** A skill enters the matchup model only as a pair: the player's deviation from average times the opponent's deviation allowed in the same dimension, weighted by how often the player uses that dimension.
3. **Proof or deletion.** BT-03 ablation tests each dimension. Any that doesn't improve out-of-sample accuracy gets weight zero and is removed from v1.
4. **Stated limits.** FTN-based dimensions have training data only from 2022, so they train on fewer seasons and are penalized harder.

**What free data cannot show.** Which cornerback covered which receiver, route types, coverage shell, and blocking assignments all need a paid charting feed (DATA-11). So v1 matches players against *team* defensive tendencies, not against individual defenders. The one exception is DEF-17, which uses individual defenders' production to size how much a team weakens when one of them is out.

### Offensive player skills

Depth bands everywhere are the OFF-13 bands: behind the line (`air_yards` < 0), short 0–9, intermediate 10–19, deep 20+. "Dev" means the shrunk value minus league average for that position.

**Quarterback**

| ID | Skill and plain meaning | Formula | Data fields | Min n | Shrink (k, prior) | Paired with | Feeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PLY-18 | Depth profile. Where he throws and how well at each depth | Share of attempts and EPA per attempt in each depth band; aDOT | `passer_player_id`, `air_yards`, `epa` | 30 attempts per band | k = 80 attempts; prior = his overall EPA per attempt | DEF-09 | Passing yards, passing TDs, receiving props |
| PLY-19 | Play-action split. How much better he is off a run fake | EPA per dropback with play action minus without; his play-action rate | FTN `is_play_action`, `epa` | 40 play-action dropbacks | k = 100; prior = league play-action gap | DEF-10 | Passing yards |
| PLY-20 | Accuracy and ball security | Completion over expected: mean(`complete_pass` − `cp`); catchable-ball rate; interception-worthy rate; throwaway rate | pbp `cp`; FTN `is_catchable_ball`, `is_interception_worthy`, `is_throw_away` | 100 attempts | k = 200; prior league QB | DEF-09 (completion over expected allowed) | Completions, interceptions, passing yards |
| PLY-21 | Time to throw and sack avoidance. Does he get rid of it or hold it | NGS average time to throw; sacks ÷ dropbacks charged to him | NGS weekly; pbp `sack` | 100 dropbacks | k = 150; prior league QB | DEF-05 (pass rush) | Passing props, MTC-03 |
| PLY-22 | Rushing threat | Scrambles ÷ dropbacks; designed runs per game; yards per rush | `qb_scramble`, `rusher_player_id`, `yards_gained` | 20 rushes | k = 40; prior = league QB of his rushing type | DEF-14 | QB rushing yards, QB anytime TD |
| PLY-23 | Direction. Left, middle or right of the field | Share of attempts and EPA per attempt by `pass_location` | `pass_location`, `epa` | 40 attempts per side | k = 100; prior = his overall | DEF-09 (by location) | Receiving props by receiver location |

**Running back** (in addition to PLY-16, the directional lane profile)

| ID | Skill and plain meaning | Formula | Data fields | Min n | Shrink (k, prior) | Paired with | Feeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PLY-24 | Box-count splits. How he does against light vs stacked fronts | Success rate and yards per carry vs light (≤ 6 in box), standard (7) and stacked (≥ 8) boxes | FTN `n_defense_box` | 20 carries per band | k = 50; prior = his overall | DEF-12 | Rushing yards |
| PLY-25 | Formation split. Shotgun vs under center | Success and yards per carry by `shotgun` | `shotgun` | 25 carries each | k = 60; prior = his overall | DEF-15 | Rushing yards |
| PLY-26 | Explosiveness and stuff avoidance | Share of carries 10+ yards; share at ≤ 0 yards; rushing yards over expected (PLY-11) | `yards_gained`; NGS | 60 carries | k = 150 explosive, 100 stuff; prior league RB | DEF-06, DEF-03 | Rushing yards (the ladder's upper rungs) |
| PLY-27 | Receiving role | Target share; share of team screen targets; yards after catch over expected | FTN `is_screen_pass`; pbp `xyac_mean_yardage` | 15 targets | k = 40; role prior | DEF-11 | RB receiving yards, receptions |

**Receivers and tight ends**

| ID | Skill and plain meaning | Formula | Data fields | Min n | Shrink (k, prior) | Paired with | Feeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PLY-28 | Depth profile | Share of his targets and EPA per target in each depth band; aDOT | `air_yards`, `epa` | 15 targets per band | k = 40; prior = his overall | DEF-09 | Receiving yards |
| PLY-29 | Field location. `middle` share is a rough stand-in for slot usage, labelled as a proxy | Share of targets and EPA per target by `pass_location` | `pass_location` | 20 targets per side | k = 50; prior = his overall | DEF-09 (by location) | Receiving yards |
| PLY-30 | Hands and ball skills | Drops ÷ catchable targets; catches ÷ contested targets; created-reception rate | FTN `is_drop`, `is_catchable_ball`, `is_contested_ball`, `is_created_reception` | 20 catchable, 10 contested | k = 60 catchable, 30 contested; prior league at position | Context; enters MTC-07 only through PLY-10 | Receptions |
| PLY-31 | Separation and yards after catch | NGS average separation and cushion; YAC over expected (PLY-09) | NGS weekly; pbp | 30 targets | k = 80; prior league at position | DEF-11 | Receiving yards |
| PLY-32 | End-zone targets | Targets where `air_yards` ≥ `yardline_100`, as a share of team end-zone targets | `air_yards`, `yardline_100` | 5 team end-zone targets | k = 15; prior = his PLY-06 red-zone share | DEF-16 | Anytime, first and 2+ TD |
| PLY-33 | Play-action and motion usage | His share of team targets on play-action and on motion plays | FTN `is_play_action`, `is_motion` | 15 targets each | k = 40; prior = his overall target share | DEF-10 | Receiving yards |

**All positions**

| ID | Skill and plain meaning | Formula | Data fields | Min n | Shrink (k, prior) | Paired with | Feeds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PLY-34 | Athletic profile. Size and speed, as percentiles within his position | Height, weight, 40-yard dash, vertical, broad jump, 3-cone, shuttle | nflverse combine data | none | none | Not paired; a prior only | Role priors for rookies and low-sample players (PLY-15) |

### Defensive counterparts

Same conventions as section 3: team-level, computed on plays against, directions in the offense's frame.

| ID | Tendency and plain meaning | Formula | Data fields | Min n | Shrink (k, prior) | Paired with |
| --- | --- | --- | --- | --- | --- | --- |
| DEF-09 | Pass map allowed. Where this defense gets beaten, by field location and depth | EPA per target and completion over expected allowed in OFF-13's 12 location × depth cells | `pass_location`, `air_yards`, `epa`, `cp` | 20 targets per cell | k = 60; prior = the defense's shrunk pass value | PLY-18, 20, 23, 28, 29 |
| DEF-10 | Play-action defense. Do run fakes fool them | EPA per dropback allowed with play action minus without | FTN `is_play_action` | 40 play-action dropbacks | k = 100; prior = league gap | PLY-19, PLY-33 |
| DEF-11 | Tackling after the catch | mean(`yards_after_catch` − `xyac_mean_yardage`) allowed per reception | pbp | 60 receptions | k = 150; prior 0 | PLY-27, PLY-31 |
| DEF-12 | Box tendency and box-split run defense | Share of snaps with ≥ 8 in the box; success and yards per carry allowed by box band | FTN `n_defense_box` | 20 carries per band | k = 50; prior = its overall run defense | PLY-24 |
| DEF-13 | Blitz results. Does blitzing help or hurt this defense | EPA per dropback allowed when blitzing minus when not | FTN `n_blitzers` | 60 blitzed dropbacks | k = 120; prior = league gap | PLY-17 |
| DEF-14 | Quarterback runs allowed | Scrambles and QB rushing yards allowed per opponent dropback | `qb_scramble`, `rusher_player_id` joined to roster position | 150 dropbacks | k = 300; prior league | PLY-22 |
| DEF-15 | Formation run defense | Success and yards per carry allowed on shotgun vs under-center runs | `shotgun` | 25 carries each | k = 60; prior = its overall run defense | PLY-25 |
| DEF-16 | End-zone pass defense | TDs allowed ÷ end-zone targets faced | `air_yards`, `yardline_100`, `touchdown` | 10 end-zone targets | k = 30; prior league | PLY-32 |
| DEF-17 | Defender contribution shares. How much of the defense's pass rush and playmaking each defender supplies | Each defender's share of team sacks, QB hits, passes defensed, interceptions and tackles for loss | pbp `sack_player_id`, `qb_hit_1_player_id`, `pass_defense_1_player_id`, `interception_player_id`, `tackle_for_loss_1_player_id` | 200 team defensive snaps | k = 20 events per share; prior = snap share | Sizes DEF-08: when a defender with share s is out, the team's pass-rush rate moves by s × (his rate − replacement rate), replacement = league backups at his position (BT-02) |

### Environment interactions

League-wide coefficients fit on 2016–2024 games, each reported with its standard error and each tested in BT-03 like any skill pair. No sizes are assumed; they are measured.

| ID | Factor | Formula | Data | Tested effect on |
| --- | --- | --- | --- | --- |
| ENV-01 | Field surface, grass vs artificial turf | Surface indicator, plus an interaction with the offense's explosive-play rate (a speed proxy) | Schedules `surface` | Explosive-play rates, pace, rushing and receiving yards |
| ENV-02 | Altitude | Stadium elevation. Wikidata's stadium items carry no elevation, so v1 uses the elevation of the city each stadium is located in (Wikidata P131, then P2044; if that place has none, the next place up the P131 chain that does), converted to metres where Wikidata gives feet, cited per row and labelled as a city-level proxy | Wikidata | Field-goal make rate by distance; visiting-team fourth-quarter efficiency |
| ENV-03 | Temperature | Continuous game-time temperature, plus an interaction for a dome-home team playing outdoors | NWS forecast; schedules `temp` history | Pass EPA, completion rate, field goals |
| ENV-04 | Wind, gusts and precipitation | As MTC-05, with gusts added | NWS forecast; schedules `wind` history | Pass EPA, deep-attempt rate, field goals, total points |

### MTC-07 Learned matchup model

Instead of fixed guesses for how much each matchup matters, a regression learns the weights from nine seasons (2016–2024) of player-games. For player i in game g and stat family s (rushing yards, receiving yards, receptions, passing yards, passing TDs, touchdowns scored), the target is how far the actual result landed from the no-matchup baseline, and each feature is one skill pair:

```latex
y = \ln\frac{\text{actual} + 1}{\text{baseline} + 1}, \qquad x_d = u_{i,d}\,\big(p_{i,d} + o_{g,d}\big)
```

The baseline is the PRJ-02 projection with the matchup layer switched off. u is how often the player uses dimension d (for example his share of carries into a given lane), p is his shrunk deviation in that dimension, and o is the opponent's shrunk deviation allowed; as in MTC-01, the part already counted by overall ratings is subtracted out.

1. **Model:** ridge regression per stat family on standardized features, penalty chosen by walk-forward cross-validation (fit on seasons before S only). FTN-based features train on 2022 onward.
2. **Output:** a multiplier on the player's projected mean, m = e^ŷ, capped at 0.85–1.15. Once fitted, it replaces the fixed λ damping in MTC-01 to MTC-03; until then the λ = 0.5 rules stand.
3. **Challenger:** a gradient-boosted tree model may replace ridge only if it beats ridge on every walk-forward test season, scored by log loss on ladder probabilities and CRPS (continuous ranked probability score: how close the whole predicted distribution was to what happened).
4. **Explainability:** every matchup story (MTC-06) lists the three skill pairs that moved each player most, with the learned weight, its standard error and the sample sizes behind both sides.
5. **Deletion:** any dimension whose weight isn't significantly different from zero on held-out seasons is dropped, and the decisions log records which survived.

## 7. Projection and pricing models

One play-by-play simulation per game feeds every market, and **for props and combos the simulation is anchored to the market's own spread and total.** Main lines are efficient, so disagreeing with them on team strength would inject our weakest opinion into every prop. Anchoring means prop edges have to come from usage and matchup modeling, where we actually might know something.

**PRJ-01 Team strength.** Two modes, both deterministic:

- **01a Model mode** (for game-line markets): opponent-adjusted ridge ratings (G6) for offense and defense, pass and run separately, recency-weighted with h = 6 games, plus home-field, rest, travel and time-zone coefficients (COA-07). Converted to expected points per drive.
- **01b Market-anchored mode** (default for props, TDs, combos): solve for the two teams' ratings, holding their pass/run mix from 01a, so the simulation's median margin and median total match the consensus spread and total within 0.25 points. Consensus = Kalshi mid on the main spread and total, or DATA-10 if licensed.

**PRJ-02 Game simulation.** Monte Carlo, N = 20,000 runs per game with a stored random seed so any run can be reproduced exactly.

1. Game state per play: possession, down, distance, yardline, clock, score, timeouts.
2. Play call: P(pass) = `xpass` model value + team PROE (OFF-05) + script response (COA-04); then run vs pass vs scramble vs sack (MTC-03).
3. Ball carrier or target: drawn from player shares (PLY-03/05), switching to red-zone shares (PLY-06) inside the 20. Injury-adjusted shares from PLY-14/15.
4. Outcome: runs draw yards from the offense's cell-weighted yards distribution with MTC-01 applied; passes draw completion (from `cp`-style model + CROE context), air yards and YAC; turnover, penalty and fumble rates at league values adjusted by team rating.
5. Special teams and decisions: 4th-down calls (COA-02), field-goal make rate by distance and weather (MTC-05), punts at league net average, 2-point tries (COA-03), clock runoff from OFF-10.
6. Record per run: final score, every player's stat line, the order of touchdowns (for first TD).

Acceptance test for PRJ-02: simulating a full past season with true pre-game inputs must reproduce league averages within tolerance: points per team-game ± 0.7, plays per team-game ± 2, pass rate ± 1.5 points, yards per pass attempt ± 0.2. **Where it runs:** 20,000 runs × 16 games × about 130 plays is roughly 40 million simulated plays a week. That belongs in a Python worker (numpy/numba) outside Base44, writing results into Base44 via its API. Whether Base44 backend functions could handle it is unverified; assume not.

**PRJ-03 Touchdown markets.** Primary value = simulation frequency. Cross-check with a Poisson model, where λ = team projected TDs × player TD share (rushing share from PLY-06 by zone, plus receiving TD share):

```latex
P(\geq 1\ \text{TD}) = 1 - e^{-\lambda}, \qquad P(\geq 2\ \text{TD}) = 1 - e^{-\lambda}(1 + \lambda)
```

First TD (game and team-specific): simulation frequency of being the first TD scorer; cross-check = P(team scores first TD) × player's share of team TDs, weighted toward his first-quarter usage. If the sim and cross-check differ by more than 3 percentage points, the app flags the market and blocks a recommendation until reviewed. Settlement edge cases (no TD scored, defensive or special-teams TDs, overtime) come from each Kalshi market's rules text, stored with the market.

**PRJ-04 Yardage and stat props.** Kalshi player props are "X or more" ladders, so P(YES) = share of runs with stat ≥ X, using the exact threshold and stat definition in the market rules. Probabilities across a ladder must be non-increasing; the code enforces it. Simulation error at N = 20,000 is about ±0.35 percentage points at 50%, small against any edge threshold.

**PRJ-05 Combos.** Same-game: joint probability = share of the same 20,000 runs in which every leg hits, so correlation is built in. Multi-game: product of each game's probability (games treated as independent). Report the correlation lift = P(joint) ÷ product of the legs' individual probabilities, so you can see whether Kalshi's combo price is treating correlated legs as independent.

**PRJ-06 Futures.** 20,000 season simulations over the remaining schedule. Each simulated season first draws every team's rating from its uncertainty distribution, then plays the games; without this step futures come out overconfident. Tiebreakers follow the NFL's published order through strength of victory, then a coin flip (an approximation, stated in the UI). Season stat totals and leaders sum per-game player simulations with a weekly probability of missing the game (from base rates estimated in BT-02).

**PRJ-07 Calibration.** Per market type: reliability table (10 probability bins, forecast vs actual hit rate), Brier score, log loss, and a logistic recalibration slope. A slope under 1 means our probabilities are too extreme. Any recalibration (Platt or isotonic) is fit on backtest seasons only and frozen before the live season. Minimum 1,000 forecasts per market type and 50 per bin before a calibration curve is trusted.

## 8. Edge and decision layer

A position is recommended only when our probability beats the **all-in cost** (price plus fee) by the market type's threshold, the book has depth at that price, and every bankroll rule passes. All of this is code; the app never lets you type in a stake.

**EDG-01 Price to probability.** Kalshi's order book lists bids only. Buying YES costs the YES ask = $1 − best NO bid. Buying NO costs the NO ask = $1 − best YES bid. The mid is shown for reference but never used for decisions.

**EDG-02 Fees** (from the [Kalshi fee schedule](https://kalshi.com/docs/kalshi-fee-schedule.pdf), last updated and effective July 7, 2026). P = price in dollars, C = contracts, M = series multiplier. Rounding: the PDF's formula text says fee plus position cost rounds up to the nearest $0.0001, but its printed table rounds fees up to the cent (100 contracts at $0.05 shows $0.34, not $0.3325). The app rounds up to the cent, the conservative reading, until a real fill confirms which rule applies.

```latex
\text{taker fee} = \lceil M_t \times 0.07 \times C \times P (1-P) \rceil, \qquad \text{maker fee} = \lceil M_m \times 0.0175 \times C \times P (1-P) \rceil
```

| Series (NFL) | Taker M | Maker M | Meaning |
| --- | --- | --- | --- |
| Default (props and any series not listed) | 1 | 0 | Resting orders pay no fee, unless Kalshi's API reports maker fees for the series; Phase 1 found KXNFLSPREAD, KXNFLTOTAL, KXNFLANYTD, KXNFLFIRSTTD and KXNFL2TD do |
| KXNFLGAME (game winner) | 1 | 1 | Resting orders pay the maker fee when filled |
| Combos (NFL combos are the KXMVENFL\* series) | 1 | 2 | Makers pay double the maker rate |
| Division, conference, Super Bowl, awards series | 1 | 1 | Maker fee applies |

The app stores multipliers per series ticker and checks them weekly against the fee fields Kalshi's API reports for each series (fee\_type, fee\_multiplier); the PDF sits behind a bot check, so you re-download it by hand whenever those fields change. Phase 1 found that NFL combos are the series KXMVENFLSINGLEGAME, KXMVENFLMULTIGAME and KXMVENFLMULTIGAMEEXTENDED, which the API lists with fee\_type quadratic; whether the doubled maker rate applies to them is settled in Phase 7 from the API fields and a real fill. There is no settlement fee, but exiting a position before settlement is a second trade with a second fee. At 50¢ the taker fee is 1.75¢ per contract, so a taker round trip costs 3.5¢ before the spread.

**EDG-03 Edge after fees.** For a YES buy at price P with fee f per contract, cost c = P + f. Edge = p\_model − c. ROI = (p\_model − c) ÷ c.

| Market type | Minimum edge after fees | Also required |
| --- | --- | --- |
| Game winner, spread, total | 4¢ | Model mode 01a only; flag "efficient market" on every one |
| Anytime TD | 4¢ | ROI ≥ 10% |
| Yardage and stat props | 5¢ | ROI ≥ 10%; bid/ask spread ≤ 6¢ |
| First TD, 2+ TD (usually priced under 25¢) | 2¢ | ROI ≥ 20% |
| Combos | 3¢ | ROI ≥ 20%; all legs from one PRJ-02 run |
| Futures | 5¢ | ROI ≥ 15% (money is tied up for months) |

Add 2¢ to the threshold when any input is a v1 proxy (PLY-02, PLY-08) or a PLY-15 low-confidence projection. These thresholds are starting points; BT-04 re-sets them from backtested CLV.

**EDG-04 Liquidity.** From the live order book: contracts available at or better than our maximum price, 24-hour volume and total volume. Maximum contracts = the smaller of the bankroll-rule size and 25% of visible depth within 2¢ of our price. Every recommendation shows depth, volume and the resulting dollar cap. A market with under $5,000 total volume is labelled "thin."

**EDG-05 Orders.** Default is a resting limit order at no more than the max acceptable price = p\_model − threshold − fee. If the price moves away, the recommendation expires; the app never suggests raising the limit.

**EDG-06 Staking.** Kelly fraction for a contract costing c that pays $1, and our quarter-Kelly stake:

```latex
f^{*} = \frac{p - c}{1 - c}, \qquad \text{stake} = \min\left( \tfrac{1}{4} f^{*},\ \text{cap} \right) \times \text{sizing bankroll}
```

Cap = 1% for every market type until it passes the go-live bar (BT-05) and shows positive CLV over 300+ live positions; after that, 2%. Stakes under 0.25% are skipped. Combos: cap 0.5%. Sizing bankroll = the lower of current bankroll and start-of-week bankroll, so stakes can never rise after losses within a week. Contracts = stake ÷ c, rounded down.

**EDG-07 Exposure and stops.** Per game: total stake across every open position tied to that game, including any combo with a leg in it, ≤ 6% of bankroll. Weekly stop: the week runs Tuesday 00:00 to Monday 23:59 Eastern; once settled P&L for the week reaches −10% of start-of-week bankroll, the app shows no new recommendations until Tuesday. Chase check: if you log a trade larger than the recommended size or not on the recommendation list, the app records it as a rule break and shows it on the scorecard.

**EDG-08 Position log and closing line value.** Each logged position stores market ticker, side, entry price, fee, contracts, timestamp, p\_model and the recommendation ID. Closing price = the last traded price before kickoff from the Kalshi trades endpoint (and the closing mid as a second measure). CLV in cents = closing price − entry price, both on the side you bought. The scorecard ranks every market type by average CLV and its standard error, not by win rate.

## 9. Backtesting plan

No real money goes into a market type until it clears every number in BT-05 on seasons the model never saw. The decisive test is not "is our model accurate" but **"does our model add anything to the market's own price"**; if it doesn't, there is no edge, however good the model looks.

**BT-01 Point-in-time rebuild.** For every past game, rebuild all inputs as they stood at the decision time (default: 24 hours before kickoff; a second pass at 90 minutes before). Only plays from earlier games, the injury report as published that week, and depth charts dated before the game. Walk-forward: every parameter used for season S is fit only on seasons before S. Walk-forward test seasons are 2021–2024, each fit only on seasons from 2016 through the year before; 2025 is a locked holdout (BT-07). FTN charting starts in 2022, so 2021 runs without FTN inputs. A leakage test in code: shuffle the order of future games and confirm no input for game g changes. **Availability rules (Phase 2).** Injury reports, weekly rosters and week-numbered depth charts (before 2025) carry no publish time: for data older than our own pulls, a team's week report counts as known at 12 noon ET, 1 day before kickoff, a stated assumption labelled in every snapshot; from our own pulls on, pulled\_at decides. ESPN-format depth charts (2025 on) use the latest chart dated on or before as\_of. Plays and game stats come only from games whose last play was run by as\_of. Schedules' temp and wind are observed, labelled observed\_as\_forecast\_proxy; spread\_line, total\_line and moneylines are closing lines, shown only when as\_of is at or after kickoff or a closing\_line\_backtest flag is passed; the target game's scores, result and starting quarterbacks are never shown. Each dataset-season is read from the latest version pulled at or before as\_of, or else the earliest version held, labelled, so history carries nflverse corrections made up to our first pull.

**BT-02 Parameter estimation.** Fit on training seasons only: every k (split-half stabilization), half-lives h, role priors, OL-absence factor, return-from-injury factor, weather coefficients, rest/travel coefficients, weekly missed-game base rates. Output: a versioned parameter file that replaces every "initial" value in this spec.

**BT-03 Ablation.** Each matchup adjustment (MTC-01/02/03) and each tendency input is switched off one at a time. It stays only if out-of-sample log loss improves; its damping λ is chosen by cross-validation, and λ = 0 means it is deleted from v1.

**BT-04 Market comparison.** Price history available:

| Market history | Where from | Seasons |
| --- | --- | --- |
| Game spread, total, moneyline closing lines | nflverse schedules (`spread_line`, `total_line`, moneylines) | 2016–2025 |
| Kalshi NFL prices, trades, candlesticks | Kalshi historical endpoints (DATA-08); [sports contracts listed from January 2025](https://www.theblock.co/news/regulation/2026-09-26-kalshi-loses-appeal-over-ohio-and-tennessee-sports-betting-laws-widening-circuit-split-416937) | 2025 season and 2026 to date |
| Sportsbook player-prop closing lines | DATA-10, paid; props history from May 2023 | 2023–2025 |

Scoring per market type: Brier score and log loss for our probability vs the market-implied probability (sportsbook prices de-vigged proportionally; Kalshi mid). **Blend test:** fit P(outcome) = logistic(a × logit(market) + b × logit(ours)) on held-out games. If b is not significantly above zero, our model adds nothing for that market type. **Simulated CLV:** for every backtest recommendation, price at decision time (Kalshi candlesticks, or sportsbook line at that hour) vs closing price, after fees.

**BT-05 Go-live bar (per market type; all must pass):**

- [ ] Calibration slope between 0.90 and 1.10 on held-out seasons, 1,000+ forecasts
- [ ] Blend weight b > 0 with p < 0.05 on held-out seasons
- [ ] Simulated mean CLV ≥ +1.5¢ per position after fees over 500+ simulated positions, with the 95% confidence interval's lower bound above 0
- [ ] Four consecutive weeks of real-time paper recommendations (logged before kickoff, no edits) with mean CLV > 0 over 100+ positions
- [ ] Every data feed the market type uses has run end to end in production for those four weeks

**BT-06 Live stop rules.** CLV standard error = standard deviation of per-position CLV ÷ √n. After 300 live positions in a market type: mean CLV ≤ 0 → stop that market type. After 1,000 live positions overall: if the 95% interval on mean CLV includes 0 → the app displays "No demonstrated edge: stop" and disables recommendations. Win/loss record is never an input to either rule.

**BT-07 Historical Performance Report.** One command replays 2021–2025 through the production code and parameter file, season by season, and reports results per season × market type. Three things to know before reading it:

- **Game-line history can only enter at the closing price.** nflverse carries closing lines, not the line at our decision time, so for game lines CLV is not measurable and ROI at the close is the real test. Beating closing lines after Kalshi-level costs is hard; failing to is the expected result.
- **Locking 2025 hides every Kalshi-only market's history.** Kalshi NFL prices begin in 2025, so combos and any market without paid odds history show nothing until the model is frozen and the holdout is opened.
- **One season of wins and ROI is mostly noise.** At about 200 positions near 50¢, ROI's standard error is roughly 1 ÷ √200 ≈ 7%, so a +5% season proves nothing. Every ROI carries its confidence interval.

**BT-07a Same code, stamped.** The harness imports the production modules (`ge.metrics`, `ge.models`, `ge.edge`); a test fails the build if any backtest file re-implements a formula. Every report is stamped with the git commit, the params file version and hash, and a hash of the data snapshot. Season S is predicted only from parameters fit on 2016 through S − 1. This replaces BT-01's original split. FTN charting starts in 2022, so 2021 runs with FTN-based metrics treated as missing (matchup terms that use them contribute zero; no earlier FTN data exists to form a prior) and is labelled "no FTN."

**BT-07b The 2025 holdout lock.** 2025 is never computed during development. The harness refuses `--season 2025` unless it is given a frozen model tag (a git tag plus params hash) recorded in `holdout_ledger.yaml`. Opening the holdout is a one-time event logged in the decisions log. Any model change after that marks every 2025 number "holdout spent" for all later versions, permanently. BT-05 is developed on 2021–2024 and must then be confirmed on the 2025 holdout before any market type goes live.

**BT-07c History tiers by market type.** Every market type also gets a Kalshi layer for 2025 on, using real Kalshi prices and fees.

| Market type | Tier | Seasons | Price source | Entry price used | CLV measurable? |
| --- | --- | --- | --- | --- | --- |
| Game winner, spread, total | **Full** | 2021–2025 | nflverse schedules closing lines, de-vigged proportionally | Closing fair price + Kalshi taker fee at that price + an assumed half-spread (params: initial 1¢) | No, closing price only |
| Anytime TD, yardage and stat props | **Partial** | 2023–2025 | Paid odds history (DATA-10), props from May 2023 | Sportsbook consensus at decision time, de-vigged, plus Kalshi-level costs | Yes, against the sportsbook close |
| First TD, 2+ TD | **Partial** if DATA-10 carries them, otherwise **Kalshi-only** | 2023–2025 or 2025 | Verify in Phase 8 | As above | As above |
| Same-game and multi-game combos | **Kalshi-only** | 2025 | Kalshi trades and candlesticks | Kalshi price at decision time, real fees | Yes |
| Futures | **Kalshi-only** unless DATA-10 historical futures are verified | 2025 | Kalshi | Kalshi price at decision time | Yes |

**BT-07d Metrics per season × market type.** A cell with fewer than 50 positions shows "too few to read" instead of numbers.

| Metric | Definition |
| --- | --- |
| Positions | Recommendations that passed every EDG rule at decision time |
| Win % | Wins ÷ settled positions |
| Expected win % | Mean p\_model over the same positions, plus the calibration gap z = (wins − Σp) ÷ √Σp(1 − p). \|z\| > 2 means our probabilities were off |
| ROI after fees | Σ profit after fees ÷ Σ stake, with a 95% bootstrap interval resampled by game, because positions in one game are correlated |
| Mean CLV ± SE | Mean of (closing price − entry price) in cents, standard error = SD ÷ √n; "n/a" for the Full tier |
| Max drawdown | Largest fall from a bankroll peak to a later low, as % of that peak |
| Longest losing streak | Most consecutive losing positions, in settlement order |
| Bankroll curve | BT-07e below |

**BT-07e Bankroll curve at our real staking rules.** Start at 100 units, both per season and as one continuous 2021–2024 curve. Positions are placed in decision-time order and settled at game end, through the production EDG-06/07 code: quarter-Kelly, 1% cap (no market type has passed a live test in history), skip under 0.25%, combos at 0.5%, 6% per game, weekly −10% stop, sizing bankroll = the lower of current and start-of-week. Two versions: a **portfolio** curve with all market types sharing the caps, and **isolated** curves per market type, labelled as ignoring cross-market caps. Liquidity: Kalshi-layer sizes are capped at 25% of contracts traded in the hour before decision time, because historical order-book depth is unlikely to be available; the worker stores its own book snapshots from now on. Sportsbook-priced tiers have no depth data, so their curves overstate the size you could really have gotten, and are labelled so.

## 10. What to expect

The most likely result of season one is **no provable edge and a small loss roughly equal to fees**; a genuine edge, if it exists, will be small, concentrated in a few prop families, and invisible in win/loss results for at least a season. These ranges are my judgment, not measured data.

| Scenario | What it looks like | Season result at these stake sizes |
| --- | --- | --- |
| Most likely | Main lines show zero edge; props show CLV near zero; BT-05 passes for zero or one market type | About −3% to −10% of bankroll, mostly fees and spread |
| Plausible good | Positive CLV in one or two prop families (for example receiving yards on backup-heavy weeks, TD markets on low-profile players) | About 0% to +10% of bankroll, with wide swings |
| Unlikely | Broad, durable edge across props and combos | Better than +10%; if you see this early, suspect a bug before celebrating |

**Why wins and losses can't tell you anything for a long time.** Say you make 180 positions in a season (10 a week) at 1% each, with a real 3% average return per position. Expected profit is 180 × 1% × 3% ≈ +5.4% of bankroll. But each 50¢ position swings about ±1 stake, so the season's standard deviation is about √180 × 1% ≈ 13.4% of bankroll. Even with a real edge, roughly one season in three finishes negative. CLV converges much faster, which is why it is the scorecard.

**Where edge is most likely.**

1. Player props on lower-profile players, especially when a teammate's absence redistributes usage (PLY-15), because fewer traders are pricing them closely.
2. Combos, where Kalshi's price may not fully reflect same-game correlation (PRJ-05 correlation lift). Tiny stakes only.
3. News reaction on thin prop markets, but only for news you see before the book reprices. On high-profile players, professional market makers will almost always be faster than a person entering news by hand.

**What the market structure costs you.** Touchdown and first-touchdown markets are [about 68% of Kalshi NFL prop volume](https://www.oddsshopper.com/articles/prediction-markets/kalshi-touchdown-props), so they are the best-priced props; receiving yards were measured trading about 8¢ wide in the same analysis, which on its own wipes out most edges for a taker. Many prop strikes [are listed early but not really priced until a day or two before kickoff](https://predictionmarketspicks.com/nfl/props), so a 1¢ bid against a 99¢ ask is a listing, not a price; the app must ignore books with a spread over 20¢.

**Where this approach most often fails.**

1. **Overfit splits.** Directional and positional cells are small; without G1 shrinkage and BT-03 ablation they produce confident nonsense.
2. **Double counting.** Adding a matchup edge on top of team ratings that already contain it. MTC residuals exist to prevent this.
3. **Adverse selection on limit orders.** A resting order fills most often right when news breaks against it (an injury you haven't seen). Cancel all resting orders on a team when any injury news on that team arrives.
4. **Settlement misreads.** A prop defined differently from how the simulation counts it (overtime, stat corrections, "X or more" vs "over X.5").
5. **Silent stubs.** A Base44 feature that returns plausible placeholder numbers. Every metric needs an acceptance test on known historical values.
6. **Behavior.** Overriding sizing after a bad week erases any statistical edge faster than any model error.
7. **Access.** Sports-contract rulings now split the [3rd Circuit against the 9th and 6th](https://www.sportico.com/law/analysis/2026/kalshi-circuit-split-scotus-1234945840/); Florida sits in the 11th Circuit. If Kalshi stops offering sports contracts in Florida, the program stops the same day.

## 11. NCAA football (v2)

College v2 is a **game-line and futures model only**. Kalshi's college board, as currently reported, carries games, spreads, totals, win-total ladders, conference and national-title futures and playoff specials, but [not the full player-prop slate the NFL board has](https://www.rockytopinsider.com/2026/09/27/kalshi-promo-code-rocky-new-25-nfl-bonus-in-tn-and-ny-for-titans-vs-giants-odds/). That removes most of the player layer and lets the simulation run drive by drive. Start v2 only after NFL v1 has completed four weeks of paper trading.

### Data sources

| ID | Source | What we pull | Access and cost | Cautions |
| --- | --- | --- | --- | --- |
| NCAA-DATA-01 | [CollegeFootballData API](https://collegefootballdata.com/terms) (official Python client) | Games, plays, drives, predicted points added (their EPA equivalent), betting lines, rosters, recruiting and team talent, coaches, venues, SP+/SRS/FPI ratings, game weather, live plays | API key required. [Free tier is 1,000 calls a month](https://collegefootballdata.com/terms); higher tiers via Patreon, [Tier 3 listed at $10/month for 75,000 calls](https://blog.collegefootballdata.com/api-v2-is-now-in-general-availability/), limits subject to change. [Commercial use is permitted](https://collegefootballdata.com/key) | No reselling or redistributing data; no excessive polling. Attribution encouraged. Verify which seasons of betting lines exist and whether they are opening or closing lines |
| NCAA-DATA-02 | [cfbfastR](https://github.com/sportsdataverse/cfbfastr/releases) (R, SportsDataverse) | Cleaned play-by-play with expected points and win probability; [loaders pull from sportsdataverse-data releases or the CFBD API](https://github.com/sportsdataverse/cfbfastr/releases) | Free package; API functions use your CFBD key | R only. The worker is Python, so use it for historical bulk loads and validation, and the CFBD Python client for weekly pulls |
| NCAA-DATA-03 | Conference player availability reports | Out / questionable / probable designations | Published by conferences. [Big Ten: four reports a week for 2026 conference games](https://kdhnews.com/sports/college/big-ten-will-release-4-player-availability-reports-per-week-for-games-matching-conference-teams/article_70da88f5-8dab-5cce-b4a1-a9a13e69b0dc.html). [SEC: daily from Wednesday, final report 90 minutes before kickoff; CFP games required from 2025](https://new.cbssports.com/college-football/news/college-football-playoff-will-require-teams-to-provide-player-availability-reports-beginning-with-2025-season/) | Conference games only, and not every conference; non-conference games may have no report at all. Manual entry via ManualNews until a terms-clean feed exists |
| NCAA-DATA-04 | NWS weather | Same as DATA-06 | Free | Venue coordinates from CFBD venues or a sourced config file |
| NCAA-DATA-05 | Kalshi public API and fee schedule | College series, prices, books, trades | Free; [KXNCAAFGAME listed at taker 1, maker 1](https://kalshi.com/docs/kalshi-fee-schedule.pdf) | Resting orders on college game markets pay the maker fee |

### What changes in the model

| Area | NFL v1 | College v2 |
| --- | --- | --- |
| Teams and schedule graph | 32 teams, densely connected | 130+ FBS teams plus FCS opponents, few cross-conference links. The ridge opponent adjustment (G6) carries far more weight; FCS games get their own prior and are down-weighted |
| Priors | Last season, regressed (G4) | Preseason prior from returning production, recruiting and talent composites, transfer-portal moves and coaching changes. Priors dominate through about week 6, not week 4 |
| Simulation | Play by play, for player props | Drive by drive, because there are no player markets to price. College clock and overtime rules get their own module, checked against the current NCAA rulebook |
| Player layer | Full usage model (section 4) | QB availability and a small set of key starters only. QB status is the single largest input |
| Garbage time and blowouts | NFL thresholds | Separate thresholds; talent gaps make blowouts and fat tails far more common |
| Home field | League-wide term | Per-venue term, heavily shrunk toward the conference average |
| Injuries | Official league report | Partial by conference (NCAA-DATA-03); missing reports widen uncertainty rather than being assumed healthy |
| Market efficiency | Main lines very efficient | Power-conference games similar to NFL; smaller-conference games, win-total rungs and futures on less-watched teams likely thinner, with tiny liquidity |

### Kalshi college markets and v2 coverage

Market list as reported in [OddsShopper's August 2026 college guide](https://www.oddsshopper.com/articles/prediction-markets/how-to-bet-college-football-on-kalshi) and Kalshi's props page; series tickers beyond those in the fee schedule are verified in Phase 1.

| Market | Series (where known) | v2 |
| --- | --- | --- |
| Single games (team to win) | KXNCAAFGAME | Model |
| Spreads and totals | Verify | Model |
| Regular-season win-total ladders (8+, 9+ …); conference title games and playoffs don't count | Verify | Model (season sim) |
| Conference champions: SEC, Big Ten, Big 12, ACC, Group of Five | KXNCAAFSEC, KXNCAAFB10, KXNCAAFB12, KXNCAAFACC | Model |
| College Football Playoff qualifiers and seeds | KXNCAAFPLAYOFF | Model, low confidence: a committee chooses, so it needs a selection model |
| National championship | KXNCAAF | Model |
| Undefeated-season specials | Verify | Model (season sim) |
| Heisman Trophy | KXHEISMAN | Track only: a vote, driven by narrative |
| AP poll ranks, College GameDay location | Verify | Track only (novelty) |

Backtesting follows BT-07 with its own tiers: college game lines are **Full** only if CFBD's betting-line history proves to contain closing lines, and every Kalshi college market is **Kalshi-only** from 2025.

## Decisions log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-10-03 | Phase 3c shrink rulings: PLY-22's k = 40 applies to yards per rush only; PLY-21 time to throw uses k = 150 with n = NGS attempts; PLY-30 created rate is per reception; DEF-12 stacked-box share is over qualifying plays; "league QB / RB / at position" priors pool plays at that position; DEF-17 shares count games he played; attempts with no air\_yards or pass\_location go to an unknown cell. Every stat with no k or prior raises until Phase 3e estimates one | Answers to Claude Code's 3c questions, 2026-10-03; the spec gave one k for several stats or none at all |
| 2026-10-03 | PLY-34 combine profile: draft years 2000 onward; percentiles within combine position across all years; higher = better (timed drills inverted); ties count half; combine rows with no pfr\_id stay in the comparison pool | Veterans drafted before 2016 still need a profile; nflverse combine data starts in 2000 |
| 2026-10-03 | PLY-14: a team's final report counts as in the feed once any game status is present; the return flag needs an injury-feed listing or a weekly-roster RES status during the missed games. PLY-15 triggers on Out and redistributes targets and carries. 2021 FTN metrics return null with the note "no FTN: missing". Collect proposes new Kalshi series without the fee-schedule rule, labelled | Answers to Claude Code's 3b questions; nflverse injuries carry no final marker, and IR shows only in weekly rosters |
| 2026-10-03 | Player rows are keyed per player-team stint; player shares count only the games he played; PLY-04 and PLY-06/07 shrink toward his role prior or his own shrunk share (raising until 3e); PLY-16 lane-share prior is set in 3e | Answers to Claude Code's 3b questions; traded players have shares on two teams |
| 2026-10-03 | Phase 3c rulings: nflverse combine data added under DATA-04 for PLY-34; PLY-22's prior is the league QB average until rushing types are defined; DEF-12 reuses PLY-24's box bands; DEF-17 counts half sacks as 0.5 and includes the \_2 columns, prior = defense snap share; NGS values are weighted by attempts or targets. PLY-14's return-from-injury flag requires an injury-report listing during the missed games | Open readings flagged in the Phase 3 plan (A16, A17, A18, A19, A24); released players were being flagged as injury returns |
| 2026-10-03 | In 2021 (no FTN charting) FTN-based metrics are treated as missing, and matchup terms that use them contribute zero; the nflverse teams table is listed under DATA-04 for franchise IDs | No earlier FTN season exists to form a prior, and borrowing 2022+ data would leak the future into the 2021 backtest |
| 2026-10-02 | New Phase 3e (BT-02 core) estimates from 2016–2024 history, before Phase 4: every k by split-half, the G6 ridge penalty, role priors, the COA-02 p\_go model, and k for team-level run-cell yards/carry, explosive and stuff rates and per-cell CPOE. Values raise only until 3e fills them | Phases 4–7 need these values, and Phase 8 needs Phases 4–7, so leaving them for Phase 8 would be circular; none of them needs the model, only history |
| 2026-10-02 | G4: new QB = the team's most-dropback passer differs from last season's; until COA-01 has rows for a season, a head-coach change in the schedules data stands in for a play-caller change; relocated teams keep their history by franchise | A hand-filled coordinator registry for nine past seasons isn't realistic; head coaches are in the schedules data for every season |
| 2026-10-02 | PLY-14: no game designation means expected to play once the team's final report is in the feed; "status unknown" applies only while a team's final report is missing at decision time | Reading it per player would have flagged 27 healthy defensive starters in one 2024 week |
| 2026-10-02 | Play sets: qualifying plays exclude no-play penalties, kneels, spikes and two-point tries; dropback = qb\_dropback == 1; attempt = pass\_attempt == 1 and sack == 0; G7's "4th quarter" includes overtime; G5's wp bounds are inclusive; "inside the 20/10/5" means yardline\_100 ≤ 20/10/5 | The spec named these sets without defining them; two-point tries carry pass/rush and EPA |
| 2026-10-02 | G3: team metrics use the efficiency half-life; the usage half-life applies to player shares; g counts the team's games; league priors are unweighted | The spec assigned h only to "usage" and "efficiency" |
| 2026-10-02 | OFF-03: goal-to-go takes precedence over red zone. OFF-10: consecutive snaps in play order, same fixed\_drive and quarter, prior play neutral, clipped at 45 s. OFF-12/DEF-03 add an unknown cell for uncharted runs, never used in MTC-01. DEF-06: share of qualifying plays plus run and pass sub-rates. DEF-08: n is the smaller side. OFF-15/DEF-05 count a sack or hit once. OFF-17 continuity by games. DEF-04 EPA as a difference vs expected. Pass-map target share shrinks to the league share | Overlapping cells, undefined denominators, a double count and a ratio that breaks below zero, all found while building 3a |
| 2026-10-02 | Player IDs: snap counts are joined to GSIS IDs through the nflverse players table (DATA-04) | 42 of 26,615 2024 snap rows unmatched, vs 8,215 through rosters' pfr\_id |
| 2026-10-02 | Phase 3's cross-check against nflverse player stats runs on 2024 | BT-07b: 2025 is never computed during development |
| 2026-10-01 | Players with no game status at decision time are flagged "status unknown"; availability comes from practice participation, and their props get no recommendation until a status or ManualNews entry arrives (PLY-14) | The live Phase 2 check found nflverse had practice reports but no game statuses for a Thursday game a day after the league published them |
| 2026-09-30 | Point-in-time rules for Phase 2: historical injury statuses known at 12 noon ET the day before kickoff; historical weather is observed (labelled a forecast proxy, backtested with and without); closing lines visible only at or after kickoff except in the Full-tier backtest; the target game's starting quarterbacks hidden; weekly rosters added to ingest (DATA-04); each dataset read from the latest version pulled at or before as\_of, else the earliest held | Each closes a way future information could leak into past predictions and inflate backtest results |
| 2026-09-29 | ENV-02 elevation comes from the stadium's city on Wikidata; known fee disagreements go in an acknowledged list so fees-check only fails on new changes | None of the 47 stadium items has an elevation claim; a check that always fails gets ignored |
| 2026-09-29 | Added section 6b: 17 player skills (PLY-18 to PLY-34), 9 defensive counterparts (DEF-09 to DEF-17), 4 environment factors (ENV-01 to ENV-04) and a learned matchup model (MTC-07) that fits each skill pair's weight from 2016–2024 data | Maximum matchup detail the free data supports, with every dimension required to prove out-of-sample value in BT-03 or be deleted |
| 2026-09-29 | Kalshi's API fee fields are the fee source of truth; where they and the PDF disagree, the model uses whichever costs more and flags it | The API reports maker fees on spreads, totals and TD props that the PDF doesn't list; understating cost is the dangerous error |
| 2026-09-29 | Added PLY-16 (running back directional profile) and PLY-17 (quarterback vs the blitz) | Brings the directional and pressure matchups down to the individual player, using free data with enough sample |
| 2026-09-29 | Quarterback handedness is not modeled | Not in free data, and a defense faces only a few left-handed starters a year, far too few to measure |
| 2026-09-29 | Weekly fee monitoring compares fees.yaml against Kalshi's API series fee fields; the fee PDF is saved by hand | kalshi.com serves the PDF behind a bot check, which we never bypass |
| 2026-09-29 | nflverse injury data has no report-date column; live runs use our own pulled\_at, and backtests assume a week's reports are known by the day before kickoff (to be confirmed in Phase 2) | Found in Phase 1; point-in-time rules need a stated assumption for past seasons |
| 2026-09-29 | Kalshi candles pulled at 60-minute periods; NWS weather kept in native units (°C, km/h, mm) | Matches BT-07e's one-hour liquidity window; unit conversion happens explicitly in the metrics layer, never silently at ingest |
| 2026-09-28 | config/stadiums.yaml is generated by code: roof from nflverse schedules, coordinates from Wikidata (new DATA-13), time zone computed from coordinates | Sourced and reproducible without hand entry; the rule against filling values from memory still holds |
| 2026-09-27 | BT-07: replay 2021–2025 walk-forward through production code; 2025 is a locked holdout opened once, only for a frozen model tag | Keeps one untouched season to confirm the model; replaces BT-01's original 2016–2021 / 2022–2025 split |
| 2026-09-27 | Full-tier game-line history is priced at the closing line, with CLV reported as n/a | nflverse carries closing lines only, so decision-time prices don't exist for those seasons |
| 2026-09-27 | NCAA football v2 covers game lines and futures only, with a drive-level simulation; work starts after four weeks of NFL paper trading | Kalshi's college board lacks the NFL's player-prop slate; NFL must prove itself first |
| 2026-09-27 | The Python worker holds no Kalshi credentials and reads public market data only | It cannot place a trade, by design or by bug; you place every trade by hand |
| 2026-09-27 | Worker writes compact records to Base44: one GameProjection per game, plus Recommendations, Scorecard and RunLog; DuckDB on the VM is the source of truth | Base44's external Apps API is beta and rate-limited (create 140/min, update 100/min per app) |
| 2026-09-27 | Fee rounding defaults to rounding up to the cent until a real fill confirms the rule | Kalshi's fee PDF formula text (centicent) and its printed table (cent) disagree; cent is the conservative reading |
| 2026-09-27 | Worker built in 11 phases, one Claude Code session each; every recommendation is PAPER ONLY until its market type passes BT-05 | Acceptance tests on real data define done, not an agent's report |
| 2026-09-27 | Props, TDs and combos use market-anchored team strength (PRJ-01b) | Main lines are efficient; prop edges should come from usage modeling, not from disagreeing with the spread |
| 2026-09-27 | Routes, alignment and coverage metrics deferred; free proxies in v1 | Not available in free in-season data; licensing a charting feed is a cost decision for you |
| 2026-09-27 | Game simulation runs in a Python worker outside Base44 | About 40 million simulated plays a week; must be deterministic and reproducible |
| 2026-09-27 | 1% stake cap until a market type passes BT-05 and 300 live positions of positive CLV; then 2% | Reconciles "default 1%" with "quarter-Kelly capped at 2%" |
| 2026-09-27 | Matchup adjustments are residuals, damped by λ = 0.5 and capped at ±15% | Prevents double counting and overfitting until BT-03 proves value |
| 2026-09-27 | NWS as primary weather source; Open-Meteo only for international games | NWS is free and public domain; Open-Meteo's free tier is non-commercial |
| 2026-09-27 | Coordinator history (COA-06) and team-specific situational records are display-only | Samples can never be large enough to move a number |

## Open questions

- [ ] Is Gridiron Edge a personal tool or an AI Wealth Builders product? Decides Open-Meteo licensing and any future data licenses
- [ ] License a charting feed (DATA-11) for routes, alignment and coverage? Needs price quotes
- [ ] Real-time inactives and injury news source (DATA-12) with terms that allow app use
- [ ] Confirm the nflverse injury feed updates during the 2026 season
- [ ] Budget for a historical odds API (DATA-10) to run the props backtest for 2023–2025
- [ ] Confirm Base44 can accept bulk writes from an external Python worker (API limits)
- [ ] **Kalshi combo history (blocks combos in Phase 8):** Kalshi's events endpoint returns no events for KXMVENFLSINGLEGAME and KXMVENFLMULTIGAME, so the by-event history pull finds no 2025 combos. Find another documented route, or combos have no backtest history and cannot pass BT-05

## Sources

[Kalshi fee schedule (effective July 7, 2026)](https://kalshi.com/docs/kalshi-fee-schedule.pdf) · [Kalshi market data quick start](https://docs.kalshi.com/getting_started/quick_start_market_data) · [Kalshi order book endpoint](https://docs.kalshi.com/api-reference/market/get-market-orderbook) · [nflreadr FTN charting](https://nflreadr.nflverse.com/reference/load_ftn_charting.html) · [nflreadr news (participation, depth charts)](https://cran.r-project.org/web/packages/nflreadr/news/news.html) · [nflreadpy (licensing note)](https://pypi.org/project/nflreadpy/) · [Open-Meteo terms](https://open-meteo.com/en/terms) · [The Odds API NFL](https://the-odds-api.com/sports/nfl-odds.html) · [OddsShopper on Kalshi TD props](https://www.oddsshopper.com/articles/prediction-markets/kalshi-touchdown-props) · [PredictionMarketsPicks prop board notes](https://predictionmarketspicks.com/nfl/props) · [Sportico on the circuit split](https://www.sportico.com/law/analysis/2026/kalshi-circuit-split-scotus-1234945840/) · [The Block on the 6th Circuit ruling](https://www.theblock.co/news/regulation/2026-09-26-kalshi-loses-appeal-over-ohio-and-tennessee-sports-betting-laws-widening-circuit-split-416937)
