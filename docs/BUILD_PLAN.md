# Gridiron Edge — Python Worker Build Plan

Sep 27, 2026 · @Rhys

## How to run this plan

The worker is built in 11 phases (0–10), **one phase per Claude Code session**, and a phase is done only when its acceptance tests pass on real nflverse or Kalshi data, run by you, not reported by Claude Code. Every metric and model refers back to its ID in the Model Spec v1.

1.  **Set up the repo once.** Create an empty GitHub repo gridiron-edge-worker. Export the Model Spec doc as Markdown and save it as docs/MODEL_SPEC.md. Save this plan as docs/BUILD_PLAN.md. Paste the CLAUDE.md below into the repo root.

2.  **Start each phase in plan mode.** Paste that phase's prompt. Read the plan Claude Code proposes; reject it if it skips a test or invents a number the spec doesn't give.

3.  **Tests before code.** Every prompt tells Claude Code to write the acceptance tests first, show them failing, then build until they pass.

4.  **You run the checks.** Run uv run pytest -m phaseN and the phase's real-data command yourself. If anything fails, paste the output back into the same session.

5.  **Lock it.** Commit, tag phase-N-verified, and move the phase's metrics from SPEC to VERIFIED in the Model Spec.

6.  **Fresh session for the next phase.** Clear context between phases so old assumptions don't leak forward; CLAUDE.md and the docs carry what matters.

**Red flags to stop a session:** a function that returns a hard-coded or "example" number, a test marked skip, a TODO inside a formula, a mock where the phase says real data, or any claim that something works without the command output to prove it.

## Architecture

The worker is the only thing that computes numbers; Base44 stores and displays them, and you are the only one who trades. Data flows one way through six steps, and the only thing Base44 sends back is your trade log, which the worker needs for closing line value.

<img src="media/image1.png" style="width:6in;height:4.41964in" alt="worker architecture · 4 sources, 6 worker steps, Base44" />

worker architecture · 4 sources, 6 worker steps, Base44

The backtest harness (Phase 8) replays steps 2–5 over past seasons from the same store, so live and backtest share one code path.

### Repo layout

gridiron-edge-worker/  
CLAUDE.md rules for Claude Code (below)  
docs/MODEL_SPEC.md exported Model Spec v1  
docs/BUILD_PLAN.md this plan  
config/params.yaml every k, half-life, threshold; "initial" until BT-02  
config/fees.yaml Kalshi series multipliers + schedule date  
config/stadiums.yaml team, lat/lon, roof type, time zone  
src/ge/ingest/ nflverse.py, weather_nws.py, kalshi.py  
src/ge/store/ duckdb schema, as-of queries  
src/ge/metrics/ conventions.py (G1–G7), offense.py, defense.py, player.py, coaching.py, registry.py  
src/ge/models/ ratings.py (PRJ-01), sim/ (PRJ-02), pricing.py (PRJ-03–06), calibration.py (PRJ-07)  
src/ge/edge/ fees.py, sizing.py, exposure.py, clv.py  
src/ge/backtest/ walkforward.py, ablation.py, report.py  
src/ge/sync/ base44.py  
src/ge/cli.py one command per job: ingest, metrics, simulate, price, sync, backtest  
tests/ one folder per phase; fixtures from real past games  
data/ parquet + duckdb (git-ignored)

## Stack and hosting

Plain, boring Python on one always-on Linux VM, with **no Kalshi credentials anywhere in the worker**: it reads public market data only, so it physically cannot place a trade. Base44's external write API is in beta and rate-limited, so the worker writes a small number of compact records rather than raw simulation output.

