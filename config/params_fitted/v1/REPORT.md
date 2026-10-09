# Phase 3e fit report — v1

Every fitted value beside its initial value (— = the spec gives none), the seasons used and n (entities for k and priors; rows or events otherwise). Change is relative to the initial value; **bold** = moved more than 50%.

## S2021 (seasons 2016-2020)

| key | spec | initial | fitted | change | n | seasons | method |
|---|---|---|---|---|---|---|---|
| `fit:k/COA-04/proe` | COA-04 | 80.0 | 84.0 | +5% | 309 | 2016-2020 | split-half (BT-02), m:r = 25:0.210, 50:0.349, 100:0.608; variance-components cross-check k = 75.8 |
| `fit:k/COA-04/seconds_per_play` | COA-04 | 80.0 | 20.6 | **-74%** | 228 | 2016-2020 | split-half (BT-02), m:r = 25:0.548; variance-components cross-check k = 12.3 |
| `fit:k/DEF-01/epa/all` | DEF-01 | 250.0 | 722.7 | **+189%** | 160 | 2016-2020 | split-half (BT-02), m:r = 200:0.218, 400:0.354; variance-components cross-check k = 566.0 |
| `fit:k/DEF-01/epa/pass` | DEF-01 | 200.0 | 669.9 | **+235%** | 160 | 2016-2020 | split-half (BT-02), m:r = 200:0.230; variance-components cross-check k = 469.7 |
| `fit:k/DEF-01/epa/run` | DEF-01 | 300.0 | 485.2 | **+62%** | 160 | 2016-2020 | split-half (BT-02), m:r = 100:0.171; variance-components cross-check k = 432.5 |
| `fit:k/DEF-02/success` | DEF-02 | 150.0 | 236.6 | **+58%** | 480 | 2016-2020 | split-half (BT-02), m:r = 25:0.103, 50:0.193, 100:0.318, 200:0.317, 400:0.406; variance-components cross-check k = 223.0 |
| `fit:k/DEF-03/explosive` | DEF-03 | 150.0 | 112.1 | -25% | 401 | 2016-2020 | split-half (BT-02), m:r = 25:0.182 |
| `fit:k/DEF-03/share` | DEF-03 | — | 23.9 |  | 1280 | 2016-2020 | split-half (BT-02), m:r = 25:0.547, 50:0.680, 100:0.777; variance-components cross-check k = 16.7 |
| `fit:k/DEF-03/success` | DEF-03 | 60.0 | 141.1 | **+135%** | 399 | 2016-2020 | split-half (BT-02), m:r = 25:0.151 |
| `fit:k/DEF-03/ypc` | DEF-03 | 100.0 | 158.9 | **+59%** | 399 | 2016-2020 | split-half (BT-02), m:r = 25:0.136 |
| `fit:k/DEF-04/epa_diff` | DEF-04 | 60.0 | 452.7 | **+654%** | 480 | 2016-2020 | split-half (BT-02), m:r = 100:0.194 |
| `fit:k/DEF-06/explosive` | DEF-06 | 300.0 | 1,058 | **+253%** | 160 | 2016-2020 | split-half (BT-02), m:r = 200:0.159; variance-components cross-check k = 899.1 |
| `fit:k/DEF-06/explosive_run` | DEF-06 | 300.0 | 470.0 | **+57%** | 160 | 2016-2020 | split-half (BT-02), m:r = 100:0.175; variance-components cross-check k = 434.2 |
| `fit:k/DEF-09/cpoe_team` | DEF-09 | — | 721.3 |  | 160 | 2016-2020 | split-half (BT-02), m:r = 200:0.217; variance-components cross-check k = 594.9 |
| `fit:k/DEF-09/epa` | DEF-09 | 60.0 | 199.1 | **+232%** | 508 | 2016-2020 | split-half (BT-02), m:r = 25:0.112 |
| `fit:k/DEF-15/success` | DEF-15 | 60.0 | 312.6 | **+421%** | 320 | 2016-2020 | split-half (BT-02), m:r = 50:0.138; variance-components cross-check k = 229.7 |
| `fit:k/DEF-15/ypc` | DEF-15 | 60.0 | 291.5 | **+386%** | 320 | 2016-2020 | split-half (BT-02), m:r = 50:0.146; variance-components cross-check k = 240.6 |
| `fit:k/DEF-17/passes_defensed` | DEF-17 | 20.0 | 19.2 | -4% | 2268 | 2016-2020 | split-half (BT-02), m:r = 25:0.589 |
| `fit:k/DEF-17/qb_hits` | DEF-17 | 20.0 | 11.7 | -42% | 2802 | 2016-2020 | split-half (BT-02), m:r = 25:0.704, 50:0.835 |
| `fit:k/DEF-17/sacks` | DEF-17 | 20.0 | 9.9557 | **-50%** | 211 | 2017-2020 | split-half (BT-02), m:r = 25:0.725 |
| `fit:k/DEF-17/tackles_for_loss` | DEF-17 | 20.0 | 28.1 | +40% | 2363 | 2016-2020 | split-half (BT-02), m:r = 25:0.493 |
| `fit:k/OFF-01/epa/all` | OFF-01 | 250.0 | 336.7 | +35% | 160 | 2016-2020 | split-half (BT-02), m:r = 100:0.239, 200:0.381, 400:0.507; variance-components cross-check k = 294.2 |
| `fit:k/OFF-01/epa/pass` | OFF-01 | 200.0 | 267.2 | +34% | 160 | 2016-2020 | split-half (BT-02), m:r = 100:0.274, 200:0.427; variance-components cross-check k = 242.2 |
| `fit:k/OFF-01/epa/run` | OFF-01 | 300.0 | 319.5 | +7% | 160 | 2016-2020 | split-half (BT-02), m:r = 100:0.238; variance-components cross-check k = 286.0 |
| `fit:k/OFF-02/success` | OFF-02 | 150.0 | 167.0 | +11% | 480 | 2016-2020 | split-half (BT-02), m:r = 25:0.141, 50:0.255, 100:0.392, 200:0.479, 400:0.539; variance-components cross-check k = 155.6 |
| `fit:k/OFF-03/epa` | OFF-03 | 100.0 | 272.8 | **+173%** | 559 | 2016-2020 | split-half (BT-02), m:r = 25:0.088, 50:0.165, 100:0.240; variance-components cross-check k = 140.9 |
| `fit:k/OFF-03/success` | OFF-03 | 100.0 | 219.4 | **+119%** | 559 | 2016-2020 | split-half (BT-02), m:r = 25:0.109, 50:0.188, 100:0.300; variance-components cross-check k = 158.4 |
| `fit:k/OFF-04/pass_rate` | OFF-04 | 60.0 | 111.0 | **+85%** | 160 | 2016-2020 | split-half (BT-02), m:r = 25:0.166, 50:0.310, 100:0.477, 200:0.649; variance-components cross-check k = 112.4 |
| `fit:k/OFF-05/proe` | OFF-05 | 100.0 | 124.5 | +24% | 160 | 2016-2020 | split-half (BT-02), m:r = 25:0.175, 50:0.296, 100:0.448, 200:0.603; variance-components cross-check k = 113.9 |
| `fit:k/OFF-09/shotgun_rate` | OFF-09 | 60.0 | 18.9 | **-69%** | 160 | 2016-2020 | split-half (BT-02), m:r = 25:0.625, 50:0.746, 100:0.834, 200:0.890, 400:0.931; variance-components cross-check k = 13.1 |
| `fit:k/OFF-10/seconds_per_play` | OFF-10 | 80.0 | 42.0 | -47% | 160 | 2016-2020 | split-half (BT-02), m:r = 25:0.417, 50:0.521, 100:0.681; variance-components cross-check k = 33.8 |
| `fit:k/OFF-12/explosive` | OFF-12 | 150.0 | 82.9 | -45% | 412 | 2016-2020 | split-half (BT-02), m:r = 25:0.232 |
| `fit:k/OFF-12/explosive_team` | OFF-12 | — | 400.2 |  | 160 | 2016-2020 | split-half (BT-02), m:r = 100:0.200; variance-components cross-check k = 355.2 |
| `fit:k/OFF-12/share` | OFF-12 | — | 21.4 |  | 1280 | 2016-2020 | split-half (BT-02), m:r = 25:0.572, 50:0.704, 100:0.797, 200:0.860; variance-components cross-check k = 15.6 |
| `fit:k/OFF-12/success` | OFF-12 | 60.0 | 164.0 | **+173%** | 411 | 2016-2020 | split-half (BT-02), m:r = 25:0.132 |
| `fit:k/OFF-12/ypc` | OFF-12 | 100.0 | 114.9 | +15% | 411 | 2016-2020 | split-half (BT-02), m:r = 25:0.179 |
| `fit:k/OFF-12/ypc_team` | OFF-12 | — | 333.6 |  | 160 | 2016-2020 | split-half (BT-02), m:r = 100:0.231; variance-components cross-check k = 310.3 |
| `fit:k/OFF-13/cpoe_team` | OFF-13 | — | 379.8 |  | 160 | 2016-2020 | split-half (BT-02), m:r = 100:0.222, 200:0.319; variance-components cross-check k = 324.2 |
| `fit:k/OFF-13/epa` | OFF-13 | 60.0 | 133.7 | **+123%** | 538 | 2016-2020 | split-half (BT-02), m:r = 25:0.158 |
| `fit:k/OFF-13/share` | OFF-13 | 60.0 | 19.5 | **-67%** | 2080 | 2016-2020 | split-half (BT-02), m:r = 25:0.567, 50:0.722, 100:0.836, 200:0.908; variance-components cross-check k = 18.5 |
| `fit:k/OFF-14/pass_share` | OFF-14 | 25.0 | 80.1 | **+221%** | 305 | 2016-2020 | split-half (BT-02), m:r = 25:0.242, 50:0.377; variance-components cross-check k = 56.5 |
| `fit:k/OFF-15/hit_rate` | OFF-15 | 200.0 | 159.2 | -20% | 160 | 2016-2020 | split-half (BT-02), m:r = 50:0.239, 100:0.393, 200:0.550; variance-components cross-check k = 150.0 |
| `fit:k/OFF-15/sack_rate` | OFF-15 | 200.0 | 318.0 | **+59%** | 160 | 2016-2020 | split-half (BT-02), m:r = 100:0.236, 200:0.389; variance-components cross-check k = 273.7 |
| `fit:k/OFF-16/stuff` | OFF-16 | 80.0 | 190.8 | **+138%** | 320 | 2016-2020 | split-half (BT-02), m:r = 50:0.208; variance-components cross-check k = 180.3 |
| `fit:k/OFF-16/stuff_team` | OFF-16 | — | 195.6 |  | 160 | 2016-2020 | split-half (BT-02), m:r = 50:0.190, 100:0.350; variance-components cross-check k = 171.7 |
| `fit:k/OFF-16/success` | OFF-16 | 80.0 | 252.8 | **+216%** | 320 | 2016-2020 | split-half (BT-02), m:r = 50:0.165; variance-components cross-check k = 209.0 |
| `fit:k/PLY-03/target_share` | PLY-03 | 60.0 | 10.5 | **-82%** | 4295 | 2016-2020 | split-half (BT-02), m:r = 25:0.714, 50:0.828, 100:0.900, 200:0.947; variance-components cross-check k = 9.0 |
| `fit:k/PLY-04/air_share` | PLY-04 | 60.0 | 13.5 | **-77%** | 4295 | 2016-2020 | split-half (BT-02), m:r = 25:0.651, 50:0.788, 100:0.880, 200:0.936 |
| `fit:k/PLY-04/wopr` | PLY-04 | 60.0 | 10.1 | **-83%** | 4295 | 2016-2020 | split-half (BT-02), m:r = 25:0.722, 50:0.832, 100:0.905, 200:0.949 |
| `fit:k/PLY-05/carry_share` | PLY-05 | 40.0 | 2.6059 | **-93%** | 4069 | 2016-2020 | split-half (BT-02), m:r = 25:0.915, 50:0.949, 100:0.969, 200:0.982; variance-components cross-check k = 1.4 |
| `fit:k/PLY-06/opportunity_share` | PLY-06 | 20.0 | 7.6926 | **-62%** | 5381 | 2016-2020 | split-half (BT-02), m:r = 25:0.769, 50:0.858 |
| `fit:k/PLY-06/opportunity_share_overall` | PLY-06 | — | 10.1 |  | 4370 | 2016-2020 | split-half (BT-02), m:r = 25:0.742, 50:0.837, 100:0.904, 200:0.942, 400:0.966; variance-components cross-check k = 7.3 |
| `fit:k/PLY-07/opportunity_share` | PLY-07 | 30.0 | 11.4 | **-62%** | 6486 | 2016-2020 | split-half (BT-02), m:r = 25:0.687, 50:0.816, 100:0.896 |
| `fit:k/PLY-08/yards_per_team_dropback` | PLY-08 | 150.0 | 27.7 | **-82%** | 4292 | 2016-2020 | split-half (BT-02), m:r = 25:0.480, 50:0.643, 100:0.780, 200:0.880; variance-components cross-check k = 26.4 |
| `fit:k/PLY-09/yacoe` | PLY-09 | 60.0 | 71.0 | +18% | 301 | 2016-2020 | split-half (BT-02), m:r = 25:0.261 |
| `fit:k/PLY-10/croe` | PLY-10 | 80.0 | 199.5 | **+149%** | 610 | 2016-2020 | split-half (BT-02), m:r = 25:0.111 |
| `fit:k/PLY-16/share` | PLY-16 | 40.0 | 18.2 | **-54%** | 2989 | 2016-2020 | split-half (BT-02), m:r = 25:0.599, 50:0.714, 100:0.811 |
| `fit:k/PLY-18/adot` | PLY-18 | 80.0 | 180.3 | **+125%** | 229 | 2016-2020 | split-half (BT-02), m:r = 50:0.238, 100:0.359, 200:0.458 |
| `fit:k/PLY-18/epa` | PLY-18 | 80.0 | 47.4 | -41% | 562 | 2016-2020 | split-half (BT-02), m:r = 25:0.366, 50:0.387 |
| `fit:k/PLY-18/epa_overall` | PLY-18 | — | 332.7 |  | 229 | 2016-2020 | split-half (BT-02), m:r = 50:0.152, 100:0.226, 200:0.323 |
| `fit:k/PLY-18/share` | PLY-18 | 80.0 | 4.3002 | **-95%** | 1145 | 2016-2020 | split-half (BT-02), m:r = 25:0.855, 50:0.921, 100:0.958, 200:0.978 |
| `fit:k/PLY-20/cpoe` | PLY-20 | 200.0 | 296.2 | +48% | 229 | 2016-2020 | split-half (BT-02), m:r = 50:0.158, 100:0.235 |
| `fit:k/PLY-21/sack_rate` | PLY-21 | 150.0 | 236.0 | **+57%** | 232 | 2016-2020 | split-half (BT-02), m:r = 50:0.203, 100:0.277, 200:0.430 |
| `fit:k/PLY-21/time_to_throw` | PLY-21 | 150.0 | 76.8 | -49% | 225 | 2016-2020 | split-half (BT-02), m:r = 25:0.330, 50:0.475, 100:0.601, 200:0.741 |
| `fit:k/PLY-22/scramble_rate` | PLY-22 | — | 62.7 |  | 232 | 2016-2020 | split-half (BT-02), m:r = 25:0.298, 50:0.456, 100:0.611, 200:0.738 |
| `fit:k/PLY-23/epa` | PLY-23 | 100.0 | 165.0 | **+65%** | 535 | 2016-2020 | split-half (BT-02), m:r = 25:0.136, 50:0.228 |
| `fit:k/PLY-23/epa_overall` | PLY-23 | — | 360.9 |  | 229 | 2016-2020 | split-half (BT-02), m:r = 100:0.233, 200:0.303 |
| `fit:k/PLY-23/share` | PLY-23 | 100.0 | 6.9106 | **-93%** | 916 | 2016-2020 | split-half (BT-02), m:r = 25:0.793, 50:0.880, 100:0.932, 200:0.962 |
| `fit:k/PLY-25/success` | PLY-25 | 60.0 | 166.1 | **+177%** | 364 | 2016-2020 | split-half (BT-02), m:r = 25:0.128, 50:0.236 |
| `fit:k/PLY-25/success_overall` | PLY-25 | — | 169.5 |  | 349 | 2016-2020 | split-half (BT-02), m:r = 25:0.142, 50:0.194 |
| `fit:k/PLY-25/ypc` | PLY-25 | 60.0 | 153.7 | **+156%** | 362 | 2016-2020 | split-half (BT-02), m:r = 25:0.149, 50:0.219 |
| `fit:k/PLY-26/explosive` | PLY-26 | 150.0 | 253.7 | **+69%** | 348 | 2016-2020 | split-half (BT-02), m:r = 50:0.165 |
| `fit:k/PLY-26/stuff` | PLY-26 | 100.0 | 171.0 | **+71%** | 349 | 2016-2020 | split-half (BT-02), m:r = 25:0.130, 50:0.224 |
| `fit:k/PLY-27/target_share` | PLY-27 | 40.0 | 10.6 | **-74%** | 4295 | 2016-2020 | split-half (BT-02), m:r = 25:0.714, 50:0.827, 100:0.900, 200:0.946; variance-components cross-check k = 9.0 |
| `fit:k/PLY-27/yacoe` | PLY-27 | 40.0 | 82.6 | **+106%** | 302 | 2016-2020 | split-half (BT-02), m:r = 25:0.232 |
| `fit:k/PLY-28/adot` | PLY-28 | 40.0 | 6.6059 | **-83%** | 609 | 2016-2020 | split-half (BT-02), m:r = 25:0.798, 50:0.808 |
| `fit:k/PLY-28/epa_overall` | PLY-28 | — | 204.0 |  | 608 | 2016-2020 | split-half (BT-02), m:r = 25:0.109 |
| `fit:k/PLY-28/share` | PLY-28 | 40.0 | 3.5610 | **-91%** | 3042 | 2016-2020 | split-half (BT-02), m:r = 25:0.877, 50:0.927 |
| `fit:k/PLY-29/epa_overall` | PLY-29 | — | 204.3 |  | 609 | 2016-2020 | split-half (BT-02), m:r = 25:0.109 |
| `fit:k/PLY-29/share` | PLY-29 | 50.0 | 6.2147 | **-88%** | 2439 | 2016-2020 | split-half (BT-02), m:r = 25:0.801, 50:0.888 |
| `fit:k/PLY-31/cushion` | PLY-31 | 80.0 | 59.5 | -26% | 403 | 2016-2020 | split-half (BT-02), m:r = 25:0.338, 50:0.437 |
| `fit:k/PLY-31/separation` | PLY-31 | 80.0 | 42.5 | -47% | 402 | 2016-2020 | split-half (BT-02), m:r = 25:0.409, 50:0.551 |
| `fit:k/PLY-32/end_zone_share` | PLY-32 | 15.0 | 5.6124 | **-63%** | 291 | 2016-2020 | split-half (BT-02), m:r = 25:0.817 |
| `conventions.g3_usage_half_life_games` | G3 | 3.0000 | 8.0000 | **+167%** | 16 | 2016-2020 | next-game n-weighted squared error / prior-only, mean over 16 usage stats (ruling 2026-10-08) |
| `conventions.g3_efficiency_half_life_games` | G3 | 6.0000 | 12.0 | **+100%** | 63 | 2016-2020 | next-game n-weighted squared error / prior-only, mean over 63 efficiency stats (ruling 2026-10-08) |
| `fit:G6/penalty` | G6 | — | 316.2 |  | 139685 | 2016-2020 | forward-chaining CV within each season (BT-02), efficiency h = 12 |
| `fit:COA-02/p_go/intercept` | COA-02 | — | 1.4031 |  | 16606 | 2016-2020 | logistic, four fields as linear terms (se 0.0802) |
| `fit:COA-02/p_go/ydstogo` | COA-02 | — | -0.3400 |  | 16606 | 2016-2020 | logistic, four fields as linear terms (se 0.0101) |
| `fit:COA-02/p_go/yardline_100` | COA-02 | — | -0.0227 |  | 16606 | 2016-2020 | logistic, four fields as linear terms (se 0.00113) |
| `fit:COA-02/p_go/score_differential` | COA-02 | — | -0.0558 |  | 16606 | 2016-2020 | logistic, four fields as linear terms (se 0.00323) |
| `fit:COA-02/p_go/game_seconds_remaining` | COA-02 | — | -0.000465 |  | 16606 | 2016-2020 | logistic, four fields as linear terms (se 2.87e-05) |
| `matchup.mtc_03_ol_absence_factor` | MTC-03 | 1.1000 | 1.0685 | -3% | 5142 | 2016-2020 | offset logistic on dropbacks, exp(coef) per missing OFF-17 starter (se of log 0.0181); undamped |
| `fit:PLY-14/practice/DNP` | PLY-14 | — | 0.1730 |  | 7267 | 2016-2020 | P(played | DNP) |
| `fit:PLY-14/practice/Limited` | PLY-14 | — | 0.6907 |  | 6341 | 2016-2020 | P(played | Limited) |
| `fit:PLY-14/practice/Full` | PLY-14 | — | 0.9404 |  | 11997 | 2016-2020 | P(played | Full) |
| `fit:PRJ-06/missed/QB` | PRJ-06 | — | 0.1595 |  | 2935 | 2016-2020 | P(no snap | played last game), QB |
| `fit:PRJ-06/missed/RB` | PRJ-06 | — | 0.1225 |  | 7826 | 2016-2020 | P(no snap | played last game), RB |
| `fit:PRJ-06/missed/WR` | PRJ-06 | — | 0.1067 |  | 11465 | 2016-2020 | P(no snap | played last game), WR |
| `fit:PRJ-06/missed/TE` | PRJ-06 | — | 0.0853 |  | 6896 | 2016-2020 | P(no snap | played last game), TE |
| `player.ply_14_return_factor` | PLY-14 | 0.8500 | 0.9305 | +9% | 546 | 2016-2020 | sum first-game-back snap share / sum baseline (usage h = 8) |
| `fit:role/PLY-01/snap_share/all/QB1` | PLY-01 | — | 0.8795 |  | 274 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/RB1` | PLY-01 | — | 0.5207 |  | 338 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/RB2` | PLY-01 | — | 0.2994 |  | 468 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/TE1` | PLY-01 | — | 0.6410 |  | 311 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR1` | PLY-01 | — | 0.7505 |  | 358 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR2` | PLY-01 | — | 0.6696 |  | 504 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR3` | PLY-01 | — | 0.5233 |  | 595 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/QB1` | PLY-02 | — | 0.8795 |  | 274 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/RB1` | PLY-02 | — | 0.5207 |  | 338 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/RB2` | PLY-02 | — | 0.2994 |  | 468 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/TE1` | PLY-02 | — | 0.6410 |  | 311 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR1` | PLY-02 | — | 0.7505 |  | 358 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR2` | PLY-02 | — | 0.6696 |  | 504 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR3` | PLY-02 | — | 0.5233 |  | 595 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/QB1` | PLY-03 | — | 0.000673 |  | 274 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/RB1` | PLY-03 | — | 0.1054 |  | 338 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/RB2` | PLY-03 | — | 0.0650 |  | 468 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/TE1` | PLY-03 | — | 0.1312 |  | 311 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR1` | PLY-03 | — | 0.2162 |  | 358 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR2` | PLY-03 | — | 0.1705 |  | 504 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR3` | PLY-03 | — | 0.1199 |  | 595 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/QB1` | PLY-04 | — | 0.000173 |  | 274 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/RB1` | PLY-04 | — | 0.00763 |  | 338 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/RB2` | PLY-04 | — | 0.00585 |  | 468 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/TE1` | PLY-04 | — | 0.1242 |  | 311 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR1` | PLY-04 | — | 0.2970 |  | 358 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR2` | PLY-04 | — | 0.2268 |  | 504 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR3` | PLY-04 | — | 0.1520 |  | 595 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/QB1` | PLY-04 | — | 0.00113 |  | 274 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/RB1` | PLY-04 | — | 0.1634 |  | 338 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/RB2` | PLY-04 | — | 0.1016 |  | 468 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/TE1` | PLY-04 | — | 0.2837 |  | 311 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR1` | PLY-04 | — | 0.5323 |  | 358 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR2` | PLY-04 | — | 0.4145 |  | 504 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR3` | PLY-04 | — | 0.2863 |  | 595 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/QB1` | PLY-05 | — | 0.0469 |  | 274 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/RB1` | PLY-05 | — | 0.5392 |  | 338 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/RB2` | PLY-05 | — | 0.2705 |  | 468 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/TE1` | PLY-05 | — | 0.000788 |  | 311 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR1` | PLY-05 | — | 0.0064 |  | 358 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR2` | PLY-05 | — | 0.00665 |  | 504 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR3` | PLY-05 | — | 0.00747 |  | 595 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/QB1` | PLY-06 | — | 0.0207 |  | 274 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/RB1` | PLY-06 | — | 0.2835 |  | 338 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/RB2` | PLY-06 | — | 0.1518 |  | 468 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/TE1` | PLY-06 | — | 0.0770 |  | 311 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR1` | PLY-06 | — | 0.1287 |  | 358 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR2` | PLY-06 | — | 0.1021 |  | 504 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR3` | PLY-06 | — | 0.0735 |  | 595 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-08/yards_per_team_dropback/all/QB1` | PLY-08 | — | 0.00144 |  | 274 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/RB1` | PLY-08 | — | 0.5681 |  | 338 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/RB2` | PLY-08 | — | 0.3250 |  | 468 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/TE1` | PLY-08 | — | 0.8721 |  | 311 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR1` | PLY-08 | — | 1.5924 |  | 358 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR2` | PLY-08 | — | 1.2026 |  | 504 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR3` | PLY-08 | — | 0.8234 |  | 595 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/QB1` | PLY-18 | — | 8.1996 |  | 271 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/WR1` | PLY-18 | — | 13.8 |  | 36 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/QB1` | PLY-18 | — | 0.1688 |  | 271 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/WR1` | PLY-18 | — | 0.5938 |  | 36 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/share/behind/QB1` | PLY-18 | — | 0.1448 |  | 271 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/behind/WR1` | PLY-18 | — | 0.1000 |  | 36 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/QB1` | PLY-18 | — | 0.1208 |  | 271 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/WR1` | PLY-18 | — | 0.2727 |  | 36 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/QB1` | PLY-18 | — | 0.2188 |  | 271 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/WR1` | PLY-18 | — | 0.3909 |  | 36 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/QB1` | PLY-18 | — | 0.5154 |  | 271 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/WR1` | PLY-18 | — | 0.2364 |  | 36 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/QB1` | PLY-18 | — | 0.000172 |  | 271 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/WR1` | PLY-18 | — | 0 |  | 36 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/epa_overall/all/QB1` | PLY-23 | — | 0.1688 |  | 271 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/epa_overall/all/WR1` | PLY-23 | — | 0.5938 |  | 36 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/share/left/QB1` | PLY-23 | — | 0.3702 |  | 271 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/left/WR1` | PLY-23 | — | 0.2409 |  | 36 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/QB1` | PLY-23 | — | 0.2306 |  | 271 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/WR1` | PLY-23 | — | 0.0455 |  | 36 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/QB1` | PLY-23 | — | 0.3988 |  | 271 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/WR1` | PLY-23 | — | 0.7136 |  | 36 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/QB1` | PLY-23 | — | 0.000372 |  | 271 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/WR1` | PLY-23 | — | 0 |  | 36 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-25/success_overall/all/QB1` | PLY-25 | — | 0.5268 |  | 226 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/RB1` | PLY-25 | — | 0.3844 |  | 331 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/RB2` | PLY-25 | — | 0.3837 |  | 446 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR1` | PLY-25 | — | 0.4905 |  | 131 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR2` | PLY-25 | — | 0.5733 |  | 148 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR3` | PLY-25 | — | 0.5214 |  | 146 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/QB1` | PLY-25 | — | 4.0814 |  | 226 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/RB1` | PLY-25 | — | 4.2680 |  | 331 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/RB2` | PLY-25 | — | 4.2284 |  | 446 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR1` | PLY-25 | — | 6.2141 |  | 131 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR2` | PLY-25 | — | 6.4424 |  | 148 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR3` | PLY-25 | — | 5.9874 |  | 146 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-27/target_share/all/QB1` | PLY-27 | — | 0.000673 |  | 274 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/RB1` | PLY-27 | — | 0.1054 |  | 338 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/RB2` | PLY-27 | — | 0.0650 |  | 468 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/TE1` | PLY-27 | — | 0.1312 |  | 311 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR1` | PLY-27 | — | 0.2162 |  | 358 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR2` | PLY-27 | — | 0.1705 |  | 504 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR3` | PLY-27 | — | 0.1199 |  | 595 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/RB1` | PLY-27 | — | 0.5746 |  | 310 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/RB2` | PLY-27 | — | 0.4898 |  | 399 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/TE1` | PLY-27 | — | 0.1823 |  | 280 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR1` | PLY-27 | — | -0.3917 |  | 341 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR2` | PLY-27 | — | -0.4239 |  | 478 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR3` | PLY-27 | — | -0.5013 |  | 536 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/adot/all/QB1` | PLY-28 | — | 2.6000 |  | 39 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/RB1` | PLY-28 | — | 0.7273 |  | 318 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/RB2` | PLY-28 | — | 0.8801 |  | 417 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/TE1` | PLY-28 | — | 7.6358 |  | 290 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR1` | PLY-28 | — | 11.2 |  | 351 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR2` | PLY-28 | — | 11.0 |  | 490 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR3` | PLY-28 | — | 10.5 |  | 558 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/QB1` | PLY-28 | — | -0.0727 |  | 39 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/RB1` | PLY-28 | — | 0.0549 |  | 318 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/RB2` | PLY-28 | — | -0.00238 |  | 417 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/TE1` | PLY-28 | — | 0.2109 |  | 290 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR1` | PLY-28 | — | 0.2858 |  | 351 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR2` | PLY-28 | — | 0.2401 |  | 490 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR3` | PLY-28 | — | 0.2063 |  | 558 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/share/behind/QB1` | PLY-28 | — | 0.3333 |  | 39 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/RB1` | PLY-28 | — | 0.4137 |  | 318 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/RB2` | PLY-28 | — | 0.4086 |  | 417 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/TE1` | PLY-28 | — | 0.0866 |  | 290 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR1` | PLY-28 | — | 0.0708 |  | 351 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR2` | PLY-28 | — | 0.0752 |  | 490 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR3` | PLY-28 | — | 0.0896 |  | 558 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/QB1` | PLY-28 | — | 0.0222 |  | 39 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/RB1` | PLY-28 | — | 0.0153 |  | 318 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/RB2` | PLY-28 | — | 0.0182 |  | 417 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/TE1` | PLY-28 | — | 0.0812 |  | 290 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR1` | PLY-28 | — | 0.1726 |  | 351 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR2` | PLY-28 | — | 0.1723 |  | 490 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR3` | PLY-28 | — | 0.1655 |  | 558 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/QB1` | PLY-28 | — | 0.2222 |  | 39 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/RB1` | PLY-28 | — | 0.0283 |  | 318 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/RB2` | PLY-28 | — | 0.0294 |  | 417 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/TE1` | PLY-28 | — | 0.2288 |  | 290 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR1` | PLY-28 | — | 0.3036 |  | 351 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR2` | PLY-28 | — | 0.2725 |  | 490 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR3` | PLY-28 | — | 0.2508 |  | 558 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/QB1` | PLY-28 | — | 0.4222 |  | 39 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/RB1` | PLY-28 | — | 0.5422 |  | 318 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/RB2` | PLY-28 | — | 0.5438 |  | 417 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/TE1` | PLY-28 | — | 0.6034 |  | 290 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR1` | PLY-28 | — | 0.4530 |  | 351 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR2` | PLY-28 | — | 0.4800 |  | 490 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR3` | PLY-28 | — | 0.4939 |  | 558 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/QB1` | PLY-28 | — | 0 |  | 39 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/RB1` | PLY-28 | — | 0.000551 |  | 318 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/RB2` | PLY-28 | — | 0 |  | 417 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/TE1` | PLY-28 | — | 0 |  | 290 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR1` | PLY-28 | — | 0 |  | 351 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR2` | PLY-28 | — | 0 |  | 490 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR3` | PLY-28 | — | 0.00022 |  | 558 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/epa_overall/all/QB1` | PLY-29 | — | -0.0727 |  | 39 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/RB1` | PLY-29 | — | 0.0549 |  | 318 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/RB2` | PLY-29 | — | -0.00238 |  | 417 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/TE1` | PLY-29 | — | 0.2109 |  | 290 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR1` | PLY-29 | — | 0.2858 |  | 351 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR2` | PLY-29 | — | 0.2401 |  | 490 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR3` | PLY-29 | — | 0.2063 |  | 558 | 2016-2020 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/share/left/QB1` | PLY-29 | — | 0.3333 |  | 39 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/RB1` | PLY-29 | — | 0.3970 |  | 318 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/RB2` | PLY-29 | — | 0.4055 |  | 417 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/TE1` | PLY-29 | — | 0.3154 |  | 290 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR1` | PLY-29 | — | 0.3927 |  | 351 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR2` | PLY-29 | — | 0.3742 |  | 490 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR3` | PLY-29 | — | 0.3755 |  | 558 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/QB1` | PLY-29 | — | 0.2889 |  | 39 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/RB1` | PLY-29 | — | 0.2028 |  | 318 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/RB2` | PLY-29 | — | 0.1988 |  | 417 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/TE1` | PLY-29 | — | 0.2802 |  | 290 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR1` | PLY-29 | — | 0.2308 |  | 351 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR2` | PLY-29 | — | 0.2386 |  | 490 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR3` | PLY-29 | — | 0.2328 |  | 558 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/QB1` | PLY-29 | — | 0.3778 |  | 39 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/RB1` | PLY-29 | — | 0.3997 |  | 318 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/RB2` | PLY-29 | — | 0.3957 |  | 417 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/TE1` | PLY-29 | — | 0.4043 |  | 290 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR1` | PLY-29 | — | 0.3764 |  | 351 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR2` | PLY-29 | — | 0.3872 |  | 490 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR3` | PLY-29 | — | 0.3915 |  | 558 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/QB1` | PLY-29 | — | 0 |  | 39 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/RB1` | PLY-29 | — | 0.000551 |  | 318 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/RB2` | PLY-29 | — | 0 |  | 417 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/TE1` | PLY-29 | — | 0.000176 |  | 290 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR1` | PLY-29 | — | 5.6e-05 |  | 351 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR2` | PLY-29 | — | 5.03e-05 |  | 490 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR3` | PLY-29 | — | 0.00022 |  | 558 | 2016-2020 | section 4 slot prior: mean over slot occupants' games of his game share |

