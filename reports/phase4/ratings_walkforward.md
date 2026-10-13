# Phase 4: rating-implied lines against closing lines (PRJ-01a)

Seasons 2021, 2022, 2023, 2024, walk-forward (each season rated with its own window's fits; never the 2025 holdout, BT-07b). Every game is rated only from its own snapshot (snapshot(game_id), decision-time as_of). Closing lines and results are read only here, after the fact. Report only: no pass/fail; beating the market is Phase 8's question.

Rated: 1075 games; skipped: 64 (listed at the end).

## Sign convention

nflverse schedules `spread_line` is positive when the home team is favoured: home team favoured = positive. Checked in every season before any comparison (both correlations must be positive):

| season | n | corr_spread | corr_total |
| --- | --- | --- | --- |
| 2021 | 285 | 0.463 | 0.252 |
| 2022 | 284 | 0.386 | 0.284 |
| 2023 | 285 | 0.408 | 0.303 |
| 2024 | 285 | 0.487 | 0.320 |

So spread_diff = rating spread (home minus away points) - spread_line, and total_diff = rating total - total_line, with no sign flip. Points are final scores including overtime and non-offensive scores, as the closing lines and Kalshi settle them: Kalshi's FOOTBALLSPREAD contract terms count all scoring in overtime periods toward the final margin, and FOOTBALLTOTALS counts overtime for all markets unless stated otherwise (contract terms retrieved 2026-10-12 from assets.kalshi.com).

## Differences by season

Mean absolute difference (mad) and mean signed difference (bias); regular season (REG) and postseason (POST) separately.

| season | phase | n | spread_mad | spread_bias | total_mad | total_bias |
| --- | --- | --- | --- | --- | --- | --- |
| 2021 | REG | 256 | 4.326 | -2.153 | 2.653 | 0.810 |
| 2021 | POST | 13 | 3.965 | -3.623 | 2.532 | -0.907 |
| 2022 | REG | 255 | 3.865 | -2.258 | 3.070 | 2.011 |
| 2022 | POST | 13 | 4.248 | -3.645 | 2.093 | 0.374 |
| 2023 | REG | 256 | 3.515 | -1.864 | 2.667 | 0.283 |
| 2023 | POST | 13 | 4.911 | -4.145 | 2.685 | -1.259 |
| 2024 | REG | 256 | 3.300 | -1.636 | 2.615 | 1.103 |
| 2024 | POST | 13 | 3.895 | -3.009 | 1.572 | -0.090 |

## Differences by week

| season | phase | week | n | spread_mad | spread_bias | total_mad | total_bias |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | REG | 2 | 16 | 3.313 | -2.303 | 2.965 | -0.301 |
| 2021 | REG | 3 | 16 | 3.832 | -2.497 | 2.925 | -0.161 |
| 2021 | REG | 4 | 16 | 3.181 | -2.573 | 2.801 | -0.057 |
| 2021 | REG | 5 | 16 | 3.842 | -2.177 | 2.394 | 0.428 |
| 2021 | REG | 6 | 14 | 4.136 | -0.798 | 2.854 | 0.629 |
| 2021 | REG | 7 | 13 | 5.530 | -4.285 | 3.309 | 2.235 |
| 2021 | REG | 8 | 15 | 4.556 | -1.668 | 2.668 | 0.920 |
| 2021 | REG | 9 | 14 | 5.505 | -3.917 | 2.726 | 1.142 |
| 2021 | REG | 10 | 14 | 3.996 | -0.815 | 2.492 | -0.460 |
| 2021 | REG | 11 | 15 | 4.120 | -2.517 | 2.446 | 0.046 |
| 2021 | REG | 12 | 15 | 2.340 | -1.241 | 1.746 | 0.553 |
| 2021 | REG | 13 | 14 | 3.604 | -0.324 | 2.159 | 0.981 |
| 2021 | REG | 14 | 14 | 4.372 | -2.435 | 2.883 | 0.709 |
| 2021 | REG | 15 | 16 | 5.332 | -2.194 | 2.193 | 0.995 |
| 2021 | REG | 16 | 16 | 4.649 | -2.096 | 2.405 | 1.698 |
| 2021 | REG | 17 | 16 | 6.318 | -4.732 | 3.121 | 1.642 |
| 2021 | REG | 18 | 16 | 5.013 | -0.052 | 3.046 | 2.854 |
| 2021 | POST | 19 | 6 | 4.433 | -4.433 | 2.503 | 0.144 |
| 2021 | POST | 20 | 4 | 3.757 | -3.757 | 2.623 | -1.313 |
| 2021 | POST | 21 | 2 | 3.850 | -3.850 | 2.081 | -2.081 |
| 2021 | POST | 22 | 1 | 2.219 | 2.219 | 3.243 | -3.243 |
| 2022 | REG | 2 | 16 | 4.382 | -2.866 | 2.481 | 0.009 |
| 2022 | REG | 3 | 16 | 2.414 | -1.287 | 3.110 | 0.989 |
| 2022 | REG | 4 | 16 | 3.436 | -2.651 | 2.251 | 1.310 |
| 2022 | REG | 5 | 16 | 4.528 | -4.028 | 2.098 | 0.909 |
| 2022 | REG | 6 | 14 | 3.651 | -0.702 | 2.498 | 1.542 |
| 2022 | REG | 7 | 14 | 4.941 | -2.754 | 2.664 | 1.520 |
| 2022 | REG | 8 | 15 | 2.957 | -2.377 | 3.032 | 1.836 |
| 2022 | REG | 9 | 13 | 3.717 | -0.049 | 1.986 | 1.064 |
| 2022 | REG | 10 | 14 | 3.798 | -3.572 | 2.625 | 2.625 |
| 2022 | REG | 11 | 14 | 3.241 | -1.229 | 3.149 | 2.220 |
| 2022 | REG | 12 | 16 | 4.459 | -3.272 | 3.689 | 2.654 |
| 2022 | REG | 13 | 15 | 3.508 | -1.449 | 2.580 | 1.855 |
| 2022 | REG | 14 | 13 | 3.716 | -1.899 | 4.026 | 1.968 |
| 2022 | REG | 15 | 16 | 3.314 | -1.881 | 3.196 | 2.599 |
| 2022 | REG | 16 | 16 | 3.298 | -1.425 | 5.441 | 4.722 |
| 2022 | REG | 17 | 15 | 4.377 | -2.008 | 3.263 | 2.531 |
| 2022 | REG | 18 | 16 | 5.880 | -4.303 | 3.887 | 3.635 |
| 2022 | POST | 19 | 6 | 4.845 | -3.539 | 2.575 | 1.669 |
| 2022 | POST | 20 | 4 | 4.958 | -4.958 | 1.474 | -1.160 |
| 2022 | POST | 21 | 2 | 2.162 | -2.162 | 1.339 | 1.339 |
| 2022 | POST | 22 | 1 | 1.990 | -1.990 | 3.187 | -3.187 |
| 2023 | REG | 2 | 16 | 2.491 | -0.815 | 5.002 | -4.593 |
| 2023 | REG | 3 | 16 | 3.152 | -1.551 | 1.856 | -0.787 |
| 2023 | REG | 4 | 16 | 2.807 | -1.675 | 1.563 | -1.065 |
| 2023 | REG | 5 | 14 | 3.345 | -2.126 | 2.354 | -1.010 |
| 2023 | REG | 6 | 15 | 4.216 | -1.419 | 1.646 | 0.012 |
| 2023 | REG | 7 | 13 | 3.006 | -1.496 | 2.560 | 0.569 |
| 2023 | REG | 8 | 16 | 2.985 | -1.507 | 1.795 | 1.023 |
| 2023 | REG | 9 | 14 | 3.727 | -3.587 | 3.120 | 0.940 |
| 2023 | REG | 10 | 14 | 3.538 | -2.423 | 2.279 | 0.770 |
| 2023 | REG | 11 | 14 | 4.728 | -3.717 | 2.489 | 0.776 |
| 2023 | REG | 12 | 16 | 2.909 | -0.492 | 2.890 | 0.443 |
| 2023 | REG | 13 | 13 | 3.390 | -1.048 | 3.065 | 1.142 |
| 2023 | REG | 14 | 15 | 3.777 | -2.811 | 2.797 | 1.884 |
| 2023 | REG | 15 | 16 | 3.772 | -1.559 | 3.129 | 1.514 |
| 2023 | REG | 16 | 16 | 4.028 | -1.673 | 2.507 | 0.683 |
| 2023 | REG | 17 | 16 | 4.438 | -3.375 | 2.430 | 0.226 |
| 2023 | REG | 18 | 16 | 3.541 | -0.777 | 3.799 | 2.628 |
| 2023 | POST | 19 | 6 | 4.957 | -3.520 | 4.067 | -0.977 |
| 2023 | POST | 20 | 4 | 6.183 | -6.183 | 1.330 | -1.330 |
| 2023 | POST | 21 | 2 | 4.349 | -4.349 | 2.194 | -2.194 |
| 2023 | POST | 22 | 1 | 0.666 | 0.666 | 0.800 | -0.800 |
| 2024 | REG | 2 | 16 | 3.730 | -2.374 | 2.519 | -1.140 |
| 2024 | REG | 3 | 16 | 2.786 | -2.192 | 2.356 | 0.825 |
| 2024 | REG | 4 | 16 | 3.384 | -1.623 | 2.248 | 2.035 |
| 2024 | REG | 5 | 14 | 2.841 | -2.248 | 2.079 | 1.281 |
| 2024 | REG | 6 | 14 | 3.285 | 0.357 | 2.851 | 1.496 |
| 2024 | REG | 7 | 15 | 3.525 | -1.507 | 3.337 | 0.683 |
| 2024 | REG | 8 | 16 | 3.543 | -2.002 | 2.363 | 0.372 |
| 2024 | REG | 9 | 15 | 3.114 | -2.294 | 1.995 | 0.187 |
| 2024 | REG | 10 | 14 | 2.739 | -0.150 | 2.987 | 1.125 |
| 2024 | REG | 11 | 14 | 3.064 | -1.562 | 1.725 | -0.159 |
| 2024 | REG | 12 | 13 | 3.167 | -0.887 | 3.387 | 1.088 |
| 2024 | REG | 13 | 16 | 2.914 | -2.281 | 2.063 | 1.381 |
| 2024 | REG | 14 | 13 | 3.078 | -2.218 | 2.177 | 0.528 |
| 2024 | REG | 15 | 16 | 2.877 | 0.185 | 2.464 | 1.271 |
| 2024 | REG | 16 | 16 | 3.507 | -2.740 | 1.540 | 1.113 |
| 2024 | REG | 17 | 16 | 2.745 | -0.785 | 3.635 | 2.617 |
| 2024 | REG | 18 | 16 | 5.575 | -3.122 | 4.695 | 3.772 |
| 2024 | POST | 19 | 6 | 3.425 | -3.115 | 1.452 | 0.043 |
| 2024 | POST | 20 | 4 | 4.467 | -4.467 | 2.428 | -0.282 |
| 2024 | POST | 21 | 2 | 3.693 | -3.693 | 0.427 | 0.427 |
| 2024 | POST | 22 | 1 | 4.828 | 4.828 | 1.159 | -1.159 |

## Calibration

Per season, the closing line and the actual result regressed on the model spread (home minus away) and on the model total, with approximate standard errors. Slope 1 and intercept 0 would mean the model's numbers sit on the target's scale; a slope below 1 against the actual result means the model's spreads or totals are too spread out.

| season | model | target | n | slope | slope_se | intercept | intercept_se |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | spread | closing_line | 269 | 2.0658 | 0.0770 | 2.6130 | 0.2242 |
| 2021 | spread | actual | 269 | 1.9322 | 0.3012 | 2.7761 | 0.8769 |
| 2021 | total | closing_line | 269 | 1.0454 | 0.0883 | -2.8699 | 4.1696 |
| 2021 | total | actual | 269 | 0.4536 | 0.3697 | 24.5466 | 17.4669 |
| 2022 | spread | closing_line | 268 | 1.8531 | 0.0867 | 2.6176 | 0.2198 |
| 2022 | spread | actual | 268 | 1.5813 | 0.2872 | 2.8846 | 0.7285 |
| 2022 | total | closing_line | 268 | 1.1243 | 0.0866 | -7.6515 | 3.9918 |
| 2022 | total | actual | 268 | 1.1392 | 0.3606 | -8.2870 | 16.6186 |
| 2023 | spread | closing_line | 269 | 1.8357 | 0.0804 | 2.1209 | 0.2082 |
| 2023 | spread | actual | 269 | 1.7298 | 0.3203 | 3.6154 | 0.8296 |
| 2023 | total | closing_line | 269 | 1.0389 | 0.0778 | -1.8931 | 3.3727 |
| 2023 | total | actual | 269 | 0.2770 | 0.3091 | 31.9820 | 13.4027 |
| 2024 | spread | closing_line | 269 | 1.5827 | 0.0686 | 1.8264 | 0.2004 |
| 2024 | spread | actual | 269 | 1.9787 | 0.2798 | 2.5930 | 0.8169 |
| 2024 | total | closing_line | 269 | 0.9475 | 0.0701 | 1.3448 | 3.1979 |
| 2024 | total | actual | 269 | 1.1654 | 0.2878 | -7.0165 | 13.1252 |

## Window constants

COA-07 coefficients (home +1/-1/0; rest days, travel km and |time-zone hours| as offense minus defense), the points-per-drive slope c, the league constants, and the Phase 3e G6 penalty and half-lives each window reads. Standard errors are approximate (penalty treated as known, residuals homoskedastic); no significance conclusions are drawn from them alone.

| season | window | constants | phase3e_fit | penalty | h_efficiency | h_usage | home | rest | travel | tz | home_se | rest_se | travel_se | tz_se | c | c_se | league_epa_per_play | league_points_per_drive | league_drives_per_team_game |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | S2021 | r1 | v3/S2021 | 316.227766 | 8.000000 | 6.000000 | -0.006574 | 0.000912 | -0.000004 | 0.003531 | 0.003933 | 0.001392 | 0.000005 | 0.005790 | 3.160741 | 0.043985 | 0.010798 | 2.009037 | 11.504862 |
| 2022 | S2022 | r1 | v3/S2022 | 316.227766 | 8.000000 | 6.000000 | -0.006089 | 0.001013 | -0.000007 | 0.008183 | 0.003542 | 0.001282 | 0.000005 | 0.005213 | 3.189923 | 0.040178 | 0.011499 | 2.021010 | 11.429716 |
| 2023 | S2023 | r1 | v3/S2023 | 316.227766 | 6.000000 | 6.000000 | -0.005202 | 0.001163 | -0.000005 | 0.005878 | 0.003255 | 0.001197 | 0.000004 | 0.004790 | 3.212450 | 0.037596 | 0.010500 | 2.015629 | 11.380115 |
| 2024 | S2024 | r1 | v3/S2024 | 316.227766 | 8.000000 | 6.000000 | -0.004069 | 0.001324 | -0.000007 | 0.009314 | 0.003033 | 0.001132 | 0.000004 | 0.004465 | 3.227987 | 0.034876 | 0.007035 | 2.006567 | 11.364217 |

Home, travel and time zone are strongly collinear (the away offense nearly always travels further), so the coefficients are not read one at a time. Their combined COA-07 effect in the rated games, home offense's offset minus away offense's (EPA/play):

| season | phase | n | mean_home_minus_away | sd |
| --- | --- | --- | --- | --- |
| 2021 | REG | 256 | -0.0119 | 0.0078 |
| 2021 | POST | 13 | -0.0075 | 0.0082 |
| 2022 | REG | 255 | -0.0098 | 0.0122 |
| 2022 | POST | 13 | -0.0040 | 0.0091 |
| 2023 | REG | 256 | -0.0091 | 0.0103 |
| 2023 | POST | 13 | -0.0033 | 0.0110 |
| 2024 | REG | 256 | -0.0080 | 0.0166 |
| 2024 | POST | 13 | -0.0005 | 0.0174 |

The same combined effect in points (league drives per team-game x c x (home offset - away offset), each game with its window's constants) next to the closing-line home edge (mean spread_line) and the mean actual home margin, non-neutral games:

| season | n | model_coa07_home_points | closing_line_home_edge | actual_home_margin |
| --- | --- | --- | --- | --- |
| 2021 | 266 | -0.430 | 1.895 | 2.068 |
| 2022 | 261 | -0.357 | 2.011 | 2.521 |
| 2023 | 263 | -0.334 | 1.833 | 3.354 |
| 2024 | 263 | -0.288 | 1.534 | 1.916 |

### c diagnostic

Over each window's training seasons: league qualifying plays per drive, c as fitted, and c refit with turnover plays (interceptions and lost fumbles) left out of x. Report only; the model uses c as fitted.

| season | window | plays_per_drive | c | c_se | c_no_turnovers | c_no_turnovers_se | n_team_games | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | S2021 | 4.8265 | 3.1607 | 0.0440 | 3.6312 | 0.0542 | 2674 |  |
| 2022 | S2022 | 4.8487 | 3.1899 | 0.0402 | 3.6445 | 0.0498 | 3244 |  |
| 2023 | S2023 | 4.8753 | 3.2125 | 0.0376 | 3.6503 | 0.0462 | 3812 |  |
| 2024 | S2024 | 4.8827 | 3.2280 | 0.0349 | 3.6441 | 0.0431 | 4382 |  |

Expected points = league drives per team-game x (league points per drive + c x (expected EPA/play - league EPA/play)). The Phase 3e penalty was cross-validated for one rating per team; with pass and run rated separately the run ratings rest on fewer plays and shrink harder (see the sensitivity check below). It is not refit here.

## Totals against pace (report only)

The totals use league drives per team-game, so team pace is ignored. Games in 5 equal-count bins of combined pace (both teams' OFF-11 plays per game, shrunk, as of the game's snapshot; mean OFF-10 seconds per snap alongside):

| bin | n | pace_min | pace_max | pace_plays_mean | pace_seconds_mean | total_diff_mean | total_vs_actual_mean | spread_diff_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 215 | 98.379 | 107.434 | 105.242 | 37.965 | 1.984 | 1.528 | -2.360 |
| 1 | 215 | 107.438 | 109.447 | 108.551 | 37.823 | 1.257 | 0.815 | -1.924 |
| 2 | 215 | 109.453 | 111.409 | 110.396 | 37.634 | 0.955 | 0.446 | -1.691 |
| 3 | 215 | 111.422 | 114.170 | 112.726 | 37.471 | 0.694 | 0.632 | -2.214 |
| 4 | 215 | 114.198 | 125.773 | 116.428 | 37.375 | -0.004 | -1.037 | -2.092 |

Per season, the OLS slope of total_diff (and of spread_diff, as a control) on combined pace, with standard errors:

| season | n | total_slope | total_slope_se | spread_slope | spread_slope_se |
| --- | --- | --- | --- | --- | --- |
| 2021 | 269 | -0.2696 | 0.0422 | -0.0441 | 0.0655 |
| 2022 | 268 | -0.1074 | 0.0516 | 0.0418 | 0.0661 |
| 2023 | 269 | -0.1651 | 0.0567 | 0.1093 | 0.0664 |
| 2024 | 269 | -0.1764 | 0.0602 | 0.0180 | 0.0716 |

## Run-penalty sensitivity (report only)

Ratings refit for each week from earlier weeks only, with the run-side penalty at 0.5x, 1x, 2x the fitted value (pass unchanged); mean squared next-week EPA/play prediction error for pass plays and run plays separately. The model is not changed on the basis of this check.

| season | run_penalty | side | n | mse |
| --- | --- | --- | --- | --- |
| 2023 | 0.5x | pass | 18317 | 2.53465 |
| 2023 | 0.5x | run | 11526 | 0.94225 |
| 2023 | 1x | pass | 18317 | 2.53465 |
| 2023 | 1x | run | 11526 | 0.94163 |
| 2023 | 2x | pass | 18317 | 2.53465 |
| 2023 | 2x | run | 11526 | 0.94162 |
| 2024 | 0.5x | pass | 17707 | 2.46532 |
| 2024 | 0.5x | run | 11584 | 1.05385 |
| 2024 | 1x | pass | 17707 | 2.46532 |
| 2024 | 1x | run | 11584 | 1.05441 |
| 2024 | 2x | pass | 17707 | 2.46532 |
| 2024 | 2x | run | 11584 | 1.05552 |

## Skipped games

| season | week | game_id | skip_reason |
| --- | --- | --- | --- |
| 2021 | 1 | 2021_01_DAL_TB | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_ARI_TEN | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_JAX_HOU | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_LAC_WAS | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_MIN_CIN | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_NYJ_CAR | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_PHI_ATL | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_PIT_BUF | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_SEA_IND | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_SF_DET | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_CLE_KC | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_DEN_NYG | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_GB_NO | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_MIA_NE | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_CHI_LA | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2021 | 1 | 2021_01_BAL_LV | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_BUF_LA | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_BAL_NYJ | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_CLE_CAR | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_IND_HOU | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_JAX_WAS | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_NE_MIA | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_NO_ATL | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_PHI_DET | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_PIT_CIN | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_SF_CHI | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_GB_MIN | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_KC_ARI | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_LV_LAC | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_NYG_TEN | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_TB_DAL | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2022 | 1 | 2022_01_DEN_SEA | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_DET_KC | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_ARI_WAS | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_CAR_ATL | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_CIN_CLE | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_HOU_BAL | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_JAX_IND | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_SF_PIT | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_TB_MIN | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_TEN_NO | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_GB_CHI | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_LA_SEA | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_LV_DEN | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_MIA_LAC | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_PHI_NE | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_DAL_NYG | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2023 | 1 | 2023_01_BUF_NYJ | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_BAL_KC | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_GB_PHI | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_ARI_BUF | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_CAR_NO | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_HOU_IND | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_JAX_MIA | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_MIN_NYG | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_NE_CIN | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_PIT_ATL | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_TEN_CHI | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_DEN_SEA | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_LV_LAC | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_DAL_CLE | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_WAS_TB | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_LA_DET | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |
| 2024 | 1 | 2024_01_NYJ_SF | G4: whether the play-caller or quarterback changed is unknown (COA-01 has no covering row, or no current-season dropbacks yet) |

Per-game rows: ratings_walkforward.csv.

Data: nflverse; charting: FTN Data via nflverse
