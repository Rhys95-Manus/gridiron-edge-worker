# Phase 4: rating-implied lines against closing lines (PRJ-01a)

Seasons 2021, 2022, 2023, 2024, walk-forward (each season rated with its own window's fits; never the 2025 holdout, BT-07b). Every game is rated only from its own snapshot (snapshot(game_id), decision-time as_of). Closing lines and results are read only here, after the fact. Report only: no pass/fail; beating the market is Phase 8's question.

Rated: 1139 games; skipped: 0 (listed at the end).

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

Mean absolute difference (mad) and mean signed difference (bias) against the closing lines; regular season (REG) and postseason (POST) separately. Raw (rating-implied) and calibrated (Phase 4b, PRJ-01a's output) side by side.

| season | phase | n | spread_mad_raw | spread_bias_raw | total_mad_raw | total_bias_raw | spread_mad_cal | spread_bias_cal | total_mad_cal | total_bias_cal |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | REG | 272 | 4.278 | -2.078 | 2.650 | 0.656 | 2.990 | -0.211 | 2.864 | 0.250 |
| 2021 | POST | 13 | 3.965 | -3.624 | 2.532 | -0.907 | 1.364 | -0.743 | 2.639 | -1.544 |
| 2022 | REG | 271 | 3.845 | -2.099 | 3.199 | 1.597 | 2.818 | -0.314 | 3.422 | 1.908 |
| 2022 | POST | 13 | 4.249 | -3.647 | 2.093 | 0.374 | 2.673 | -0.567 | 2.276 | -0.046 |
| 2023 | REG | 272 | 3.482 | -1.900 | 2.928 | -0.152 | 2.570 | 0.093 | 3.254 | 1.507 |
| 2023 | POST | 13 | 4.911 | -4.146 | 2.685 | -1.259 | 3.098 | -1.655 | 2.908 | -1.087 |
| 2024 | REG | 272 | 3.296 | -1.713 | 2.929 | 1.457 | 2.564 | 0.324 | 2.982 | 1.426 |
| 2024 | POST | 13 | 3.895 | -3.010 | 1.572 | -0.090 | 2.236 | -0.460 | 2.490 | -0.882 |

## Differences by week (calibrated)

| season | phase | week | n | spread_mad | spread_bias | total_mad | total_bias |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | REG | 1 | 16 | 3.226 | 1.423 | 2.716 | -1.622 |
| 2021 | REG | 2 | 16 | 1.928 | -0.156 | 2.873 | -1.255 |
| 2021 | REG | 3 | 16 | 2.846 | -0.845 | 3.422 | -1.052 |
| 2021 | REG | 4 | 16 | 2.510 | -0.419 | 3.152 | -0.830 |
| 2021 | REG | 5 | 16 | 2.834 | 0.059 | 2.990 | -0.514 |
| 2021 | REG | 6 | 14 | 4.127 | -0.559 | 2.772 | -0.741 |
| 2021 | REG | 7 | 13 | 3.769 | -1.447 | 3.097 | 1.015 |
| 2021 | REG | 8 | 15 | 2.668 | 0.212 | 2.874 | -0.135 |
| 2021 | REG | 9 | 14 | 3.982 | -2.210 | 2.623 | 0.292 |
| 2021 | REG | 10 | 14 | 3.011 | 1.308 | 2.981 | -1.131 |
| 2021 | REG | 11 | 15 | 3.000 | -0.437 | 2.682 | -0.115 |
| 2021 | REG | 12 | 15 | 2.059 | 0.087 | 1.989 | 0.406 |
| 2021 | REG | 13 | 14 | 2.406 | 0.447 | 2.204 | 0.912 |
| 2021 | REG | 14 | 14 | 2.670 | 0.498 | 3.189 | 0.916 |
| 2021 | REG | 15 | 16 | 3.194 | -0.527 | 2.598 | 1.240 |
| 2021 | REG | 16 | 16 | 2.466 | 0.069 | 2.644 | 2.183 |
| 2021 | REG | 17 | 16 | 3.556 | -2.549 | 3.411 | 1.874 |
| 2021 | REG | 18 | 16 | 3.792 | 1.116 | 3.238 | 3.037 |
| 2021 | POST | 19 | 6 | 1.365 | -0.438 | 2.454 | -0.423 |
| 2021 | POST | 20 | 4 | 2.196 | -1.629 | 2.654 | -2.260 |
| 2021 | POST | 21 | 2 | 0.318 | -0.318 | 3.184 | -2.947 |
| 2021 | POST | 22 | 1 | 0.125 | 0.125 | 2.597 | -2.597 |
| 2022 | REG | 1 | 16 | 3.446 | 1.963 | 3.181 | -2.161 |
| 2022 | REG | 2 | 16 | 3.468 | -0.221 | 2.839 | 0.712 |
| 2022 | REG | 3 | 16 | 3.046 | -0.642 | 3.375 | 1.066 |
| 2022 | REG | 4 | 16 | 3.410 | -1.307 | 2.629 | 1.701 |
| 2022 | REG | 5 | 16 | 3.065 | -2.105 | 2.237 | 1.120 |
| 2022 | REG | 6 | 14 | 3.407 | 0.900 | 2.864 | 1.497 |
| 2022 | REG | 7 | 14 | 3.269 | -0.594 | 3.158 | 1.650 |
| 2022 | REG | 8 | 15 | 1.834 | -0.225 | 3.382 | 2.032 |
| 2022 | REG | 9 | 13 | 2.801 | 1.350 | 2.019 | 0.776 |
| 2022 | REG | 10 | 14 | 1.974 | -1.161 | 3.193 | 2.432 |
| 2022 | REG | 11 | 14 | 2.617 | 0.095 | 3.804 | 2.277 |
| 2022 | REG | 12 | 16 | 2.564 | -0.789 | 3.780 | 2.619 |
| 2022 | REG | 13 | 15 | 2.341 | 0.203 | 2.934 | 1.568 |
| 2022 | REG | 14 | 13 | 2.120 | -0.128 | 3.792 | 1.865 |
| 2022 | REG | 15 | 16 | 2.031 | -0.934 | 3.238 | 2.613 |
| 2022 | REG | 16 | 16 | 2.529 | 0.591 | 5.887 | 4.985 |
| 2022 | REG | 17 | 15 | 2.865 | -0.055 | 4.144 | 3.278 |
| 2022 | REG | 18 | 16 | 3.708 | -2.125 | 4.872 | 4.196 |
| 2022 | POST | 19 | 6 | 3.315 | -0.101 | 2.436 | 1.809 |
| 2022 | POST | 20 | 4 | 2.161 | -1.043 | 2.056 | -1.991 |
| 2022 | POST | 21 | 2 | 1.678 | 0.136 | 1.341 | 0.295 |
| 2022 | POST | 22 | 1 | 2.860 | -2.860 | 4.074 | -4.074 |
| 2023 | REG | 1 | 16 | 2.266 | -0.967 | 3.076 | -2.420 |
| 2023 | REG | 2 | 16 | 3.238 | 1.415 | 3.238 | -0.777 |
| 2023 | REG | 3 | 16 | 2.506 | 1.365 | 2.149 | 0.600 |
| 2023 | REG | 4 | 16 | 2.427 | -0.099 | 1.976 | 0.387 |
| 2023 | REG | 5 | 14 | 2.513 | -0.108 | 2.557 | 0.070 |
| 2023 | REG | 6 | 15 | 2.787 | 1.073 | 2.159 | 0.988 |
| 2023 | REG | 7 | 13 | 1.793 | -0.064 | 3.230 | 1.981 |
| 2023 | REG | 8 | 16 | 1.906 | -0.012 | 2.491 | 2.262 |
| 2023 | REG | 9 | 14 | 2.219 | -1.773 | 4.070 | 2.408 |
| 2023 | REG | 10 | 14 | 2.733 | -0.016 | 3.220 | 2.538 |
| 2023 | REG | 11 | 14 | 2.877 | -0.725 | 3.024 | 1.894 |
| 2023 | REG | 12 | 16 | 2.316 | 0.928 | 3.464 | 1.741 |
| 2023 | REG | 13 | 13 | 2.389 | 0.769 | 3.942 | 2.269 |
| 2023 | REG | 14 | 15 | 2.214 | -0.216 | 4.138 | 3.053 |
| 2023 | REG | 15 | 16 | 2.416 | -0.145 | 4.475 | 2.957 |
| 2023 | REG | 16 | 16 | 3.667 | 0.454 | 3.161 | 2.170 |
| 2023 | REG | 17 | 16 | 2.449 | -0.996 | 3.431 | 1.640 |
| 2023 | REG | 18 | 16 | 3.354 | 0.550 | 4.874 | 3.778 |
| 2023 | POST | 19 | 6 | 4.163 | -1.434 | 4.031 | -0.505 |
| 2023 | POST | 20 | 4 | 3.150 | -2.927 | 1.721 | -1.402 |
| 2023 | POST | 21 | 2 | 1.289 | -0.541 | 2.890 | -2.272 |
| 2023 | POST | 22 | 1 | 0.118 | -0.118 | 0.955 | -0.955 |
| 2024 | REG | 1 | 16 | 3.277 | -0.440 | 4.762 | 3.959 |
| 2024 | REG | 2 | 16 | 2.950 | -0.791 | 2.524 | 0.405 |
| 2024 | REG | 3 | 16 | 2.735 | 0.036 | 3.012 | 1.701 |
| 2024 | REG | 4 | 16 | 2.652 | 0.334 | 2.948 | 2.604 |
| 2024 | REG | 5 | 14 | 2.552 | -0.009 | 2.932 | 1.693 |
| 2024 | REG | 6 | 14 | 3.343 | 1.933 | 3.527 | 1.608 |
| 2024 | REG | 7 | 15 | 3.260 | 0.779 | 3.624 | 0.733 |
| 2024 | REG | 8 | 16 | 2.279 | -0.227 | 2.171 | 0.748 |
| 2024 | REG | 9 | 15 | 2.983 | 0.206 | 2.048 | 0.165 |
| 2024 | REG | 10 | 14 | 1.450 | 1.248 | 3.161 | 0.814 |
| 2024 | REG | 11 | 14 | 1.992 | 0.270 | 1.890 | 0.371 |
| 2024 | REG | 12 | 13 | 2.696 | -0.089 | 3.536 | 1.352 |
| 2024 | REG | 13 | 16 | 1.402 | 0.377 | 2.146 | 1.114 |
| 2024 | REG | 14 | 13 | 1.710 | 0.884 | 2.577 | 0.320 |
| 2024 | REG | 15 | 16 | 2.255 | 2.036 | 2.405 | 0.832 |
| 2024 | REG | 16 | 16 | 1.729 | -0.728 | 1.584 | 1.035 |
| 2024 | REG | 17 | 16 | 2.274 | 1.040 | 3.921 | 2.357 |
| 2024 | REG | 18 | 16 | 4.436 | -0.713 | 4.870 | 3.365 |
| 2024 | POST | 19 | 6 | 1.975 | -1.060 | 2.045 | -0.375 |
| 2024 | POST | 20 | 4 | 1.677 | -1.084 | 4.038 | -1.316 |
| 2024 | POST | 21 | 2 | 1.506 | -1.393 | 0.978 | -0.978 |
| 2024 | POST | 22 | 1 | 7.504 | 7.504 | 1.995 | -1.995 |

## Calibration

Per season, the closing line and the actual result regressed on the model spread (home minus away) and on the model total, with approximate standard errors. Slope 1 and intercept 0 would mean the model's numbers sit on the target's scale; a slope above 1 means the model's spreads or totals are too compressed. Rows for raw and calibrated lines.

| lines | season | model | target | n | slope | slope_se | intercept | intercept_se |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| raw | 2021 | spread | actual | 285 | 1.8502 | 0.2961 | 2.5463 | 0.8573 |
| calibrated | 2021 | spread | actual | 285 | 0.9503 | 0.1542 | 0.4295 | 0.8873 |
| raw | 2021 | spread | closing_line | 285 | 2.0235 | 0.0768 | 2.4880 | 0.2222 |
| calibrated | 2021 | spread | closing_line | 285 | 1.0530 | 0.0398 | 0.1513 | 0.2291 |
| raw | 2021 | total | actual | 285 | 0.5670 | 0.3484 | 19.3430 | 16.4374 |
| calibrated | 2021 | total | actual | 285 | 1.3124 | 0.8063 | -15.2401 | 37.6717 |
| raw | 2021 | total | closing_line | 285 | 0.9996 | 0.0845 | -0.5659 | 3.9894 |
| calibrated | 2021 | total | closing_line | 285 | 2.3136 | 0.1957 | -61.5307 | 9.1431 |
| raw | 2022 | spread | actual | 284 | 1.5688 | 0.2806 | 2.6659 | 0.7081 |
| calibrated | 2022 | spread | actual | 284 | 0.8470 | 0.1485 | 0.8381 | 0.7326 |
| raw | 2022 | spread | closing_line | 284 | 1.8505 | 0.0859 | 2.4828 | 0.2167 |
| calibrated | 2022 | spread | closing_line | 284 | 0.9827 | 0.0455 | 0.3509 | 0.2242 |
| raw | 2022 | total | actual | 284 | 0.9520 | 0.3130 | 0.4704 | 14.3457 |
| calibrated | 2022 | total | actual | 284 | 2.1987 | 0.7229 | -57.1878 | 33.2908 |
| raw | 2022 | total | closing_line | 284 | 0.8279 | 0.0830 | 6.3350 | 3.8046 |
| calibrated | 2022 | total | closing_line | 284 | 1.9121 | 0.1917 | -43.8077 | 8.8289 |
| raw | 2023 | spread | actual | 285 | 1.7561 | 0.3182 | 3.2933 | 0.8149 |
| calibrated | 2023 | spread | actual | 285 | 0.9089 | 0.1641 | 1.2830 | 0.8642 |
| raw | 2023 | spread | closing_line | 285 | 1.8253 | 0.0781 | 2.1763 | 0.2000 |
| calibrated | 2023 | spread | closing_line | 285 | 0.9447 | 0.0401 | 0.0867 | 0.2110 |
| raw | 2023 | total | actual | 285 | 0.3187 | 0.2584 | 30.1190 | 11.1219 |
| calibrated | 2023 | total | actual | 285 | 0.6825 | 0.5533 | 13.4205 | 24.6444 |
| raw | 2023 | total | closing_line | 285 | 0.7548 | 0.0713 | 10.7271 | 3.0700 |
| calibrated | 2023 | total | closing_line | 285 | 1.6162 | 0.1527 | -28.8181 | 6.8027 |
| raw | 2024 | spread | actual | 285 | 1.9939 | 0.2734 | 2.6241 | 0.7891 |
| calibrated | 2024 | spread | actual | 285 | 1.0835 | 0.1519 | 0.2333 | 0.8408 |
| raw | 2024 | spread | closing_line | 285 | 1.5538 | 0.0673 | 1.8686 | 0.1944 |
| calibrated | 2024 | spread | closing_line | 285 | 0.8637 | 0.0370 | -0.0309 | 0.2049 |
| raw | 2024 | total | actual | 285 | 0.7886 | 0.2392 | 9.8430 | 10.9982 |
| calibrated | 2024 | total | actual | 285 | 1.6568 | 0.5025 | -29.8747 | 23.0300 |
| raw | 2024 | total | closing_line | 285 | 0.6807 | 0.0632 | 13.2602 | 2.9074 |
| calibrated | 2024 | total | closing_line | 285 | 1.4301 | 0.1328 | -21.0221 | 6.0881 |

## Phase 4b acceptance quantities

Per season: calibrated spread slope against actual results and against closing lines (with standard errors), calibrated spread bias against closing lines for regular-season games (counts toward acceptance) and postseason games (reported only), and week-1 games rated or unrated. The Build Plan's thresholds are checked by tests/phase4/test_realdata_acceptance.py; nothing is tuned on these seasons.

| season | slope_vs_actual | slope_vs_actual_se | slope_vs_closing | slope_vs_closing_se | reg_n | reg_spread_bias | post_n | post_spread_bias | week1_games | week1_rated | week1_unrated_no_chart | week1_unrated_other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | 0.9503 | 0.1542 | 1.0530 | 0.0398 | 272 | -0.2109 | 13 | -0.7426 | 16 | 16 | 0 | 0 |
| 2022 | 0.8470 | 0.1485 | 0.9827 | 0.0455 | 271 | -0.3138 | 13 | -0.5668 | 16 | 16 | 0 | 0 |
| 2023 | 0.9089 | 0.1641 | 0.9447 | 0.0401 | 272 | 0.0927 | 13 | -1.6548 | 16 | 16 | 0 | 0 |
| 2024 | 1.0835 | 0.1519 | 0.8637 | 0.0370 | 272 | 0.3238 | 13 | -0.4600 | 16 | 16 | 0 | 0 |

## Calibration training games

Per window, the training-season games its calibration rated point-in-time and those it left unrated, by reason (from the window file).

| window | rated | reason | games |
| --- | --- | --- | --- |
| S2021 | 1273 | (rated) | 1273 |
| S2021 | 1273 | COA-07: travel origin unknown (no earlier season in the store) | 62 |
| S2021 | 1273 | G4: no depth-chart QB1 at decision time | 1 |
| S2021 | 1273 | G4: no prior season in the store | 1 |
| S2022 | 1558 | (rated) | 1558 |
| S2022 | 1558 | COA-07: travel origin unknown (no earlier season in the store) | 62 |
| S2022 | 1558 | G4: no depth-chart QB1 at decision time | 1 |
| S2022 | 1558 | G4: no prior season in the store | 1 |
| S2023 | 1842 | (rated) | 1842 |
| S2023 | 1842 | COA-07: travel origin unknown (no earlier season in the store) | 62 |
| S2023 | 1842 | G4: no depth-chart QB1 at decision time | 1 |
| S2023 | 1842 | G4: no prior season in the store | 1 |
| S2024 | 2127 | (rated) | 2127 |
| S2024 | 2127 | COA-07: travel origin unknown (no earlier season in the store) | 62 |
| S2024 | 2127 | G4: no depth-chart QB1 at decision time | 1 |
| S2024 | 2127 | G4: no prior season in the store | 1 |

## Window constants

COA-07 coefficients (home +1/-1/0; rest days, travel km and |time-zone hours| as offense minus defense), the points-per-drive slope c, the league constants, and the Phase 3e G6 penalty and half-lives each window reads. Standard errors are approximate (penalty treated as known, residuals homoskedastic); no significance conclusions are drawn from them alone.

| season | window | constants | phase3e_fit | penalty | h_efficiency | h_usage | home | rest | travel | tz | home_se | rest_se | travel_se | tz_se | c | c_se | league_epa_per_play | league_points_per_drive | league_drives_per_team_game | calib_a | calib_a_se | calib_b | calib_b_se | calib_a_t | calib_a_t_se | calib_b_t | calib_b_t_se | calib_n_games |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | S2021 | r2 | v3/S2021 | 316.227766 | 8.000000 | 6.000000 | -0.006557 | 0.000914 | -0.000004 | 0.003436 | 0.003933 | 0.001392 | 0.000005 | 0.005792 | 3.160741 | 0.043985 | 0.010798 | 2.009037 | 11.504862 | 2.249606 | 0.377624 | 1.918526 | 0.136845 | 26.350231 | 4.453250 | 0.432048 | 0.096416 | 1273 |
| 2022 | S2022 | r2 | v3/S2022 | 316.227766 | 8.000000 | 6.000000 | -0.006077 | 0.001014 | -0.000007 | 0.008109 | 0.003542 | 0.001282 | 0.000005 | 0.005214 | 3.189923 | 0.040178 | 0.011499 | 2.021010 | 11.429716 | 2.224574 | 0.346200 | 1.884036 | 0.123285 | 26.224333 | 4.253074 | 0.432974 | 0.091874 | 1558 |
| 2023 | S2023 | r2 | v3/S2023 | 316.227766 | 6.000000 | 6.000000 | -0.005191 | 0.001164 | -0.000005 | 0.005813 | 0.003255 | 0.001197 | 0.000004 | 0.004791 | 3.212450 | 0.037596 | 0.010500 | 2.015629 | 11.380115 | 2.260531 | 0.312713 | 1.937405 | 0.119330 | 24.468423 | 4.111423 | 0.467030 | 0.089464 | 1842 |
| 2024 | S2024 | r2 | v3/S2024 | 316.227766 | 8.000000 | 6.000000 | -0.004060 | 0.001325 | -0.000007 | 0.009260 | 0.003034 | 0.001132 | 0.000004 | 0.004466 | 3.227987 | 0.034876 | 0.007035 | 2.006567 | 11.364217 | 2.255735 | 0.291348 | 1.804986 | 0.104535 | 23.971883 | 3.621460 | 0.475978 | 0.079468 | 2127 |

Home, travel and time zone are strongly collinear (the away offense nearly always travels further), so the coefficients are not read one at a time. Their combined COA-07 effect in the rated games, home offense's offset minus away offense's (EPA/play):

| season | phase | n | mean_home_minus_away | sd |
| --- | --- | --- | --- | --- |
| 2021 | REG | 272 | -0.0116 | 0.0076 |
| 2021 | POST | 13 | -0.0075 | 0.0081 |
| 2022 | REG | 271 | -0.0097 | 0.0120 |
| 2022 | POST | 13 | -0.0040 | 0.0091 |
| 2023 | REG | 272 | -0.0089 | 0.0100 |
| 2023 | POST | 13 | -0.0033 | 0.0109 |
| 2024 | REG | 272 | -0.0077 | 0.0162 |
| 2024 | POST | 13 | -0.0005 | 0.0173 |

The same combined effect in points (league drives per team-game x c x (home offset - away offset), each game with its window's constants) next to the closing-line home edge (mean spread_line) and the mean actual home margin, non-neutral games:

| season | n | model_coa07_home_points | closing_line_home_edge | actual_home_margin |
| --- | --- | --- | --- | --- |
| 2021 | 281 | -0.421 | 1.872 | 1.811 |
| 2022 | 277 | -0.352 | 1.823 | 2.249 |
| 2023 | 279 | -0.326 | 1.823 | 2.953 |
| 2024 | 278 | -0.280 | 1.642 | 2.029 |

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
| 0 | 216 | 98.379 | 107.438 | 105.253 | 37.973 | 2.219 | 1.770 | -0.125 |
| 1 | 215 | 107.458 | 109.453 | 108.560 | 37.811 | 1.596 | 1.121 | 0.055 |
| 2 | 215 | 109.455 | 111.422 | 110.405 | 37.633 | 1.306 | 0.883 | -0.047 |
| 3 | 215 | 111.422 | 114.170 | 112.728 | 37.480 | 0.850 | 0.685 | -0.177 |
| 4 | 215 | 114.198 | 125.773 | 116.428 | 37.375 | 0.388 | -0.645 | -0.199 |

Per season, the OLS slope of total_diff (and of spread_diff, as a control) on combined pace, with standard errors:

| season | n | total_slope | total_slope_se | spread_slope | spread_slope_se |
| --- | --- | --- | --- | --- | --- |
| 2021 | 270 | -0.3087 | 0.0455 | -0.0421 | 0.0500 |
| 2022 | 268 | -0.1705 | 0.0567 | 0.0086 | 0.0564 |
| 2023 | 269 | -0.0871 | 0.0629 | 0.0986 | 0.0558 |
| 2024 | 269 | -0.2062 | 0.0649 | 0.0040 | 0.0639 |

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

None.

Per-game rows: ratings_walkforward.csv.

Data: nflverse; charting: FTN Data via nflverse