## S2022 (seasons 2016-2021)

| key | spec | initial | fitted | change | n | seasons | method |
|---|---|---|---|---|---|---|---|
| `fit:k/COA-04/proe` | COA-04 | 80.0 | 93.6 | +17% | 371 | 2016-2021 | split-half (BT-02), m:r = 25:0.204, 50:0.328, 100:0.570; variance-components cross-check k = 78.5 |
| `fit:k/COA-04/seconds_per_play` | COA-04 | 80.0 | 20.2 | **-75%** | 281 | 2016-2021 | split-half (BT-02), m:r = 25:0.559, 50:0.683; variance-components cross-check k = 11.9 |
| `fit:k/DEF-01/epa/all` | DEF-01 | 250.0 | 792.6 | **+217%** | 192 | 2016-2021 | split-half (BT-02), m:r = 200:0.206, 400:0.328; variance-components cross-check k = 602.2 |
| `fit:k/DEF-01/epa/pass` | DEF-01 | 200.0 | 716.2 | **+258%** | 192 | 2016-2021 | split-half (BT-02), m:r = 200:0.218; variance-components cross-check k = 479.9 |
| `fit:k/DEF-01/epa/run` | DEF-01 | 300.0 | 513.8 | **+71%** | 192 | 2016-2021 | split-half (BT-02), m:r = 100:0.163; variance-components cross-check k = 479.0 |
| `fit:k/DEF-02/success` | DEF-02 | 150.0 | 247.8 | **+65%** | 576 | 2016-2021 | split-half (BT-02), m:r = 25:0.100, 50:0.187, 100:0.307, 200:0.311, 400:0.389; variance-components cross-check k = 234.3 |
| `fit:k/DEF-03/explosive` | DEF-03 | 150.0 | 112.4 | -25% | 501 | 2016-2021 | split-half (BT-02), m:r = 25:0.182 |
| `fit:k/DEF-03/share` | DEF-03 | — | 24.0 |  | 1536 | 2016-2021 | split-half (BT-02), m:r = 25:0.544, 50:0.679, 100:0.777; variance-components cross-check k = 17.0 |
| `fit:k/DEF-03/success` | DEF-03 | 60.0 | 140.4 | **+134%** | 499 | 2016-2021 | split-half (BT-02), m:r = 25:0.151 |
| `fit:k/DEF-03/ypc` | DEF-03 | 100.0 | 144.3 | +44% | 499 | 2016-2021 | split-half (BT-02), m:r = 25:0.148 |
| `fit:k/DEF-03/ypc_team` | DEF-03 | — | 556.5 |  | 192 | 2016-2021 | split-half (BT-02), m:r = 100:0.152; variance-components cross-check k = 486.9 |
| `fit:k/DEF-04/epa_diff` | DEF-04 | 60.0 | 513.3 | **+755%** | 576 | 2016-2021 | split-half (BT-02), m:r = 100:0.175 |
| `fit:k/DEF-04/receptions` | DEF-04 | 60.0 | 310.1 | **+417%** | 576 | 2016-2021 | split-half (BT-02), m:r = 25:0.098, 50:0.138 |
| `fit:k/DEF-04/targets` | DEF-04 | 60.0 | 351.7 | **+486%** | 576 | 2016-2021 | split-half (BT-02), m:r = 25:0.087, 50:0.125 |
| `fit:k/DEF-04/yards` | DEF-04 | 60.0 | 323.3 | **+439%** | 576 | 2016-2021 | split-half (BT-02), m:r = 25:0.099, 50:0.147, 100:0.172 |
| `fit:k/DEF-06/explosive` | DEF-06 | 300.0 | 1,218 | **+306%** | 192 | 2016-2021 | split-half (BT-02), m:r = 200:0.149, 400:0.230; variance-components cross-check k = 949.4 |
| `fit:k/DEF-06/explosive_run` | DEF-06 | 300.0 | 486.4 | **+62%** | 192 | 2016-2021 | split-half (BT-02), m:r = 100:0.171; variance-components cross-check k = 463.1 |
| `fit:k/DEF-09/cpoe_team` | DEF-09 | — | 714.5 |  | 192 | 2016-2021 | split-half (BT-02), m:r = 200:0.219; variance-components cross-check k = 557.3 |
| `fit:k/DEF-09/epa` | DEF-09 | 60.0 | 197.9 | **+230%** | 615 | 2016-2021 | split-half (BT-02), m:r = 25:0.112 |
| `fit:k/DEF-15/success` | DEF-15 | 60.0 | 310.1 | **+417%** | 384 | 2016-2021 | split-half (BT-02), m:r = 50:0.139; variance-components cross-check k = 238.1 |
| `fit:k/DEF-15/ypc` | DEF-15 | 60.0 | 314.1 | **+423%** | 384 | 2016-2021 | split-half (BT-02), m:r = 50:0.137; variance-components cross-check k = 265.8 |
| `fit:k/DEF-17/passes_defensed` | DEF-17 | 20.0 | 19.6 | -2% | 2744 | 2016-2021 | split-half (BT-02), m:r = 25:0.583 |
| `fit:k/DEF-17/qb_hits` | DEF-17 | 20.0 | 11.8 | -41% | 3397 | 2016-2021 | split-half (BT-02), m:r = 25:0.703, 50:0.831 |
| `fit:k/DEF-17/sacks` | DEF-17 | 20.0 | 8.2754 | **-59%** | 263 | 2017-2021 | split-half (BT-02), m:r = 25:0.760 |
| `fit:k/DEF-17/tackles_for_loss` | DEF-17 | 20.0 | 27.6 | +38% | 2855 | 2016-2021 | split-half (BT-02), m:r = 25:0.497 |
| `fit:k/OFF-01/epa/all` | OFF-01 | 250.0 | 342.2 | +37% | 192 | 2016-2021 | split-half (BT-02), m:r = 50:0.149, 100:0.233, 200:0.372, 400:0.490; variance-components cross-check k = 305.4 |
| `fit:k/OFF-01/epa/pass` | OFF-01 | 200.0 | 285.9 | +43% | 192 | 2016-2021 | split-half (BT-02), m:r = 100:0.263, 200:0.408; variance-components cross-check k = 254.3 |
| `fit:k/OFF-01/epa/run` | OFF-01 | 300.0 | 296.2 | -1% | 192 | 2016-2021 | split-half (BT-02), m:r = 50:0.145, 100:0.252; variance-components cross-check k = 274.7 |
| `fit:k/OFF-02/success` | OFF-02 | 150.0 | 172.1 | +15% | 576 | 2016-2021 | split-half (BT-02), m:r = 25:0.140, 50:0.250, 100:0.385, 200:0.467, 400:0.538; variance-components cross-check k = 160.2 |
| `fit:k/OFF-03/epa` | OFF-03 | 100.0 | 310.8 | **+211%** | 670 | 2016-2021 | split-half (BT-02), m:r = 50:0.147, 100:0.227; variance-components cross-check k = 154.3 |
| `fit:k/OFF-03/success` | OFF-03 | 100.0 | 225.1 | **+125%** | 671 | 2016-2021 | split-half (BT-02), m:r = 25:0.106, 50:0.177, 100:0.307; variance-components cross-check k = 162.8 |
| `fit:k/OFF-04/pass_rate` | OFF-04 | 60.0 | 114.9 | **+92%** | 192 | 2016-2021 | split-half (BT-02), m:r = 25:0.162, 50:0.301, 100:0.468, 200:0.642; variance-components cross-check k = 109.5 |
| `fit:k/OFF-05/proe` | OFF-05 | 100.0 | 121.4 | +21% | 192 | 2016-2021 | split-half (BT-02), m:r = 25:0.181, 50:0.305, 100:0.453, 200:0.607; variance-components cross-check k = 109.7 |
| `fit:k/OFF-09/shotgun_rate` | OFF-09 | 60.0 | 18.9 | **-69%** | 192 | 2016-2021 | split-half (BT-02), m:r = 25:0.624, 50:0.747, 100:0.835, 200:0.890, 400:0.931; variance-components cross-check k = 13.1 |
| `fit:k/OFF-10/seconds_per_play` | OFF-10 | 80.0 | 40.1 | -50% | 192 | 2016-2021 | split-half (BT-02), m:r = 25:0.426, 50:0.537, 100:0.690; variance-components cross-check k = 30.6 |
| `fit:k/OFF-12/epa` | OFF-12 | 100.0 | 173.7 | **+74%** | 506 | 2016-2021 | split-half (BT-02), m:r = 25:0.126 |
| `fit:k/OFF-12/explosive` | OFF-12 | 150.0 | 73.2 | **-51%** | 506 | 2016-2021 | split-half (BT-02), m:r = 25:0.255 |
| `fit:k/OFF-12/explosive_team` | OFF-12 | — | 395.5 |  | 192 | 2016-2021 | split-half (BT-02), m:r = 100:0.202; variance-components cross-check k = 350.7 |
| `fit:k/OFF-12/share` | OFF-12 | — | 21.8 |  | 1536 | 2016-2021 | split-half (BT-02), m:r = 25:0.568, 50:0.701, 100:0.794, 200:0.859; variance-components cross-check k = 16.0 |
| `fit:k/OFF-12/success` | OFF-12 | 60.0 | 163.4 | **+172%** | 505 | 2016-2021 | split-half (BT-02), m:r = 25:0.133 |
| `fit:k/OFF-12/ypc` | OFF-12 | 100.0 | 106.5 | +6% | 505 | 2016-2021 | split-half (BT-02), m:r = 25:0.190 |
| `fit:k/OFF-12/ypc_team` | OFF-12 | — | 319.0 |  | 192 | 2016-2021 | split-half (BT-02), m:r = 100:0.239; variance-components cross-check k = 297.4 |
| `fit:k/OFF-13/cpoe_team` | OFF-13 | — | 387.3 |  | 192 | 2016-2021 | split-half (BT-02), m:r = 100:0.221, 200:0.306; variance-components cross-check k = 321.3 |
| `fit:k/OFF-13/epa` | OFF-13 | 60.0 | 154.6 | **+158%** | 643 | 2016-2021 | split-half (BT-02), m:r = 25:0.139 |
| `fit:k/OFF-13/share` | OFF-13 | 60.0 | 19.4 | **-68%** | 2496 | 2016-2021 | split-half (BT-02), m:r = 25:0.569, 50:0.723, 100:0.837, 200:0.908; variance-components cross-check k = 18.4 |
| `fit:k/OFF-14/pass_share` | OFF-14 | 25.0 | 82.0 | **+228%** | 372 | 2016-2021 | split-half (BT-02), m:r = 25:0.238, 50:0.371; variance-components cross-check k = 58.8 |
| `fit:k/OFF-15/hit_rate` | OFF-15 | 200.0 | 170.9 | -15% | 192 | 2016-2021 | split-half (BT-02), m:r = 50:0.225, 100:0.375, 200:0.534; variance-components cross-check k = 159.2 |
| `fit:k/OFF-15/sack_rate` | OFF-15 | 200.0 | 318.9 | **+59%** | 192 | 2016-2021 | split-half (BT-02), m:r = 100:0.238, 200:0.386; variance-components cross-check k = 278.1 |
| `fit:k/OFF-16/stuff` | OFF-16 | 80.0 | 206.2 | **+158%** | 384 | 2016-2021 | split-half (BT-02), m:r = 25:0.104, 50:0.199; variance-components cross-check k = 176.1 |
| `fit:k/OFF-16/stuff_team` | OFF-16 | — | 200.6 |  | 192 | 2016-2021 | split-half (BT-02), m:r = 50:0.195, 100:0.338; variance-components cross-check k = 174.7 |
| `fit:k/OFF-16/success` | OFF-16 | 80.0 | 205.2 | **+156%** | 384 | 2016-2021 | split-half (BT-02), m:r = 25:0.111, 50:0.193; variance-components cross-check k = 188.5 |
| `fit:k/PLY-03/target_share` | PLY-03 | 60.0 | 10.6 | **-82%** | 5226 | 2016-2021 | split-half (BT-02), m:r = 25:0.714, 50:0.827, 100:0.900, 200:0.947; variance-components cross-check k = 9.0 |
| `fit:k/PLY-04/air_share` | PLY-04 | 60.0 | 13.6 | **-77%** | 5226 | 2016-2021 | split-half (BT-02), m:r = 25:0.647, 50:0.787, 100:0.880, 200:0.936 |
| `fit:k/PLY-04/wopr` | PLY-04 | 60.0 | 10.1 | **-83%** | 5226 | 2016-2021 | split-half (BT-02), m:r = 25:0.722, 50:0.833, 100:0.905, 200:0.950 |
| `fit:k/PLY-05/carry_share` | PLY-05 | 40.0 | 2.6839 | **-93%** | 4955 | 2016-2021 | split-half (BT-02), m:r = 25:0.913, 50:0.947, 100:0.968, 200:0.982; variance-components cross-check k = 1.4 |
| `fit:k/PLY-06/opportunity_share` | PLY-06 | 20.0 | 7.7053 | **-61%** | 6592 | 2016-2021 | split-half (BT-02), m:r = 25:0.769, 50:0.858, 100:0.916 |
| `fit:k/PLY-06/opportunity_share_overall` | PLY-06 | — | 10.1 |  | 5319 | 2016-2021 | split-half (BT-02), m:r = 25:0.742, 50:0.837, 100:0.903, 200:0.941, 400:0.965; variance-components cross-check k = 7.3 |
| `fit:k/PLY-07/opportunity_share` | PLY-07 | 30.0 | 11.4 | **-62%** | 7869 | 2016-2021 | split-half (BT-02), m:r = 25:0.685, 50:0.815, 100:0.898 |
| `fit:k/PLY-08/yards_per_team_dropback` | PLY-08 | 150.0 | 27.5 | **-82%** | 5228 | 2016-2021 | split-half (BT-02), m:r = 25:0.481, 50:0.644, 100:0.781, 200:0.881; variance-components cross-check k = 26.2 |
| `fit:k/PLY-09/yacoe` | PLY-09 | 60.0 | 61.1 | +2% | 364 | 2016-2021 | split-half (BT-02), m:r = 25:0.290 |
| `fit:k/PLY-10/croe` | PLY-10 | 80.0 | 228.9 | **+186%** | 733 | 2016-2021 | split-half (BT-02), m:r = 25:0.098 |
| `fit:k/PLY-16/share` | PLY-16 | 40.0 | 18.5 | **-54%** | 3660 | 2016-2021 | split-half (BT-02), m:r = 25:0.595, 50:0.710, 100:0.806 |
| `fit:k/PLY-18/adot` | PLY-18 | 80.0 | 192.3 | **+140%** | 275 | 2016-2021 | split-half (BT-02), m:r = 25:0.124, 50:0.224, 100:0.343, 200:0.431 |
| `fit:k/PLY-18/epa` | PLY-18 | 80.0 | 46.8 | -41% | 681 | 2016-2021 | split-half (BT-02), m:r = 25:0.369, 50:0.382 |
| `fit:k/PLY-18/epa_overall` | PLY-18 | — | 369.9 |  | 275 | 2016-2021 | split-half (BT-02), m:r = 50:0.139, 100:0.208, 200:0.302 |
| `fit:k/PLY-18/share` | PLY-18 | 80.0 | 4.3576 | **-95%** | 1375 | 2016-2021 | split-half (BT-02), m:r = 25:0.854, 50:0.920, 100:0.957, 200:0.978 |
| `fit:k/PLY-20/cpoe` | PLY-20 | 200.0 | 334.4 | **+67%** | 275 | 2016-2021 | split-half (BT-02), m:r = 50:0.151, 100:0.224, 200:0.250 |
| `fit:k/PLY-21/sack_rate` | PLY-21 | 150.0 | 241.2 | **+61%** | 280 | 2016-2021 | split-half (BT-02), m:r = 50:0.197, 100:0.282, 200:0.420 |
| `fit:k/PLY-21/time_to_throw` | PLY-21 | 150.0 | 76.0 | -49% | 271 | 2016-2021 | split-half (BT-02), m:r = 25:0.341, 50:0.476, 100:0.597, 200:0.744 |
| `fit:k/PLY-22/scramble_rate` | PLY-22 | — | 62.9 |  | 280 | 2016-2021 | split-half (BT-02), m:r = 25:0.300, 50:0.461, 100:0.607, 200:0.728 |
| `fit:k/PLY-23/epa` | PLY-23 | 100.0 | 179.0 | **+79%** | 640 | 2016-2021 | split-half (BT-02), m:r = 25:0.126, 50:0.215 |
| `fit:k/PLY-23/epa_overall` | PLY-23 | — | 403.0 |  | 275 | 2016-2021 | split-half (BT-02), m:r = 100:0.214, 200:0.284 |
| `fit:k/PLY-23/share` | PLY-23 | 100.0 | 6.8242 | **-93%** | 1100 | 2016-2021 | split-half (BT-02), m:r = 25:0.794, 50:0.882, 100:0.933, 200:0.962 |
| `fit:k/PLY-25/success` | PLY-25 | 60.0 | 165.8 | **+176%** | 442 | 2016-2021 | split-half (BT-02), m:r = 25:0.133, 50:0.227 |
| `fit:k/PLY-25/success_overall` | PLY-25 | — | 150.2 |  | 421 | 2016-2021 | split-half (BT-02), m:r = 25:0.159, 50:0.192 |
| `fit:k/PLY-25/ypc` | PLY-25 | 60.0 | 155.0 | **+158%** | 440 | 2016-2021 | split-half (BT-02), m:r = 25:0.148, 50:0.212 |
| `fit:k/PLY-25/ypc_overall` | PLY-25 | — | 214.4 |  | 421 | 2016-2021 | split-half (BT-02), m:r = 25:0.116, 50:0.158 |
| `fit:k/PLY-26/explosive` | PLY-26 | 150.0 | 259.9 | **+73%** | 420 | 2016-2021 | split-half (BT-02), m:r = 50:0.161 |
| `fit:k/PLY-26/stuff` | PLY-26 | 100.0 | 185.7 | **+86%** | 421 | 2016-2021 | split-half (BT-02), m:r = 25:0.122, 50:0.208 |
| `fit:k/PLY-27/target_share` | PLY-27 | 40.0 | 10.6 | **-73%** | 5226 | 2016-2021 | split-half (BT-02), m:r = 25:0.713, 50:0.827, 100:0.899, 200:0.946; variance-components cross-check k = 9.0 |
| `fit:k/PLY-27/yacoe` | PLY-27 | 40.0 | 65.1 | **+63%** | 365 | 2016-2021 | split-half (BT-02), m:r = 25:0.277 |
| `fit:k/PLY-28/adot` | PLY-28 | 40.0 | 6.7450 | **-83%** | 732 | 2016-2021 | split-half (BT-02), m:r = 25:0.794, 50:0.782 |
| `fit:k/PLY-28/epa_overall` | PLY-28 | — | 201.6 |  | 731 | 2016-2021 | split-half (BT-02), m:r = 25:0.110 |
| `fit:k/PLY-28/share` | PLY-28 | 40.0 | 3.5746 | **-91%** | 3654 | 2016-2021 | split-half (BT-02), m:r = 25:0.877, 50:0.925 |
| `fit:k/PLY-29/epa_overall` | PLY-29 | — | 216.0 |  | 732 | 2016-2021 | split-half (BT-02), m:r = 25:0.104 |
| `fit:k/PLY-29/share` | PLY-29 | 50.0 | 6.1488 | **-88%** | 2929 | 2016-2021 | split-half (BT-02), m:r = 25:0.803, 50:0.888 |
| `fit:k/PLY-31/cushion` | PLY-31 | 80.0 | 55.5 | -31% | 481 | 2016-2021 | split-half (BT-02), m:r = 25:0.346, 50:0.486 |
| `fit:k/PLY-31/separation` | PLY-31 | 80.0 | 39.3 | **-51%** | 480 | 2016-2021 | split-half (BT-02), m:r = 25:0.429, 50:0.568 |
| `fit:k/PLY-32/end_zone_share` | PLY-32 | 15.0 | 5.5862 | **-63%** | 335 | 2016-2021 | split-half (BT-02), m:r = 25:0.817 |
| `conventions.g3_usage_half_life_games` | G3 | 3.0000 | 8.0000 | **+167%** | 16 | 2016-2021 | next-game n-weighted squared error / prior-only, mean over 16 usage stats (ruling 2026-10-08) |
| `conventions.g3_efficiency_half_life_games` | G3 | 6.0000 | 12.0 | **+100%** | 66 | 2016-2021 | next-game n-weighted squared error / prior-only, mean over 66 efficiency stats (ruling 2026-10-08) |
| `fit:G6/penalty` | G6 | — | 316.2 |  | 169195 | 2016-2021 | forward-chaining CV within each season (BT-02), efficiency h = 12 |
| `fit:COA-02/p_go/intercept` | COA-02 | — | 1.4559 |  | 20042 | 2016-2021 | logistic, four fields as linear terms (se 0.0715) |
| `fit:COA-02/p_go/ydstogo` | COA-02 | — | -0.3483 |  | 20042 | 2016-2021 | logistic, four fields as linear terms (se 0.00904) |
| `fit:COA-02/p_go/yardline_100` | COA-02 | — | -0.0225 |  | 20042 | 2016-2021 | logistic, four fields as linear terms (se 0.001) |
| `fit:COA-02/p_go/score_differential` | COA-02 | — | -0.0537 |  | 20042 | 2016-2021 | logistic, four fields as linear terms (se 0.00286) |
| `fit:COA-02/p_go/game_seconds_remaining` | COA-02 | — | -0.00042 |  | 20042 | 2016-2021 | logistic, four fields as linear terms (se 2.53e-05) |
| `matchup.mtc_03_ol_absence_factor` | MTC-03 | 1.1000 | 1.0579 | -4% | 6234 | 2016-2021 | offset logistic on dropbacks, exp(coef) per missing OFF-17 starter (se of log 0.0167); undamped |
| `fit:PLY-14/practice/DNP` | PLY-14 | — | 0.1883 |  | 8968 | 2016-2021 | P(played | DNP) |
| `fit:PLY-14/practice/Limited` | PLY-14 | — | 0.6994 |  | 7769 | 2016-2021 | P(played | Limited) |
| `fit:PLY-14/practice/Full` | PLY-14 | — | 0.9387 |  | 14410 | 2016-2021 | P(played | Full) |
| `fit:PRJ-06/missed/QB` | PRJ-06 | — | 0.1695 |  | 3616 | 2016-2021 | P(no snap | played last game), QB |
| `fit:PRJ-06/missed/RB` | PRJ-06 | — | 0.1297 |  | 9496 | 2016-2021 | P(no snap | played last game), RB |
| `fit:PRJ-06/missed/WR` | PRJ-06 | — | 0.1128 |  | 14118 | 2016-2021 | P(no snap | played last game), WR |
| `fit:PRJ-06/missed/TE` | PRJ-06 | — | 0.0910 |  | 8474 | 2016-2021 | P(no snap | played last game), TE |
| `player.ply_14_return_factor` | PLY-14 | 0.8500 | 0.9363 | +10% | 736 | 2016-2021 | sum first-game-back snap share / sum baseline (usage h = 8) |
| `fit:role/PLY-01/snap_share/all/QB1` | PLY-01 | — | 0.8785 |  | 336 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/RB1` | PLY-01 | — | 0.5216 |  | 418 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/RB2` | PLY-01 | — | 0.2988 |  | 575 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/TE1` | PLY-01 | — | 0.6425 |  | 378 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR1` | PLY-01 | — | 0.7493 |  | 431 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR2` | PLY-01 | — | 0.6671 |  | 611 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR3` | PLY-01 | — | 0.5175 |  | 727 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/QB1` | PLY-02 | — | 0.8785 |  | 336 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/RB1` | PLY-02 | — | 0.5216 |  | 418 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/RB2` | PLY-02 | — | 0.2988 |  | 575 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/TE1` | PLY-02 | — | 0.6425 |  | 378 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR1` | PLY-02 | — | 0.7493 |  | 431 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR2` | PLY-02 | — | 0.6671 |  | 611 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR3` | PLY-02 | — | 0.5175 |  | 727 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/QB1` | PLY-03 | — | 0.000632 |  | 336 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/RB1` | PLY-03 | — | 0.1048 |  | 418 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/RB2` | PLY-03 | — | 0.0650 |  | 575 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/TE1` | PLY-03 | — | 0.1323 |  | 378 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR1` | PLY-03 | — | 0.2173 |  | 431 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR2` | PLY-03 | — | 0.1693 |  | 611 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR3` | PLY-03 | — | 0.1188 |  | 727 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/QB1` | PLY-04 | — | 0.000173 |  | 336 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/RB1` | PLY-04 | — | 0.00698 |  | 418 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/RB2` | PLY-04 | — | 0.0055 |  | 575 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/TE1` | PLY-04 | — | 0.1255 |  | 378 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR1` | PLY-04 | — | 0.2991 |  | 431 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR2` | PLY-04 | — | 0.2244 |  | 611 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR3` | PLY-04 | — | 0.1513 |  | 727 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/QB1` | PLY-04 | — | 0.00107 |  | 336 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/RB1` | PLY-04 | — | 0.1621 |  | 418 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/RB2` | PLY-04 | — | 0.1014 |  | 575 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/TE1` | PLY-04 | — | 0.2863 |  | 378 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR1` | PLY-04 | — | 0.5354 |  | 431 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR2` | PLY-04 | — | 0.4111 |  | 611 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR3` | PLY-04 | — | 0.2841 |  | 727 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/QB1` | PLY-05 | — | 0.0489 |  | 336 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/RB1` | PLY-05 | — | 0.5403 |  | 418 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/RB2` | PLY-05 | — | 0.2676 |  | 575 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/TE1` | PLY-05 | — | 0.00074 |  | 378 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR1` | PLY-05 | — | 0.00691 |  | 431 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR2` | PLY-05 | — | 0.00742 |  | 611 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR3` | PLY-05 | — | 0.00736 |  | 727 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/QB1` | PLY-06 | — | 0.0214 |  | 336 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/RB1` | PLY-06 | — | 0.2840 |  | 418 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/RB2` | PLY-06 | — | 0.1505 |  | 575 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/TE1` | PLY-06 | — | 0.0775 |  | 378 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR1` | PLY-06 | — | 0.1294 |  | 431 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR2` | PLY-06 | — | 0.1017 |  | 611 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR3` | PLY-06 | — | 0.0728 |  | 727 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-08/yards_per_team_dropback/all/QB1` | PLY-08 | — | 0.0013 |  | 336 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/RB1` | PLY-08 | — | 0.5592 |  | 418 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/RB2` | PLY-08 | — | 0.3245 |  | 575 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/TE1` | PLY-08 | — | 0.8810 |  | 378 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR1` | PLY-08 | — | 1.5946 |  | 431 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR2` | PLY-08 | — | 1.1960 |  | 611 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR3` | PLY-08 | — | 0.8190 |  | 727 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/QB1` | PLY-18 | — | 8.1143 |  | 332 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/WR1` | PLY-18 | — | 13.9 |  | 42 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/QB1` | PLY-18 | — | 0.1681 |  | 332 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/WR1` | PLY-18 | — | 0.5608 |  | 42 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/share/behind/QB1` | PLY-18 | — | 0.1493 |  | 332 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/behind/WR1` | PLY-18 | — | 0.0961 |  | 42 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/QB1` | PLY-18 | — | 0.1200 |  | 332 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/WR1` | PLY-18 | — | 0.2745 |  | 42 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/QB1` | PLY-18 | — | 0.2157 |  | 332 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/WR1` | PLY-18 | — | 0.4059 |  | 42 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/QB1` | PLY-18 | — | 0.5149 |  | 332 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/WR1` | PLY-18 | — | 0.2235 |  | 42 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/QB1` | PLY-18 | — | 0.00015 |  | 332 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/WR1` | PLY-18 | — | 0 |  | 42 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/epa_overall/all/QB1` | PLY-23 | — | 0.1681 |  | 332 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/epa_overall/all/WR1` | PLY-23 | — | 0.5608 |  | 42 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/share/left/QB1` | PLY-23 | — | 0.3707 |  | 332 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/left/WR1` | PLY-23 | — | 0.2176 |  | 42 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/QB1` | PLY-23 | — | 0.2276 |  | 332 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/WR1` | PLY-23 | — | 0.0588 |  | 42 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/QB1` | PLY-23 | — | 0.4014 |  | 332 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/WR1` | PLY-23 | — | 0.7235 |  | 42 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/QB1` | PLY-23 | — | 0.000335 |  | 332 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/WR1` | PLY-23 | — | 0 |  | 42 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-25/success_overall/all/QB1` | PLY-25 | — | 0.5296 |  | 281 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/RB1` | PLY-25 | — | 0.3878 |  | 409 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/RB2` | PLY-25 | — | 0.3875 |  | 550 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/TE1` | PLY-25 | — | 0.5636 |  | 30 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR1` | PLY-25 | — | 0.5122 |  | 161 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR2` | PLY-25 | — | 0.5486 |  | 179 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR3` | PLY-25 | — | 0.5299 |  | 176 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/QB1` | PLY-25 | — | 3.9727 |  | 281 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/RB1` | PLY-25 | — | 4.2821 |  | 409 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/RB2` | PLY-25 | — | 4.2345 |  | 550 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/TE1` | PLY-25 | — | 3.8909 |  | 30 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR1` | PLY-25 | — | 6.3408 |  | 161 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR2` | PLY-25 | — | 6.1771 |  | 179 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR3` | PLY-25 | — | 6.1959 |  | 176 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-27/target_share/all/QB1` | PLY-27 | — | 0.000632 |  | 336 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/RB1` | PLY-27 | — | 0.1048 |  | 418 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/RB2` | PLY-27 | — | 0.0650 |  | 575 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/TE1` | PLY-27 | — | 0.1323 |  | 378 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR1` | PLY-27 | — | 0.2173 |  | 431 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR2` | PLY-27 | — | 0.1693 |  | 611 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR3` | PLY-27 | — | 0.1188 |  | 727 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/QB1` | PLY-27 | — | -2.7773 |  | 31 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/RB1` | PLY-27 | — | 0.4870 |  | 385 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/RB2` | PLY-27 | — | 0.4126 |  | 489 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/TE1` | PLY-27 | — | 0.1583 |  | 341 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR1` | PLY-27 | — | -0.4276 |  | 413 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR2` | PLY-27 | — | -0.4168 |  | 580 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR3` | PLY-27 | — | -0.4914 |  | 653 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/adot/all/QB1` | PLY-28 | — | 2.6863 |  | 45 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/RB1` | PLY-28 | — | 0.6537 |  | 394 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/RB2` | PLY-28 | — | 0.8357 |  | 510 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/TE1` | PLY-28 | — | 7.5838 |  | 352 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR1` | PLY-28 | — | 11.1 |  | 423 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR2` | PLY-28 | — | 10.9 |  | 596 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR3` | PLY-28 | — | 10.4 |  | 683 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/QB1` | PLY-28 | — | -0.2299 |  | 45 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/RB1` | PLY-28 | — | 0.0475 |  | 394 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/RB2` | PLY-28 | — | 0.00672 |  | 510 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/TE1` | PLY-28 | — | 0.2137 |  | 352 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR1` | PLY-28 | — | 0.2836 |  | 423 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR2` | PLY-28 | — | 0.2474 |  | 596 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR3` | PLY-28 | — | 0.2127 |  | 683 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/share/behind/QB1` | PLY-28 | — | 0.3333 |  | 45 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/RB1` | PLY-28 | — | 0.4206 |  | 394 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/RB2` | PLY-28 | — | 0.4102 |  | 510 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/TE1` | PLY-28 | — | 0.0915 |  | 352 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR1` | PLY-28 | — | 0.0752 |  | 423 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR2` | PLY-28 | — | 0.0784 |  | 596 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR3` | PLY-28 | — | 0.0941 |  | 683 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/QB1` | PLY-28 | — | 0.0196 |  | 45 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/RB1` | PLY-28 | — | 0.0151 |  | 394 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/RB2` | PLY-28 | — | 0.0173 |  | 510 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/TE1` | PLY-28 | — | 0.0799 |  | 352 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR1` | PLY-28 | — | 0.1734 |  | 423 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR2` | PLY-28 | — | 0.1710 |  | 596 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR3` | PLY-28 | — | 0.1637 |  | 683 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/QB1` | PLY-28 | — | 0.2157 |  | 45 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/RB1` | PLY-28 | — | 0.0279 |  | 394 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/RB2` | PLY-28 | — | 0.0280 |  | 510 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/TE1` | PLY-28 | — | 0.2247 |  | 352 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR1` | PLY-28 | — | 0.2993 |  | 423 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR2` | PLY-28 | — | 0.2684 |  | 596 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR3` | PLY-28 | — | 0.2489 |  | 683 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/QB1` | PLY-28 | — | 0.4314 |  | 45 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/RB1` | PLY-28 | — | 0.5359 |  | 394 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/RB2` | PLY-28 | — | 0.5445 |  | 510 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/TE1` | PLY-28 | — | 0.6038 |  | 352 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR1` | PLY-28 | — | 0.4522 |  | 423 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR2` | PLY-28 | — | 0.4822 |  | 596 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR3` | PLY-28 | — | 0.4932 |  | 683 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/QB1` | PLY-28 | — | 0 |  | 45 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/RB1` | PLY-28 | — | 0.000451 |  | 394 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/RB2` | PLY-28 | — | 0 |  | 510 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/TE1` | PLY-28 | — | 0 |  | 352 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR1` | PLY-28 | — | 3.21e-05 |  | 423 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR2` | PLY-28 | — | 0 |  | 596 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR3` | PLY-28 | — | 0.000181 |  | 683 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/epa_overall/all/QB1` | PLY-29 | — | -0.2299 |  | 45 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/RB1` | PLY-29 | — | 0.0475 |  | 394 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/RB2` | PLY-29 | — | 0.00672 |  | 510 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/TE1` | PLY-29 | — | 0.2137 |  | 352 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR1` | PLY-29 | — | 0.2836 |  | 423 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR2` | PLY-29 | — | 0.2474 |  | 596 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR3` | PLY-29 | — | 0.2127 |  | 683 | 2016-2021 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/share/left/QB1` | PLY-29 | — | 0.3137 |  | 45 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/RB1` | PLY-29 | — | 0.3988 |  | 394 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/RB2` | PLY-29 | — | 0.4076 |  | 510 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/TE1` | PLY-29 | — | 0.3157 |  | 352 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR1` | PLY-29 | — | 0.3883 |  | 423 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR2` | PLY-29 | — | 0.3731 |  | 596 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR3` | PLY-29 | — | 0.3750 |  | 683 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/QB1` | PLY-29 | — | 0.2745 |  | 45 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/RB1` | PLY-29 | — | 0.1982 |  | 394 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/RB2` | PLY-29 | — | 0.1943 |  | 510 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/TE1` | PLY-29 | — | 0.2789 |  | 352 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR1` | PLY-29 | — | 0.2291 |  | 423 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR2` | PLY-29 | — | 0.2363 |  | 596 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR3` | PLY-29 | — | 0.2289 |  | 683 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/QB1` | PLY-29 | — | 0.4118 |  | 45 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/RB1` | PLY-29 | — | 0.4025 |  | 394 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/RB2` | PLY-29 | — | 0.3981 |  | 510 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/TE1` | PLY-29 | — | 0.4051 |  | 352 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR1` | PLY-29 | — | 0.3825 |  | 423 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR2` | PLY-29 | — | 0.3905 |  | 596 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR3` | PLY-29 | — | 0.3959 |  | 683 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/QB1` | PLY-29 | — | 0 |  | 45 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/RB1` | PLY-29 | — | 0.000451 |  | 394 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/RB2` | PLY-29 | — | 0 |  | 510 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/TE1` | PLY-29 | — | 0.000182 |  | 352 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR1` | PLY-29 | — | 7.8e-05 |  | 423 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR2` | PLY-29 | — | 4.13e-05 |  | 596 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR3` | PLY-29 | — | 0.000232 |  | 683 | 2016-2021 | section 4 slot prior: mean over slot occupants' games of his game share |

## S2023 (seasons 2016-2022)

| key | spec | initial | fitted | change | n | seasons | method |
|---|---|---|---|---|---|---|---|
| `fit:k/COA-04/proe` | COA-04 | 80.0 | 82.5 | +3% | 430 | 2016-2022 | split-half (BT-02), m:r = 25:0.226, 50:0.365, 100:0.593; variance-components cross-check k = 66.9 |
| `fit:k/COA-04/seconds_per_play` | COA-04 | 80.0 | 20.2 | **-75%** | 326 | 2016-2022 | split-half (BT-02), m:r = 25:0.560, 50:0.666; variance-components cross-check k = 11.8 |
| `fit:k/DEF-01/epa/all` | DEF-01 | 250.0 | 906.9 | **+263%** | 224 | 2016-2022 | split-half (BT-02), m:r = 200:0.185, 400:0.300; variance-components cross-check k = 679.6 |
| `fit:k/DEF-01/epa/pass` | DEF-01 | 200.0 | 789.1 | **+295%** | 224 | 2016-2022 | split-half (BT-02), m:r = 200:0.202; variance-components cross-check k = 538.5 |
| `fit:k/DEF-01/epa/run` | DEF-01 | 300.0 | 578.6 | **+93%** | 224 | 2016-2022 | split-half (BT-02), m:r = 100:0.147; variance-components cross-check k = 474.8 |
| `fit:k/DEF-02/success` | DEF-02 | 150.0 | 273.7 | **+82%** | 672 | 2016-2022 | split-half (BT-02), m:r = 25:0.092, 50:0.173, 100:0.286, 200:0.290, 400:0.364; variance-components cross-check k = 255.4 |
| `fit:k/DEF-03/explosive` | DEF-03 | 150.0 | 105.4 | -30% | 617 | 2016-2022 | split-half (BT-02), m:r = 25:0.192 |
| `fit:k/DEF-03/explosive_team` | DEF-03 | — | 534.9 |  | 224 | 2016-2022 | split-half (BT-02), m:r = 100:0.158; variance-components cross-check k = 445.5 |
| `fit:k/DEF-03/share` | DEF-03 | — | 24.7 |  | 1792 | 2016-2022 | split-half (BT-02), m:r = 25:0.537, 50:0.673, 100:0.773, 200:0.851; variance-components cross-check k = 17.6 |
| `fit:k/DEF-03/success` | DEF-03 | 60.0 | 153.5 | **+156%** | 614 | 2016-2022 | split-half (BT-02), m:r = 25:0.140 |
| `fit:k/DEF-03/ypc` | DEF-03 | 100.0 | 138.1 | +38% | 615 | 2016-2022 | split-half (BT-02), m:r = 25:0.153 |
| `fit:k/DEF-03/ypc_team` | DEF-03 | — | 482.8 |  | 224 | 2016-2022 | split-half (BT-02), m:r = 100:0.172; variance-components cross-check k = 409.1 |
| `fit:k/DEF-04/epa_diff` | DEF-04 | 60.0 | 607.4 | **+912%** | 672 | 2016-2022 | split-half (BT-02), m:r = 100:0.152 |
| `fit:k/DEF-04/receptions` | DEF-04 | 60.0 | 326.7 | **+445%** | 672 | 2016-2022 | split-half (BT-02), m:r = 25:0.098, 50:0.148, 100:0.173 |
| `fit:k/DEF-04/targets` | DEF-04 | 60.0 | 385.7 | **+543%** | 672 | 2016-2022 | split-half (BT-02), m:r = 25:0.085, 50:0.128, 100:0.172 |
| `fit:k/DEF-04/yards` | DEF-04 | 60.0 | 332.4 | **+454%** | 672 | 2016-2022 | split-half (BT-02), m:r = 25:0.097, 50:0.146, 100:0.190 |
| `fit:k/DEF-05/blitz_rate` | DEF-05 | 150.0 | 82.3 | -45% | 32 | 2022 | split-half (BT-02), m:r = 50:0.413, 100:0.561, 200:0.665; variance-components cross-check k = 50.5 |
| `fit:k/DEF-05/hit_rate` | DEF-05 | 150.0 | 957.2 | **+538%** | 224 | 2016-2022 | split-half (BT-02), m:r = 200:0.173; variance-components cross-check k = 518.9 |
| `fit:k/DEF-06/explosive` | DEF-06 | 300.0 | 1,159 | **+286%** | 224 | 2016-2022 | split-half (BT-02), m:r = 200:0.155, 400:0.240; variance-components cross-check k = 957.9 |
| `fit:k/DEF-06/explosive_run` | DEF-06 | 300.0 | 491.5 | **+64%** | 224 | 2016-2022 | split-half (BT-02), m:r = 100:0.169; variance-components cross-check k = 445.5 |
| `fit:k/DEF-09/cpoe_team` | DEF-09 | — | 829.5 |  | 224 | 2016-2022 | split-half (BT-02), m:r = 200:0.194; variance-components cross-check k = 659.5 |
| `fit:k/DEF-09/epa` | DEF-09 | 60.0 | 215.0 | **+258%** | 718 | 2016-2022 | split-half (BT-02), m:r = 25:0.104 |
| `fit:k/DEF-12/stacked_box_share` | DEF-12 | — | 200.4 |  | 32 | 2022 | split-half (BT-02), m:r = 100:0.352, 200:0.482; variance-components cross-check k = 83.2 |
| `fit:k/DEF-15/success` | DEF-15 | 60.0 | 305.3 | **+409%** | 448 | 2016-2022 | split-half (BT-02), m:r = 50:0.136, 100:0.258; variance-components cross-check k = 239.6 |
| `fit:k/DEF-15/ypc` | DEF-15 | 60.0 | 280.9 | **+368%** | 448 | 2016-2022 | split-half (BT-02), m:r = 50:0.151; variance-components cross-check k = 246.4 |
| `fit:k/DEF-17/passes_defensed` | DEF-17 | 20.0 | 20.4 | +2% | 3231 | 2016-2022 | split-half (BT-02), m:r = 25:0.573, 50:0.712 |
| `fit:k/DEF-17/qb_hits` | DEF-17 | 20.0 | 11.8 | -41% | 3981 | 2016-2022 | split-half (BT-02), m:r = 25:0.703, 50:0.829 |
| `fit:k/DEF-17/sacks` | DEF-17 | 20.0 | 8.7235 | **-56%** | 324 | 2017-2022 | split-half (BT-02), m:r = 25:0.751 |
| `fit:k/DEF-17/tackles_for_loss` | DEF-17 | 20.0 | 27.9 | +39% | 3387 | 2016-2022 | split-half (BT-02), m:r = 25:0.495 |
| `fit:k/OFF-01/epa/all` | OFF-01 | 250.0 | 346.9 | +39% | 224 | 2016-2022 | split-half (BT-02), m:r = 50:0.145, 100:0.232, 200:0.369, 400:0.493; variance-components cross-check k = 312.1 |
| `fit:k/OFF-01/epa/pass` | OFF-01 | 200.0 | 286.8 | +43% | 224 | 2016-2022 | split-half (BT-02), m:r = 50:0.136, 100:0.261, 200:0.413; variance-components cross-check k = 256.2 |
| `fit:k/OFF-01/epa/run` | OFF-01 | 300.0 | 312.1 | +4% | 224 | 2016-2022 | split-half (BT-02), m:r = 50:0.141, 100:0.241; variance-components cross-check k = 286.6 |
| `fit:k/OFF-02/success` | OFF-02 | 150.0 | 181.2 | +21% | 672 | 2016-2022 | split-half (BT-02), m:r = 25:0.136, 50:0.240, 100:0.372, 200:0.463, 400:0.539; variance-components cross-check k = 166.6 |
| `fit:k/OFF-03/epa` | OFF-03 | 100.0 | 291.2 | **+191%** | 782 | 2016-2022 | split-half (BT-02), m:r = 25:0.080, 50:0.158, 100:0.228; variance-components cross-check k = 149.8 |
| `fit:k/OFF-03/success` | OFF-03 | 100.0 | 213.9 | **+114%** | 783 | 2016-2022 | split-half (BT-02), m:r = 25:0.112, 50:0.185, 100:0.316; variance-components cross-check k = 160.1 |
| `fit:k/OFF-04/pass_rate` | OFF-04 | 60.0 | 104.9 | **+75%** | 224 | 2016-2022 | split-half (BT-02), m:r = 25:0.177, 50:0.320, 100:0.487, 200:0.668; variance-components cross-check k = 99.5 |
| `fit:k/OFF-05/proe` | OFF-05 | 100.0 | 108.1 | +8% | 224 | 2016-2022 | split-half (BT-02), m:r = 25:0.198, 50:0.327, 100:0.481, 200:0.637; variance-components cross-check k = 96.1 |
| `fit:k/OFF-06/play_action_rate` | OFF-06 | 80.0 | 63.9 | -20% | 32 | 2022 | split-half (BT-02), m:r = 50:0.465, 100:0.584; variance-components cross-check k = 50.6 |
| `fit:k/OFF-07/motion_rate` | OFF-07 | 80.0 | 32.2 | **-60%** | 32 | 2022 | split-half (BT-02), m:r = 25:0.501, 50:0.624, 100:0.743, 200:0.817; variance-components cross-check k = 21.8 |
| `fit:k/OFF-08/rpo_rate` | OFF-08 | 80.0 | 133.4 | **+67%** | 32 | 2022 | split-half (BT-02), m:r = 100:0.459, 200:0.566; variance-components cross-check k = 64.6 |
| `fit:k/OFF-09/shotgun_rate` | OFF-09 | 60.0 | 19.1 | **-68%** | 224 | 2016-2022 | split-half (BT-02), m:r = 25:0.620, 50:0.744, 100:0.835, 200:0.890, 400:0.931; variance-components cross-check k = 13.2 |
| `fit:k/OFF-10/seconds_per_play` | OFF-10 | 80.0 | 38.2 | **-52%** | 224 | 2016-2022 | split-half (BT-02), m:r = 25:0.436, 50:0.550, 100:0.701; variance-components cross-check k = 29.0 |
| `fit:k/OFF-12/epa` | OFF-12 | 100.0 | 186.9 | **+87%** | 616 | 2016-2022 | split-half (BT-02), m:r = 25:0.118 |
| `fit:k/OFF-12/explosive` | OFF-12 | 150.0 | 74.7 | **-50%** | 617 | 2016-2022 | split-half (BT-02), m:r = 25:0.251 |
| `fit:k/OFF-12/explosive_team` | OFF-12 | — | 436.6 |  | 224 | 2016-2022 | split-half (BT-02), m:r = 100:0.186; variance-components cross-check k = 377.8 |
| `fit:k/OFF-12/share` | OFF-12 | — | 22.3 |  | 1792 | 2016-2022 | split-half (BT-02), m:r = 25:0.562, 50:0.696, 100:0.791, 200:0.851; variance-components cross-check k = 16.6 |
| `fit:k/OFF-12/success` | OFF-12 | 60.0 | 126.5 | **+111%** | 616 | 2016-2022 | split-half (BT-02), m:r = 25:0.138, 50:0.325 |
| `fit:k/OFF-12/ypc` | OFF-12 | 100.0 | 109.8 | +10% | 616 | 2016-2022 | split-half (BT-02), m:r = 25:0.186 |
| `fit:k/OFF-12/ypc_team` | OFF-12 | — | 349.4 |  | 224 | 2016-2022 | split-half (BT-02), m:r = 100:0.223; variance-components cross-check k = 313.8 |
| `fit:k/OFF-13/cpoe_team` | OFF-13 | — | 403.4 |  | 224 | 2016-2022 | split-half (BT-02), m:r = 100:0.215, 200:0.296; variance-components cross-check k = 350.0 |
| `fit:k/OFF-13/epa` | OFF-13 | 60.0 | 142.2 | **+137%** | 756 | 2016-2022 | split-half (BT-02), m:r = 25:0.150 |
| `fit:k/OFF-13/share` | OFF-13 | 60.0 | 19.5 | **-67%** | 2912 | 2016-2022 | split-half (BT-02), m:r = 25:0.567, 50:0.722, 100:0.836, 200:0.908; variance-components cross-check k = 18.5 |
| `fit:k/OFF-14/pass_share` | OFF-14 | 25.0 | 70.8 | **+183%** | 438 | 2016-2022 | split-half (BT-02), m:r = 25:0.255, 50:0.423; variance-components cross-check k = 53.9 |
| `fit:k/OFF-15/hit_rate` | OFF-15 | 200.0 | 168.7 | -16% | 224 | 2016-2022 | split-half (BT-02), m:r = 25:0.134, 50:0.229, 100:0.377, 200:0.535; variance-components cross-check k = 157.7 |
| `fit:k/OFF-15/sack_rate` | OFF-15 | 200.0 | 303.8 | **+52%** | 224 | 2016-2022 | split-half (BT-02), m:r = 50:0.147, 100:0.249, 200:0.393; variance-components cross-check k = 266.7 |
| `fit:k/OFF-16/stuff` | OFF-16 | 80.0 | 228.7 | **+186%** | 448 | 2016-2022 | split-half (BT-02), m:r = 25:0.096, 50:0.182; variance-components cross-check k = 195.3 |
| `fit:k/OFF-16/stuff_team` | OFF-16 | — | 233.6 |  | 224 | 2016-2022 | split-half (BT-02), m:r = 50:0.179, 100:0.297; variance-components cross-check k = 196.9 |
| `fit:k/OFF-16/success` | OFF-16 | 80.0 | 232.1 | **+190%** | 448 | 2016-2022 | split-half (BT-02), m:r = 25:0.102, 50:0.170; variance-components cross-check k = 193.4 |
| `fit:k/PLY-03/target_share` | PLY-03 | 60.0 | 10.5 | **-83%** | 6123 | 2016-2022 | split-half (BT-02), m:r = 25:0.715, 50:0.828, 100:0.900, 200:0.947; variance-components cross-check k = 8.9 |
| `fit:k/PLY-04/air_share` | PLY-04 | 60.0 | 13.6 | **-77%** | 6123 | 2016-2022 | split-half (BT-02), m:r = 25:0.647, 50:0.786, 100:0.879, 200:0.937 |
| `fit:k/PLY-04/wopr` | PLY-04 | 60.0 | 10.0 | **-83%** | 6123 | 2016-2022 | split-half (BT-02), m:r = 25:0.724, 50:0.834, 100:0.906, 200:0.950 |
| `fit:k/PLY-05/carry_share` | PLY-05 | 40.0 | 2.6841 | **-93%** | 5827 | 2016-2022 | split-half (BT-02), m:r = 25:0.913, 50:0.947, 100:0.969, 200:0.983; variance-components cross-check k = 1.5 |
| `fit:k/PLY-06/opportunity_share` | PLY-06 | 20.0 | 7.6616 | **-62%** | 7701 | 2016-2022 | split-half (BT-02), m:r = 25:0.770, 50:0.859, 100:0.913 |
| `fit:k/PLY-06/opportunity_share_overall` | PLY-06 | — | 10.1 |  | 6249 | 2016-2022 | split-half (BT-02), m:r = 25:0.742, 50:0.838, 100:0.903, 200:0.942, 400:0.966; variance-components cross-check k = 7.3 |
| `fit:k/PLY-07/opportunity_share` | PLY-07 | 30.0 | 11.4 | **-62%** | 9238 | 2016-2022 | split-half (BT-02), m:r = 25:0.685, 50:0.815, 100:0.896 |
| `fit:k/PLY-08/yards_per_team_dropback` | PLY-08 | 150.0 | 27.3 | **-82%** | 6135 | 2016-2022 | split-half (BT-02), m:r = 25:0.481, 50:0.645, 100:0.783, 200:0.882; variance-components cross-check k = 26.0 |
| `fit:k/PLY-09/yacoe` | PLY-09 | 60.0 | 60.9 | +1% | 432 | 2016-2022 | split-half (BT-02), m:r = 25:0.291 |
| `fit:k/PLY-10/croe` | PLY-10 | 80.0 | 250.3 | **+213%** | 853 | 2016-2022 | split-half (BT-02), m:r = 25:0.091 |
| `fit:k/PLY-16/share` | PLY-16 | 40.0 | 18.9 | **-53%** | 4276 | 2016-2022 | split-half (BT-02), m:r = 25:0.590, 50:0.709, 100:0.804 |
| `fit:k/PLY-18/adot` | PLY-18 | 80.0 | 186.4 | **+133%** | 329 | 2016-2022 | split-half (BT-02), m:r = 25:0.119, 50:0.225, 100:0.357, 200:0.466 |
| `fit:k/PLY-18/epa` | PLY-18 | 80.0 | 46.1 | -42% | 792 | 2016-2022 | split-half (BT-02), m:r = 25:0.373, 50:0.387 |
| `fit:k/PLY-18/epa_overall` | PLY-18 | — | 378.3 |  | 329 | 2016-2022 | split-half (BT-02), m:r = 50:0.137, 100:0.204, 200:0.290 |
| `fit:k/PLY-18/share` | PLY-18 | 80.0 | 4.4118 | **-94%** | 1645 | 2016-2022 | split-half (BT-02), m:r = 25:0.852, 50:0.919, 100:0.957, 200:0.978 |
| `fit:k/PLY-19/play_action_rate` | PLY-19 | — | 53.5 |  | 57 | 2022 | split-half (BT-02), m:r = 25:0.332, 50:0.487, 100:0.635 |
| `fit:k/PLY-20/cpoe` | PLY-20 | 200.0 | 358.7 | **+79%** | 328 | 2016-2022 | split-half (BT-02), m:r = 50:0.143, 100:0.211, 200:0.241 |
| `fit:k/PLY-20/throwaway_rate` | PLY-20 | 200.0 | 127.9 | -36% | 54 | 2022 | split-half (BT-02), m:r = 100:0.439 |
| `fit:k/PLY-21/sack_rate` | PLY-21 | 150.0 | 251.6 | **+68%** | 337 | 2016-2022 | split-half (BT-02), m:r = 50:0.182, 100:0.281, 200:0.425 |
| `fit:k/PLY-21/time_to_throw` | PLY-21 | 150.0 | 73.4 | **-51%** | 324 | 2016-2022 | split-half (BT-02), m:r = 25:0.353, 50:0.488, 100:0.602, 200:0.744 |
| `fit:k/PLY-22/scramble_rate` | PLY-22 | — | 61.3 |  | 337 | 2016-2022 | split-half (BT-02), m:r = 25:0.305, 50:0.465, 100:0.616, 200:0.732 |
| `fit:k/PLY-23/epa` | PLY-23 | 100.0 | 191.3 | **+91%** | 754 | 2016-2022 | split-half (BT-02), m:r = 25:0.119, 50:0.204 |
| `fit:k/PLY-23/epa_overall` | PLY-23 | — | 413.8 |  | 329 | 2016-2022 | split-half (BT-02), m:r = 100:0.209, 200:0.280 |
| `fit:k/PLY-23/share` | PLY-23 | 100.0 | 6.7670 | **-93%** | 1316 | 2016-2022 | split-half (BT-02), m:r = 25:0.796, 50:0.882, 100:0.934, 200:0.963 |
| `fit:k/PLY-25/success` | PLY-25 | 60.0 | 174.5 | **+191%** | 532 | 2016-2022 | split-half (BT-02), m:r = 25:0.128, 50:0.216 |
| `fit:k/PLY-25/success_overall` | PLY-25 | — | 142.4 |  | 495 | 2016-2022 | split-half (BT-02), m:r = 25:0.166, 50:0.192 |
| `fit:k/PLY-25/ypc` | PLY-25 | 60.0 | 156.5 | **+161%** | 531 | 2016-2022 | split-half (BT-02), m:r = 25:0.148, 50:0.177 |
| `fit:k/PLY-25/ypc_overall` | PLY-25 | — | 201.3 |  | 495 | 2016-2022 | split-half (BT-02), m:r = 25:0.124, 50:0.154 |
| `fit:k/PLY-26/explosive` | PLY-26 | 150.0 | 227.8 | **+52%** | 494 | 2016-2022 | split-half (BT-02), m:r = 25:0.108, 50:0.161 |
| `fit:k/PLY-26/stuff` | PLY-26 | 100.0 | 192.8 | **+93%** | 495 | 2016-2022 | split-half (BT-02), m:r = 25:0.121, 50:0.197 |
| `fit:k/PLY-27/screen_share` | PLY-27 | 40.0 | 6.5814 | **-84%** | 210 | 2022 | split-half (BT-02), m:r = 25:0.792 |
| `fit:k/PLY-27/target_share` | PLY-27 | 40.0 | 10.5 | **-74%** | 6123 | 2016-2022 | split-half (BT-02), m:r = 25:0.715, 50:0.828, 100:0.900, 200:0.946; variance-components cross-check k = 8.9 |
| `fit:k/PLY-27/yacoe` | PLY-27 | 40.0 | 63.7 | **+59%** | 434 | 2016-2022 | split-half (BT-02), m:r = 25:0.282 |
| `fit:k/PLY-28/adot` | PLY-28 | 40.0 | 6.6241 | **-83%** | 853 | 2016-2022 | split-half (BT-02), m:r = 25:0.797, 50:0.780 |
| `fit:k/PLY-28/epa_overall` | PLY-28 | — | 218.2 |  | 852 | 2016-2022 | split-half (BT-02), m:r = 25:0.103 |
| `fit:k/PLY-28/share` | PLY-28 | 40.0 | 3.6118 | **-91%** | 4257 | 2016-2022 | split-half (BT-02), m:r = 25:0.876, 50:0.924 |
| `fit:k/PLY-29/epa_overall` | PLY-29 | — | 227.7 |  | 853 | 2016-2022 | split-half (BT-02), m:r = 25:0.099 |
| `fit:k/PLY-29/share` | PLY-29 | 50.0 | 6.1230 | **-88%** | 3411 | 2016-2022 | split-half (BT-02), m:r = 25:0.804, 50:0.888 |
| `fit:k/PLY-31/cushion` | PLY-31 | 80.0 | 54.9 | -31% | 558 | 2016-2022 | split-half (BT-02), m:r = 25:0.343, 50:0.501 |
| `fit:k/PLY-31/separation` | PLY-31 | 80.0 | 40.8 | -49% | 557 | 2016-2022 | split-half (BT-02), m:r = 25:0.423, 50:0.545 |
| `fit:k/PLY-32/end_zone_share` | PLY-32 | 15.0 | 5.4677 | **-64%** | 363 | 2016-2022 | split-half (BT-02), m:r = 25:0.821 |
| `fit:k/PLY-33/target_share` | PLY-33 | 40.0 | 8.8767 | **-78%** | 1323 | 2022 | split-half (BT-02), m:r = 25:0.739, 50:0.845, 100:0.925 |
| `conventions.g3_usage_half_life_games` | G3 | 3.0000 | 8.0000 | **+167%** | 18 | 2016-2022 | next-game n-weighted squared error / prior-only, mean over 18 usage stats (ruling 2026-10-08) |
| `conventions.g3_efficiency_half_life_games` | G3 | 6.0000 | 8.0000 | +33% | 75 | 2016-2022 | next-game n-weighted squared error / prior-only, mean over 75 efficiency stats (ruling 2026-10-08) |
| `fit:G6/penalty` | G6 | — | 316.2 |  | 199127 | 2016-2022 | forward-chaining CV within each season (BT-02), efficiency h = 8 |
| `fit:COA-02/p_go/intercept` | COA-02 | — | 1.4981 |  | 23612 | 2016-2022 | logistic, four fields as linear terms (se 0.0657) |
| `fit:COA-02/p_go/ydstogo` | COA-02 | — | -0.3530 |  | 23612 | 2016-2022 | logistic, four fields as linear terms (se 0.00828) |
| `fit:COA-02/p_go/yardline_100` | COA-02 | — | -0.0227 |  | 23612 | 2016-2022 | logistic, four fields as linear terms (se 0.000914) |
| `fit:COA-02/p_go/score_differential` | COA-02 | — | -0.0548 |  | 23612 | 2016-2022 | logistic, four fields as linear terms (se 0.00264) |
| `fit:COA-02/p_go/game_seconds_remaining` | COA-02 | — | -0.000409 |  | 23612 | 2016-2022 | logistic, four fields as linear terms (se 2.3e-05) |
| `fit:k/COA-02/go_over_expected` | COA-02 | 30.0 | 120.6 | **+302%** | 224 | 2016-2022 | split-half (BT-02), m:r = 25:0.172 |
| `matchup.mtc_03_ol_absence_factor` | MTC-03 | 1.1000 | 1.0530 | -4% | 7369 | 2016-2022 | offset logistic on dropbacks, exp(coef) per missing OFF-17 starter (se of log 0.0155); undamped |
| `fit:PLY-14/practice/DNP` | PLY-14 | — | 0.1955 |  | 10711 | 2016-2022 | P(played | DNP) |
| `fit:PLY-14/practice/Limited` | PLY-14 | — | 0.7032 |  | 9277 | 2016-2022 | P(played | Limited) |
| `fit:PLY-14/practice/Full` | PLY-14 | — | 0.9383 |  | 16797 | 2016-2022 | P(played | Full) |
| `fit:PRJ-06/missed/QB` | PRJ-06 | — | 0.1721 |  | 4260 | 2016-2022 | P(no snap | played last game), QB |
| `fit:PRJ-06/missed/RB` | PRJ-06 | — | 0.1294 |  | 11173 | 2016-2022 | P(no snap | played last game), RB |
| `fit:PRJ-06/missed/WR` | PRJ-06 | — | 0.1135 |  | 16689 | 2016-2022 | P(no snap | played last game), WR |
| `fit:PRJ-06/missed/TE` | PRJ-06 | — | 0.0908 |  | 10096 | 2016-2022 | P(no snap | played last game), TE |
| `player.ply_14_return_factor` | PLY-14 | 0.8500 | 0.9332 | +10% | 876 | 2016-2022 | sum first-game-back snap share / sum baseline (usage h = 8) |
| `fit:role/PLY-01/snap_share/all/QB1` | PLY-01 | — | 0.8762 |  | 404 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/RB1` | PLY-01 | — | 0.5243 |  | 485 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/RB2` | PLY-01 | — | 0.2988 |  | 680 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/TE1` | PLY-01 | — | 0.6410 |  | 443 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR1` | PLY-01 | — | 0.7502 |  | 506 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR2` | PLY-01 | — | 0.6672 |  | 712 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR3` | PLY-01 | — | 0.5152 |  | 854 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/QB1` | PLY-02 | — | 0.8762 |  | 404 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/RB1` | PLY-02 | — | 0.5243 |  | 485 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/RB2` | PLY-02 | — | 0.2988 |  | 680 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/TE1` | PLY-02 | — | 0.6410 |  | 443 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR1` | PLY-02 | — | 0.7502 |  | 506 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR2` | PLY-02 | — | 0.6672 |  | 712 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR3` | PLY-02 | — | 0.5152 |  | 854 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/QB1` | PLY-03 | — | 0.000608 |  | 404 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/RB1` | PLY-03 | — | 0.1043 |  | 485 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/RB2` | PLY-03 | — | 0.0645 |  | 680 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/TE1` | PLY-03 | — | 0.1326 |  | 443 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR1` | PLY-03 | — | 0.2185 |  | 506 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR2` | PLY-03 | — | 0.1692 |  | 712 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR3` | PLY-03 | — | 0.1180 |  | 854 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/QB1` | PLY-04 | — | 0.000119 |  | 404 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/RB1` | PLY-04 | — | 0.0057 |  | 485 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/RB2` | PLY-04 | — | 0.00521 |  | 680 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/TE1` | PLY-04 | — | 0.1246 |  | 443 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR1` | PLY-04 | — | 0.3008 |  | 506 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR2` | PLY-04 | — | 0.2242 |  | 712 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR3` | PLY-04 | — | 0.1511 |  | 854 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/QB1` | PLY-04 | — | 0.000995 |  | 404 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/RB1` | PLY-04 | — | 0.1605 |  | 485 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/RB2` | PLY-04 | — | 0.1005 |  | 680 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/TE1` | PLY-04 | — | 0.2861 |  | 443 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR1` | PLY-04 | — | 0.5384 |  | 506 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR2` | PLY-04 | — | 0.4108 |  | 712 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR3` | PLY-04 | — | 0.2828 |  | 854 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/QB1` | PLY-05 | — | 0.0516 |  | 404 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/RB1` | PLY-05 | — | 0.5397 |  | 485 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/RB2` | PLY-05 | — | 0.2655 |  | 680 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/TE1` | PLY-05 | — | 0.000827 |  | 443 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR1` | PLY-05 | — | 0.00718 |  | 506 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR2` | PLY-05 | — | 0.00772 |  | 712 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR3` | PLY-05 | — | 0.00726 |  | 854 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/QB1` | PLY-06 | — | 0.0229 |  | 404 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/RB1` | PLY-06 | — | 0.2850 |  | 485 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/RB2` | PLY-06 | — | 0.1496 |  | 680 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/TE1` | PLY-06 | — | 0.0772 |  | 443 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR1` | PLY-06 | — | 0.1294 |  | 506 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR2` | PLY-06 | — | 0.1015 |  | 712 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR3` | PLY-06 | — | 0.0720 |  | 854 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-08/yards_per_team_dropback/all/QB1` | PLY-08 | — | 0.00108 |  | 404 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/RB1` | PLY-08 | — | 0.5502 |  | 485 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/RB2` | PLY-08 | — | 0.3188 |  | 680 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/TE1` | PLY-08 | — | 0.8774 |  | 443 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR1` | PLY-08 | — | 1.5951 |  | 506 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR2` | PLY-08 | — | 1.1942 |  | 712 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR3` | PLY-08 | — | 0.8054 |  | 854 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/QB1` | PLY-18 | — | 8.0590 |  | 400 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/WR1` | PLY-18 | — | 13.4 |  | 46 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/WR2` | PLY-18 | — | 15.0 |  | 30 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/QB1` | PLY-18 | — | 0.1634 |  | 400 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/WR1` | PLY-18 | — | 0.4652 |  | 46 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/WR2` | PLY-18 | — | 0.7579 |  | 30 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/share/behind/QB1` | PLY-18 | — | 0.1532 |  | 400 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/behind/WR1` | PLY-18 | — | 0.1054 |  | 46 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/behind/WR2` | PLY-18 | — | 0.2237 |  | 30 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/QB1` | PLY-18 | — | 0.1195 |  | 400 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/WR1` | PLY-18 | — | 0.2679 |  | 46 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/WR2` | PLY-18 | — | 0.3816 |  | 30 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/QB1` | PLY-18 | — | 0.2142 |  | 400 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/WR1` | PLY-18 | — | 0.3696 |  | 46 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/WR2` | PLY-18 | — | 0.2632 |  | 30 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/QB1` | PLY-18 | — | 0.5129 |  | 400 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/WR1` | PLY-18 | — | 0.2571 |  | 46 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/WR2` | PLY-18 | — | 0.1316 |  | 30 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/QB1` | PLY-18 | — | 0.000128 |  | 400 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/WR1` | PLY-18 | — | 0 |  | 46 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/WR2` | PLY-18 | — | 0 |  | 30 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/epa_overall/all/QB1` | PLY-23 | — | 0.1634 |  | 400 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/epa_overall/all/WR1` | PLY-23 | — | 0.4652 |  | 46 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/epa_overall/all/WR2` | PLY-23 | — | 0.7579 |  | 30 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/share/left/QB1` | PLY-23 | — | 0.3708 |  | 400 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/left/WR1` | PLY-23 | — | 0.2161 |  | 46 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/left/WR2` | PLY-23 | — | 0.3289 |  | 30 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/QB1` | PLY-23 | — | 0.2260 |  | 400 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/WR1` | PLY-23 | — | 0.0536 |  | 46 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/WR2` | PLY-23 | — | 0.0263 |  | 30 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/QB1` | PLY-23 | — | 0.4029 |  | 400 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/WR1` | PLY-23 | — | 0.7304 |  | 46 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/WR2` | PLY-23 | — | 0.6447 |  | 30 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/QB1` | PLY-23 | — | 0.000293 |  | 400 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/WR1` | PLY-23 | — | 0 |  | 46 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/WR2` | PLY-23 | — | 0 |  | 30 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-24/success_overall/all/QB1` | PLY-24 | — | 0.5835 |  | 62 | 2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/RB1` | PLY-24 | — | 0.4046 |  | 66 | 2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/RB2` | PLY-24 | — | 0.4185 |  | 100 | 2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/WR1` | PLY-24 | — | 0.4821 |  | 30 | 2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/WR3` | PLY-24 | — | 0.5976 |  | 37 | 2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/QB1` | PLY-24 | — | 4.1570 |  | 62 | 2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/RB1` | PLY-24 | — | 4.5139 |  | 66 | 2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/RB2` | PLY-24 | — | 4.3718 |  | 100 | 2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/WR1` | PLY-24 | — | 4.8125 |  | 30 | 2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/WR3` | PLY-24 | — | 7.9878 |  | 37 | 2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/QB1` | PLY-25 | — | 0.5407 |  | 343 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/RB1` | PLY-25 | — | 0.3904 |  | 475 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/RB2` | PLY-25 | — | 0.3923 |  | 650 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/TE1` | PLY-25 | — | 0.5972 |  | 40 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR1` | PLY-25 | — | 0.5066 |  | 191 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR2` | PLY-25 | — | 0.5250 |  | 205 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR3` | PLY-25 | — | 0.5397 |  | 213 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/QB1` | PLY-25 | — | 4.0105 |  | 343 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/RB1` | PLY-25 | — | 4.3186 |  | 475 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/RB2` | PLY-25 | — | 4.2557 |  | 650 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/TE1` | PLY-25 | — | 3.5278 |  | 40 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR1` | PLY-25 | — | 6.0565 |  | 191 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR2` | PLY-25 | — | 6.1123 |  | 205 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR3` | PLY-25 | — | 6.4550 |  | 213 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-27/screen_share/all/QB1` | PLY-27 | — | 0.000475 |  | 67 | 2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/RB1` | PLY-27 | — | 0.2375 |  | 66 | 2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/RB2` | PLY-27 | — | 0.1222 |  | 105 | 2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/TE1` | PLY-27 | — | 0.0820 |  | 62 | 2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/WR1` | PLY-27 | — | 0.1644 |  | 75 | 2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/WR2` | PLY-27 | — | 0.1210 |  | 99 | 2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/WR3` | PLY-27 | — | 0.0847 |  | 124 | 2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/QB1` | PLY-27 | — | 0.000608 |  | 404 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/RB1` | PLY-27 | — | 0.1043 |  | 485 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/RB2` | PLY-27 | — | 0.0645 |  | 680 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/TE1` | PLY-27 | — | 0.1326 |  | 443 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR1` | PLY-27 | — | 0.2185 |  | 506 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR2` | PLY-27 | — | 0.1692 |  | 712 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR3` | PLY-27 | — | 0.1180 |  | 854 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/QB1` | PLY-27 | — | -3.1339 |  | 37 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/RB1` | PLY-27 | — | 0.4302 |  | 447 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/RB2` | PLY-27 | — | 0.3428 |  | 576 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/TE1` | PLY-27 | — | 0.1679 |  | 399 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR1` | PLY-27 | — | -0.4657 |  | 486 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR2` | PLY-27 | — | -0.4412 |  | 676 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR3` | PLY-27 | — | -0.5306 |  | 764 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/adot/all/QB1` | PLY-28 | — | 1.8667 |  | 53 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/RB1` | PLY-28 | — | 0.5655 |  | 457 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/RB2` | PLY-28 | — | 0.8013 |  | 599 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/TE1` | PLY-28 | — | 7.4779 |  | 412 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR1` | PLY-28 | — | 11.1 |  | 498 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR2` | PLY-28 | — | 10.8 |  | 695 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR3` | PLY-28 | — | 10.4 |  | 798 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/QB1` | PLY-28 | — | -0.3636 |  | 53 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/RB1` | PLY-28 | — | 0.0410 |  | 457 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/RB2` | PLY-28 | — | 0.00238 |  | 599 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/TE1` | PLY-28 | — | 0.2145 |  | 412 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR1` | PLY-28 | — | 0.2740 |  | 498 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR2` | PLY-28 | — | 0.2504 |  | 695 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR3` | PLY-28 | — | 0.2078 |  | 798 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/share/behind/QB1` | PLY-28 | — | 0.4000 |  | 53 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/RB1` | PLY-28 | — | 0.4263 |  | 457 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/RB2` | PLY-28 | — | 0.4128 |  | 599 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/TE1` | PLY-28 | — | 0.0958 |  | 412 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR1` | PLY-28 | — | 0.0779 |  | 498 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR2` | PLY-28 | — | 0.0801 |  | 695 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR3` | PLY-28 | — | 0.0986 |  | 798 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/QB1` | PLY-28 | — | 0.0167 |  | 53 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/RB1` | PLY-28 | — | 0.0148 |  | 457 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/RB2` | PLY-28 | — | 0.0169 |  | 599 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/TE1` | PLY-28 | — | 0.0779 |  | 412 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR1` | PLY-28 | — | 0.1722 |  | 498 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR2` | PLY-28 | — | 0.1697 |  | 695 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR3` | PLY-28 | — | 0.1636 |  | 798 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/QB1` | PLY-28 | — | 0.2000 |  | 53 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/RB1` | PLY-28 | — | 0.0268 |  | 457 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/RB2` | PLY-28 | — | 0.0275 |  | 599 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/TE1` | PLY-28 | — | 0.2203 |  | 412 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR1` | PLY-28 | — | 0.2973 |  | 498 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR2` | PLY-28 | — | 0.2687 |  | 695 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR3` | PLY-28 | — | 0.2474 |  | 798 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/QB1` | PLY-28 | — | 0.3833 |  | 53 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/RB1` | PLY-28 | — | 0.5318 |  | 457 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/RB2` | PLY-28 | — | 0.5428 |  | 599 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/TE1` | PLY-28 | — | 0.6060 |  | 412 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR1` | PLY-28 | — | 0.4526 |  | 498 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR2` | PLY-28 | — | 0.4814 |  | 695 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR3` | PLY-28 | — | 0.4903 |  | 798 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/QB1` | PLY-28 | — | 0 |  | 53 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/RB1` | PLY-28 | — | 0.000383 |  | 457 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/RB2` | PLY-28 | — | 0 |  | 599 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/TE1` | PLY-28 | — | 0 |  | 412 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR1` | PLY-28 | — | 2.72e-05 |  | 498 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR2` | PLY-28 | — | 0 |  | 695 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR3` | PLY-28 | — | 0.000153 |  | 798 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/epa_overall/all/QB1` | PLY-29 | — | -0.3636 |  | 53 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/RB1` | PLY-29 | — | 0.0410 |  | 457 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/RB2` | PLY-29 | — | 0.00238 |  | 599 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/TE1` | PLY-29 | — | 0.2145 |  | 412 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR1` | PLY-29 | — | 0.2740 |  | 498 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR2` | PLY-29 | — | 0.2504 |  | 695 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR3` | PLY-29 | — | 0.2078 |  | 798 | 2016-2022 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/share/left/QB1` | PLY-29 | — | 0.3167 |  | 53 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/RB1` | PLY-29 | — | 0.4026 |  | 457 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/RB2` | PLY-29 | — | 0.4099 |  | 599 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/TE1` | PLY-29 | — | 0.3163 |  | 412 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR1` | PLY-29 | — | 0.3883 |  | 498 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR2` | PLY-29 | — | 0.3740 |  | 695 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR3` | PLY-29 | — | 0.3756 |  | 798 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/QB1` | PLY-29 | — | 0.3000 |  | 53 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/RB1` | PLY-29 | — | 0.1945 |  | 457 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/RB2` | PLY-29 | — | 0.1904 |  | 599 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/TE1` | PLY-29 | — | 0.2771 |  | 412 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR1` | PLY-29 | — | 0.2268 |  | 498 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR2` | PLY-29 | — | 0.2333 |  | 695 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR3` | PLY-29 | — | 0.2266 |  | 798 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/QB1` | PLY-29 | — | 0.3833 |  | 53 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/RB1` | PLY-29 | — | 0.4024 |  | 457 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/RB2` | PLY-29 | — | 0.3997 |  | 599 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/TE1` | PLY-29 | — | 0.4065 |  | 412 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR1` | PLY-29 | — | 0.3848 |  | 498 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR2` | PLY-29 | — | 0.3927 |  | 695 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR3` | PLY-29 | — | 0.3976 |  | 798 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/QB1` | PLY-29 | — | 0 |  | 53 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/RB1` | PLY-29 | — | 0.000383 |  | 457 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/RB2` | PLY-29 | — | 0 |  | 599 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/TE1` | PLY-29 | — | 0.000155 |  | 412 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR1` | PLY-29 | — | 6.62e-05 |  | 498 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR2` | PLY-29 | — | 3.51e-05 |  | 695 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR3` | PLY-29 | — | 0.000197 |  | 798 | 2016-2022 | section 4 slot prior: mean over slot occupants' games of his game share |

## S2024 (seasons 2016-2023)

| key | spec | initial | fitted | change | n | seasons | method |
|---|---|---|---|---|---|---|---|
| `fit:k/COA-04/proe` | COA-04 | 80.0 | 87.6 | +9% | 490 | 2016-2023 | split-half (BT-02), m:r = 25:0.220, 50:0.350, 100:0.572; variance-components cross-check k = 70.3 |
| `fit:k/COA-04/seconds_per_play` | COA-04 | 80.0 | 22.8 | **-71%** | 376 | 2016-2023 | split-half (BT-02), m:r = 25:0.531, 50:0.626; variance-components cross-check k = 12.8 |
| `fit:k/DEF-01/epa/all` | DEF-01 | 250.0 | 986.1 | **+294%** | 256 | 2016-2023 | split-half (BT-02), m:r = 200:0.174, 400:0.279; variance-components cross-check k = 714.7 |
| `fit:k/DEF-01/epa/pass` | DEF-01 | 200.0 | 821.5 | **+311%** | 256 | 2016-2023 | split-half (BT-02), m:r = 200:0.196; variance-components cross-check k = 556.6 |
| `fit:k/DEF-01/epa/run` | DEF-01 | 300.0 | 648.3 | **+116%** | 256 | 2016-2023 | split-half (BT-02), m:r = 100:0.134; variance-components cross-check k = 522.9 |
| `fit:k/DEF-02/success` | DEF-02 | 150.0 | 285.6 | **+90%** | 768 | 2016-2023 | split-half (BT-02), m:r = 25:0.089, 50:0.167, 100:0.278, 200:0.289, 400:0.348; variance-components cross-check k = 263.8 |
| `fit:k/DEF-03/explosive` | DEF-03 | 150.0 | 104.7 | -30% | 716 | 2016-2023 | split-half (BT-02), m:r = 25:0.193 |
| `fit:k/DEF-03/explosive_team` | DEF-03 | — | 519.9 |  | 256 | 2016-2023 | split-half (BT-02), m:r = 100:0.161; variance-components cross-check k = 437.9 |
| `fit:k/DEF-03/share` | DEF-03 | — | 25.1 |  | 2048 | 2016-2023 | split-half (BT-02), m:r = 25:0.534, 50:0.671, 100:0.770, 200:0.845; variance-components cross-check k = 17.9 |
| `fit:k/DEF-03/success` | DEF-03 | 60.0 | 171.8 | **+186%** | 713 | 2016-2023 | split-half (BT-02), m:r = 25:0.127 |
| `fit:k/DEF-03/ypc` | DEF-03 | 100.0 | 143.4 | +43% | 714 | 2016-2023 | split-half (BT-02), m:r = 25:0.148 |
| `fit:k/DEF-03/ypc_team` | DEF-03 | — | 452.8 |  | 256 | 2016-2023 | split-half (BT-02), m:r = 100:0.181; variance-components cross-check k = 405.6 |
| `fit:k/DEF-04/epa_diff` | DEF-04 | 60.0 | 511.1 | **+752%** | 768 | 2016-2023 | split-half (BT-02), m:r = 50:0.110, 100:0.160 |
| `fit:k/DEF-04/receptions` | DEF-04 | 60.0 | 316.7 | **+428%** | 768 | 2016-2023 | split-half (BT-02), m:r = 25:0.101, 50:0.153, 100:0.190 |
| `fit:k/DEF-04/targets` | DEF-04 | 60.0 | 367.2 | **+512%** | 768 | 2016-2023 | split-half (BT-02), m:r = 25:0.088, 50:0.135, 100:0.190 |
| `fit:k/DEF-04/yards` | DEF-04 | 60.0 | 316.1 | **+427%** | 768 | 2016-2023 | split-half (BT-02), m:r = 25:0.098, 50:0.157, 100:0.214 |
| `fit:k/DEF-05/blitz_rate` | DEF-05 | 150.0 | 60.9 | **-59%** | 64 | 2022-2023 | split-half (BT-02), m:r = 25:0.336, 50:0.475, 100:0.615, 200:0.710; variance-components cross-check k = 38.6 |
| `fit:k/DEF-05/box` | DEF-05 | 150.0 | 294.6 | **+96%** | 64 | 2022-2023 | split-half (BT-02), m:r = 100:0.285, 200:0.325; variance-components cross-check k = 51.0 |
| `fit:k/DEF-05/hit_rate` | DEF-05 | 150.0 | 907.4 | **+505%** | 256 | 2016-2023 | split-half (BT-02), m:r = 200:0.181; variance-components cross-check k = 521.5 |
| `fit:k/DEF-05/rushers` | DEF-05 | 150.0 | 82.0 | -45% | 64 | 2022-2023 | split-half (BT-02), m:r = 25:0.291, 50:0.411, 100:0.519, 200:0.628; variance-components cross-check k = 47.7 |
| `fit:k/DEF-06/explosive` | DEF-06 | 300.0 | 1,293 | **+331%** | 256 | 2016-2023 | split-half (BT-02), m:r = 200:0.142, 400:0.220; variance-components cross-check k = 1024.4 |
| `fit:k/DEF-06/explosive_run` | DEF-06 | 300.0 | 481.1 | **+60%** | 256 | 2016-2023 | split-half (BT-02), m:r = 100:0.172; variance-components cross-check k = 437.9 |
| `fit:k/DEF-09/cpoe_team` | DEF-09 | — | 821.6 |  | 256 | 2016-2023 | split-half (BT-02), m:r = 200:0.196; variance-components cross-check k = 610.1 |
| `fit:k/DEF-09/epa` | DEF-09 | 60.0 | 223.5 | **+272%** | 820 | 2016-2023 | split-half (BT-02), m:r = 25:0.101 |
| `fit:k/DEF-11/yacoe` | DEF-11 | 150.0 | 628.9 | **+319%** | 256 | 2016-2023 | split-half (BT-02), m:r = 100:0.137; variance-components cross-check k = 434.6 |
| `fit:k/DEF-12/stacked_box_share` | DEF-12 | — | 201.9 |  | 64 | 2022-2023 | split-half (BT-02), m:r = 50:0.262, 100:0.342, 200:0.433, 400:0.480; variance-components cross-check k = 67.3 |
| `fit:k/DEF-15/success` | DEF-15 | 60.0 | 333.1 | **+455%** | 512 | 2016-2023 | split-half (BT-02), m:r = 50:0.127, 100:0.240; variance-components cross-check k = 257.9 |
| `fit:k/DEF-15/ypc` | DEF-15 | 60.0 | 277.8 | **+363%** | 512 | 2016-2023 | split-half (BT-02), m:r = 50:0.153; variance-components cross-check k = 247.8 |
| `fit:k/DEF-17/passes_defensed` | DEF-17 | 20.0 | 21.0 | +5% | 3764 | 2016-2023 | split-half (BT-02), m:r = 25:0.566, 50:0.712 |
| `fit:k/DEF-17/qb_hits` | DEF-17 | 20.0 | 11.7 | -41% | 4599 | 2016-2023 | split-half (BT-02), m:r = 25:0.704, 50:0.827 |
| `fit:k/DEF-17/sacks` | DEF-17 | 20.0 | 9.4046 | **-53%** | 404 | 2017-2023 | split-half (BT-02), m:r = 25:0.737 |
| `fit:k/DEF-17/tackles_for_loss` | DEF-17 | 20.0 | 27.5 | +37% | 3965 | 2016-2023 | split-half (BT-02), m:r = 25:0.497, 50:0.702 |
| `fit:k/OFF-01/epa/all` | OFF-01 | 250.0 | 331.5 | +33% | 256 | 2016-2023 | split-half (BT-02), m:r = 50:0.150, 100:0.240, 200:0.376, 400:0.516; variance-components cross-check k = 300.9 |
| `fit:k/OFF-01/epa/pass` | OFF-01 | 200.0 | 277.1 | +39% | 256 | 2016-2023 | split-half (BT-02), m:r = 50:0.146, 100:0.266, 200:0.421; variance-components cross-check k = 248.3 |
| `fit:k/OFF-01/epa/run` | OFF-01 | 300.0 | 325.1 | +8% | 256 | 2016-2023 | split-half (BT-02), m:r = 50:0.133, 100:0.236; variance-components cross-check k = 288.5 |
| `fit:k/OFF-02/success` | OFF-02 | 150.0 | 182.3 | +22% | 768 | 2016-2023 | split-half (BT-02), m:r = 25:0.135, 50:0.239, 100:0.372, 200:0.462, 400:0.557; variance-components cross-check k = 166.6 |
| `fit:k/OFF-03/epa` | OFF-03 | 100.0 | 276.4 | **+176%** | 890 | 2016-2023 | split-half (BT-02), m:r = 25:0.086, 50:0.164, 100:0.237; variance-components cross-check k = 147.1 |
| `fit:k/OFF-03/success` | OFF-03 | 100.0 | 212.9 | **+113%** | 890 | 2016-2023 | split-half (BT-02), m:r = 25:0.114, 50:0.190, 100:0.308; variance-components cross-check k = 160.5 |
| `fit:k/OFF-04/pass_rate` | OFF-04 | 60.0 | 111.9 | **+87%** | 256 | 2016-2023 | split-half (BT-02), m:r = 25:0.168, 50:0.307, 100:0.473, 200:0.649; variance-components cross-check k = 104.3 |
| `fit:k/OFF-05/proe` | OFF-05 | 100.0 | 114.7 | +15% | 256 | 2016-2023 | split-half (BT-02), m:r = 25:0.189, 50:0.317, 100:0.466, 200:0.621; variance-components cross-check k = 100.6 |
| `fit:k/OFF-06/play_action_rate` | OFF-06 | 80.0 | 100.8 | +26% | 64 | 2022-2023 | split-half (BT-02), m:r = 50:0.367, 100:0.508, 200:0.606; variance-components cross-check k = 73.4 |
| `fit:k/OFF-07/motion_rate` | OFF-07 | 80.0 | 23.5 | **-71%** | 64 | 2022-2023 | split-half (BT-02), m:r = 25:0.578, 50:0.703, 100:0.808, 200:0.863, 400:0.907; variance-components cross-check k = 16.6 |
| `fit:k/OFF-08/rpo_rate` | OFF-08 | 80.0 | 95.2 | +19% | 64 | 2022-2023 | split-half (BT-02), m:r = 25:0.260, 50:0.396, 100:0.515, 200:0.627, 400:0.716; variance-components cross-check k = 54.6 |
| `fit:k/OFF-09/shotgun_rate` | OFF-09 | 60.0 | 18.7 | **-69%** | 256 | 2016-2023 | split-half (BT-02), m:r = 25:0.624, 50:0.750, 100:0.838, 200:0.892, 400:0.931; variance-components cross-check k = 13.0 |
| `fit:k/OFF-10/seconds_per_play` | OFF-10 | 80.0 | 38.3 | **-52%** | 256 | 2016-2023 | split-half (BT-02), m:r = 25:0.435, 50:0.551, 100:0.701; variance-components cross-check k = 28.8 |
| `fit:k/OFF-12/epa` | OFF-12 | 100.0 | 168.8 | **+69%** | 715 | 2016-2023 | split-half (BT-02), m:r = 25:0.129 |
| `fit:k/OFF-12/explosive` | OFF-12 | 150.0 | 73.9 | **-51%** | 717 | 2016-2023 | split-half (BT-02), m:r = 25:0.253 |
| `fit:k/OFF-12/explosive_team` | OFF-12 | — | 420.2 |  | 256 | 2016-2023 | split-half (BT-02), m:r = 100:0.192; variance-components cross-check k = 372.4 |
| `fit:k/OFF-12/share` | OFF-12 | — | 22.6 |  | 2048 | 2016-2023 | split-half (BT-02), m:r = 25:0.559, 50:0.694, 100:0.791, 200:0.848; variance-components cross-check k = 16.8 |
| `fit:k/OFF-12/success` | OFF-12 | 60.0 | 124.2 | **+107%** | 716 | 2016-2023 | split-half (BT-02), m:r = 25:0.142, 50:0.328 |
| `fit:k/OFF-12/ypc` | OFF-12 | 100.0 | 102.7 | +3% | 716 | 2016-2023 | split-half (BT-02), m:r = 25:0.196 |
| `fit:k/OFF-12/ypc_team` | OFF-12 | — | 345.8 |  | 256 | 2016-2023 | split-half (BT-02), m:r = 100:0.224; variance-components cross-check k = 321.7 |
| `fit:k/OFF-13/cpoe_team` | OFF-13 | — | 425.2 |  | 256 | 2016-2023 | split-half (BT-02), m:r = 100:0.205, 200:0.290; variance-components cross-check k = 358.3 |
| `fit:k/OFF-13/epa` | OFF-13 | 60.0 | 148.1 | **+147%** | 872 | 2016-2023 | split-half (BT-02), m:r = 25:0.144 |
| `fit:k/OFF-13/share` | OFF-13 | 60.0 | 19.6 | **-67%** | 3328 | 2016-2023 | split-half (BT-02), m:r = 25:0.565, 50:0.721, 100:0.836, 200:0.907; variance-components cross-check k = 18.6 |
| `fit:k/OFF-14/pass_share` | OFF-14 | 25.0 | 68.7 | **+175%** | 501 | 2016-2023 | split-half (BT-02), m:r = 25:0.265, 50:0.424; variance-components cross-check k = 52.3 |
| `fit:k/OFF-15/hit_rate` | OFF-15 | 200.0 | 164.6 | -18% | 256 | 2016-2023 | split-half (BT-02), m:r = 25:0.140, 50:0.233, 100:0.384, 200:0.539; variance-components cross-check k = 157.6 |
| `fit:k/OFF-15/sack_rate` | OFF-15 | 200.0 | 284.3 | +42% | 256 | 2016-2023 | split-half (BT-02), m:r = 50:0.152, 100:0.263, 200:0.410; variance-components cross-check k = 255.2 |
| `fit:k/OFF-16/stuff` | OFF-16 | 80.0 | 240.4 | **+200%** | 512 | 2016-2023 | split-half (BT-02), m:r = 25:0.092, 50:0.174; variance-components cross-check k = 205.3 |
| `fit:k/OFF-16/stuff_team` | OFF-16 | — | 255.6 |  | 256 | 2016-2023 | split-half (BT-02), m:r = 50:0.169, 100:0.274; variance-components cross-check k = 210.9 |
| `fit:k/OFF-16/success` | OFF-16 | 80.0 | 226.9 | **+184%** | 512 | 2016-2023 | split-half (BT-02), m:r = 25:0.103, 50:0.176; variance-components cross-check k = 194.4 |
| `fit:k/PLY-03/target_share` | PLY-03 | 60.0 | 10.4 | **-83%** | 7004 | 2016-2023 | split-half (BT-02), m:r = 25:0.718, 50:0.830, 100:0.901, 200:0.948; variance-components cross-check k = 8.9 |
| `fit:k/PLY-04/air_share` | PLY-04 | 60.0 | 13.5 | **-77%** | 7004 | 2016-2023 | split-half (BT-02), m:r = 25:0.648, 50:0.788, 100:0.880, 200:0.937 |
| `fit:k/PLY-04/wopr` | PLY-04 | 60.0 | 9.9041 | **-83%** | 7004 | 2016-2023 | split-half (BT-02), m:r = 25:0.726, 50:0.835, 100:0.907, 200:0.950 |
| `fit:k/PLY-05/carry_share` | PLY-05 | 40.0 | 2.6731 | **-93%** | 6672 | 2016-2023 | split-half (BT-02), m:r = 25:0.913, 50:0.947, 100:0.969, 200:0.984; variance-components cross-check k = 1.5 |
| `fit:k/PLY-06/opportunity_share` | PLY-06 | 20.0 | 7.4940 | **-63%** | 8849 | 2016-2023 | split-half (BT-02), m:r = 25:0.774, 50:0.861, 100:0.915 |
| `fit:k/PLY-06/opportunity_share_overall` | PLY-06 | — | 9.9526 |  | 7144 | 2016-2023 | split-half (BT-02), m:r = 25:0.744, 50:0.839, 100:0.904, 200:0.943, 400:0.967; variance-components cross-check k = 7.3 |
| `fit:k/PLY-07/opportunity_share` | PLY-07 | 30.0 | 11.4 | **-62%** | 10602 | 2016-2023 | split-half (BT-02), m:r = 25:0.686, 50:0.815, 100:0.898 |
| `fit:k/PLY-08/yards_per_team_dropback` | PLY-08 | 150.0 | 27.0 | **-82%** | 7016 | 2016-2023 | split-half (BT-02), m:r = 25:0.485, 50:0.649, 100:0.784, 200:0.883; variance-components cross-check k = 25.7 |
| `fit:k/PLY-09/yacoe` | PLY-09 | 60.0 | 63.4 | +6% | 500 | 2016-2023 | split-half (BT-02), m:r = 25:0.283 |
| `fit:k/PLY-10/croe` | PLY-10 | 80.0 | 247.4 | **+209%** | 978 | 2016-2023 | split-half (BT-02), m:r = 25:0.092 |
| `fit:k/PLY-16/share` | PLY-16 | 40.0 | 19.1 | **-52%** | 4857 | 2016-2023 | split-half (BT-02), m:r = 25:0.587, 50:0.707, 100:0.802 |
| `fit:k/PLY-18/adot` | PLY-18 | 80.0 | 192.1 | **+140%** | 382 | 2016-2023 | split-half (BT-02), m:r = 25:0.113, 50:0.221, 100:0.352, 200:0.452 |
| `fit:k/PLY-18/epa` | PLY-18 | 80.0 | 43.0 | -46% | 913 | 2016-2023 | split-half (BT-02), m:r = 25:0.389, 50:0.403 |
| `fit:k/PLY-18/epa_overall` | PLY-18 | — | 375.4 |  | 382 | 2016-2023 | split-half (BT-02), m:r = 50:0.138, 100:0.206, 200:0.280 |
| `fit:k/PLY-18/share` | PLY-18 | 80.0 | 4.4944 | **-94%** | 1910 | 2016-2023 | split-half (BT-02), m:r = 25:0.850, 50:0.918, 100:0.956, 200:0.978 |
| `fit:k/PLY-19/play_action_rate` | PLY-19 | — | 82.1 |  | 110 | 2022-2023 | split-half (BT-02), m:r = 25:0.260, 50:0.379, 100:0.554, 200:0.551 |
| `fit:k/PLY-20/catchable_rate` | PLY-20 | 200.0 | 298.6 | +49% | 107 | 2022-2023 | split-half (BT-02), m:r = 200:0.401 |
| `fit:k/PLY-20/cpoe` | PLY-20 | 200.0 | 395.8 | **+98%** | 381 | 2016-2023 | split-half (BT-02), m:r = 50:0.129, 100:0.200, 200:0.222 |
| `fit:k/PLY-21/sack_rate` | PLY-21 | 150.0 | 238.6 | **+59%** | 390 | 2016-2023 | split-half (BT-02), m:r = 25:0.106, 50:0.197, 100:0.278, 200:0.418 |
| `fit:k/PLY-21/time_to_throw` | PLY-21 | 150.0 | 69.9 | **-53%** | 377 | 2016-2023 | split-half (BT-02), m:r = 25:0.361, 50:0.502, 100:0.617, 200:0.749 |
| `fit:k/PLY-22/scramble_rate` | PLY-22 | — | 63.3 |  | 390 | 2016-2023 | split-half (BT-02), m:r = 25:0.299, 50:0.454, 100:0.608, 200:0.732 |
| `fit:k/PLY-23/epa` | PLY-23 | 100.0 | 192.6 | **+93%** | 864 | 2016-2023 | split-half (BT-02), m:r = 25:0.119, 50:0.202 |
| `fit:k/PLY-23/epa_overall` | PLY-23 | — | 409.8 |  | 382 | 2016-2023 | split-half (BT-02), m:r = 50:0.119, 100:0.205, 200:0.263 |
| `fit:k/PLY-23/share` | PLY-23 | 100.0 | 6.6514 | **-93%** | 1528 | 2016-2023 | split-half (BT-02), m:r = 25:0.798, 50:0.884, 100:0.935, 200:0.964 |
| `fit:k/PLY-24/success_overall` | PLY-24 | — | 87.6 |  | 141 | 2022-2023 | split-half (BT-02), m:r = 25:0.222 |
| `fit:k/PLY-25/success` | PLY-25 | 60.0 | 178.8 | **+198%** | 619 | 2016-2023 | split-half (BT-02), m:r = 25:0.128, 50:0.206 |
| `fit:k/PLY-25/success_overall` | PLY-25 | — | 127.0 |  | 562 | 2016-2023 | split-half (BT-02), m:r = 25:0.182, 50:0.192 |
| `fit:k/PLY-25/ypc` | PLY-25 | 60.0 | 158.8 | **+165%** | 619 | 2016-2023 | split-half (BT-02), m:r = 25:0.146, 50:0.162 |
| `fit:k/PLY-25/ypc_overall` | PLY-25 | — | 199.2 |  | 562 | 2016-2023 | split-half (BT-02), m:r = 25:0.125, 50:0.158 |
| `fit:k/PLY-26/explosive` | PLY-26 | 150.0 | 214.7 | +43% | 561 | 2016-2023 | split-half (BT-02), m:r = 25:0.113, 50:0.174 |
| `fit:k/PLY-26/stuff` | PLY-26 | 100.0 | 195.3 | **+95%** | 561 | 2016-2023 | split-half (BT-02), m:r = 25:0.117, 50:0.200 |
| `fit:k/PLY-27/screen_share` | PLY-27 | 40.0 | 6.0907 | **-85%** | 610 | 2022-2023 | split-half (BT-02), m:r = 25:0.804 |
| `fit:k/PLY-27/target_share` | PLY-27 | 40.0 | 10.4 | **-74%** | 7004 | 2016-2023 | split-half (BT-02), m:r = 25:0.719, 50:0.830, 100:0.901, 200:0.947; variance-components cross-check k = 8.9 |
| `fit:k/PLY-27/yacoe` | PLY-27 | 40.0 | 66.1 | **+65%** | 503 | 2016-2023 | split-half (BT-02), m:r = 25:0.274 |
| `fit:k/PLY-28/adot` | PLY-28 | 40.0 | 6.4456 | **-84%** | 978 | 2016-2023 | split-half (BT-02), m:r = 25:0.802, 50:0.776 |
| `fit:k/PLY-28/epa_overall` | PLY-28 | — | 213.8 |  | 978 | 2016-2023 | split-half (BT-02), m:r = 25:0.105 |
| `fit:k/PLY-28/share` | PLY-28 | 40.0 | 3.6457 | **-91%** | 4884 | 2016-2023 | split-half (BT-02), m:r = 25:0.875, 50:0.923 |
| `fit:k/PLY-29/epa_overall` | PLY-29 | — | 226.7 |  | 979 | 2016-2023 | split-half (BT-02), m:r = 25:0.099 |
| `fit:k/PLY-29/share` | PLY-29 | 50.0 | 6.0336 | **-88%** | 3910 | 2016-2023 | split-half (BT-02), m:r = 25:0.806, 50:0.891 |
| `fit:k/PLY-30/created_reception_rate` | PLY-30 | — | 63.5 |  | 143 | 2022-2023 | split-half (BT-02), m:r = 25:0.283 |
| `fit:k/PLY-31/cushion` | PLY-31 | 80.0 | 53.8 | -33% | 636 | 2016-2023 | split-half (BT-02), m:r = 25:0.349, 50:0.505 |
| `fit:k/PLY-31/separation` | PLY-31 | 80.0 | 38.3 | **-52%** | 636 | 2016-2023 | split-half (BT-02), m:r = 25:0.439, 50:0.562 |
| `fit:k/PLY-32/end_zone_share` | PLY-32 | 15.0 | 5.4678 | **-64%** | 403 | 2016-2023 | split-half (BT-02), m:r = 25:0.821 |
| `fit:k/PLY-33/target_share` | PLY-33 | 40.0 | 9.0891 | **-77%** | 2708 | 2022-2023 | split-half (BT-02), m:r = 25:0.735, 50:0.845, 100:0.916 |
| `conventions.g3_usage_half_life_games` | G3 | 3.0000 | 8.0000 | **+167%** | 18 | 2016-2023 | next-game n-weighted squared error / prior-only, mean over 18 usage stats (ruling 2026-10-08) |
| `conventions.g3_efficiency_half_life_games` | G3 | 6.0000 | 8.0000 | +33% | 80 | 2016-2023 | next-game n-weighted squared error / prior-only, mean over 80 efficiency stats (ruling 2026-10-08) |
| `fit:G6/penalty` | G6 | — | 316.2 |  | 228970 | 2016-2023 | forward-chaining CV within each season (BT-02), efficiency h = 8 |
| `fit:COA-02/p_go/intercept` | COA-02 | — | 1.5623 |  | 27287 | 2016-2023 | logistic, four fields as linear terms (se 0.061) |
| `fit:COA-02/p_go/ydstogo` | COA-02 | — | -0.3609 |  | 27287 | 2016-2023 | logistic, four fields as linear terms (se 0.00772) |
| `fit:COA-02/p_go/yardline_100` | COA-02 | — | -0.0227 |  | 27287 | 2016-2023 | logistic, four fields as linear terms (se 0.000845) |
| `fit:COA-02/p_go/score_differential` | COA-02 | — | -0.0552 |  | 27287 | 2016-2023 | logistic, four fields as linear terms (se 0.00244) |
| `fit:COA-02/p_go/game_seconds_remaining` | COA-02 | — | -0.000407 |  | 27287 | 2016-2023 | logistic, four fields as linear terms (se 2.12e-05) |
| `fit:k/COA-02/go_over_expected` | COA-02 | 30.0 | 110.8 | **+269%** | 256 | 2016-2023 | split-half (BT-02), m:r = 25:0.184 |
| `matchup.mtc_03_ol_absence_factor` | MTC-03 | 1.1000 | 1.0434 | -5% | 8544 | 2016-2023 | offset logistic on dropbacks, exp(coef) per missing OFF-17 starter (se of log 0.0146); undamped |
| `fit:PLY-14/practice/DNP` | PLY-14 | — | 0.2059 |  | 12299 | 2016-2023 | P(played | DNP) |
| `fit:PLY-14/practice/Limited` | PLY-14 | — | 0.7023 |  | 10730 | 2016-2023 | P(played | Limited) |
| `fit:PLY-14/practice/Full` | PLY-14 | — | 0.9332 |  | 19322 | 2016-2023 | P(played | Full) |
| `fit:PRJ-06/missed/QB` | PRJ-06 | — | 0.1744 |  | 4943 | 2016-2023 | P(no snap | played last game), QB |
| `fit:PRJ-06/missed/RB` | PRJ-06 | — | 0.1282 |  | 12793 | 2016-2023 | P(no snap | played last game), RB |
| `fit:PRJ-06/missed/WR` | PRJ-06 | — | 0.1120 |  | 19388 | 2016-2023 | P(no snap | played last game), WR |
| `fit:PRJ-06/missed/TE` | PRJ-06 | — | 0.0895 |  | 11674 | 2016-2023 | P(no snap | played last game), TE |
| `player.ply_14_return_factor` | PLY-14 | 0.8500 | 0.9293 | +9% | 1015 | 2016-2023 | sum first-game-back snap share / sum baseline (usage h = 8) |
| `fit:role/PLY-01/snap_share/all/QB1` | PLY-01 | — | 0.8751 |  | 472 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/RB1` | PLY-01 | — | 0.5279 |  | 551 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/RB2` | PLY-01 | — | 0.2991 |  | 773 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/TE1` | PLY-01 | — | 0.6423 |  | 506 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR1` | PLY-01 | — | 0.7496 |  | 582 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR2` | PLY-01 | — | 0.6675 |  | 813 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR3` | PLY-01 | — | 0.5136 |  | 978 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/QB1` | PLY-02 | — | 0.8751 |  | 472 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/RB1` | PLY-02 | — | 0.5279 |  | 551 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/RB2` | PLY-02 | — | 0.2991 |  | 773 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/TE1` | PLY-02 | — | 0.6423 |  | 506 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR1` | PLY-02 | — | 0.7496 |  | 582 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR2` | PLY-02 | — | 0.6675 |  | 813 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR3` | PLY-02 | — | 0.5136 |  | 978 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/QB1` | PLY-03 | — | 0.000591 |  | 472 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/RB1` | PLY-03 | — | 0.1045 |  | 551 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/RB2` | PLY-03 | — | 0.0641 |  | 773 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/TE1` | PLY-03 | — | 0.1342 |  | 506 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR1` | PLY-03 | — | 0.2195 |  | 582 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR2` | PLY-03 | — | 0.1690 |  | 813 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR3` | PLY-03 | — | 0.1168 |  | 978 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/QB1` | PLY-04 | — | 4.71e-05 |  | 472 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/RB1` | PLY-04 | — | 0.00401 |  | 551 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/RB2` | PLY-04 | — | 0.00389 |  | 773 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/TE1` | PLY-04 | — | 0.1254 |  | 506 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR1` | PLY-04 | — | 0.3033 |  | 582 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR2` | PLY-04 | — | 0.2254 |  | 813 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR3` | PLY-04 | — | 0.1504 |  | 978 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/QB1` | PLY-04 | — | 0.00092 |  | 472 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/RB1` | PLY-04 | — | 0.1596 |  | 551 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/RB2` | PLY-04 | — | 0.0989 |  | 773 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/TE1` | PLY-04 | — | 0.2892 |  | 506 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR1` | PLY-04 | — | 0.5416 |  | 582 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR2` | PLY-04 | — | 0.4113 |  | 813 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR3` | PLY-04 | — | 0.2804 |  | 978 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/QB1` | PLY-05 | — | 0.0523 |  | 472 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/RB1` | PLY-05 | — | 0.5446 |  | 551 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/RB2` | PLY-05 | — | 0.2634 |  | 773 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/TE1` | PLY-05 | — | 0.000873 |  | 506 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR1` | PLY-05 | — | 0.00726 |  | 582 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR2` | PLY-05 | — | 0.00775 |  | 813 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR3` | PLY-05 | — | 0.00723 |  | 978 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/QB1` | PLY-06 | — | 0.0232 |  | 472 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/RB1` | PLY-06 | — | 0.2871 |  | 551 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/RB2` | PLY-06 | — | 0.1490 |  | 773 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/TE1` | PLY-06 | — | 0.0780 |  | 506 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR1` | PLY-06 | — | 0.1298 |  | 582 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR2` | PLY-06 | — | 0.1011 |  | 813 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR3` | PLY-06 | — | 0.0712 |  | 978 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-08/yards_per_team_dropback/all/QB1` | PLY-08 | — | 0.00102 |  | 472 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/RB1` | PLY-08 | — | 0.5473 |  | 551 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/RB2` | PLY-08 | — | 0.3105 |  | 773 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/TE1` | PLY-08 | — | 0.8835 |  | 506 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR1` | PLY-08 | — | 1.6033 |  | 582 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR2` | PLY-08 | — | 1.1845 |  | 813 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR3` | PLY-08 | — | 0.7963 |  | 978 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/QB1` | PLY-18 | — | 8.0057 |  | 466 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/WR1` | PLY-18 | — | 13.1 |  | 52 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/WR2` | PLY-18 | — | 13.9 |  | 34 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/QB1` | PLY-18 | — | 0.1597 |  | 466 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/WR1` | PLY-18 | — | 0.4422 |  | 52 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/WR2` | PLY-18 | — | 0.5098 |  | 34 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/share/behind/QB1` | PLY-18 | — | 0.1588 |  | 466 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/behind/WR1` | PLY-18 | — | 0.1254 |  | 52 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/behind/WR2` | PLY-18 | — | 0.2209 |  | 34 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/QB1` | PLY-18 | — | 0.1189 |  | 466 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/WR1` | PLY-18 | — | 0.2540 |  | 52 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/WR2` | PLY-18 | — | 0.3605 |  | 34 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/QB1` | PLY-18 | — | 0.2128 |  | 466 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/WR1` | PLY-18 | — | 0.3921 |  | 52 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/WR2` | PLY-18 | — | 0.2558 |  | 34 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/QB1` | PLY-18 | — | 0.5094 |  | 466 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/WR1` | PLY-18 | — | 0.2286 |  | 52 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/WR2` | PLY-18 | — | 0.1628 |  | 34 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/QB1` | PLY-18 | — | 0.000122 |  | 466 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/WR1` | PLY-18 | — | 0 |  | 52 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/WR2` | PLY-18 | — | 0 |  | 34 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/epa_overall/all/QB1` | PLY-23 | — | 0.1597 |  | 466 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/epa_overall/all/WR1` | PLY-23 | — | 0.4422 |  | 52 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/epa_overall/all/WR2` | PLY-23 | — | 0.5098 |  | 34 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/share/left/QB1` | PLY-23 | — | 0.3735 |  | 466 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/left/WR1` | PLY-23 | — | 0.2397 |  | 52 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/left/WR2` | PLY-23 | — | 0.2907 |  | 34 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/QB1` | PLY-23 | — | 0.2213 |  | 466 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/WR1` | PLY-23 | — | 0.0476 |  | 52 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/WR2` | PLY-23 | — | 0.0233 |  | 34 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/QB1` | PLY-23 | — | 0.4049 |  | 466 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/WR1` | PLY-23 | — | 0.7127 |  | 52 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/WR2` | PLY-23 | — | 0.6860 |  | 34 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/QB1` | PLY-23 | — | 0.000265 |  | 466 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/WR1` | PLY-23 | — | 0 |  | 52 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/WR2` | PLY-23 | — | 0 |  | 34 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-24/success_overall/all/QB1` | PLY-24 | — | 0.5581 |  | 120 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/RB1` | PLY-24 | — | 0.3965 |  | 131 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/RB2` | PLY-24 | — | 0.4051 |  | 186 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/WR1` | PLY-24 | — | 0.5213 |  | 55 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/WR2` | PLY-24 | — | 0.4557 |  | 55 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/WR3` | PLY-24 | — | 0.5491 |  | 71 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/QB1` | PLY-24 | — | 3.7005 |  | 120 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/RB1` | PLY-24 | — | 4.3504 |  | 131 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/RB2` | PLY-24 | — | 4.2531 |  | 186 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/WR1` | PLY-24 | — | 5.2559 |  | 55 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/WR2` | PLY-24 | — | 5.6203 |  | 55 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/WR3` | PLY-24 | — | 7.3006 |  | 71 | 2022-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/QB1` | PLY-25 | — | 0.5387 |  | 401 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/RB1` | PLY-25 | — | 0.3902 |  | 540 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/RB2` | PLY-25 | — | 0.3921 |  | 736 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/TE1` | PLY-25 | — | 0.5862 |  | 50 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR1` | PLY-25 | — | 0.5150 |  | 216 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR2` | PLY-25 | — | 0.5197 |  | 234 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR3` | PLY-25 | — | 0.5350 |  | 247 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/QB1` | PLY-25 | — | 3.8854 |  | 401 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/RB1` | PLY-25 | — | 4.3009 |  | 540 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/RB2` | PLY-25 | — | 4.2394 |  | 736 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/TE1` | PLY-25 | — | 3.2989 |  | 50 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR1` | PLY-25 | — | 6.0143 |  | 216 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR2` | PLY-25 | — | 6.0039 |  | 234 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR3` | PLY-25 | — | 6.4863 |  | 247 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-27/screen_share/all/QB1` | PLY-27 | — | 0.000314 |  | 135 | 2022-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/RB1` | PLY-27 | — | 0.2372 |  | 132 | 2022-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/RB2` | PLY-27 | — | 0.1329 |  | 198 | 2022-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/TE1` | PLY-27 | — | 0.0802 |  | 125 | 2022-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/WR1` | PLY-27 | — | 0.1635 |  | 149 | 2022-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/WR2` | PLY-27 | — | 0.1180 |  | 198 | 2022-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/WR3` | PLY-27 | — | 0.0914 |  | 248 | 2022-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/QB1` | PLY-27 | — | 0.000591 |  | 472 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/RB1` | PLY-27 | — | 0.1045 |  | 551 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/RB2` | PLY-27 | — | 0.0641 |  | 773 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/TE1` | PLY-27 | — | 0.1342 |  | 506 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR1` | PLY-27 | — | 0.2195 |  | 582 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR2` | PLY-27 | — | 0.1690 |  | 813 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR3` | PLY-27 | — | 0.1168 |  | 978 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/QB1` | PLY-27 | — | -3.1783 |  | 44 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/RB1` | PLY-27 | — | 0.4584 |  | 510 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/RB2` | PLY-27 | — | 0.2781 |  | 652 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/TE1` | PLY-27 | — | 0.1381 |  | 457 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR1` | PLY-27 | — | -0.4445 |  | 555 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR2` | PLY-27 | — | -0.4529 |  | 771 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR3` | PLY-27 | — | -0.5615 |  | 874 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/adot/all/QB1` | PLY-28 | — | 1.2059 |  | 61 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/RB1` | PLY-28 | — | 0.4795 |  | 520 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/RB2` | PLY-28 | — | 0.6560 |  | 678 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/TE1` | PLY-28 | — | 7.3624 |  | 473 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR1` | PLY-28 | — | 11.0 |  | 571 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR2` | PLY-28 | — | 10.8 |  | 793 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR3` | PLY-28 | — | 10.3 |  | 912 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/QB1` | PLY-28 | — | -0.3754 |  | 61 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/RB1` | PLY-28 | — | 0.0382 |  | 520 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/RB2` | PLY-28 | — | -0.0128 |  | 678 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/TE1` | PLY-28 | — | 0.2123 |  | 473 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR1` | PLY-28 | — | 0.2794 |  | 571 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR2` | PLY-28 | — | 0.2427 |  | 793 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR3` | PLY-28 | — | 0.2023 |  | 912 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/share/behind/QB1` | PLY-28 | — | 0.4559 |  | 61 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/RB1` | PLY-28 | — | 0.4379 |  | 520 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/RB2` | PLY-28 | — | 0.4235 |  | 678 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/TE1` | PLY-28 | — | 0.0998 |  | 473 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR1` | PLY-28 | — | 0.0813 |  | 571 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR2` | PLY-28 | — | 0.0823 |  | 793 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR3` | PLY-28 | — | 0.1031 |  | 912 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/QB1` | PLY-28 | — | 0.0147 |  | 61 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/RB1` | PLY-28 | — | 0.0142 |  | 520 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/RB2` | PLY-28 | — | 0.0161 |  | 678 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/TE1` | PLY-28 | — | 0.0764 |  | 473 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR1` | PLY-28 | — | 0.1725 |  | 571 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR2` | PLY-28 | — | 0.1691 |  | 793 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR3` | PLY-28 | — | 0.1632 |  | 912 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/QB1` | PLY-28 | — | 0.1765 |  | 61 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/RB1` | PLY-28 | — | 0.0268 |  | 520 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/RB2` | PLY-28 | — | 0.0271 |  | 678 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/TE1` | PLY-28 | — | 0.2160 |  | 473 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR1` | PLY-28 | — | 0.2935 |  | 571 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR2` | PLY-28 | — | 0.2708 |  | 793 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR3` | PLY-28 | — | 0.2500 |  | 912 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/QB1` | PLY-28 | — | 0.3529 |  | 61 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/RB1` | PLY-28 | — | 0.5208 |  | 520 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/RB2` | PLY-28 | — | 0.5333 |  | 678 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/TE1` | PLY-28 | — | 0.6078 |  | 473 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR1` | PLY-28 | — | 0.4527 |  | 571 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR2` | PLY-28 | — | 0.4777 |  | 793 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR3` | PLY-28 | — | 0.4835 |  | 912 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/QB1` | PLY-28 | — | 0 |  | 61 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/RB1` | PLY-28 | — | 0.000331 |  | 520 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/RB2` | PLY-28 | — | 0 |  | 678 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/TE1` | PLY-28 | — | 0 |  | 473 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR1` | PLY-28 | — | 2.36e-05 |  | 571 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR2` | PLY-28 | — | 0 |  | 793 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR3` | PLY-28 | — | 0.000134 |  | 912 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/epa_overall/all/QB1` | PLY-29 | — | -0.3754 |  | 61 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/RB1` | PLY-29 | — | 0.0382 |  | 520 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/RB2` | PLY-29 | — | -0.0128 |  | 678 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/TE1` | PLY-29 | — | 0.2123 |  | 473 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR1` | PLY-29 | — | 0.2794 |  | 571 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR2` | PLY-29 | — | 0.2427 |  | 793 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR3` | PLY-29 | — | 0.2023 |  | 912 | 2016-2023 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/share/left/QB1` | PLY-29 | — | 0.3382 |  | 61 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/RB1` | PLY-29 | — | 0.4067 |  | 520 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/RB2` | PLY-29 | — | 0.4072 |  | 678 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/TE1` | PLY-29 | — | 0.3195 |  | 473 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR1` | PLY-29 | — | 0.3909 |  | 571 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR2` | PLY-29 | — | 0.3786 |  | 793 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR3` | PLY-29 | — | 0.3778 |  | 912 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/QB1` | PLY-29 | — | 0.3088 |  | 61 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/RB1` | PLY-29 | — | 0.1884 |  | 520 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/RB2` | PLY-29 | — | 0.1846 |  | 678 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/TE1` | PLY-29 | — | 0.2714 |  | 473 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR1` | PLY-29 | — | 0.2213 |  | 571 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR2` | PLY-29 | — | 0.2272 |  | 793 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR3` | PLY-29 | — | 0.2228 |  | 912 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/QB1` | PLY-29 | — | 0.3529 |  | 61 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/RB1` | PLY-29 | — | 0.4046 |  | 520 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/RB2` | PLY-29 | — | 0.4082 |  | 678 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/TE1` | PLY-29 | — | 0.4090 |  | 473 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR1` | PLY-29 | — | 0.3878 |  | 571 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR2` | PLY-29 | — | 0.3941 |  | 793 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR3` | PLY-29 | — | 0.3993 |  | 912 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/QB1` | PLY-29 | — | 0 |  | 61 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/RB1` | PLY-29 | — | 0.000331 |  | 520 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/RB2` | PLY-29 | — | 0 |  | 678 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/TE1` | PLY-29 | — | 0.000134 |  | 473 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR1` | PLY-29 | — | 5.74e-05 |  | 571 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR2` | PLY-29 | — | 3.05e-05 |  | 793 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR3` | PLY-29 | — | 0.000172 |  | 912 | 2016-2023 | section 4 slot prior: mean over slot occupants' games of his game share |

## live (seasons 2016-2024)

| key | spec | initial | fitted | change | n | seasons | method |
|---|---|---|---|---|---|---|---|
| `fit:k/COA-04/proe` | COA-04 | 80.0 | 89.0 | +11% | 548 | 2016-2024 | split-half (BT-02), m:r = 25:0.216, 50:0.344, 100:0.571; variance-components cross-check k = 71.8 |
| `fit:k/COA-04/seconds_per_play` | COA-04 | 80.0 | 24.8 | **-69%** | 420 | 2016-2024 | split-half (BT-02), m:r = 25:0.510, 50:0.612; variance-components cross-check k = 14.4 |
| `fit:k/DEF-01/epa/all` | DEF-01 | 250.0 | 1,010 | **+304%** | 288 | 2016-2024 | split-half (BT-02), m:r = 200:0.169, 400:0.278; variance-components cross-check k = 720.7 |
| `fit:k/DEF-01/epa/pass` | DEF-01 | 200.0 | 924.0 | **+362%** | 288 | 2016-2024 | split-half (BT-02), m:r = 200:0.178; variance-components cross-check k = 601.3 |
| `fit:k/DEF-01/epa/run` | DEF-01 | 300.0 | 554.7 | **+85%** | 288 | 2016-2024 | split-half (BT-02), m:r = 100:0.153; variance-components cross-check k = 464.7 |
| `fit:k/DEF-02/success` | DEF-02 | 150.0 | 289.2 | **+93%** | 864 | 2016-2024 | split-half (BT-02), m:r = 25:0.090, 50:0.165, 100:0.275, 200:0.282, 400:0.344; variance-components cross-check k = 268.7 |
| `fit:k/DEF-03/explosive` | DEF-03 | 150.0 | 97.7 | -35% | 827 | 2016-2024 | split-half (BT-02), m:r = 25:0.204 |
| `fit:k/DEF-03/explosive_team` | DEF-03 | — | 528.2 |  | 288 | 2016-2024 | split-half (BT-02), m:r = 100:0.159; variance-components cross-check k = 450.7 |
| `fit:k/DEF-03/share` | DEF-03 | — | 25.5 |  | 2304 | 2016-2024 | split-half (BT-02), m:r = 25:0.529, 50:0.667, 100:0.768, 200:0.843; variance-components cross-check k = 18.5 |
| `fit:k/DEF-03/success` | DEF-03 | 60.0 | 161.0 | **+168%** | 823 | 2016-2024 | split-half (BT-02), m:r = 25:0.134 |
| `fit:k/DEF-03/ypc` | DEF-03 | 100.0 | 124.0 | +24% | 825 | 2016-2024 | split-half (BT-02), m:r = 25:0.168 |
| `fit:k/DEF-03/ypc_team` | DEF-03 | — | 492.2 |  | 288 | 2016-2024 | split-half (BT-02), m:r = 100:0.169; variance-components cross-check k = 426.0 |
| `fit:k/DEF-04/epa_diff` | DEF-04 | 60.0 | 665.4 | **+1009%** | 864 | 2016-2024 | split-half (BT-02), m:r = 100:0.141 |
| `fit:k/DEF-04/receptions` | DEF-04 | 60.0 | 321.0 | **+435%** | 864 | 2016-2024 | split-half (BT-02), m:r = 25:0.099, 50:0.151, 100:0.178 |
| `fit:k/DEF-04/targets` | DEF-04 | 60.0 | 382.9 | **+538%** | 864 | 2016-2024 | split-half (BT-02), m:r = 25:0.085, 50:0.129, 100:0.173 |
| `fit:k/DEF-04/yards` | DEF-04 | 60.0 | 337.6 | **+463%** | 864 | 2016-2024 | split-half (BT-02), m:r = 25:0.091, 50:0.152, 100:0.198 |
| `fit:k/DEF-05/blitz_rate` | DEF-05 | 150.0 | 60.4 | **-60%** | 96 | 2022-2024 | split-half (BT-02), m:r = 25:0.341, 50:0.477, 100:0.612, 200:0.714; variance-components cross-check k = 39.5 |
| `fit:k/DEF-05/box` | DEF-05 | 150.0 | 385.5 | **+157%** | 96 | 2022-2024 | split-half (BT-02), m:r = 100:0.233, 200:0.282; variance-components cross-check k = 37.0 |
| `fit:k/DEF-05/hit_rate` | DEF-05 | 150.0 | 799.8 | **+433%** | 288 | 2016-2024 | split-half (BT-02), m:r = 100:0.119, 200:0.191; variance-components cross-check k = 499.2 |
| `fit:k/DEF-05/rushers` | DEF-05 | 150.0 | 102.0 | -32% | 96 | 2022-2024 | split-half (BT-02), m:r = 25:0.266, 50:0.349, 100:0.429, 200:0.501; variance-components cross-check k = 42.0 |
| `fit:k/DEF-06/explosive` | DEF-06 | 300.0 | 1,416 | **+372%** | 288 | 2016-2024 | split-half (BT-02), m:r = 200:0.132, 400:0.205; variance-components cross-check k = 1076.1 |
| `fit:k/DEF-06/explosive_run` | DEF-06 | 300.0 | 512.0 | **+71%** | 288 | 2016-2024 | split-half (BT-02), m:r = 100:0.163; variance-components cross-check k = 450.7 |
| `fit:k/DEF-09/cpoe_team` | DEF-09 | — | 748.5 |  | 288 | 2016-2024 | split-half (BT-02), m:r = 100:0.119, 200:0.210; variance-components cross-check k = 587.9 |
| `fit:k/DEF-09/epa` | DEF-09 | 60.0 | 212.6 | **+254%** | 920 | 2016-2024 | split-half (BT-02), m:r = 25:0.105 |
| `fit:k/DEF-12/stacked_box_share` | DEF-12 | — | 120.4 |  | 96 | 2022-2024 | split-half (BT-02), m:r = 25:0.242, 50:0.337, 100:0.437, 200:0.533, 400:0.585; variance-components cross-check k = 55.9 |
| `fit:k/DEF-12/ypc` | DEF-12 | 50.0 | 146.3 | **+193%** | 242 | 2022-2024 | split-half (BT-02), m:r = 25:0.146; variance-components cross-check k = 130.7 |
| `fit:k/DEF-15/success` | DEF-15 | 60.0 | 303.7 | **+406%** | 576 | 2016-2024 | split-half (BT-02), m:r = 50:0.140, 100:0.253; variance-components cross-check k = 243.9 |
| `fit:k/DEF-15/ypc` | DEF-15 | 60.0 | 297.7 | **+396%** | 576 | 2016-2024 | split-half (BT-02), m:r = 50:0.144; variance-components cross-check k = 256.5 |
| `fit:k/DEF-17/passes_defensed` | DEF-17 | 20.0 | 21.1 | +5% | 4256 | 2016-2024 | split-half (BT-02), m:r = 25:0.564, 50:0.732 |
| `fit:k/DEF-17/qb_hits` | DEF-17 | 20.0 | 11.8 | -41% | 5195 | 2016-2024 | split-half (BT-02), m:r = 25:0.703, 50:0.828 |
| `fit:k/DEF-17/sacks` | DEF-17 | 20.0 | 9.7738 | **-51%** | 496 | 2017-2024 | split-half (BT-02), m:r = 25:0.729 |
| `fit:k/DEF-17/tackles_for_loss` | DEF-17 | 20.0 | 28.4 | +42% | 4532 | 2016-2024 | split-half (BT-02), m:r = 25:0.491, 50:0.636 |
| `fit:k/OFF-01/epa/all` | OFF-01 | 250.0 | 319.1 | +28% | 288 | 2016-2024 | split-half (BT-02), m:r = 50:0.150, 100:0.246, 200:0.386, 400:0.531; variance-components cross-check k = 288.5 |
| `fit:k/OFF-01/epa/pass` | OFF-01 | 200.0 | 273.7 | +37% | 288 | 2016-2024 | split-half (BT-02), m:r = 50:0.148, 100:0.270, 200:0.423; variance-components cross-check k = 245.0 |
| `fit:k/OFF-01/epa/run` | OFF-01 | 300.0 | 303.3 | +1% | 288 | 2016-2024 | split-half (BT-02), m:r = 50:0.138, 100:0.250; variance-components cross-check k = 265.8 |
| `fit:k/OFF-02/success` | OFF-02 | 150.0 | 182.1 | +21% | 864 | 2016-2024 | split-half (BT-02), m:r = 25:0.134, 50:0.239, 100:0.373, 200:0.463, 400:0.561; variance-components cross-check k = 165.7 |
| `fit:k/OFF-03/epa` | OFF-03 | 100.0 | 277.6 | **+178%** | 996 | 2016-2024 | split-half (BT-02), m:r = 25:0.086, 50:0.162, 100:0.239; variance-components cross-check k = 144.2 |
| `fit:k/OFF-03/success` | OFF-03 | 100.0 | 212.1 | **+112%** | 996 | 2016-2024 | split-half (BT-02), m:r = 25:0.113, 50:0.190, 100:0.313; variance-components cross-check k = 158.9 |
| `fit:k/OFF-04/pass_rate` | OFF-04 | 60.0 | 116.7 | **+94%** | 288 | 2016-2024 | split-half (BT-02), m:r = 25:0.165, 50:0.299, 100:0.461, 200:0.639; variance-components cross-check k = 108.7 |
| `fit:k/OFF-05/proe` | OFF-05 | 100.0 | 115.7 | +16% | 288 | 2016-2024 | split-half (BT-02), m:r = 25:0.190, 50:0.313, 100:0.462, 200:0.621; variance-components cross-check k = 101.2 |
| `fit:k/OFF-06/play_action_rate` | OFF-06 | 80.0 | 100.2 | +25% | 96 | 2022-2024 | split-half (BT-02), m:r = 25:0.233, 50:0.361, 100:0.496, 200:0.611; variance-components cross-check k = 78.2 |
| `fit:k/OFF-07/motion_rate` | OFF-07 | 80.0 | 23.7 | **-70%** | 96 | 2022-2024 | split-half (BT-02), m:r = 25:0.580, 50:0.703, 100:0.803, 200:0.860, 400:0.906; variance-components cross-check k = 16.1 |
| `fit:k/OFF-08/rpo_rate` | OFF-08 | 80.0 | 104.9 | +31% | 96 | 2022-2024 | split-half (BT-02), m:r = 25:0.239, 50:0.374, 100:0.494, 200:0.611, 400:0.698; variance-components cross-check k = 59.1 |
| `fit:k/OFF-09/shotgun_rate` | OFF-09 | 60.0 | 18.8 | **-69%** | 288 | 2016-2024 | split-half (BT-02), m:r = 25:0.622, 50:0.748, 100:0.837, 200:0.892, 400:0.931; variance-components cross-check k = 13.0 |
| `fit:k/OFF-10/seconds_per_play` | OFF-10 | 80.0 | 39.3 | **-51%** | 288 | 2016-2024 | split-half (BT-02), m:r = 25:0.428, 50:0.548, 100:0.694; variance-components cross-check k = 29.3 |
| `fit:k/OFF-12/epa` | OFF-12 | 100.0 | 162.1 | **+62%** | 821 | 2016-2024 | split-half (BT-02), m:r = 25:0.130, 50:0.249 |
| `fit:k/OFF-12/explosive` | OFF-12 | 150.0 | 75.1 | -50% | 823 | 2016-2024 | split-half (BT-02), m:r = 25:0.250 |
| `fit:k/OFF-12/explosive_team` | OFF-12 | — | 411.1 |  | 288 | 2016-2024 | split-half (BT-02), m:r = 100:0.196; variance-components cross-check k = 369.3 |
| `fit:k/OFF-12/share` | OFF-12 | — | 22.8 |  | 2304 | 2016-2024 | split-half (BT-02), m:r = 25:0.556, 50:0.691, 100:0.791, 200:0.848; variance-components cross-check k = 17.3 |
| `fit:k/OFF-12/success` | OFF-12 | 60.0 | 126.5 | **+111%** | 822 | 2016-2024 | split-half (BT-02), m:r = 25:0.134, 50:0.328 |
| `fit:k/OFF-12/ypc` | OFF-12 | 100.0 | 93.7 | -6% | 822 | 2016-2024 | split-half (BT-02), m:r = 25:0.211 |
| `fit:k/OFF-12/ypc_team` | OFF-12 | — | 329.6 |  | 288 | 2016-2024 | split-half (BT-02), m:r = 50:0.131, 100:0.233; variance-components cross-check k = 302.8 |
| `fit:k/OFF-13/cpoe` | OFF-13 | 60.0 | 294.2 | **+390%** | 979 | 2016-2024 | split-half (BT-02), m:r = 25:0.078 |
| `fit:k/OFF-13/cpoe_team` | OFF-13 | — | 390.8 |  | 288 | 2016-2024 | split-half (BT-02), m:r = 50:0.123, 100:0.215, 200:0.303; variance-components cross-check k = 342.4 |
| `fit:k/OFF-13/epa` | OFF-13 | 60.0 | 136.9 | **+128%** | 979 | 2016-2024 | split-half (BT-02), m:r = 25:0.154 |
| `fit:k/OFF-13/share` | OFF-13 | 60.0 | 19.8 | **-67%** | 3744 | 2016-2024 | split-half (BT-02), m:r = 25:0.563, 50:0.719, 100:0.835, 200:0.907; variance-components cross-check k = 18.8 |
| `fit:k/OFF-14/pass_share` | OFF-14 | 25.0 | 63.3 | **+153%** | 569 | 2016-2024 | split-half (BT-02), m:r = 25:0.287, 50:0.435; variance-components cross-check k = 48.7 |
| `fit:k/OFF-15/hit_rate` | OFF-15 | 200.0 | 163.6 | -18% | 288 | 2016-2024 | split-half (BT-02), m:r = 25:0.141, 50:0.235, 100:0.386, 200:0.540; variance-components cross-check k = 154.9 |
| `fit:k/OFF-15/sack_rate` | OFF-15 | 200.0 | 287.7 | +44% | 288 | 2016-2024 | split-half (BT-02), m:r = 50:0.148, 100:0.259, 200:0.409; variance-components cross-check k = 259.7 |
| `fit:k/OFF-16/stuff` | OFF-16 | 80.0 | 258.5 | **+223%** | 576 | 2016-2024 | split-half (BT-02), m:r = 25:0.084, 50:0.165; variance-components cross-check k = 223.3 |
| `fit:k/OFF-16/stuff_team` | OFF-16 | — | 272.6 |  | 288 | 2016-2024 | split-half (BT-02), m:r = 50:0.158, 100:0.265; variance-components cross-check k = 223.8 |
| `fit:k/OFF-16/success` | OFF-16 | 80.0 | 235.1 | **+194%** | 576 | 2016-2024 | split-half (BT-02), m:r = 25:0.101, 50:0.169; variance-components cross-check k = 192.7 |
| `fit:k/PLY-03/target_share` | PLY-03 | 60.0 | 10.2 | **-83%** | 7916 | 2016-2024 | split-half (BT-02), m:r = 25:0.721, 50:0.832, 100:0.902, 200:0.947; variance-components cross-check k = 8.8 |
| `fit:k/PLY-04/air_share` | PLY-04 | 60.0 | 13.4 | **-78%** | 7916 | 2016-2024 | split-half (BT-02), m:r = 25:0.651, 50:0.790, 100:0.881, 200:0.937 |
| `fit:k/PLY-04/wopr` | PLY-04 | 60.0 | 9.7756 | **-84%** | 7916 | 2016-2024 | split-half (BT-02), m:r = 25:0.729, 50:0.837, 100:0.908, 200:0.950 |
| `fit:k/PLY-05/carry_share` | PLY-05 | 40.0 | 2.6533 | **-93%** | 7541 | 2016-2024 | split-half (BT-02), m:r = 25:0.913, 50:0.948, 100:0.969, 200:0.984; variance-components cross-check k = 1.5 |
| `fit:k/PLY-06/opportunity_share` | PLY-06 | 20.0 | 7.3013 | **-63%** | 10038 | 2016-2024 | split-half (BT-02), m:r = 25:0.778, 50:0.865, 100:0.919 |
| `fit:k/PLY-06/opportunity_share_overall` | PLY-06 | — | 9.8604 |  | 8076 | 2016-2024 | split-half (BT-02), m:r = 25:0.746, 50:0.840, 100:0.905, 200:0.944, 400:0.967; variance-components cross-check k = 7.2 |
| `fit:k/PLY-07/opportunity_share` | PLY-07 | 30.0 | 11.4 | **-62%** | 11957 | 2016-2024 | split-half (BT-02), m:r = 25:0.687, 50:0.816, 100:0.896 |
| `fit:k/PLY-08/yards_per_team_dropback` | PLY-08 | 150.0 | 26.6 | **-82%** | 7932 | 2016-2024 | split-half (BT-02), m:r = 25:0.489, 50:0.652, 100:0.787, 200:0.884; variance-components cross-check k = 25.5 |
| `fit:k/PLY-09/yacoe` | PLY-09 | 60.0 | 66.6 | +11% | 563 | 2016-2024 | split-half (BT-02), m:r = 25:0.273 |
| `fit:k/PLY-10/croe` | PLY-10 | 80.0 | 228.4 | **+186%** | 1107 | 2016-2024 | split-half (BT-02), m:r = 25:0.099 |
| `fit:k/PLY-11/ryoe_per_carry` | PLY-11 | 100.0 | 198.7 | **+99%** | 335 | 2018-2024 | split-half (BT-02), m:r = 100:0.353 |
| `fit:k/PLY-16/share` | PLY-16 | 40.0 | 19.2 | **-52%** | 5464 | 2016-2024 | split-half (BT-02), m:r = 25:0.585, 50:0.706, 100:0.801 |
| `fit:k/PLY-18/adot` | PLY-18 | 80.0 | 183.7 | **+130%** | 428 | 2016-2024 | split-half (BT-02), m:r = 25:0.124, 50:0.232, 100:0.356, 200:0.453 |
| `fit:k/PLY-18/epa` | PLY-18 | 80.0 | 44.4 | -44% | 1027 | 2016-2024 | split-half (BT-02), m:r = 25:0.382, 50:0.410 |
| `fit:k/PLY-18/epa_overall` | PLY-18 | — | 387.8 |  | 428 | 2016-2024 | split-half (BT-02), m:r = 50:0.134, 100:0.201, 200:0.274 |
| `fit:k/PLY-18/share` | PLY-18 | 80.0 | 4.5469 | **-94%** | 2140 | 2016-2024 | split-half (BT-02), m:r = 25:0.848, 50:0.917, 100:0.956, 200:0.977 |
| `fit:k/PLY-19/play_action_rate` | PLY-19 | — | 93.8 |  | 158 | 2022-2024 | split-half (BT-02), m:r = 25:0.234, 50:0.347, 100:0.521, 200:0.621 |
| `fit:k/PLY-20/catchable_rate` | PLY-20 | 200.0 | 285.4 | +43% | 153 | 2022-2024 | split-half (BT-02), m:r = 100:0.259 |
| `fit:k/PLY-20/cpoe` | PLY-20 | 200.0 | 377.7 | **+89%** | 427 | 2016-2024 | split-half (BT-02), m:r = 50:0.135, 100:0.206, 200:0.228 |
| `fit:k/PLY-20/throwaway_rate` | PLY-20 | 200.0 | 240.4 | +20% | 153 | 2022-2024 | split-half (BT-02), m:r = 100:0.313, 200:0.367 |
| `fit:k/PLY-21/sack_rate` | PLY-21 | 150.0 | 229.2 | **+53%** | 438 | 2016-2024 | split-half (BT-02), m:r = 25:0.113, 50:0.200, 100:0.291, 200:0.424 |
| `fit:k/PLY-21/time_to_throw` | PLY-21 | 150.0 | 71.4 | **-52%** | 423 | 2016-2024 | split-half (BT-02), m:r = 25:0.350, 50:0.493, 100:0.618, 200:0.748 |
| `fit:k/PLY-22/scramble_rate` | PLY-22 | — | 63.1 |  | 438 | 2016-2024 | split-half (BT-02), m:r = 25:0.293, 50:0.447, 100:0.614, 200:0.743 |
| `fit:k/PLY-23/epa` | PLY-23 | 100.0 | 186.0 | **+86%** | 979 | 2016-2024 | split-half (BT-02), m:r = 25:0.123, 50:0.206 |
| `fit:k/PLY-23/epa_overall` | PLY-23 | — | 410.1 |  | 428 | 2016-2024 | split-half (BT-02), m:r = 50:0.120, 100:0.204, 200:0.251 |
| `fit:k/PLY-23/share` | PLY-23 | 100.0 | 6.6265 | **-93%** | 1712 | 2016-2024 | split-half (BT-02), m:r = 25:0.799, 50:0.884, 100:0.935, 200:0.964 |
| `fit:k/PLY-24/success_overall` | PLY-24 | — | 80.6 |  | 208 | 2022-2024 | split-half (BT-02), m:r = 25:0.237 |
| `fit:k/PLY-24/ypc_overall` | PLY-24 | — | 135.5 |  | 207 | 2022-2024 | split-half (BT-02), m:r = 25:0.156 |
| `fit:k/PLY-25/success` | PLY-25 | 60.0 | 173.0 | **+188%** | 699 | 2016-2024 | split-half (BT-02), m:r = 25:0.130, 50:0.215 |
| `fit:k/PLY-25/success_overall` | PLY-25 | — | 122.3 |  | 629 | 2016-2024 | split-half (BT-02), m:r = 25:0.192, 50:0.195, 100:0.267 |
| `fit:k/PLY-25/ypc` | PLY-25 | 60.0 | 164.0 | **+173%** | 699 | 2016-2024 | split-half (BT-02), m:r = 25:0.142, 50:0.181 |
| `fit:k/PLY-25/ypc_overall` | PLY-25 | — | 198.7 |  | 629 | 2016-2024 | split-half (BT-02), m:r = 25:0.128, 50:0.165, 100:0.307 |
| `fit:k/PLY-26/explosive` | PLY-26 | 150.0 | 213.9 | +43% | 627 | 2016-2024 | split-half (BT-02), m:r = 25:0.116, 50:0.163 |
| `fit:k/PLY-26/stuff` | PLY-26 | 100.0 | 217.0 | **+117%** | 628 | 2016-2024 | split-half (BT-02), m:r = 25:0.108, 50:0.190, 100:0.265 |
| `fit:k/PLY-27/screen_share` | PLY-27 | 40.0 | 6.0841 | **-85%** | 863 | 2022-2024 | split-half (BT-02), m:r = 25:0.804 |
| `fit:k/PLY-27/target_share` | PLY-27 | 40.0 | 10.2 | **-74%** | 7916 | 2016-2024 | split-half (BT-02), m:r = 25:0.722, 50:0.832, 100:0.902, 200:0.947; variance-components cross-check k = 8.8 |
| `fit:k/PLY-27/yacoe` | PLY-27 | 40.0 | 68.1 | **+70%** | 566 | 2016-2024 | split-half (BT-02), m:r = 25:0.269 |
| `fit:k/PLY-28/adot` | PLY-28 | 40.0 | 6.5195 | **-84%** | 1109 | 2016-2024 | split-half (BT-02), m:r = 25:0.800, 50:0.769 |
| `fit:k/PLY-28/epa_overall` | PLY-28 | — | 201.2 |  | 1108 | 2016-2024 | split-half (BT-02), m:r = 25:0.111 |
| `fit:k/PLY-28/share` | PLY-28 | 40.0 | 3.6663 | **-91%** | 5535 | 2016-2024 | split-half (BT-02), m:r = 25:0.875, 50:0.922 |
| `fit:k/PLY-29/epa_overall` | PLY-29 | — | 213.5 |  | 1110 | 2016-2024 | split-half (BT-02), m:r = 25:0.105 |
| `fit:k/PLY-29/share` | PLY-29 | 50.0 | 6.0209 | **-88%** | 4429 | 2016-2024 | split-half (BT-02), m:r = 25:0.807, 50:0.891 |
| `fit:k/PLY-30/created_reception_rate` | PLY-30 | — | 77.1 |  | 209 | 2022-2024 | split-half (BT-02), m:r = 25:0.245 |
| `fit:k/PLY-31/cushion` | PLY-31 | 80.0 | 56.1 | -30% | 709 | 2016-2024 | split-half (BT-02), m:r = 25:0.338, 50:0.498 |
| `fit:k/PLY-31/separation` | PLY-31 | 80.0 | 38.1 | **-52%** | 710 | 2016-2024 | split-half (BT-02), m:r = 25:0.438, 50:0.571 |
| `fit:k/PLY-32/end_zone_share` | PLY-32 | 15.0 | 5.4511 | **-64%** | 434 | 2016-2024 | split-half (BT-02), m:r = 25:0.821 |
| `fit:k/PLY-33/target_share` | PLY-33 | 40.0 | 9.0566 | **-77%** | 4134 | 2022-2024 | split-half (BT-02), m:r = 25:0.738, 50:0.844, 100:0.913 |
| `conventions.g3_usage_half_life_games` | G3 | 3.0000 | 8.0000 | **+167%** | 18 | 2016-2024 | next-game n-weighted squared error / prior-only, mean over 18 usage stats (ruling 2026-10-08) |
| `conventions.g3_efficiency_half_life_games` | G3 | 6.0000 | 8.0000 | +33% | 84 | 2016-2024 | next-game n-weighted squared error / prior-only, mean over 84 efficiency stats (ruling 2026-10-08) |
| `fit:G6/penalty` | G6 | — | 316.2 |  | 258261 | 2016-2024 | forward-chaining CV within each season (BT-02), efficiency h = 8 |
| `fit:COA-02/p_go/intercept` | COA-02 | — | 1.6236 |  | 30796 | 2016-2024 | logistic, four fields as linear terms (se 0.0573) |
| `fit:COA-02/p_go/ydstogo` | COA-02 | — | -0.3702 |  | 30796 | 2016-2024 | logistic, four fields as linear terms (se 0.00727) |
| `fit:COA-02/p_go/yardline_100` | COA-02 | — | -0.0224 |  | 30796 | 2016-2024 | logistic, four fields as linear terms (se 0.000792) |
| `fit:COA-02/p_go/score_differential` | COA-02 | — | -0.0563 |  | 30796 | 2016-2024 | logistic, four fields as linear terms (se 0.0023) |
| `fit:COA-02/p_go/game_seconds_remaining` | COA-02 | — | -0.000404 |  | 30796 | 2016-2024 | logistic, four fields as linear terms (se 1.97e-05) |
| `fit:k/COA-02/go_over_expected` | COA-02 | 30.0 | 119.2 | **+297%** | 288 | 2016-2024 | split-half (BT-02), m:r = 25:0.177, 50:0.283 |
| `matchup.mtc_03_ol_absence_factor` | MTC-03 | 1.1000 | 1.0375 | -6% | 9698 | 2016-2024 | offset logistic on dropbacks, exp(coef) per missing OFF-17 starter (se of log 0.0138); undamped |
| `fit:PLY-14/practice/DNP` | PLY-14 | — | 0.2066 |  | 13836 | 2016-2024 | P(played | DNP) |
| `fit:PLY-14/practice/Limited` | PLY-14 | — | 0.7009 |  | 12226 | 2016-2024 | P(played | Limited) |
| `fit:PLY-14/practice/Full` | PLY-14 | — | 0.9277 |  | 22467 | 2016-2024 | P(played | Full) |
| `fit:PRJ-06/missed/QB` | PRJ-06 | — | 0.1782 |  | 5618 | 2016-2024 | P(no snap | played last game), QB |
| `fit:PRJ-06/missed/RB` | PRJ-06 | — | 0.1281 |  | 14391 | 2016-2024 | P(no snap | played last game), RB |
| `fit:PRJ-06/missed/WR` | PRJ-06 | — | 0.1119 |  | 22012 | 2016-2024 | P(no snap | played last game), WR |
| `fit:PRJ-06/missed/TE` | PRJ-06 | — | 0.0879 |  | 13317 | 2016-2024 | P(no snap | played last game), TE |
| `player.ply_14_return_factor` | PLY-14 | 0.8500 | 0.9238 | +9% | 1161 | 2016-2024 | sum first-game-back snap share / sum baseline (usage h = 8) |
| `fit:role/PLY-01/snap_share/all/QB1` | PLY-01 | — | 0.8744 |  | 529 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/RB1` | PLY-01 | — | 0.5315 |  | 617 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/RB2` | PLY-01 | — | 0.2948 |  | 861 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/TE1` | PLY-01 | — | 0.6393 |  | 567 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR1` | PLY-01 | — | 0.7471 |  | 660 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR2` | PLY-01 | — | 0.6663 |  | 923 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-01/snap_share/all/WR3` | PLY-01 | — | 0.5149 |  | 1108 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/QB1` | PLY-02 | — | 0.8744 |  | 529 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/RB1` | PLY-02 | — | 0.5315 |  | 617 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/RB2` | PLY-02 | — | 0.2948 |  | 861 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/TE1` | PLY-02 | — | 0.6393 |  | 567 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR1` | PLY-02 | — | 0.7471 |  | 660 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR2` | PLY-02 | — | 0.6663 |  | 923 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-02/snap_share/all/WR3` | PLY-02 | — | 0.5149 |  | 1108 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/QB1` | PLY-03 | — | 0.000559 |  | 529 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/RB1` | PLY-03 | — | 0.1042 |  | 617 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/RB2` | PLY-03 | — | 0.0627 |  | 861 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/TE1` | PLY-03 | — | 0.1347 |  | 567 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR1` | PLY-03 | — | 0.2195 |  | 660 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR2` | PLY-03 | — | 0.1686 |  | 923 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-03/target_share/all/WR3` | PLY-03 | — | 0.1176 |  | 1108 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/QB1` | PLY-04 | — | 5.44e-05 |  | 529 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/RB1` | PLY-04 | — | 0.00276 |  | 617 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/RB2` | PLY-04 | — | 0.003 |  | 861 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/TE1` | PLY-04 | — | 0.1248 |  | 567 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR1` | PLY-04 | — | 0.3037 |  | 660 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR2` | PLY-04 | — | 0.2273 |  | 923 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/air_share/all/WR3` | PLY-04 | — | 0.1512 |  | 1108 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/QB1` | PLY-04 | — | 0.000877 |  | 529 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/RB1` | PLY-04 | — | 0.1583 |  | 617 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/RB2` | PLY-04 | — | 0.0961 |  | 861 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/TE1` | PLY-04 | — | 0.2894 |  | 567 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR1` | PLY-04 | — | 0.5418 |  | 660 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR2` | PLY-04 | — | 0.4121 |  | 923 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-04/wopr/all/WR3` | PLY-04 | — | 0.2822 |  | 1108 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/QB1` | PLY-05 | — | 0.0536 |  | 529 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/RB1` | PLY-05 | — | 0.5479 |  | 617 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/RB2` | PLY-05 | — | 0.2595 |  | 861 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/TE1` | PLY-05 | — | 0.000989 |  | 567 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR1` | PLY-05 | — | 0.00775 |  | 660 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR2` | PLY-05 | — | 0.00761 |  | 923 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-05/carry_share/all/WR3` | PLY-05 | — | 0.00694 |  | 1108 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/QB1` | PLY-06 | — | 0.0239 |  | 529 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/RB1` | PLY-06 | — | 0.2896 |  | 617 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/RB2` | PLY-06 | — | 0.1467 |  | 861 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/TE1` | PLY-06 | — | 0.0781 |  | 567 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR1` | PLY-06 | — | 0.1296 |  | 660 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR2` | PLY-06 | — | 0.1004 |  | 923 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-06/opportunity_share_overall/all/WR3` | PLY-06 | — | 0.0713 |  | 1108 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-08/yards_per_team_dropback/all/QB1` | PLY-08 | — | 0.000961 |  | 529 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/RB1` | PLY-08 | — | 0.5444 |  | 617 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/RB2` | PLY-08 | — | 0.3050 |  | 861 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/TE1` | PLY-08 | — | 0.8839 |  | 567 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR1` | PLY-08 | — | 1.6050 |  | 660 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR2` | PLY-08 | — | 1.1802 |  | 923 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-08/yards_per_team_dropback/all/WR3` | PLY-08 | — | 0.7966 |  | 1108 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/QB1` | PLY-18 | — | 7.9692 |  | 523 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/WR1` | PLY-18 | — | 12.8 |  | 58 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/WR2` | PLY-18 | — | 14.5 |  | 40 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/adot/all/WR3` | PLY-18 | — | 13.4 |  | 31 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/QB1` | PLY-18 | — | 0.1612 |  | 523 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/WR1` | PLY-18 | — | 0.5317 |  | 58 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/WR2` | PLY-18 | — | 0.4242 |  | 40 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/epa_overall/all/WR3` | PLY-18 | — | -0.0345 |  | 31 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-18/share/behind/QB1` | PLY-18 | — | 0.1623 |  | 523 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/behind/WR1` | PLY-18 | — | 0.1290 |  | 58 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/behind/WR2` | PLY-18 | — | 0.2143 |  | 40 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/behind/WR3` | PLY-18 | — | 0.2344 |  | 31 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/QB1` | PLY-18 | — | 0.1188 |  | 523 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/WR1` | PLY-18 | — | 0.2609 |  | 58 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/WR2` | PLY-18 | — | 0.3776 |  | 40 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/deep/WR3` | PLY-18 | — | 0.3750 |  | 31 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/QB1` | PLY-18 | — | 0.2117 |  | 523 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/WR1` | PLY-18 | — | 0.3580 |  | 58 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/WR2` | PLY-18 | — | 0.2653 |  | 40 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/intermediate/WR3` | PLY-18 | — | 0.2188 |  | 31 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/QB1` | PLY-18 | — | 0.5071 |  | 523 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/WR1` | PLY-18 | — | 0.2522 |  | 58 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/WR2` | PLY-18 | — | 0.1429 |  | 40 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/short/WR3` | PLY-18 | — | 0.1719 |  | 31 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/QB1` | PLY-18 | — | 0.000108 |  | 523 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/WR1` | PLY-18 | — | 0 |  | 58 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/WR2` | PLY-18 | — | 0 |  | 40 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-18/share/unknown/WR3` | PLY-18 | — | 0 |  | 31 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/epa_overall/all/QB1` | PLY-23 | — | 0.1612 |  | 523 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/epa_overall/all/WR1` | PLY-23 | — | 0.5317 |  | 58 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/epa_overall/all/WR2` | PLY-23 | — | 0.4242 |  | 40 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/epa_overall/all/WR3` | PLY-23 | — | -0.0345 |  | 31 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-23/share/left/QB1` | PLY-23 | — | 0.3735 |  | 523 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/left/WR1` | PLY-23 | — | 0.2333 |  | 58 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/left/WR2` | PLY-23 | — | 0.2551 |  | 40 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/left/WR3` | PLY-23 | — | 0.3594 |  | 31 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/QB1` | PLY-23 | — | 0.2208 |  | 523 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/WR1` | PLY-23 | — | 0.0435 |  | 58 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/WR2` | PLY-23 | — | 0.0204 |  | 40 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/middle/WR3` | PLY-23 | — | 0 |  | 31 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/QB1` | PLY-23 | — | 0.4055 |  | 523 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/WR1` | PLY-23 | — | 0.7232 |  | 58 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/WR2` | PLY-23 | — | 0.7245 |  | 40 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/right/WR3` | PLY-23 | — | 0.6406 |  | 31 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/QB1` | PLY-23 | — | 0.000234 |  | 523 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/WR1` | PLY-23 | — | 0 |  | 58 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/WR2` | PLY-23 | — | 0 |  | 40 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-23/share/unknown/WR3` | PLY-23 | — | 0 |  | 31 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-24/success_overall/all/QB1` | PLY-24 | — | 0.5548 |  | 174 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/RB1` | PLY-24 | — | 0.3972 |  | 196 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/RB2` | PLY-24 | — | 0.4060 |  | 272 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/TE1` | PLY-24 | — | 0.6000 |  | 31 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/WR1` | PLY-24 | — | 0.5084 |  | 89 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/WR2` | PLY-24 | — | 0.4650 |  | 87 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/success_overall/all/WR3` | PLY-24 | — | 0.5593 |  | 100 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/QB1` | PLY-24 | — | 3.6853 |  | 174 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/RB1` | PLY-24 | — | 4.3878 |  | 196 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/RB2` | PLY-24 | — | 4.2828 |  | 272 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/TE1` | PLY-24 | — | 2.1455 |  | 31 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/WR1` | PLY-24 | — | 5.0112 |  | 89 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/WR2` | PLY-24 | — | 5.6231 |  | 87 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-24/ypc_overall/all/WR3` | PLY-24 | — | 7.0678 |  | 100 | 2022-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/QB1` | PLY-25 | — | 0.5401 |  | 455 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/RB1` | PLY-25 | — | 0.3913 |  | 605 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/RB2` | PLY-25 | — | 0.3938 |  | 822 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/TE1` | PLY-25 | — | 0.5818 |  | 61 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR1` | PLY-25 | — | 0.5106 |  | 250 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR2` | PLY-25 | — | 0.5164 |  | 266 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/success_overall/all/WR3` | PLY-25 | — | 0.5395 |  | 276 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/QB1` | PLY-25 | — | 3.8531 |  | 455 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/RB1` | PLY-25 | — | 4.3209 |  | 605 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/RB2` | PLY-25 | — | 4.2509 |  | 822 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/TE1` | PLY-25 | — | 3.0182 |  | 61 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR1` | PLY-25 | — | 5.7813 |  | 250 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR2` | PLY-25 | — | 5.9637 |  | 266 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-25/ypc_overall/all/WR3` | PLY-25 | — | 6.4813 |  | 276 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-27/screen_share/all/QB1` | PLY-27 | — | 0.000211 |  | 192 | 2022-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/RB1` | PLY-27 | — | 0.2411 |  | 197 | 2022-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/RB2` | PLY-27 | — | 0.1251 |  | 285 | 2022-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/TE1` | PLY-27 | — | 0.0828 |  | 183 | 2022-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/WR1` | PLY-27 | — | 0.1689 |  | 226 | 2022-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/WR2` | PLY-27 | — | 0.1188 |  | 308 | 2022-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/screen_share/all/WR3` | PLY-27 | — | 0.0928 |  | 378 | 2022-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/QB1` | PLY-27 | — | 0.000559 |  | 529 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/RB1` | PLY-27 | — | 0.1042 |  | 617 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/RB2` | PLY-27 | — | 0.0627 |  | 861 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/TE1` | PLY-27 | — | 0.1347 |  | 567 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR1` | PLY-27 | — | 0.2195 |  | 660 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR2` | PLY-27 | — | 0.1686 |  | 923 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/target_share/all/WR3` | PLY-27 | — | 0.1176 |  | 1108 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/QB1` | PLY-27 | — | -3.1846 |  | 47 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/RB1` | PLY-27 | — | 0.5001 |  | 574 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/RB2` | PLY-27 | — | 0.3027 |  | 727 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/TE1` | PLY-27 | — | 0.1785 |  | 513 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR1` | PLY-27 | — | -0.4421 |  | 630 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR2` | PLY-27 | — | -0.4440 |  | 875 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-27/yacoe/all/WR3` | PLY-27 | — | -0.5385 |  | 992 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/adot/all/QB1` | PLY-28 | — | 1.2329 |  | 66 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/RB1` | PLY-28 | — | 0.4031 |  | 584 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/RB2` | PLY-28 | — | 0.5640 |  | 757 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/TE1` | PLY-28 | — | 7.2487 |  | 532 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR1` | PLY-28 | — | 11.0 |  | 648 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR2` | PLY-28 | — | 10.8 |  | 899 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/adot/all/WR3` | PLY-28 | — | 10.3 |  | 1036 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/QB1` | PLY-28 | — | -0.3029 |  | 66 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/RB1` | PLY-28 | — | 0.0385 |  | 584 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/RB2` | PLY-28 | — | -0.00797 |  | 757 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/TE1` | PLY-28 | — | 0.2163 |  | 532 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR1` | PLY-28 | — | 0.2861 |  | 648 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR2` | PLY-28 | — | 0.2414 |  | 899 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/epa_overall/all/WR3` | PLY-28 | — | 0.2007 |  | 1036 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-28/share/behind/QB1` | PLY-28 | — | 0.4521 |  | 66 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/RB1` | PLY-28 | — | 0.4474 |  | 584 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/RB2` | PLY-28 | — | 0.4337 |  | 757 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/TE1` | PLY-28 | — | 0.1024 |  | 532 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR1` | PLY-28 | — | 0.0849 |  | 648 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR2` | PLY-28 | — | 0.0838 |  | 899 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/behind/WR3` | PLY-28 | — | 0.1062 |  | 1036 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/QB1` | PLY-28 | — | 0.0137 |  | 66 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/RB1` | PLY-28 | — | 0.0149 |  | 584 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/RB2` | PLY-28 | — | 0.0164 |  | 757 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/TE1` | PLY-28 | — | 0.0750 |  | 532 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR1` | PLY-28 | — | 0.1729 |  | 648 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR2` | PLY-28 | — | 0.1727 |  | 899 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/deep/WR3` | PLY-28 | — | 0.1628 |  | 1036 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/QB1` | PLY-28 | — | 0.1781 |  | 66 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/RB1` | PLY-28 | — | 0.0261 |  | 584 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/RB2` | PLY-28 | — | 0.0271 |  | 757 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/TE1` | PLY-28 | — | 0.2125 |  | 532 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR1` | PLY-28 | — | 0.2925 |  | 648 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR2` | PLY-28 | — | 0.2710 |  | 899 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/intermediate/WR3` | PLY-28 | — | 0.2505 |  | 1036 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/QB1` | PLY-28 | — | 0.3562 |  | 66 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/RB1` | PLY-28 | — | 0.5113 |  | 584 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/RB2` | PLY-28 | — | 0.5227 |  | 757 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/TE1` | PLY-28 | — | 0.6100 |  | 532 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR1` | PLY-28 | — | 0.4497 |  | 648 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR2` | PLY-28 | — | 0.4724 |  | 899 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/short/WR3` | PLY-28 | — | 0.4804 |  | 1036 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/QB1` | PLY-28 | — | 0 |  | 66 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/RB1` | PLY-28 | — | 0.000292 |  | 584 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/RB2` | PLY-28 | — | 0 |  | 757 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/TE1` | PLY-28 | — | 0 |  | 532 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR1` | PLY-28 | — | 2.09e-05 |  | 648 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR2` | PLY-28 | — | 0 |  | 899 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-28/share/unknown/WR3` | PLY-28 | — | 0.000118 |  | 1036 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/epa_overall/all/QB1` | PLY-29 | — | -0.3029 |  | 66 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/RB1` | PLY-29 | — | 0.0385 |  | 584 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/RB2` | PLY-29 | — | -0.00797 |  | 757 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/TE1` | PLY-29 | — | 0.2163 |  | 532 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR1` | PLY-29 | — | 0.2861 |  | 648 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR2` | PLY-29 | — | 0.2414 |  | 899 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/epa_overall/all/WR3` | PLY-29 | — | 0.2007 |  | 1036 | 2016-2024 | section 4 slot prior: pooled over slot occupants' units |
| `fit:role/PLY-29/share/left/QB1` | PLY-29 | — | 0.3288 |  | 66 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/RB1` | PLY-29 | — | 0.4066 |  | 584 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/RB2` | PLY-29 | — | 0.4074 |  | 757 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/TE1` | PLY-29 | — | 0.3215 |  | 532 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR1` | PLY-29 | — | 0.3941 |  | 648 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR2` | PLY-29 | — | 0.3751 |  | 899 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/left/WR3` | PLY-29 | — | 0.3764 |  | 1036 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/QB1` | PLY-29 | — | 0.3014 |  | 66 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/RB1` | PLY-29 | — | 0.1877 |  | 584 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/RB2` | PLY-29 | — | 0.1863 |  | 757 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/TE1` | PLY-29 | — | 0.2695 |  | 532 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR1` | PLY-29 | — | 0.2204 |  | 648 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR2` | PLY-29 | — | 0.2278 |  | 899 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/middle/WR3` | PLY-29 | — | 0.2244 |  | 1036 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/QB1` | PLY-29 | — | 0.3699 |  | 66 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/RB1` | PLY-29 | — | 0.4055 |  | 584 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/RB2` | PLY-29 | — | 0.4063 |  | 757 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/TE1` | PLY-29 | — | 0.4089 |  | 532 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR1` | PLY-29 | — | 0.3855 |  | 648 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR2` | PLY-29 | — | 0.3971 |  | 899 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/right/WR3` | PLY-29 | — | 0.3991 |  | 1036 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/QB1` | PLY-29 | — | 0 |  | 66 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/RB1` | PLY-29 | — | 0.000292 |  | 584 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/RB2` | PLY-29 | — | 0 |  | 757 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/TE1` | PLY-29 | — | 0.000118 |  | 532 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR1` | PLY-29 | — | 5.08e-05 |  | 648 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR2` | PLY-29 | — | 2.7e-05 |  | 899 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |
| `fit:role/PLY-29/share/unknown/WR3` | PLY-29 | — | 0.000152 |  | 1036 | 2016-2024 | section 4 slot prior: mean over slot occupants' games of his game share |

## Moved more than 50% from the initial guess

| window | key | initial | fitted | change | n |
|---|---|---|---|---|---|
| S2021 | `fit:k/COA-04/seconds_per_play` | 80.0 | 20.6 | **-74%** | 228 |
| S2021 | `fit:k/DEF-01/epa/all` | 250.0 | 722.7 | **+189%** | 160 |
| S2021 | `fit:k/DEF-01/epa/pass` | 200.0 | 669.9 | **+235%** | 160 |
| S2021 | `fit:k/DEF-01/epa/run` | 300.0 | 485.2 | **+62%** | 160 |
| S2021 | `fit:k/DEF-02/success` | 150.0 | 236.6 | **+58%** | 480 |
| S2021 | `fit:k/DEF-03/success` | 60.0 | 141.1 | **+135%** | 399 |
| S2021 | `fit:k/DEF-03/ypc` | 100.0 | 158.9 | **+59%** | 399 |
| S2021 | `fit:k/DEF-04/epa_diff` | 60.0 | 452.7 | **+654%** | 480 |
| S2021 | `fit:k/DEF-06/explosive` | 300.0 | 1,058 | **+253%** | 160 |
| S2021 | `fit:k/DEF-06/explosive_run` | 300.0 | 470.0 | **+57%** | 160 |
| S2021 | `fit:k/DEF-09/epa` | 60.0 | 199.1 | **+232%** | 508 |
| S2021 | `fit:k/DEF-15/success` | 60.0 | 312.6 | **+421%** | 320 |
| S2021 | `fit:k/DEF-15/ypc` | 60.0 | 291.5 | **+386%** | 320 |
| S2021 | `fit:k/DEF-17/sacks` | 20.0 | 9.9557 | **-50%** | 211 |
| S2021 | `fit:k/OFF-03/epa` | 100.0 | 272.8 | **+173%** | 559 |
| S2021 | `fit:k/OFF-03/success` | 100.0 | 219.4 | **+119%** | 559 |
| S2021 | `fit:k/OFF-04/pass_rate` | 60.0 | 111.0 | **+85%** | 160 |
| S2021 | `fit:k/OFF-09/shotgun_rate` | 60.0 | 18.9 | **-69%** | 160 |
| S2021 | `fit:k/OFF-12/success` | 60.0 | 164.0 | **+173%** | 411 |
| S2021 | `fit:k/OFF-13/epa` | 60.0 | 133.7 | **+123%** | 538 |
| S2021 | `fit:k/OFF-13/share` | 60.0 | 19.5 | **-67%** | 2080 |
| S2021 | `fit:k/OFF-14/pass_share` | 25.0 | 80.1 | **+221%** | 305 |
| S2021 | `fit:k/OFF-15/sack_rate` | 200.0 | 318.0 | **+59%** | 160 |
| S2021 | `fit:k/OFF-16/stuff` | 80.0 | 190.8 | **+138%** | 320 |
| S2021 | `fit:k/OFF-16/success` | 80.0 | 252.8 | **+216%** | 320 |
| S2021 | `fit:k/PLY-03/target_share` | 60.0 | 10.5 | **-82%** | 4295 |
| S2021 | `fit:k/PLY-04/air_share` | 60.0 | 13.5 | **-77%** | 4295 |
| S2021 | `fit:k/PLY-04/wopr` | 60.0 | 10.1 | **-83%** | 4295 |
| S2021 | `fit:k/PLY-05/carry_share` | 40.0 | 2.6059 | **-93%** | 4069 |
| S2021 | `fit:k/PLY-06/opportunity_share` | 20.0 | 7.6926 | **-62%** | 5381 |
| S2021 | `fit:k/PLY-07/opportunity_share` | 30.0 | 11.4 | **-62%** | 6486 |
| S2021 | `fit:k/PLY-08/yards_per_team_dropback` | 150.0 | 27.7 | **-82%** | 4292 |
| S2021 | `fit:k/PLY-10/croe` | 80.0 | 199.5 | **+149%** | 610 |
| S2021 | `fit:k/PLY-16/share` | 40.0 | 18.2 | **-54%** | 2989 |
| S2021 | `fit:k/PLY-18/adot` | 80.0 | 180.3 | **+125%** | 229 |
| S2021 | `fit:k/PLY-18/share` | 80.0 | 4.3002 | **-95%** | 1145 |
| S2021 | `fit:k/PLY-21/sack_rate` | 150.0 | 236.0 | **+57%** | 232 |
| S2021 | `fit:k/PLY-23/epa` | 100.0 | 165.0 | **+65%** | 535 |
| S2021 | `fit:k/PLY-23/share` | 100.0 | 6.9106 | **-93%** | 916 |
| S2021 | `fit:k/PLY-25/success` | 60.0 | 166.1 | **+177%** | 364 |
| S2021 | `fit:k/PLY-25/ypc` | 60.0 | 153.7 | **+156%** | 362 |
| S2021 | `fit:k/PLY-26/explosive` | 150.0 | 253.7 | **+69%** | 348 |
| S2021 | `fit:k/PLY-26/stuff` | 100.0 | 171.0 | **+71%** | 349 |
| S2021 | `fit:k/PLY-27/target_share` | 40.0 | 10.6 | **-74%** | 4295 |
| S2021 | `fit:k/PLY-27/yacoe` | 40.0 | 82.6 | **+106%** | 302 |
| S2021 | `fit:k/PLY-28/adot` | 40.0 | 6.6059 | **-83%** | 609 |
| S2021 | `fit:k/PLY-28/share` | 40.0 | 3.5610 | **-91%** | 3042 |
| S2021 | `fit:k/PLY-29/share` | 50.0 | 6.2147 | **-88%** | 2439 |
| S2021 | `fit:k/PLY-32/end_zone_share` | 15.0 | 5.6124 | **-63%** | 291 |
| S2021 | `conventions.g3_usage_half_life_games` | 3.0000 | 8.0000 | **+167%** | 16 |
| S2021 | `conventions.g3_efficiency_half_life_games` | 6.0000 | 12.0 | **+100%** | 63 |
| S2022 | `fit:k/COA-04/seconds_per_play` | 80.0 | 20.2 | **-75%** | 281 |
| S2022 | `fit:k/DEF-01/epa/all` | 250.0 | 792.6 | **+217%** | 192 |
| S2022 | `fit:k/DEF-01/epa/pass` | 200.0 | 716.2 | **+258%** | 192 |
| S2022 | `fit:k/DEF-01/epa/run` | 300.0 | 513.8 | **+71%** | 192 |
| S2022 | `fit:k/DEF-02/success` | 150.0 | 247.8 | **+65%** | 576 |
| S2022 | `fit:k/DEF-03/success` | 60.0 | 140.4 | **+134%** | 499 |
| S2022 | `fit:k/DEF-04/epa_diff` | 60.0 | 513.3 | **+755%** | 576 |
| S2022 | `fit:k/DEF-04/receptions` | 60.0 | 310.1 | **+417%** | 576 |
| S2022 | `fit:k/DEF-04/targets` | 60.0 | 351.7 | **+486%** | 576 |
| S2022 | `fit:k/DEF-04/yards` | 60.0 | 323.3 | **+439%** | 576 |
| S2022 | `fit:k/DEF-06/explosive` | 300.0 | 1,218 | **+306%** | 192 |
| S2022 | `fit:k/DEF-06/explosive_run` | 300.0 | 486.4 | **+62%** | 192 |
| S2022 | `fit:k/DEF-09/epa` | 60.0 | 197.9 | **+230%** | 615 |
| S2022 | `fit:k/DEF-15/success` | 60.0 | 310.1 | **+417%** | 384 |
| S2022 | `fit:k/DEF-15/ypc` | 60.0 | 314.1 | **+423%** | 384 |
| S2022 | `fit:k/DEF-17/sacks` | 20.0 | 8.2754 | **-59%** | 263 |
| S2022 | `fit:k/OFF-03/epa` | 100.0 | 310.8 | **+211%** | 670 |
| S2022 | `fit:k/OFF-03/success` | 100.0 | 225.1 | **+125%** | 671 |
| S2022 | `fit:k/OFF-04/pass_rate` | 60.0 | 114.9 | **+92%** | 192 |
| S2022 | `fit:k/OFF-09/shotgun_rate` | 60.0 | 18.9 | **-69%** | 192 |
| S2022 | `fit:k/OFF-12/epa` | 100.0 | 173.7 | **+74%** | 506 |
| S2022 | `fit:k/OFF-12/explosive` | 150.0 | 73.2 | **-51%** | 506 |
| S2022 | `fit:k/OFF-12/success` | 60.0 | 163.4 | **+172%** | 505 |
| S2022 | `fit:k/OFF-13/epa` | 60.0 | 154.6 | **+158%** | 643 |
| S2022 | `fit:k/OFF-13/share` | 60.0 | 19.4 | **-68%** | 2496 |
| S2022 | `fit:k/OFF-14/pass_share` | 25.0 | 82.0 | **+228%** | 372 |
| S2022 | `fit:k/OFF-15/sack_rate` | 200.0 | 318.9 | **+59%** | 192 |
| S2022 | `fit:k/OFF-16/stuff` | 80.0 | 206.2 | **+158%** | 384 |
| S2022 | `fit:k/OFF-16/success` | 80.0 | 205.2 | **+156%** | 384 |
| S2022 | `fit:k/PLY-03/target_share` | 60.0 | 10.6 | **-82%** | 5226 |
| S2022 | `fit:k/PLY-04/air_share` | 60.0 | 13.6 | **-77%** | 5226 |
| S2022 | `fit:k/PLY-04/wopr` | 60.0 | 10.1 | **-83%** | 5226 |
| S2022 | `fit:k/PLY-05/carry_share` | 40.0 | 2.6839 | **-93%** | 4955 |
| S2022 | `fit:k/PLY-06/opportunity_share` | 20.0 | 7.7053 | **-61%** | 6592 |
| S2022 | `fit:k/PLY-07/opportunity_share` | 30.0 | 11.4 | **-62%** | 7869 |
| S2022 | `fit:k/PLY-08/yards_per_team_dropback` | 150.0 | 27.5 | **-82%** | 5228 |
| S2022 | `fit:k/PLY-10/croe` | 80.0 | 228.9 | **+186%** | 733 |
| S2022 | `fit:k/PLY-16/share` | 40.0 | 18.5 | **-54%** | 3660 |
| S2022 | `fit:k/PLY-18/adot` | 80.0 | 192.3 | **+140%** | 275 |
| S2022 | `fit:k/PLY-18/share` | 80.0 | 4.3576 | **-95%** | 1375 |
| S2022 | `fit:k/PLY-20/cpoe` | 200.0 | 334.4 | **+67%** | 275 |
| S2022 | `fit:k/PLY-21/sack_rate` | 150.0 | 241.2 | **+61%** | 280 |
| S2022 | `fit:k/PLY-23/epa` | 100.0 | 179.0 | **+79%** | 640 |
| S2022 | `fit:k/PLY-23/share` | 100.0 | 6.8242 | **-93%** | 1100 |
| S2022 | `fit:k/PLY-25/success` | 60.0 | 165.8 | **+176%** | 442 |
| S2022 | `fit:k/PLY-25/ypc` | 60.0 | 155.0 | **+158%** | 440 |
| S2022 | `fit:k/PLY-26/explosive` | 150.0 | 259.9 | **+73%** | 420 |
| S2022 | `fit:k/PLY-26/stuff` | 100.0 | 185.7 | **+86%** | 421 |
| S2022 | `fit:k/PLY-27/target_share` | 40.0 | 10.6 | **-73%** | 5226 |
| S2022 | `fit:k/PLY-27/yacoe` | 40.0 | 65.1 | **+63%** | 365 |
| S2022 | `fit:k/PLY-28/adot` | 40.0 | 6.7450 | **-83%** | 732 |
| S2022 | `fit:k/PLY-28/share` | 40.0 | 3.5746 | **-91%** | 3654 |
| S2022 | `fit:k/PLY-29/share` | 50.0 | 6.1488 | **-88%** | 2929 |
| S2022 | `fit:k/PLY-31/separation` | 80.0 | 39.3 | **-51%** | 480 |
| S2022 | `fit:k/PLY-32/end_zone_share` | 15.0 | 5.5862 | **-63%** | 335 |
| S2022 | `conventions.g3_usage_half_life_games` | 3.0000 | 8.0000 | **+167%** | 16 |
| S2022 | `conventions.g3_efficiency_half_life_games` | 6.0000 | 12.0 | **+100%** | 66 |
| S2023 | `fit:k/COA-04/seconds_per_play` | 80.0 | 20.2 | **-75%** | 326 |
| S2023 | `fit:k/DEF-01/epa/all` | 250.0 | 906.9 | **+263%** | 224 |
| S2023 | `fit:k/DEF-01/epa/pass` | 200.0 | 789.1 | **+295%** | 224 |
| S2023 | `fit:k/DEF-01/epa/run` | 300.0 | 578.6 | **+93%** | 224 |
| S2023 | `fit:k/DEF-02/success` | 150.0 | 273.7 | **+82%** | 672 |
| S2023 | `fit:k/DEF-03/success` | 60.0 | 153.5 | **+156%** | 614 |
| S2023 | `fit:k/DEF-04/epa_diff` | 60.0 | 607.4 | **+912%** | 672 |
| S2023 | `fit:k/DEF-04/receptions` | 60.0 | 326.7 | **+445%** | 672 |
| S2023 | `fit:k/DEF-04/targets` | 60.0 | 385.7 | **+543%** | 672 |
| S2023 | `fit:k/DEF-04/yards` | 60.0 | 332.4 | **+454%** | 672 |
| S2023 | `fit:k/DEF-05/hit_rate` | 150.0 | 957.2 | **+538%** | 224 |
| S2023 | `fit:k/DEF-06/explosive` | 300.0 | 1,159 | **+286%** | 224 |
| S2023 | `fit:k/DEF-06/explosive_run` | 300.0 | 491.5 | **+64%** | 224 |
| S2023 | `fit:k/DEF-09/epa` | 60.0 | 215.0 | **+258%** | 718 |
| S2023 | `fit:k/DEF-15/success` | 60.0 | 305.3 | **+409%** | 448 |
| S2023 | `fit:k/DEF-15/ypc` | 60.0 | 280.9 | **+368%** | 448 |
| S2023 | `fit:k/DEF-17/sacks` | 20.0 | 8.7235 | **-56%** | 324 |
| S2023 | `fit:k/OFF-03/epa` | 100.0 | 291.2 | **+191%** | 782 |
| S2023 | `fit:k/OFF-03/success` | 100.0 | 213.9 | **+114%** | 783 |
| S2023 | `fit:k/OFF-04/pass_rate` | 60.0 | 104.9 | **+75%** | 224 |
| S2023 | `fit:k/OFF-07/motion_rate` | 80.0 | 32.2 | **-60%** | 32 |
| S2023 | `fit:k/OFF-08/rpo_rate` | 80.0 | 133.4 | **+67%** | 32 |
| S2023 | `fit:k/OFF-09/shotgun_rate` | 60.0 | 19.1 | **-68%** | 224 |
| S2023 | `fit:k/OFF-10/seconds_per_play` | 80.0 | 38.2 | **-52%** | 224 |
| S2023 | `fit:k/OFF-12/epa` | 100.0 | 186.9 | **+87%** | 616 |
| S2023 | `fit:k/OFF-12/explosive` | 150.0 | 74.7 | **-50%** | 617 |
| S2023 | `fit:k/OFF-12/success` | 60.0 | 126.5 | **+111%** | 616 |
| S2023 | `fit:k/OFF-13/epa` | 60.0 | 142.2 | **+137%** | 756 |
| S2023 | `fit:k/OFF-13/share` | 60.0 | 19.5 | **-67%** | 2912 |
| S2023 | `fit:k/OFF-14/pass_share` | 25.0 | 70.8 | **+183%** | 438 |
| S2023 | `fit:k/OFF-15/sack_rate` | 200.0 | 303.8 | **+52%** | 224 |
| S2023 | `fit:k/OFF-16/stuff` | 80.0 | 228.7 | **+186%** | 448 |
| S2023 | `fit:k/OFF-16/success` | 80.0 | 232.1 | **+190%** | 448 |
| S2023 | `fit:k/PLY-03/target_share` | 60.0 | 10.5 | **-83%** | 6123 |
| S2023 | `fit:k/PLY-04/air_share` | 60.0 | 13.6 | **-77%** | 6123 |
| S2023 | `fit:k/PLY-04/wopr` | 60.0 | 10.0 | **-83%** | 6123 |
| S2023 | `fit:k/PLY-05/carry_share` | 40.0 | 2.6841 | **-93%** | 5827 |
| S2023 | `fit:k/PLY-06/opportunity_share` | 20.0 | 7.6616 | **-62%** | 7701 |
| S2023 | `fit:k/PLY-07/opportunity_share` | 30.0 | 11.4 | **-62%** | 9238 |
| S2023 | `fit:k/PLY-08/yards_per_team_dropback` | 150.0 | 27.3 | **-82%** | 6135 |
| S2023 | `fit:k/PLY-10/croe` | 80.0 | 250.3 | **+213%** | 853 |
| S2023 | `fit:k/PLY-16/share` | 40.0 | 18.9 | **-53%** | 4276 |
| S2023 | `fit:k/PLY-18/adot` | 80.0 | 186.4 | **+133%** | 329 |
| S2023 | `fit:k/PLY-18/share` | 80.0 | 4.4118 | **-94%** | 1645 |
| S2023 | `fit:k/PLY-20/cpoe` | 200.0 | 358.7 | **+79%** | 328 |
| S2023 | `fit:k/PLY-21/sack_rate` | 150.0 | 251.6 | **+68%** | 337 |
| S2023 | `fit:k/PLY-21/time_to_throw` | 150.0 | 73.4 | **-51%** | 324 |
| S2023 | `fit:k/PLY-23/epa` | 100.0 | 191.3 | **+91%** | 754 |
| S2023 | `fit:k/PLY-23/share` | 100.0 | 6.7670 | **-93%** | 1316 |
| S2023 | `fit:k/PLY-25/success` | 60.0 | 174.5 | **+191%** | 532 |
| S2023 | `fit:k/PLY-25/ypc` | 60.0 | 156.5 | **+161%** | 531 |
| S2023 | `fit:k/PLY-26/explosive` | 150.0 | 227.8 | **+52%** | 494 |
| S2023 | `fit:k/PLY-26/stuff` | 100.0 | 192.8 | **+93%** | 495 |
| S2023 | `fit:k/PLY-27/screen_share` | 40.0 | 6.5814 | **-84%** | 210 |
| S2023 | `fit:k/PLY-27/target_share` | 40.0 | 10.5 | **-74%** | 6123 |
| S2023 | `fit:k/PLY-27/yacoe` | 40.0 | 63.7 | **+59%** | 434 |
| S2023 | `fit:k/PLY-28/adot` | 40.0 | 6.6241 | **-83%** | 853 |
| S2023 | `fit:k/PLY-28/share` | 40.0 | 3.6118 | **-91%** | 4257 |
| S2023 | `fit:k/PLY-29/share` | 50.0 | 6.1230 | **-88%** | 3411 |
| S2023 | `fit:k/PLY-32/end_zone_share` | 15.0 | 5.4677 | **-64%** | 363 |
| S2023 | `fit:k/PLY-33/target_share` | 40.0 | 8.8767 | **-78%** | 1323 |
| S2023 | `conventions.g3_usage_half_life_games` | 3.0000 | 8.0000 | **+167%** | 18 |
| S2023 | `fit:k/COA-02/go_over_expected` | 30.0 | 120.6 | **+302%** | 224 |
| S2024 | `fit:k/COA-04/seconds_per_play` | 80.0 | 22.8 | **-71%** | 376 |
| S2024 | `fit:k/DEF-01/epa/all` | 250.0 | 986.1 | **+294%** | 256 |
| S2024 | `fit:k/DEF-01/epa/pass` | 200.0 | 821.5 | **+311%** | 256 |
| S2024 | `fit:k/DEF-01/epa/run` | 300.0 | 648.3 | **+116%** | 256 |
| S2024 | `fit:k/DEF-02/success` | 150.0 | 285.6 | **+90%** | 768 |
| S2024 | `fit:k/DEF-03/success` | 60.0 | 171.8 | **+186%** | 713 |
| S2024 | `fit:k/DEF-04/epa_diff` | 60.0 | 511.1 | **+752%** | 768 |
| S2024 | `fit:k/DEF-04/receptions` | 60.0 | 316.7 | **+428%** | 768 |
| S2024 | `fit:k/DEF-04/targets` | 60.0 | 367.2 | **+512%** | 768 |
| S2024 | `fit:k/DEF-04/yards` | 60.0 | 316.1 | **+427%** | 768 |
| S2024 | `fit:k/DEF-05/blitz_rate` | 150.0 | 60.9 | **-59%** | 64 |
| S2024 | `fit:k/DEF-05/box` | 150.0 | 294.6 | **+96%** | 64 |
| S2024 | `fit:k/DEF-05/hit_rate` | 150.0 | 907.4 | **+505%** | 256 |
| S2024 | `fit:k/DEF-06/explosive` | 300.0 | 1,293 | **+331%** | 256 |
| S2024 | `fit:k/DEF-06/explosive_run` | 300.0 | 481.1 | **+60%** | 256 |
| S2024 | `fit:k/DEF-09/epa` | 60.0 | 223.5 | **+272%** | 820 |
| S2024 | `fit:k/DEF-11/yacoe` | 150.0 | 628.9 | **+319%** | 256 |
| S2024 | `fit:k/DEF-15/success` | 60.0 | 333.1 | **+455%** | 512 |
| S2024 | `fit:k/DEF-15/ypc` | 60.0 | 277.8 | **+363%** | 512 |
| S2024 | `fit:k/DEF-17/sacks` | 20.0 | 9.4046 | **-53%** | 404 |
| S2024 | `fit:k/OFF-03/epa` | 100.0 | 276.4 | **+176%** | 890 |
| S2024 | `fit:k/OFF-03/success` | 100.0 | 212.9 | **+113%** | 890 |
| S2024 | `fit:k/OFF-04/pass_rate` | 60.0 | 111.9 | **+87%** | 256 |
| S2024 | `fit:k/OFF-07/motion_rate` | 80.0 | 23.5 | **-71%** | 64 |
| S2024 | `fit:k/OFF-09/shotgun_rate` | 60.0 | 18.7 | **-69%** | 256 |
| S2024 | `fit:k/OFF-10/seconds_per_play` | 80.0 | 38.3 | **-52%** | 256 |
| S2024 | `fit:k/OFF-12/epa` | 100.0 | 168.8 | **+69%** | 715 |
| S2024 | `fit:k/OFF-12/explosive` | 150.0 | 73.9 | **-51%** | 717 |
| S2024 | `fit:k/OFF-12/success` | 60.0 | 124.2 | **+107%** | 716 |
| S2024 | `fit:k/OFF-13/epa` | 60.0 | 148.1 | **+147%** | 872 |
| S2024 | `fit:k/OFF-13/share` | 60.0 | 19.6 | **-67%** | 3328 |
| S2024 | `fit:k/OFF-14/pass_share` | 25.0 | 68.7 | **+175%** | 501 |
| S2024 | `fit:k/OFF-16/stuff` | 80.0 | 240.4 | **+200%** | 512 |
| S2024 | `fit:k/OFF-16/success` | 80.0 | 226.9 | **+184%** | 512 |
| S2024 | `fit:k/PLY-03/target_share` | 60.0 | 10.4 | **-83%** | 7004 |
| S2024 | `fit:k/PLY-04/air_share` | 60.0 | 13.5 | **-77%** | 7004 |
| S2024 | `fit:k/PLY-04/wopr` | 60.0 | 9.9041 | **-83%** | 7004 |
| S2024 | `fit:k/PLY-05/carry_share` | 40.0 | 2.6731 | **-93%** | 6672 |
| S2024 | `fit:k/PLY-06/opportunity_share` | 20.0 | 7.4940 | **-63%** | 8849 |
| S2024 | `fit:k/PLY-07/opportunity_share` | 30.0 | 11.4 | **-62%** | 10602 |
| S2024 | `fit:k/PLY-08/yards_per_team_dropback` | 150.0 | 27.0 | **-82%** | 7016 |
| S2024 | `fit:k/PLY-10/croe` | 80.0 | 247.4 | **+209%** | 978 |
| S2024 | `fit:k/PLY-16/share` | 40.0 | 19.1 | **-52%** | 4857 |
| S2024 | `fit:k/PLY-18/adot` | 80.0 | 192.1 | **+140%** | 382 |
| S2024 | `fit:k/PLY-18/share` | 80.0 | 4.4944 | **-94%** | 1910 |
| S2024 | `fit:k/PLY-20/cpoe` | 200.0 | 395.8 | **+98%** | 381 |
| S2024 | `fit:k/PLY-21/sack_rate` | 150.0 | 238.6 | **+59%** | 390 |
| S2024 | `fit:k/PLY-21/time_to_throw` | 150.0 | 69.9 | **-53%** | 377 |
| S2024 | `fit:k/PLY-23/epa` | 100.0 | 192.6 | **+93%** | 864 |
| S2024 | `fit:k/PLY-23/share` | 100.0 | 6.6514 | **-93%** | 1528 |
| S2024 | `fit:k/PLY-25/success` | 60.0 | 178.8 | **+198%** | 619 |
| S2024 | `fit:k/PLY-25/ypc` | 60.0 | 158.8 | **+165%** | 619 |
| S2024 | `fit:k/PLY-26/stuff` | 100.0 | 195.3 | **+95%** | 561 |
| S2024 | `fit:k/PLY-27/screen_share` | 40.0 | 6.0907 | **-85%** | 610 |
| S2024 | `fit:k/PLY-27/target_share` | 40.0 | 10.4 | **-74%** | 7004 |
| S2024 | `fit:k/PLY-27/yacoe` | 40.0 | 66.1 | **+65%** | 503 |
| S2024 | `fit:k/PLY-28/adot` | 40.0 | 6.4456 | **-84%** | 978 |
| S2024 | `fit:k/PLY-28/share` | 40.0 | 3.6457 | **-91%** | 4884 |
| S2024 | `fit:k/PLY-29/share` | 50.0 | 6.0336 | **-88%** | 3910 |
| S2024 | `fit:k/PLY-31/separation` | 80.0 | 38.3 | **-52%** | 636 |
| S2024 | `fit:k/PLY-32/end_zone_share` | 15.0 | 5.4678 | **-64%** | 403 |
| S2024 | `fit:k/PLY-33/target_share` | 40.0 | 9.0891 | **-77%** | 2708 |
| S2024 | `conventions.g3_usage_half_life_games` | 3.0000 | 8.0000 | **+167%** | 18 |
| S2024 | `fit:k/COA-02/go_over_expected` | 30.0 | 110.8 | **+269%** | 256 |
| live | `fit:k/COA-04/seconds_per_play` | 80.0 | 24.8 | **-69%** | 420 |
| live | `fit:k/DEF-01/epa/all` | 250.0 | 1,010 | **+304%** | 288 |
| live | `fit:k/DEF-01/epa/pass` | 200.0 | 924.0 | **+362%** | 288 |
| live | `fit:k/DEF-01/epa/run` | 300.0 | 554.7 | **+85%** | 288 |
| live | `fit:k/DEF-02/success` | 150.0 | 289.2 | **+93%** | 864 |
| live | `fit:k/DEF-03/success` | 60.0 | 161.0 | **+168%** | 823 |
| live | `fit:k/DEF-04/epa_diff` | 60.0 | 665.4 | **+1009%** | 864 |
| live | `fit:k/DEF-04/receptions` | 60.0 | 321.0 | **+435%** | 864 |
| live | `fit:k/DEF-04/targets` | 60.0 | 382.9 | **+538%** | 864 |
| live | `fit:k/DEF-04/yards` | 60.0 | 337.6 | **+463%** | 864 |
| live | `fit:k/DEF-05/blitz_rate` | 150.0 | 60.4 | **-60%** | 96 |
| live | `fit:k/DEF-05/box` | 150.0 | 385.5 | **+157%** | 96 |
| live | `fit:k/DEF-05/hit_rate` | 150.0 | 799.8 | **+433%** | 288 |
| live | `fit:k/DEF-06/explosive` | 300.0 | 1,416 | **+372%** | 288 |
| live | `fit:k/DEF-06/explosive_run` | 300.0 | 512.0 | **+71%** | 288 |
| live | `fit:k/DEF-09/epa` | 60.0 | 212.6 | **+254%** | 920 |
| live | `fit:k/DEF-12/ypc` | 50.0 | 146.3 | **+193%** | 242 |
| live | `fit:k/DEF-15/success` | 60.0 | 303.7 | **+406%** | 576 |
| live | `fit:k/DEF-15/ypc` | 60.0 | 297.7 | **+396%** | 576 |
| live | `fit:k/DEF-17/sacks` | 20.0 | 9.7738 | **-51%** | 496 |
| live | `fit:k/OFF-03/epa` | 100.0 | 277.6 | **+178%** | 996 |
| live | `fit:k/OFF-03/success` | 100.0 | 212.1 | **+112%** | 996 |
| live | `fit:k/OFF-04/pass_rate` | 60.0 | 116.7 | **+94%** | 288 |
| live | `fit:k/OFF-07/motion_rate` | 80.0 | 23.7 | **-70%** | 96 |
| live | `fit:k/OFF-09/shotgun_rate` | 60.0 | 18.8 | **-69%** | 288 |
| live | `fit:k/OFF-10/seconds_per_play` | 80.0 | 39.3 | **-51%** | 288 |
| live | `fit:k/OFF-12/epa` | 100.0 | 162.1 | **+62%** | 821 |
| live | `fit:k/OFF-12/success` | 60.0 | 126.5 | **+111%** | 822 |
| live | `fit:k/OFF-13/cpoe` | 60.0 | 294.2 | **+390%** | 979 |
| live | `fit:k/OFF-13/epa` | 60.0 | 136.9 | **+128%** | 979 |
| live | `fit:k/OFF-13/share` | 60.0 | 19.8 | **-67%** | 3744 |
| live | `fit:k/OFF-14/pass_share` | 25.0 | 63.3 | **+153%** | 569 |
| live | `fit:k/OFF-16/stuff` | 80.0 | 258.5 | **+223%** | 576 |
| live | `fit:k/OFF-16/success` | 80.0 | 235.1 | **+194%** | 576 |
| live | `fit:k/PLY-03/target_share` | 60.0 | 10.2 | **-83%** | 7916 |
| live | `fit:k/PLY-04/air_share` | 60.0 | 13.4 | **-78%** | 7916 |
| live | `fit:k/PLY-04/wopr` | 60.0 | 9.7756 | **-84%** | 7916 |
| live | `fit:k/PLY-05/carry_share` | 40.0 | 2.6533 | **-93%** | 7541 |
| live | `fit:k/PLY-06/opportunity_share` | 20.0 | 7.3013 | **-63%** | 10038 |
| live | `fit:k/PLY-07/opportunity_share` | 30.0 | 11.4 | **-62%** | 11957 |
| live | `fit:k/PLY-08/yards_per_team_dropback` | 150.0 | 26.6 | **-82%** | 7932 |
| live | `fit:k/PLY-10/croe` | 80.0 | 228.4 | **+186%** | 1107 |
| live | `fit:k/PLY-11/ryoe_per_carry` | 100.0 | 198.7 | **+99%** | 335 |
| live | `fit:k/PLY-16/share` | 40.0 | 19.2 | **-52%** | 5464 |
| live | `fit:k/PLY-18/adot` | 80.0 | 183.7 | **+130%** | 428 |
| live | `fit:k/PLY-18/share` | 80.0 | 4.5469 | **-94%** | 2140 |
| live | `fit:k/PLY-20/cpoe` | 200.0 | 377.7 | **+89%** | 427 |
| live | `fit:k/PLY-21/sack_rate` | 150.0 | 229.2 | **+53%** | 438 |
| live | `fit:k/PLY-21/time_to_throw` | 150.0 | 71.4 | **-52%** | 423 |
| live | `fit:k/PLY-23/epa` | 100.0 | 186.0 | **+86%** | 979 |
| live | `fit:k/PLY-23/share` | 100.0 | 6.6265 | **-93%** | 1712 |
| live | `fit:k/PLY-25/success` | 60.0 | 173.0 | **+188%** | 699 |
| live | `fit:k/PLY-25/ypc` | 60.0 | 164.0 | **+173%** | 699 |
| live | `fit:k/PLY-26/stuff` | 100.0 | 217.0 | **+117%** | 628 |
| live | `fit:k/PLY-27/screen_share` | 40.0 | 6.0841 | **-85%** | 863 |
| live | `fit:k/PLY-27/target_share` | 40.0 | 10.2 | **-74%** | 7916 |
| live | `fit:k/PLY-27/yacoe` | 40.0 | 68.1 | **+70%** | 566 |
| live | `fit:k/PLY-28/adot` | 40.0 | 6.5195 | **-84%** | 1109 |
| live | `fit:k/PLY-28/share` | 40.0 | 3.6663 | **-91%** | 5535 |
| live | `fit:k/PLY-29/share` | 50.0 | 6.0209 | **-88%** | 4429 |
| live | `fit:k/PLY-31/separation` | 80.0 | 38.1 | **-52%** | 710 |
| live | `fit:k/PLY-32/end_zone_share` | 15.0 | 5.4511 | **-64%** | 434 |
| live | `fit:k/PLY-33/target_share` | 40.0 | 9.0566 | **-77%** | 4134 |
| live | `conventions.g3_usage_half_life_games` | 3.0000 | 8.0000 | **+167%** | 18 |
| live | `fit:k/COA-02/go_over_expected` | 30.0 | 119.2 | **+297%** | 288 |

## No detectable signal (BT-02): shrunk value = prior, matchup terms contribute zero

**S2021** (26): `fit:k/DEF-03/epa`, `fit:k/DEF-03/explosive_team`, `fit:k/DEF-03/ypc_team`, `fit:k/DEF-04/receptions`, `fit:k/DEF-04/targets`, `fit:k/DEF-04/tds`, `fit:k/DEF-04/yards`, `fit:k/DEF-05/hit_rate`, `fit:k/DEF-05/sack_rate`, `fit:k/DEF-06/explosive_pass`, `fit:k/DEF-07/td_per_trip`, `fit:k/DEF-08/on_off`, `fit:k/DEF-09/cpoe`, `fit:k/DEF-11/yacoe`, `fit:k/DEF-14/qb_rush_yards`, `fit:k/DEF-14/scramble_rate`, `fit:k/OFF-12/epa`, `fit:k/OFF-13/cpoe`, `fit:k/OFF-14/td_per_trip`, `fit:k/PLY-11/ryoe_per_carry`, `fit:k/PLY-16/epa`, `fit:k/PLY-16/success`, `fit:k/PLY-25/ypc_overall`, `fit:k/PLY-28/epa`, `fit:k/PLY-29/epa`, `fit:k/COA-02/go_over_expected`

**S2022** (21): `fit:k/DEF-03/epa`, `fit:k/DEF-03/explosive_team`, `fit:k/DEF-04/tds`, `fit:k/DEF-05/hit_rate`, `fit:k/DEF-05/sack_rate`, `fit:k/DEF-06/explosive_pass`, `fit:k/DEF-07/td_per_trip`, `fit:k/DEF-08/on_off`, `fit:k/DEF-09/cpoe`, `fit:k/DEF-11/yacoe`, `fit:k/DEF-14/qb_rush_yards`, `fit:k/DEF-14/scramble_rate`, `fit:k/OFF-13/cpoe`, `fit:k/OFF-14/td_per_trip`, `fit:k/PLY-11/ryoe_per_carry`, `fit:k/PLY-16/epa`, `fit:k/PLY-16/success`, `fit:k/PLY-22/yards_per_rush`, `fit:k/PLY-28/epa`, `fit:k/PLY-29/epa`, `fit:k/COA-02/go_over_expected`

**S2023** (34): `fit:k/DEF-03/epa`, `fit:k/DEF-04/tds`, `fit:k/DEF-05/box`, `fit:k/DEF-05/rushers`, `fit:k/DEF-05/sack_rate`, `fit:k/DEF-06/explosive_pass`, `fit:k/DEF-07/td_per_trip`, `fit:k/DEF-08/on_off`, `fit:k/DEF-09/cpoe`, `fit:k/DEF-10/epa_gap`, `fit:k/DEF-11/yacoe`, `fit:k/DEF-12/success`, `fit:k/DEF-12/ypc`, `fit:k/DEF-13/epa_gap`, `fit:k/DEF-14/qb_rush_yards`, `fit:k/DEF-14/scramble_rate`, `fit:k/OFF-13/cpoe`, `fit:k/OFF-14/td_per_trip`, `fit:k/PLY-11/ryoe_per_carry`, `fit:k/PLY-16/epa`, `fit:k/PLY-16/success`, `fit:k/PLY-17/epa_gap`, `fit:k/PLY-17/sack_gap`, `fit:k/PLY-20/catchable_rate`, `fit:k/PLY-20/interception_worthy_rate`, `fit:k/PLY-22/yards_per_rush`, `fit:k/PLY-24/success`, `fit:k/PLY-24/success_overall`, `fit:k/PLY-24/ypc`, `fit:k/PLY-24/ypc_overall`, `fit:k/PLY-28/epa`, `fit:k/PLY-29/epa`, `fit:k/PLY-30/created_reception_rate`, `fit:k/PLY-30/drop_rate`

**S2024** (30): `fit:k/DEF-03/epa`, `fit:k/DEF-04/tds`, `fit:k/DEF-05/sack_rate`, `fit:k/DEF-06/explosive_pass`, `fit:k/DEF-07/td_per_trip`, `fit:k/DEF-08/on_off`, `fit:k/DEF-09/cpoe`, `fit:k/DEF-10/epa_gap`, `fit:k/DEF-12/success`, `fit:k/DEF-12/ypc`, `fit:k/DEF-13/epa_gap`, `fit:k/DEF-14/qb_rush_yards`, `fit:k/DEF-14/scramble_rate`, `fit:k/OFF-13/cpoe`, `fit:k/OFF-14/td_per_trip`, `fit:k/PLY-11/ryoe_per_carry`, `fit:k/PLY-16/epa`, `fit:k/PLY-16/success`, `fit:k/PLY-17/epa_gap`, `fit:k/PLY-17/sack_gap`, `fit:k/PLY-19/epa_gap`, `fit:k/PLY-20/interception_worthy_rate`, `fit:k/PLY-20/throwaway_rate`, `fit:k/PLY-22/yards_per_rush`, `fit:k/PLY-24/success`, `fit:k/PLY-24/ypc`, `fit:k/PLY-24/ypc_overall`, `fit:k/PLY-28/epa`, `fit:k/PLY-29/epa`, `fit:k/PLY-30/drop_rate`

**live** (26): `fit:k/DEF-03/epa`, `fit:k/DEF-04/tds`, `fit:k/DEF-05/sack_rate`, `fit:k/DEF-06/explosive_pass`, `fit:k/DEF-07/td_per_trip`, `fit:k/DEF-08/on_off`, `fit:k/DEF-09/cpoe`, `fit:k/DEF-10/epa_gap`, `fit:k/DEF-11/yacoe`, `fit:k/DEF-12/success`, `fit:k/DEF-13/epa_gap`, `fit:k/DEF-14/qb_rush_yards`, `fit:k/DEF-14/scramble_rate`, `fit:k/OFF-14/td_per_trip`, `fit:k/PLY-16/epa`, `fit:k/PLY-16/success`, `fit:k/PLY-17/epa_gap`, `fit:k/PLY-17/sack_gap`, `fit:k/PLY-19/epa_gap`, `fit:k/PLY-20/interception_worthy_rate`, `fit:k/PLY-22/yards_per_rush`, `fit:k/PLY-24/success`, `fit:k/PLY-24/ypc`, `fit:k/PLY-28/epa`, `fit:k/PLY-29/epa`, `fit:k/PLY-30/drop_rate`

## Left missing

### S2021

- `fit:k/COA-03/two_point_rate`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/DEF-05/blitz_rate`: no FTN training data; initial k kept
- `fit:k/DEF-05/box`: no FTN training data; initial k kept
- `fit:k/DEF-05/rushers`: no FTN training data; initial k kept
- `fit:k/DEF-10/epa_gap`: no FTN training data; initial k kept
- `fit:k/DEF-12/stacked_box_share`: no FTN training data
- `fit:k/DEF-12/success`: no FTN training data; initial k kept
- `fit:k/DEF-12/ypc`: no FTN training data; initial k kept
- `fit:k/DEF-13/epa_gap`: no FTN training data; initial k kept
- `fit:k/DEF-16/td_rate`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/DEF-17/interceptions`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/OFF-06/play_action_rate`: no FTN training data; initial k kept
- `fit:k/OFF-07/motion_rate`: no FTN training data; initial k kept
- `fit:k/OFF-08/rpo_rate`: no FTN training data; initial k kept
- `fit:k/OFF-11/plays_per_game`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-01/snap_share`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-02/snap_share`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-17/epa_gap`: no FTN training data; initial k kept
- `fit:k/PLY-17/sack_gap`: no FTN training data; initial k kept
- `fit:k/PLY-19/epa_gap`: no FTN training data; initial k kept
- `fit:k/PLY-19/play_action_rate`: no FTN training data
- `fit:k/PLY-20/catchable_rate`: no FTN training data; initial k kept
- `fit:k/PLY-20/interception_worthy_rate`: no FTN training data; initial k kept
- `fit:k/PLY-20/throwaway_rate`: no FTN training data; initial k kept
- `fit:k/PLY-22/designed_runs_per_game`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum)
- `fit:k/PLY-22/yards_per_rush`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/PLY-24/success`: no FTN training data; initial k kept
- `fit:k/PLY-24/success_overall`: no FTN training data
- `fit:k/PLY-24/ypc`: no FTN training data; initial k kept
- `fit:k/PLY-24/ypc_overall`: no FTN training data
- `fit:k/PLY-27/screen_share`: no FTN training data; initial k kept
- `fit:k/PLY-30/contested_catch_rate`: no FTN training data; initial k kept
- `fit:k/PLY-30/created_reception_rate`: no FTN training data
- `fit:k/PLY-30/drop_rate`: no FTN training data; initial k kept
- `fit:k/PLY-33/target_share`: no FTN training data; initial k kept
- `fit:role/PLY-18/adot/all/RB1`: 8 player-seasons < 30
- `fit:role/PLY-18/adot/all/RB2`: 8 player-seasons < 30
- `fit:role/PLY-18/adot/all/TE1`: 4 player-seasons < 30
- `fit:role/PLY-18/adot/all/WR2`: 17 player-seasons < 30
- `fit:role/PLY-18/adot/all/WR3`: 17 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/RB1`: 8 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/RB2`: 8 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/TE1`: 4 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/WR2`: 17 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/WR3`: 17 player-seasons < 30
- `fit:role/PLY-18/share/behind/RB1`: 8 player-seasons < 30
- `fit:role/PLY-18/share/behind/RB2`: 8 player-seasons < 30
- `fit:role/PLY-18/share/behind/TE1`: 4 player-seasons < 30
- `fit:role/PLY-18/share/behind/WR2`: 17 player-seasons < 30
- `fit:role/PLY-18/share/behind/WR3`: 17 player-seasons < 30
- `fit:role/PLY-18/share/deep/RB1`: 8 player-seasons < 30
- `fit:role/PLY-18/share/deep/RB2`: 8 player-seasons < 30
- `fit:role/PLY-18/share/deep/TE1`: 4 player-seasons < 30
- `fit:role/PLY-18/share/deep/WR2`: 17 player-seasons < 30
- `fit:role/PLY-18/share/deep/WR3`: 17 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/RB1`: 8 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/RB2`: 8 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/TE1`: 4 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/WR2`: 17 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/WR3`: 17 player-seasons < 30
- `fit:role/PLY-18/share/short/RB1`: 8 player-seasons < 30
- `fit:role/PLY-18/share/short/RB2`: 8 player-seasons < 30
- `fit:role/PLY-18/share/short/TE1`: 4 player-seasons < 30
- `fit:role/PLY-18/share/short/WR2`: 17 player-seasons < 30
- `fit:role/PLY-18/share/short/WR3`: 17 player-seasons < 30
- `fit:role/PLY-18/share/unknown/RB1`: 8 player-seasons < 30
- `fit:role/PLY-18/share/unknown/RB2`: 8 player-seasons < 30
- `fit:role/PLY-18/share/unknown/TE1`: 4 player-seasons < 30
- `fit:role/PLY-18/share/unknown/WR2`: 17 player-seasons < 30
- `fit:role/PLY-18/share/unknown/WR3`: 17 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/RB1`: 8 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/RB2`: 8 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/TE1`: 4 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/WR2`: 17 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/WR3`: 17 player-seasons < 30
- `fit:role/PLY-23/share/left/RB1`: 8 player-seasons < 30
- `fit:role/PLY-23/share/left/RB2`: 8 player-seasons < 30
- `fit:role/PLY-23/share/left/TE1`: 4 player-seasons < 30
- `fit:role/PLY-23/share/left/WR2`: 17 player-seasons < 30
- `fit:role/PLY-23/share/left/WR3`: 17 player-seasons < 30
- `fit:role/PLY-23/share/middle/RB1`: 8 player-seasons < 30
- `fit:role/PLY-23/share/middle/RB2`: 8 player-seasons < 30
- `fit:role/PLY-23/share/middle/TE1`: 4 player-seasons < 30
- `fit:role/PLY-23/share/middle/WR2`: 17 player-seasons < 30
- `fit:role/PLY-23/share/middle/WR3`: 17 player-seasons < 30
- `fit:role/PLY-23/share/right/RB1`: 8 player-seasons < 30
- `fit:role/PLY-23/share/right/RB2`: 8 player-seasons < 30
- `fit:role/PLY-23/share/right/TE1`: 4 player-seasons < 30
- `fit:role/PLY-23/share/right/WR2`: 17 player-seasons < 30
- `fit:role/PLY-23/share/right/WR3`: 17 player-seasons < 30
- `fit:role/PLY-23/share/unknown/RB1`: 8 player-seasons < 30
- `fit:role/PLY-23/share/unknown/RB2`: 8 player-seasons < 30
- `fit:role/PLY-23/share/unknown/TE1`: 4 player-seasons < 30
- `fit:role/PLY-23/share/unknown/WR2`: 17 player-seasons < 30
- `fit:role/PLY-23/share/unknown/WR3`: 17 player-seasons < 30
- `fit:role/PLY-24/success_overall`: no FTN training data
- `fit:role/PLY-24/ypc_overall`: no FTN training data
- `fit:role/PLY-25/success_overall/all/TE1`: 26 player-seasons < 30
- `fit:role/PLY-25/ypc_overall/all/TE1`: 26 player-seasons < 30
- `fit:role/PLY-27/screen_share`: no FTN training data
- `fit:role/PLY-27/yacoe/all/QB1`: 28 player-seasons < 30

### S2022

- `fit:k/COA-03/two_point_rate`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/DEF-05/blitz_rate`: no FTN training data; initial k kept
- `fit:k/DEF-05/box`: no FTN training data; initial k kept
- `fit:k/DEF-05/rushers`: no FTN training data; initial k kept
- `fit:k/DEF-10/epa_gap`: no FTN training data; initial k kept
- `fit:k/DEF-12/stacked_box_share`: no FTN training data
- `fit:k/DEF-12/success`: no FTN training data; initial k kept
- `fit:k/DEF-12/ypc`: no FTN training data; initial k kept
- `fit:k/DEF-13/epa_gap`: no FTN training data; initial k kept
- `fit:k/DEF-16/td_rate`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/DEF-17/interceptions`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/OFF-06/play_action_rate`: no FTN training data; initial k kept
- `fit:k/OFF-07/motion_rate`: no FTN training data; initial k kept
- `fit:k/OFF-08/rpo_rate`: no FTN training data; initial k kept
- `fit:k/OFF-11/plays_per_game`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-01/snap_share`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-02/snap_share`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-17/epa_gap`: no FTN training data; initial k kept
- `fit:k/PLY-17/sack_gap`: no FTN training data; initial k kept
- `fit:k/PLY-19/epa_gap`: no FTN training data; initial k kept
- `fit:k/PLY-19/play_action_rate`: no FTN training data
- `fit:k/PLY-20/catchable_rate`: no FTN training data; initial k kept
- `fit:k/PLY-20/interception_worthy_rate`: no FTN training data; initial k kept
- `fit:k/PLY-20/throwaway_rate`: no FTN training data; initial k kept
- `fit:k/PLY-22/designed_runs_per_game`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum)
- `fit:k/PLY-24/success`: no FTN training data; initial k kept
- `fit:k/PLY-24/success_overall`: no FTN training data
- `fit:k/PLY-24/ypc`: no FTN training data; initial k kept
- `fit:k/PLY-24/ypc_overall`: no FTN training data
- `fit:k/PLY-27/screen_share`: no FTN training data; initial k kept
- `fit:k/PLY-30/contested_catch_rate`: no FTN training data; initial k kept
- `fit:k/PLY-30/created_reception_rate`: no FTN training data
- `fit:k/PLY-30/drop_rate`: no FTN training data; initial k kept
- `fit:k/PLY-33/target_share`: no FTN training data; initial k kept
- `fit:role/PLY-18/adot/all/RB1`: 13 player-seasons < 30
- `fit:role/PLY-18/adot/all/RB2`: 9 player-seasons < 30
- `fit:role/PLY-18/adot/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/adot/all/WR2`: 24 player-seasons < 30
- `fit:role/PLY-18/adot/all/WR3`: 23 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/RB1`: 13 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/RB2`: 9 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/WR2`: 24 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/WR3`: 23 player-seasons < 30
- `fit:role/PLY-18/share/behind/RB1`: 13 player-seasons < 30
- `fit:role/PLY-18/share/behind/RB2`: 9 player-seasons < 30
- `fit:role/PLY-18/share/behind/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/behind/WR2`: 24 player-seasons < 30
- `fit:role/PLY-18/share/behind/WR3`: 23 player-seasons < 30
- `fit:role/PLY-18/share/deep/RB1`: 13 player-seasons < 30
- `fit:role/PLY-18/share/deep/RB2`: 9 player-seasons < 30
- `fit:role/PLY-18/share/deep/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/deep/WR2`: 24 player-seasons < 30
- `fit:role/PLY-18/share/deep/WR3`: 23 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/RB1`: 13 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/RB2`: 9 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/WR2`: 24 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/WR3`: 23 player-seasons < 30
- `fit:role/PLY-18/share/short/RB1`: 13 player-seasons < 30
- `fit:role/PLY-18/share/short/RB2`: 9 player-seasons < 30
- `fit:role/PLY-18/share/short/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/short/WR2`: 24 player-seasons < 30
- `fit:role/PLY-18/share/short/WR3`: 23 player-seasons < 30
- `fit:role/PLY-18/share/unknown/RB1`: 13 player-seasons < 30
- `fit:role/PLY-18/share/unknown/RB2`: 9 player-seasons < 30
- `fit:role/PLY-18/share/unknown/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/unknown/WR2`: 24 player-seasons < 30
- `fit:role/PLY-18/share/unknown/WR3`: 23 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/RB1`: 13 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/RB2`: 9 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/WR2`: 24 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/WR3`: 23 player-seasons < 30
- `fit:role/PLY-23/share/left/RB1`: 13 player-seasons < 30
- `fit:role/PLY-23/share/left/RB2`: 9 player-seasons < 30
- `fit:role/PLY-23/share/left/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/left/WR2`: 24 player-seasons < 30
- `fit:role/PLY-23/share/left/WR3`: 23 player-seasons < 30
- `fit:role/PLY-23/share/middle/RB1`: 13 player-seasons < 30
- `fit:role/PLY-23/share/middle/RB2`: 9 player-seasons < 30
- `fit:role/PLY-23/share/middle/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/middle/WR2`: 24 player-seasons < 30
- `fit:role/PLY-23/share/middle/WR3`: 23 player-seasons < 30
- `fit:role/PLY-23/share/right/RB1`: 13 player-seasons < 30
- `fit:role/PLY-23/share/right/RB2`: 9 player-seasons < 30
- `fit:role/PLY-23/share/right/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/right/WR2`: 24 player-seasons < 30
- `fit:role/PLY-23/share/right/WR3`: 23 player-seasons < 30
- `fit:role/PLY-23/share/unknown/RB1`: 13 player-seasons < 30
- `fit:role/PLY-23/share/unknown/RB2`: 9 player-seasons < 30
- `fit:role/PLY-23/share/unknown/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/unknown/WR2`: 24 player-seasons < 30
- `fit:role/PLY-23/share/unknown/WR3`: 23 player-seasons < 30
- `fit:role/PLY-24/success_overall`: no FTN training data
- `fit:role/PLY-24/ypc_overall`: no FTN training data
- `fit:role/PLY-27/screen_share`: no FTN training data

### S2023

- `fit:k/COA-03/two_point_rate`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/DEF-16/td_rate`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/DEF-17/interceptions`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/OFF-11/plays_per_game`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-01/snap_share`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-02/snap_share`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-19/epa_gap`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/PLY-22/designed_runs_per_game`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum)
- `fit:k/PLY-30/contested_catch_rate`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:role/PLY-18/adot/all/RB1`: 16 player-seasons < 30
- `fit:role/PLY-18/adot/all/RB2`: 11 player-seasons < 30
- `fit:role/PLY-18/adot/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/adot/all/WR3`: 24 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/RB1`: 16 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/RB2`: 11 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/WR3`: 24 player-seasons < 30
- `fit:role/PLY-18/share/behind/RB1`: 16 player-seasons < 30
- `fit:role/PLY-18/share/behind/RB2`: 11 player-seasons < 30
- `fit:role/PLY-18/share/behind/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/behind/WR3`: 24 player-seasons < 30
- `fit:role/PLY-18/share/deep/RB1`: 16 player-seasons < 30
- `fit:role/PLY-18/share/deep/RB2`: 11 player-seasons < 30
- `fit:role/PLY-18/share/deep/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/deep/WR3`: 24 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/RB1`: 16 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/RB2`: 11 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/WR3`: 24 player-seasons < 30
- `fit:role/PLY-18/share/short/RB1`: 16 player-seasons < 30
- `fit:role/PLY-18/share/short/RB2`: 11 player-seasons < 30
- `fit:role/PLY-18/share/short/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/short/WR3`: 24 player-seasons < 30
- `fit:role/PLY-18/share/unknown/RB1`: 16 player-seasons < 30
- `fit:role/PLY-18/share/unknown/RB2`: 11 player-seasons < 30
- `fit:role/PLY-18/share/unknown/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/unknown/WR3`: 24 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/RB1`: 16 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/RB2`: 11 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/WR3`: 24 player-seasons < 30
- `fit:role/PLY-23/share/left/RB1`: 16 player-seasons < 30
- `fit:role/PLY-23/share/left/RB2`: 11 player-seasons < 30
- `fit:role/PLY-23/share/left/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/left/WR3`: 24 player-seasons < 30
- `fit:role/PLY-23/share/middle/RB1`: 16 player-seasons < 30
- `fit:role/PLY-23/share/middle/RB2`: 11 player-seasons < 30
- `fit:role/PLY-23/share/middle/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/middle/WR3`: 24 player-seasons < 30
- `fit:role/PLY-23/share/right/RB1`: 16 player-seasons < 30
- `fit:role/PLY-23/share/right/RB2`: 11 player-seasons < 30
- `fit:role/PLY-23/share/right/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/right/WR3`: 24 player-seasons < 30
- `fit:role/PLY-23/share/unknown/RB1`: 16 player-seasons < 30
- `fit:role/PLY-23/share/unknown/RB2`: 11 player-seasons < 30
- `fit:role/PLY-23/share/unknown/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/unknown/WR3`: 24 player-seasons < 30
- `fit:role/PLY-24/success_overall/all/TE1`: 10 player-seasons < 30
- `fit:role/PLY-24/success_overall/all/WR2`: 26 player-seasons < 30
- `fit:role/PLY-24/ypc_overall/all/TE1`: 10 player-seasons < 30
- `fit:role/PLY-24/ypc_overall/all/WR2`: 26 player-seasons < 30