| Layer            | Choice                                                                                                                        | Why                                                                                                                                                                             |
|------------------|-------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Language and env | Python 3.12, uv for dependencies and lockfile                                                                                 | Reproducible installs; one command to run anything                                                                                                                              |
| Data frames      | polars (what nflreadpy returns); pandas only where a library needs it                                                         | Fast on multi-season play-by-play                                                                                                                                               |
| Store            | DuckDB file + Parquet partitions by season and pull date                                                                      | Point-in-time queries in SQL; no database server to run                                                                                                                         |
| Math             | numpy; numba for the PRJ-02 inner loop; scikit-learn / statsmodels for ridge, logistic, isotonic                              | Deterministic, well-tested, fast enough for 40M simulated plays a week                                                                                                          |
| HTTP             | httpx with retries and backoff (tenacity)                                                                                     | Kalshi, NWS and Base44 calls fail sometimes; every call is retried and logged                                                                                                   |
| Config           | YAML files validated by pydantic                                                                                              | Every parameter in one place; the app refuses to run on a missing or malformed value                                                                                            |
| Tests            | pytest, hypothesis (property tests for fees, Kelly, ladders), fixtures from real past games                                   | Tests are the definition of done                                                                                                                                                |
| Quality          | ruff, mypy (strict on edge/ and models/), pre-commit                                                                          | Catches the sloppy-code failures before you do                                                                                                                                  |
| Scheduling       | systemd timers calling ge \<job\> CLI commands; one long-running game-day poller service                                      | Survives reboots; each job is idempotent and logs to a file                                                                                                                     |
| Hosting          | Small always-on Linux VM, 4 vCPU / 8 GB RAM to start                                                                          | Game-day polling needs a process that is always up; GitHub Actions cron runs can be delayed at busy times                                                                       |
| Secrets          | .env on the VM only, never committed: BASE44_APP_ID, BASE44_API_KEY, NWS_USER_AGENT                                           | The Base44 key can edit your app's data, so it stays off GitHub                                                                                                                 |
| Base44 writes    | [<u>Base44 Apps API</u>](https://docs.base44.com/api-reference/create-entity-record) entity endpoints with a personal API key | Documented limits: create 140 requests per minute per app, [<u>update 100 per minute</u>](https://docs.base44.com/api-reference/update-entity-record); the API is labelled beta |
| Alerts           | A failure message to your phone (Slack webhook or email; your choice)                                                         | A silent failed job on Sunday morning is the worst failure                                                                                                                      |

**What the beta API means for the design.** Base44 itself warns against depending on the beta API in production, and a full week of per-market projections could run to thousands of rows. So the worker writes one GameProjection record per game (market probabilities packed in a JSON field), one record per Recommendation, and scorecard rows, which is tens of writes per run, not thousands. The DuckDB store on the VM stays the source of truth, and a sync failure never loses data: the next run re-sends.

## CLAUDE.md (paste into the repo root)

Claude Code reads this file at the start of every session, so the non-negotiables live here rather than being repeated in each prompt. Copy the block exactly.

\# Gridiron Edge Worker — rules for Claude Code  
  
\## What this repo is  
A Python worker that ingests NFL and Kalshi data, computes the metrics in  
docs/MODEL_SPEC.md, simulates games, prices Kalshi markets, and writes  
recommendations to a Base44 app. A human places every trade by hand.  
The build order is docs/BUILD_PLAN.md. Work on ONE phase per session.  
  
\## Source of truth  
- Every metric, formula, threshold and rule has an ID in docs/MODEL_SPEC.md  
(DATA-, G1-G7, OFF-, DEF-, PLY-, COA-, MTC-, PRJ-, EDG-, BT-).  
- Every function that implements one starts its docstring with that ID.  
- If the spec does not define something you need, STOP and ask. Do not guess.  
  
\## Non-negotiables  
1. No numbers from memory. Every constant lives in config/params.yaml or  
config/fees.yaml with its spec ID and a status of initial or fitted.  
2. Never write real-world facts into code: no player names, stats, injuries,  
coaches or schedules. Test fixtures come from downloaded data, with the  
source and pull date recorded in the fixture file.  
3. No stubs that return plausible values. Unfinished code raises  
NotImplementedError with the spec ID.  
4. Tests first. Never skip, xfail or loosen a tolerance to make a test pass.  
If a test seems wrong, say so and wait for approval.  
5. Point in time. Any computation for a game takes an as_of timestamp and may  
only read rows with pulled_at \<= as_of from games that kicked off earlier.  
6. Deterministic. All randomness uses numpy.random.Generator seeded from  
(game_id, model_version). Same inputs must give byte-identical outputs.  
7. Money. Prices and fees are integer centicents (1/10,000 of a dollar) to  
match Kalshi's fee rounding. Probabilities are floats in \[0, 1\].  
8. No trading, ever. Never add Kalshi authentication, API keys, or any order,  
portfolio or account endpoint. Public market-data endpoints only.  
9. Data sources are only those listed as DATA-01 to DATA-12. No scraping.  
Show "Data: nflverse; charting: FTN Data via nflverse" wherever data is  
exported.  
10. Secrets come from .env via pydantic settings. Never print or log them.  
11. Stay in the current phase. Do not refactor other phases without asking.  
  
\## Reporting when you finish a task  
- Paste the exact commands you ran and their real output.  
- List what is NOT done, anything mocked, and any assumption you made.  
- Never say "works" or "done" without that output.  
  
\## Commands  
- uv sync  
- uv run pytest -m phase\<N\>  
- uv run ruff check . && uv run mypy src  
- uv run ge \<job\> --season \<YYYY\> --week \<W\> \[--as-of \<ISO timestamp\>\]

## Phases 0–3: foundation

These four phases produce no predictions at all; they make every later number trustworthy. Expect them to take longer than you want, and don't skip ahead: a simulation built on a leaky store will backtest beautifully and lose money live.

### Phase 0 — Scaffold and guardrails

**Spec IDs:** none (infrastructure). **Done when:** config loads, every spec ID in config exists in the spec, CI is green.

Phase 0. Read CLAUDE.md, docs/MODEL_SPEC.md and docs/BUILD_PLAN.md first.  
Set up the repo exactly as the Repo layout in BUILD_PLAN.md shows: a uv  
project with package \`ge\` under src/, a typer CLI \`ge\` with placeholder  
subcommands ingest, metrics, simulate, price, sync, backtest (each raises  
NotImplementedError for now), and pytest markers phase0 to phase10.  
Create config/params.yaml containing EVERY numeric value the spec labels  
"initial" (all k values, half-lives, lambda, beta, return factor, OL factor,  
edge thresholds, caps, tolerances), each entry with spec_id, value, and  
status: initial. Create config/fees.yaml from the EDG-02 table with  
schedule_effective_date 2026-07-07. Load both through pydantic models that  
fail loudly on a missing or extra key. Add ruff, mypy and pre-commit, and a  
GitHub Actions workflow running ruff, mypy and pytest.  
Write these tests first and show them failing before you implement.

- ☐ uv sync completes with a committed lockfile

- ☐ uv run ge --help lists all six jobs

- ☐ Test: params.yaml loads; deleting any key makes loading fail

- ☐ Test: every spec_id in params.yaml and fees.yaml appears in docs/MODEL_SPEC.md

- ☐ Test: every value the spec labels "initial" appears in params.yaml (you spot-check 10 by hand)

- ☐ GitHub Actions run is green

### Phase 1 — Data ingestion

**Spec IDs:** DATA-01 to DATA-09. **Done when:** 2016–2025 plus 2026 to date is stored with pull timestamps, and live Kalshi and NWS pulls work.

Phase 1. Implement src/ge/ingest/ for DATA-01 to DATA-09 in MODEL_SPEC.md.  
1) nflverse via nflreadpy: pbp, FTN charting, participation, snap counts,  
rosters, depth charts, schedules, injuries, player stats and Next Gen  
Stats for 2016 to the current season (FTN from 2022). Save as Parquet  
partitioned by dataset/season/pulled_at, adding columns pulled_at (UTC)  
and source.  
2) config/stadiums.yaml: one row per stadium in the schedules data with  
lat, lon, roof, time zone and a source_url I will fill in; write a check  
that fails if any 2026 game's stadium is missing or has no source_url.  
Do NOT fill coordinates from memory.  
3) NWS client: hourly forecast (wind, gusts, precipitation probability and  
amount, temperature) for each outdoor game within 7 days of kickoff.  
Requires a User-Agent from .env. Skip dome/closed roofs.  
4) Kalshi public client, no auth: series, events, markets (with rules text),  
orderbook, trades, candlesticks and historical endpoints, with  
pagination, retries and backoff. Discover every NFL series ticker and  
store it. Derive YES ask = 1 - best NO bid and NO ask = 1 - best YES bid,  
in integer centicents.  
5) \`ge ingest fees-check\`: download the Kalshi fee schedule PDF, read its  
"Last updated and effective" date, and exit non-zero with an alert if it  
differs from fees.yaml.  
Every ingest must be idempotent. Tests first.

- ☐ Test: for every completed season, the set of game IDs in play-by-play equals the completed games in schedules

- ☐ Test: FTN rows join to play-by-play on game and play ID with unique keys; the phase report prints the join rate per season for you to review

- ☐ Test: running ingest twice creates no duplicate rows

- ☐ Test: a saved real Kalshi order-book snapshot (fixture) produces the correct YES and NO asks

- ☐ Live check: uv run ge ingest kalshi --season 2026 --week \<current\> lists every NFL market for the week with rules text

- ☐ Live check: uv run ge ingest weather --days 7 returns hourly wind for each outdoor game and skips domes

- ☐ Live check: uv run ge ingest fees-check exits 0 today

### Phase 2 — Point-in-time store

**Spec IDs:** BT-01, G4. **Done when:** any game's inputs can be rebuilt exactly as they stood at any past moment, and the leakage test passes.

Phase 2. Implement src/ge/store/ for BT-01. Build a DuckDB database over the  
Phase 1 Parquet files and a function snapshot(game_id, as_of) that returns  
every input a later phase may use for that game: plays only from games that  
kicked off before as_of, injury and practice reports published before as_of,  
the depth chart dated on or before as_of, the latest weather forecast pulled  
before as_of, and Kalshi prices as of as_of. Default as_of = kickoff minus  
24 hours; allow kickoff minus 90 minutes. Add a leakage test: shuffle or  
delete every game on or after the target game in a copy of the store and  
assert the snapshot is byte-identical. Tests first.

- ☐ Leakage test passes on 20 randomly chosen 2022–2025 games

- ☐ Test: no snapshot contains a play from the target game or any later game

- ☐ Test: a player listed Out on the Friday report appears as Out in a Saturday as_of and not in a Tuesday as_of

- ☐ Test: the same snapshot requested twice is identical

- ☐ Live check: uv run ge store snapshot --game \<a real 2026 game ID\> prints a summary you can sanity-check against what you know about that week

### Phase 3 — Metric engine

**Spec IDs:** G1–G7, OFF-01 to OFF-17, DEF-01 to DEF-08, PLY-01 to PLY-15, COA-01 to COA-07. **Done when:** every free-data metric computes from a snapshot, matches independent checks, and paid-only metrics refuse cleanly.

Phase 3. Implement src/ge/metrics/. First conventions.py for G1-G7 exactly  
as MODEL_SPEC.md defines them: shrink(observed, n, prior, k), recency  
weights w = 0.5^(g/h) with n_eff = (sum w)^2 / sum w^2, prior-season  
carryover, the neutral-script and garbage-time filters, and the ridge  
opponent adjustment. Then one pure function per metric in offense.py,  
defense.py, player.py and coaching.py, each taking a snapshot and returning  
value, n, n_eff, shrunk value, and a below_min_sample flag. Store directions  
in the offense's frame (spec section 3). register every metric in  
registry.py with its spec ID, min n, k and h read from params.yaml.  
Metrics marked PAID (PLY-02 full, PLY-08 full, PLY-12, DEF-04b, DEF-05b,  
COA-05b) must raise NotImplementedError("PAID: DATA-11"); implement their  
v1 proxies where the spec gives one. COA-01 is a CSV registry: validation  
fails any row without a source_url and effective date. Tests first.

- ☐ Property tests (hypothesis): shrink returns the prior at n = 0, the midpoint at n = k, and approaches the observed value as n grows

- ☐ Golden test: for one real game fixture, EPA per play and success rate per team equal a value the test computes independently from raw rows

- ☐ Cross-check: per player-week targets, carries and receiving yards match nflverse player stats for 2025 on at least 99% of player-weeks; every mismatch is listed in the report

- ☐ Test: OFF-12 cell carries sum to the team's designed carries

- ☐ Test: every metric row in spec sections 2–5 has a registry entry; PAID metrics raise the PAID error

- ☐ Test: COA-01 validation rejects a row with no source_url

- ☐ Live check: uv run ge metrics --season 2026 --through-week \<last completed\> writes a table for all 32 teams; you spot-check 5 numbers against a public site you trust

## Phases 4–6: the models

This is where most of the risk lives. The tests here check that the models are internally correct and reproduce real football on average; whether they beat the market is a separate question that only Phase 8 answers.

### Phase 4 — Team ratings (model mode)

**Spec IDs:** PRJ-01a, G6, COA-07. **Done when:** ratings recover planted effects on synthetic data and run walk-forward on real seasons.

Phase 4. Implement PRJ-01a in src/ge/models/ratings.py: weighted ridge  
ratings for offense and defense, pass and run separately, with home-field,  
rest, travel and time-zone terms (COA-07), recency half-life from  
params.yaml, and conversion to expected points per drive. Ratings for any  
game must be built only from snapshot(game_id, as_of). Fit the ridge penalty  
by cross-validation on training seasons only (2016-2021). Also write a  
synthetic-data generator that plants known team effects so the fitter can be  
tested against the truth. Tests first. Do not build PRJ-01b yet; it needs  
the simulator.

- ☐ Test: on synthetic plays with planted effects, recovered ratings correlate above 0.9 with the truth and the home term is within 10% of the planted value

- ☐ Test: ratings for a game change by zero when any later game is altered (reuses the Phase 2 leakage harness)

- ☐ Report: for each week of 2022–2025, the rating-implied spread vs the closing spread_line, with mean absolute difference per season. You review it; no pass/fail, because beating the market is Phase 8's question

- ☐ Live check: uv run ge ratings --season 2026 --through-week \<last\> prints all 32 teams ranked, with each rating's standard error

### Phase 5 — Game simulation

**Spec IDs:** PRJ-02, PRJ-01b, MTC-01 to MTC-05. **Done when:** the simulator reproduces a real season's league averages within the spec's tolerances, is fully reproducible, and the market-anchor solver works.

Phase 5. Implement PRJ-02 in src/ge/models/sim/ exactly as MODEL_SPEC.md  
section 7 lists its six steps, with numba for the play loop and a seeded  
numpy Generator per game. Apply the matchup residuals MTC-01 to MTC-03 with  
lambda and the +/-15% cap from params.yaml, and weather via MTC-05. Each run  
records the final score, every player's stat line, and the order of  
touchdowns. Store per-game results as compact arrays (not per-play logs).  
Then implement PRJ-01b: solve for team ratings, holding pass/run mix from  
01a, so the simulated median margin and median total match a given spread  
and total within 0.25 points. Tests first.

- ☐ Test: simulating all 2024 games from true pre-game snapshots reproduces league averages within PRJ-02 tolerances: points per team-game ±0.7, plays ±2, pass rate ±1.5 points, yards per attempt ±0.2

- ☐ Test: the standard deviation of simulated margins is within 1 point of the actual 2016–2025 margin standard deviation, which the test computes from schedules (not from memory)

- ☐ Test: in every run, player receiving yards sum to team passing yards, and player TDs sum to team offensive TDs

- ☐ Test: same game, same seed → identical output; different seed → different output

- ☐ Test: PRJ-01b hits a target spread and total within 0.25 points for 20 real games

- ☐ Test: with λ = 0 the matchup layer changes nothing

- ☐ Timing: 20,000 runs of one game completes on the VM in a time you record in the report (target under 60 seconds)

### Phase 6 — Market pricing

**Spec IDs:** PRJ-03 to PRJ-07. **Done when:** every mapped Kalshi NFL market for the week has a probability, and every market whose rules can't be parsed is marked unpriced rather than guessed.

Phase 6. Implement src/ge/models/pricing.py and calibration.py.  
1) Market mapper: turn each Kalshi NFL market's rules text into a settlement  
spec (market type, player, stat, threshold as "X or more", whether  
overtime counts, what happens with no TD). Any market the mapper cannot  
parse with certainty is status=unpriced with the reason. Never guess.  
2) Prices from the PRJ-02 runs: anytime, first, first-team and 2+ TD with  
the Poisson cross-check (flag and block if they differ by \>3 points);  
stat ladders as P(stat \>= X), enforced non-increasing across strikes;  
same-game combos as the share of runs where every leg hits, plus the  
correlation lift; multi-game combos as products.  
3) PRJ-06 season simulator: 20,000 seasons, each drawing team ratings from  
their uncertainty first, NFL tiebreakers through strength of victory then  
a coin flip; season stat totals with weekly missed-game probabilities.  
4) PRJ-07 calibration: reliability table (10 bins), Brier, log loss,  
logistic recalibration slope. Tests first; save 10 real Kalshi rules  
texts as fixtures for the mapper tests.

- ☐ Test: all 10 rules-text fixtures map to the correct settlement spec; a deliberately garbled one maps to unpriced

- ☐ Report: share of this week's NFL markets mapped vs unpriced, with reasons for every unpriced one

- ☐ Test: every ladder's probabilities are non-increasing

- ☐ Test: for a combo of legs from two different games, joint probability equals the product of the legs

- ☐ Test: division-winner probabilities sum to 1 in every division; Super Bowl winner probabilities sum to 1

- ☐ Test: on synthetic, perfectly calibrated forecasts the calibration slope is 1.00 ± 0.05

- ☐ Live check: uv run ge price --season 2026 --week \<current\> prints, for one game you pick, every TD and yardage market with our probability beside Kalshi's ask

## Phases 7–10: decisions, proof, and running it

Phase 7 turns probabilities into sized recommendations, Phase 8 decides whether any market type deserves real money, and Phases 9–10 run it every week without you babysitting it. **Nothing reaches you as a live recommendation until Phase 8's go-live report says that market type passed.**

### Phase 7 — Edge and decision layer

**Spec IDs:** EDG-01 to EDG-08. **Done when:** fees, sizing, exposure, stops and CLV are pure functions that pass property tests and reproduce Kalshi's published fee table.

Phase 7. Implement src/ge/edge/ for EDG-01 to EDG-08, all as pure functions  
on integer centicents. fees.py: taker and maker formulas with per-series  
multipliers from fees.yaml. Kalshi's fee PDF is internally inconsistent: the  
formula text says fee plus cost rounds up to a centicent, but its printed  
table rounds fees up to the cent. Implement rounding as a config switch  
(cent \| centicent), default cent (the conservative choice), and do not  
resolve it by guessing. sizing.py: quarter-Kelly f\* = (p - c)/(1 - c), caps  
from params.yaml, skip stakes under 0.25%, sizing bankroll = min(current,  
start of week). exposure.py: 6% per game including any combo with a leg in  
that game; weekly -10% stop on the Tuesday-Monday Eastern week; chase check.  
Liquidity: max contracts = min(bankroll size, 25% of depth within 2 cents);  
ignore books with a spread over 20 cents. clv.py: closing price = last trade  
before kickoff from the trades endpoint, plus closing mid. Recommendations  
for a team are withdrawn when injury news for that team arrives. Tests first,  
including hypothesis property tests.

- ☐ Test (rounding = cent): taker fees for 100 contracts reproduce every row of the official table, for example \$0.05 → \$0.34, \$0.10 → \$0.63, \$0.50 → \$1.75, \$0.99 → \$0.07

- ☐ Test: KXNFLGAME resting orders pay the maker fee; a default-series resting order pays zero; KXMVE combos use maker multiplier 2

- ☐ Property: no stake ever exceeds its cap; no recommendation exists when edge after fees is below the market-type threshold

- ☐ Property: within a week, the sizing bankroll never rises after a settled loss

- ☐ Test: a seventh position that would take one game above 6% is cut down or refused

- ☐ Test: at −10% for the week, no new recommendation is produced until Tuesday 00:00 Eastern

- ☐ Test: CLV on a saved real trades fixture matches a hand calculation

### Phase 8 — Backtest harness

**Spec IDs:** BT-02 to BT-06, PRJ-07. **Done when:** one command produces a reproducible go-live report with pass or fail for every market type against BT-05.

Phase 8. Implement src/ge/backtest/. walkforward.py replays phases 3-7 for  
every game from 2022 on, using snapshots only, fitting every parameter on  
seasons before the test season (BT-02) and writing fitted values to a new  
versioned params file (never overwriting the initial one). ablation.py  
switches each MTC adjustment and tendency input off one at a time and keeps  
it only if out-of-sample log loss improves (BT-03). report.py produces, per  
market type: calibration table and slope, Brier and log loss vs the market,  
the blend-test weight b with its p-value, simulated CLV after fees with a  
95% interval, and a PASS/FAIL line for each BT-05 criterion. Kalshi history  
comes from its historical endpoints (2025 on); earlier game lines from  
nflverse schedules. Add a canary test: inject the game's final score as a  
feature and confirm the leakage guard stops the run. Tests first.

- ☐ Canary test: an injected future feature makes the run fail with a leakage error

- ☐ Test: running the full backtest twice produces byte-identical reports

- ☐ Test: fitted parameters for season S use no data from season S or later

- ☐ Report saved to docs/reports/backtest\_\<date\>.md with PASS/FAIL per market type and per BT-05 criterion

- ☐ You read the report and record in the Model Spec's decisions log which market types, if any, may proceed to paper trading

### Phase 8b — Historical Performance Report

**Spec IDs:** BT-07a to BT-07e. **Done when:** one command produces the 2021–2024 report from production code, the 2025 holdout refuses to run without a frozen tag, and results reach Base44.

Phase 8b. Implement BT-07 from MODEL_SPEC.md in src/ge/backtest/report.py  
and holdout.py. Replay 2021-2024 walk-forward by calling the production  
modules only (ge.metrics, ge.models, ge.edge); season S uses parameters fit  
on 2016 through S-1. 2021 runs with FTN inputs at their priors, labelled  
"no FTN". Tag every position with its history tier from BT-07c (Full,  
Partial, Kalshi-only) and price it exactly as that table says; Full-tier  
CLV is n/a. For each season x market type, compute every BT-07d metric and  
the BT-07e bankroll curves (portfolio and isolated) through the production  
EDG-06/07 code. Cells under 50 positions report "too few to read".  
Stamp the report with git commit, params version and hash, and data  
snapshot hash. holdout.py: \`--season 2025\` refuses to run unless given a  
model tag listed in holdout_ledger.yaml; running it writes the opening to  
the ledger once, and any later model version shows 2025 as "holdout spent".  
Write BacktestResult records to Base44 (data contract). Tests first.

- ☐ Test: a backtest module that defines its own fee, Kelly or probability formula fails the build

- ☐ Test: ge backtest --season 2025 without a frozen tag exits with an error and computes nothing

- ☐ Test: after the ledger records an opening, a changed params file marks 2025 results "holdout spent"

- ☐ Test: bankroll curves obey every EDG rule (no stake over cap, weekly stop enforced, 6% per game) on the replayed positions

- ☐ Test: two runs from the same commit and data give byte-identical BacktestResult records

- ☐ Report: 2021–2024 with tier labels; you confirm Full-tier rows show CLV as n/a and Kalshi-only rows show no history

### Phase 9 — Base44 sync, scheduler, paper mode

**Spec IDs:** EDG-07, EDG-08, BT-05 (paper-trading criterion). **Done when:** a real week flows end to end into Base44, every recommendation is auto-logged as a paper position, and the kill switches work.

Phase 9. Implement src/ge/sync/base44.py against the Base44 Apps API entity  
endpoints with a personal API key from .env. Respect the documented rate  
limits with backoff on 429, and upsert by our own IDs so re-runs never  
duplicate. Write only the entities in BUILD_PLAN.md's data contract. Read  
Position and ManualNews records the user creates. Read SystemStatus before  
every run: if access_ok is false or weekly_stop is true, write no new  
recommendations. Paper mode: every recommendation is also recorded as a  
paper position at the price the book offered at that moment, and its CLV is  
scored at kickoff. Market types that have not passed Phase 8 are labelled  
PAPER ONLY in every record. Add systemd unit and timer files for the  
schedule in BUILD_PLAN.md. Tests first; use a separate Base44 test app for  
integration tests, never the live one.

- ☐ Integration test against a Base44 test app: create, update and re-run with no duplicates

- ☐ Test: a forced 429 response is retried with backoff and the run still completes

- ☐ Test: with access_ok = false, a full run writes zero recommendations

- ☐ End to end: one real week appears in the Base44 preview with correct games, probabilities, prices, sizes and PAPER ONLY labels

- ☐ A position you enter in Base44 is picked up and its CLV is scored after kickoff

### Phase 10 — Live operations

**Spec IDs:** DATA-09 (weekly fee check), BT-05, BT-06. **Done when:** the worker survives a reboot, a crashed job and stale data, alerts you each time, and has completed four weeks of paper trading.

Phase 10. Harden for unattended running: systemd services restart on  
failure and on boot; every job writes a RunLog record (start, end, status,  
rows, data freshness) to Base44; alerts go to my phone on any failed job,  
any data source older than its freshness limit, a changed Kalshi fee  
schedule date, or a Kalshi API that stops returning NFL markets. Nightly  
backup of the DuckDB file and Parquet store. Implement BT-06 stop rules on  
live and paper CLV and show them in the Scorecard entity. Write  
docs/RUNBOOK.md: how to restart, restore a backup, rotate the Base44 key,  
and pause everything. Tests first where testable.

- ☐ Reboot the VM: all timers and the game-day poller come back without you touching them

- ☐ Kill a job mid-run: the next scheduled run completes and the RunLog shows both

- ☐ Point ingest at an old snapshot: the stale-data alert reaches your phone

- ☐ Restore last night's backup to a fresh folder and re-run one week with identical output

- ☐ Four consecutive weeks of paper trading logged with no manual edits, CLV reported per market type

## Base44 ↔ worker data contract

Eight entities, and one rule: **Base44 never computes a number.** It displays what the worker wrote and stores what you type. Prices are integer centicents; probabilities are 0–1.

| Entity         | Written by                           | Key fields                                                                                                                                                                                                                                                                                                                                                                | Writes per week (rough)        |
|----------------|--------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------|
| SystemStatus   | You (worker sets weekly_stop)        | access_ok, paused, weekly_stop, note, updated_at                                                                                                                                                                                                                                                                                                                          | a few                          |
| GameProjection | Worker                               | game_id, season, week, kickoff_utc, as_of, model_version, median_margin, median_total, markets_json (ticker → p, asks, status), story_text, story_valid                                                                                                                                                                                                                   | 16 games × runs per day        |
| Recommendation | Worker                               | rec_id, game_id, market_ticker, side, p_model, max_price_cc, edge_cc, roi, stake_pct, contracts, depth_contracts, volume_24h, thin, mode (PAPER ONLY / LIVE), expires_at, withdrawn, withdraw_reason, spec_ids                                                                                                                                                            | tens                           |
| Position       | You enter; worker adds close and CLV | position_id, rec_id (blank if off-list), market_ticker, side, entry_price_cc, contracts, fee_cc, filled_at; worker: close_price_cc, clv_cc, settled, pnl_cc, rule_break                                                                                                                                                                                                   | as many as you trade           |
| ManualNews     | You                                  | team, player, type (injury, inactive, weather, depth chart), text, source_url, entered_at                                                                                                                                                                                                                                                                                 | as news breaks                 |
| Scorecard      | Worker                               | market_type, mode, n_positions, mean_clv_cc, clv_se_cc, ci_low_cc, ci_high_cc, status (paper, live, stopped), rule_breaks                                                                                                                                                                                                                                                 | one per market type per day    |
| RunLog         | Worker                               | job, started_at, ended_at, status, rows, freshness_json, error                                                                                                                                                                                                                                                                                                            | a few per job run              |
| BacktestResult | Worker (Phase 8b)                    | season (2021–2025 or all), market_type, tier, positions, win_pct, exp_win_pct, calib_z, roi, roi_ci_low, roi_ci_high, mean_clv_cc (blank for Full tier), clv_se_cc, max_drawdown_pct, longest_losing_streak, curve_type (portfolio or isolated), bankroll_curve_json, notes, holdout_status (locked, opened, spent), model_tag, params_version, code_commit, generated_at | a few hundred per backtest run |

**Base44 prompt to create the entities** (paste into Base44 chat, attach the Model Spec):

Create seven entities exactly as named with exactly these fields and types:  
SystemStatus, GameProjection, Recommendation, Position, ManualNews,  
Scorecard, RunLog (fields as in the attached build plan's data contract).  
All money fields ending in \_cc are integers. p_model and probabilities are  
numbers between 0 and 1. Do NOT add any calculation, formula, default value  
or computed field anywhere in the app: every number shown comes from a  
record an external worker writes. Build three pages: This Week (games with  
their recommendations, PAPER ONLY badge, depth and volume shown, withdrawn  
recommendations greyed out), Log a Trade (form creating a Position; rec_id  
picked from open recommendations or left blank), and Scorecard (Scorecard  
records plus the latest RunLog per job). Add a single SystemStatus toggle  
"Kalshi sports access OK in Florida" on a Settings page.

Acceptance tests in Base44 preview: create a Position with a 45¢ entry and confirm the stored value is 4500; confirm no page shows any number when the worker has written nothing (empty states, not zeros or examples); flip the access toggle off and confirm access_ok = false in the data screen.

### Backtest screen

The Backtest screen shows the BT-07 report exactly as the worker wrote it, filtered by season and market type; Base44 plots the stored bankroll series but calculates nothing, and the 2025 holdout shows no numbers until it is opened.

Add an entity BacktestResult with exactly the fields listed for it in the  
attached build plan's data contract (money fields ending in \_cc are  
integers; bankroll_curve_json is text holding a list of {date, bankroll}).  
Add a Backtest page:  
- Two toggles at the top: Season (2021, 2022, 2023, 2024, 2025, All) and  
Market type (every market_type present in the records, plus All).  
- A table of the matching records: market type, tier badge (Full, Partial,  
Kalshi-only), positions, win % beside expected win %, calibration z, ROI  
with its interval shown as "roi (low to high)", mean CLV ± SE, max  
drawdown, longest losing streak, notes.  
- Where mean_clv_cc is empty show "n/a (closing price only)", never 0.  
- Where notes says "too few to read" show that text instead of the numbers.  
- A line chart of bankroll_curve_json for the selected rows, with a switch  
between the portfolio and isolated curve_type.  
- If holdout_status is "locked" for 2025, show "Locked holdout: opens once  
when the model is frozen" and no numbers. If "spent", show a warning  
badge on every 2025 row.  
- A header line showing model_tag, params_version, code_commit and  
generated_at from the records.  
- A fixed note under the table: "One season of wins and ROI is mostly  
noise. CLV is the scorecard."  
Do NOT compute, average, total or fill in any value. Every number shown  
comes straight from a BacktestResult field. Empty data shows an empty  
state, never example numbers.

Acceptance tests in Base44 preview, using records the worker writes to the test app: switching Season to 2023 and Market type to Anytime TD shows only matching rows; a Full-tier row shows "n/a (closing price only)" for CLV; a 2025 row with holdout_status = locked shows the lock message and no numbers; editing one record's roi in the data screen changes the displayed value exactly, proving nothing is recalculated; with no records, the page shows an empty state.

## Weekly run schedule (Eastern time)

The heavy work runs Tuesday, the pricing runs daily, and the game-day poller does the fast work on Sundays; prop ladders often aren't really priced until a day or two before kickoff, so Friday through Sunday matter most. Times are starting values in the systemd timers, easy to change.

| When                                          | Job                                          | What it does                                                                                                   |
|-----------------------------------------------|----------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| Tue 06:00                                     | ge ingest nflverse → ge metrics → ge ratings | Loads the completed week; fails with an alert if nflverse hasn't updated yet, then retries hourly              |
| Tue 07:00                                     | ge ingest fees-check                         | Alerts if the Kalshi fee schedule date changed                                                                 |
| Tue–Sat 08:00 daily                           | ge simulate → ge price → ge sync             | Re-simulates and prices every upcoming game with the latest snapshot                                           |
| Wed–Fri, evening                              | ge ingest injuries → re-price affected games | Picks up each day's practice report and Friday game statuses                                                   |
| Every run                                     | ge ingest weather                            | Latest forecast for outdoor games within 7 days                                                                |
| Kickoff − 24 h, each game                     | Decision-time snapshot (as_of)               | The price and inputs recorded for backtest-comparable CLV                                                      |
| Game days, every 5 minutes until last kickoff | Game-day poller                              | Re-reads order books, checks ManualNews, withdraws or re-prices; respects Kalshi's rate limits read in Phase 1 |
| Kickoff − 90 min, each game                   | Inactives run                                | Re-prices after you enter inactives in ManualNews                                                              |
| Kickoff + 5 min, each game                    | Close capture                                | Stores last trade before kickoff and the closing mid; scores CLV for every paper and real position             |
| Mon 23:59                                     | Week close                                   | Settles the week's P&L, resets the weekly stop, writes Scorecard                                               |
| Nightly 03:00                                 | Backup                                       | Copies the DuckDB file and Parquet store off the VM                                                            |

Thursday, Saturday and Monday games get the same kickoff-relative jobs automatically, because the poller reads kickoff times from schedules rather than assuming Sunday.

## Open questions before Phase 0

None of these block Phase 0, but each blocks a later phase if left open.

- ☐ **VM provider and budget** (blocks Phase 9). Any Linux VM with 4 vCPU / 8 GB works; pick one you already have an account with.

- ☐ **Base44 test app** (blocks Phase 9). Duplicate the Gridiron Edge app so integration tests never touch live data.

- ☐ **Alert channel** (blocks Phase 10): Slack webhook or email.

- ☐ **Fee rounding** (blocks Phase 7 sign-off): Kalshi's PDF formula text and its printed table disagree. Confirm with your first real fill or Kalshi support; until then the worker uses the conservative cent rounding.

- ☐ **Stadium coordinates** (blocks Phase 1 sign-off): you fill config/stadiums.yaml with a source URL per row.

- ☐ **Historical props odds** (affects Phase 8): without a paid odds history, the props backtest has only Kalshi's own history from 2025 on, which is about one season of games. That is a small sample for props; the report will say so plainly.

- ☐ **Personal tool or company product**: decides Open-Meteo licensing and any future data licenses.

- ☐ **Stake cap reading** in the Model Spec (the open comment on EDG-06) sets two values in params.yaml.

## Sources

[<u>Base44: Create entity record</u>](https://docs.base44.com/api-reference/create-entity-record) · [<u>Base44: Update entity record</u>](https://docs.base44.com/api-reference/update-entity-record) · [<u>Base44 docs index (Apps API, beta)</u>](https://docs.base44.com/llms.txt) · [<u>Kalshi fee schedule (effective July 7, 2026)</u>](https://kalshi.com/docs/kalshi-fee-schedule.pdf)
