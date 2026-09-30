# Gridiron Edge Worker — rules for Claude Code

## What this repo is
A Python worker that ingests NFL and Kalshi data, computes the metrics in
docs/MODEL_SPEC.md, simulates games, prices Kalshi markets, and writes
recommendations to a Base44 app. A human places every trade by hand.
The build order is docs/BUILD_PLAN.md. Work on ONE phase per session.

## Source of truth
- Every metric, formula, threshold and rule has an ID in docs/MODEL_SPEC.md
  (DATA-, G1-G7, OFF-, DEF-, PLY-, COA-, MTC-, ENV-, PRJ-, EDG-, BT-).
- Every function that implements one starts its docstring with that ID.
- If the spec does not define something you need, STOP and ask. Do not guess.

## Non-negotiables
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
  only read rows with pulled_at <= as_of from games that kicked off earlier.
6. Deterministic. All randomness uses numpy.random.Generator seeded from
  (game_id, model_version). Same inputs must give byte-identical outputs.
7. Money. Prices and fees are integer centicents (1/10,000 of a dollar) to
  match Kalshi's fee rounding. Probabilities are floats in [0, 1].
8. No trading, ever. Never add Kalshi authentication, API keys, or any order,
  portfolio or account endpoint. Public market-data endpoints only.
9. Data sources are only those listed as DATA-01 to DATA-13. No scraping.
  Show "Data: nflverse; charting: FTN Data via nflverse" wherever data is
  exported.
10. Secrets come from .env via pydantic settings. Never print or log them.
11. Stay in the current phase. Do not refactor other phases without asking.

## Reporting when you finish a task
- Paste the exact commands you ran and their real output.
- List what is NOT done, anything mocked, and any assumption you made.
- Never say "works" or "done" without that output.

## Commands
- uv sync
- uv run pytest -m phase<N>
- uv run ruff check . && uv run mypy src
- uv run ge <job> --season <YYYY> --week <W> [--as-of <ISO timestamp>]