### S2024

- `fit:k/COA-03/two_point_rate`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/DEF-16/td_rate`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/DEF-17/interceptions`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/OFF-11/plays_per_game`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-01/snap_share`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-02/snap_share`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-22/designed_runs_per_game`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum)
- `fit:k/PLY-30/contested_catch_rate`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:role/PLY-18/adot/all/RB1`: 18 player-seasons < 30
- `fit:role/PLY-18/adot/all/RB2`: 14 player-seasons < 30
- `fit:role/PLY-18/adot/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/adot/all/WR3`: 27 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/RB1`: 18 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/RB2`: 14 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/WR3`: 27 player-seasons < 30
- `fit:role/PLY-18/share/behind/RB1`: 18 player-seasons < 30
- `fit:role/PLY-18/share/behind/RB2`: 14 player-seasons < 30
- `fit:role/PLY-18/share/behind/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/behind/WR3`: 27 player-seasons < 30
- `fit:role/PLY-18/share/deep/RB1`: 18 player-seasons < 30
- `fit:role/PLY-18/share/deep/RB2`: 14 player-seasons < 30
- `fit:role/PLY-18/share/deep/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/deep/WR3`: 27 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/RB1`: 18 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/RB2`: 14 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/WR3`: 27 player-seasons < 30
- `fit:role/PLY-18/share/short/RB1`: 18 player-seasons < 30
- `fit:role/PLY-18/share/short/RB2`: 14 player-seasons < 30
- `fit:role/PLY-18/share/short/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/short/WR3`: 27 player-seasons < 30
- `fit:role/PLY-18/share/unknown/RB1`: 18 player-seasons < 30
- `fit:role/PLY-18/share/unknown/RB2`: 14 player-seasons < 30
- `fit:role/PLY-18/share/unknown/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/unknown/WR3`: 27 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/RB1`: 18 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/RB2`: 14 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/WR3`: 27 player-seasons < 30
- `fit:role/PLY-23/share/left/RB1`: 18 player-seasons < 30
- `fit:role/PLY-23/share/left/RB2`: 14 player-seasons < 30
- `fit:role/PLY-23/share/left/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/left/WR3`: 27 player-seasons < 30
- `fit:role/PLY-23/share/middle/RB1`: 18 player-seasons < 30
- `fit:role/PLY-23/share/middle/RB2`: 14 player-seasons < 30
- `fit:role/PLY-23/share/middle/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/middle/WR3`: 27 player-seasons < 30
- `fit:role/PLY-23/share/right/RB1`: 18 player-seasons < 30
- `fit:role/PLY-23/share/right/RB2`: 14 player-seasons < 30
- `fit:role/PLY-23/share/right/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/right/WR3`: 27 player-seasons < 30
- `fit:role/PLY-23/share/unknown/RB1`: 18 player-seasons < 30
- `fit:role/PLY-23/share/unknown/RB2`: 14 player-seasons < 30
- `fit:role/PLY-23/share/unknown/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/unknown/WR3`: 27 player-seasons < 30
- `fit:role/PLY-24/success_overall/all/TE1`: 20 player-seasons < 30
- `fit:role/PLY-24/ypc_overall/all/TE1`: 20 player-seasons < 30

### live

- `fit:k/COA-03/two_point_rate`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/DEF-16/td_rate`: fewer than 30 entities with 2m units for every m in (25, 50, 100, 200, 400); initial k kept
- `fit:k/DEF-17/interceptions`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/OFF-11/plays_per_game`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-01/snap_share`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-02/snap_share`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:k/PLY-22/designed_runs_per_game`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum)
- `fit:k/PLY-30/contested_catch_rate`: fewer than 30 entities reach 2m = 50 units at any m (BT-02 minimum); initial k kept
- `fit:role/PLY-18/adot/all/RB1`: 19 player-seasons < 30
- `fit:role/PLY-18/adot/all/RB2`: 15 player-seasons < 30
- `fit:role/PLY-18/adot/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/RB1`: 19 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/RB2`: 15 player-seasons < 30
- `fit:role/PLY-18/epa_overall/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/behind/RB1`: 19 player-seasons < 30
- `fit:role/PLY-18/share/behind/RB2`: 15 player-seasons < 30
- `fit:role/PLY-18/share/behind/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/deep/RB1`: 19 player-seasons < 30
- `fit:role/PLY-18/share/deep/RB2`: 15 player-seasons < 30
- `fit:role/PLY-18/share/deep/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/RB1`: 19 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/RB2`: 15 player-seasons < 30
- `fit:role/PLY-18/share/intermediate/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/short/RB1`: 19 player-seasons < 30
- `fit:role/PLY-18/share/short/RB2`: 15 player-seasons < 30
- `fit:role/PLY-18/share/short/TE1`: 5 player-seasons < 30
- `fit:role/PLY-18/share/unknown/RB1`: 19 player-seasons < 30
- `fit:role/PLY-18/share/unknown/RB2`: 15 player-seasons < 30
- `fit:role/PLY-18/share/unknown/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/RB1`: 19 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/RB2`: 15 player-seasons < 30
- `fit:role/PLY-23/epa_overall/all/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/left/RB1`: 19 player-seasons < 30
- `fit:role/PLY-23/share/left/RB2`: 15 player-seasons < 30
- `fit:role/PLY-23/share/left/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/middle/RB1`: 19 player-seasons < 30
- `fit:role/PLY-23/share/middle/RB2`: 15 player-seasons < 30
- `fit:role/PLY-23/share/middle/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/right/RB1`: 19 player-seasons < 30
- `fit:role/PLY-23/share/right/RB2`: 15 player-seasons < 30
- `fit:role/PLY-23/share/right/TE1`: 5 player-seasons < 30
- `fit:role/PLY-23/share/unknown/RB1`: 19 player-seasons < 30
- `fit:role/PLY-23/share/unknown/RB2`: 15 player-seasons < 30
- `fit:role/PLY-23/share/unknown/TE1`: 5 player-seasons < 30

Data: nflverse; charting: FTN Data via nflverse
