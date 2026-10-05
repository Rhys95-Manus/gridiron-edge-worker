"""Strict loaders for config/params.yaml and config/fees.yaml.

Every field is listed explicitly and required, and unknown keys are rejected, so a missing,
misspelled or extra parameter stops the worker instead of silently falling back to a default.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StringConstraints

REPO_ROOT = Path(__file__).resolve().parents[2]
PARAMS_PATH = REPO_ROOT / "config" / "params.yaml"
FEES_PATH = REPO_ROOT / "config" / "fees.yaml"
INGEST_PATH = REPO_ROOT / "config" / "ingest.yaml"

SPEC_ID_PATTERN = r"^(?:(?:DATA|OFF|DEF|PLY|COA|MTC|ENV|PRJ|EDG|BT)-\d{2}[a-z]?|G[1-7])$"

SpecId = Annotated[str, StringConstraints(pattern=SPEC_ID_PATTERN)]
Status = Literal["initial", "fitted"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Entry(_Strict):
    spec_id: SpecId | Annotated[list[SpecId], Field(min_length=1)]
    status: Status
    source: Annotated[str, StringConstraints(min_length=1)]


class Param(_Entry):
    value: StrictInt | StrictFloat


class CenticentParam(_Entry):
    """Money in integer centicents (1/10,000 of a dollar), per CLAUDE.md rule 7."""

    value: StrictInt


class _Group(_Strict):
    pass


class Conventions(_Group):
    g3_usage_half_life_games: Param
    g3_efficiency_half_life_games: Param
    g4_prior_carryover_last_week: Param
    g4_new_caller_or_qb_extra_regression: Param
    g5_neutral_wp_min: Param
    g5_neutral_wp_max: Param
    g5_end_of_half_excluded_seconds: Param
    g7_garbage_wp_low: Param
    g7_garbage_wp_high: Param


class Offense(_Group):
    off_01_min_plays: Param
    off_01_min_pass_plays: Param
    off_01_min_run_plays: Param
    off_01_k_overall: Param
    off_01_k_pass: Param
    off_01_k_run: Param
    off_02_min_plays: Param
    off_02_k: Param
    off_03_min_plays_per_cell: Param
    off_03_k: Param
    off_03_own_zone_min_yardline_100: Param
    off_03_red_zone_max_yardline_100: Param
    off_04_min_plays: Param
    off_04_k: Param
    off_05_min_plays: Param
    off_05_k: Param
    off_06_min_dropbacks: Param
    off_06_k: Param
    off_07_min_plays: Param
    off_07_k: Param
    off_08_min_plays: Param
    off_08_k: Param
    off_09_min_plays: Param
    off_09_k: Param
    off_10_min_pairs: Param
    off_10_k_pairs: Param
    off_10_max_snap_gap_seconds: Param
    off_11_min_games: Param
    off_11_k_games: Param
    off_12_min_carries_per_cell: Param
    off_12_k_success: Param
    off_12_k_epa_ypc: Param
    off_12_k_explosive: Param
    off_12_explosive_run_min_yards: Param
    off_13_min_targets_per_cell: Param
    off_13_k_targets: Param
    off_13_short_min_air_yards: Param
    off_13_intermediate_min_air_yards: Param
    off_13_deep_min_air_yards: Param
    off_14_min_plays: Param
    off_14_min_trips: Param
    off_14_k_plays: Param
    off_14_k_trips: Param
    off_14_zone_20_yardline_100: Param
    off_14_zone_10_yardline_100: Param
    off_14_zone_5_yardline_100: Param
    off_15_min_dropbacks: Param
    off_15_k: Param
    off_16_min_carries_per_side: Param
    off_16_k: Param
    off_16_stuff_max_yards: Param
    off_17_starting_ol_count: Param
    off_17_starter_lookback_games: Param
    off_17_continuity_min_snap_share: Param


class Defense(_Group):
    def_01_min_plays: Param
    def_01_k_overall: Param
    def_01_k_pass: Param
    def_01_k_run: Param
    def_02_min_plays: Param
    def_02_k: Param
    def_03_min_carries_per_cell: Param
    def_03_k_success: Param
    def_03_k_epa_ypc: Param
    def_03_k_explosive: Param
    def_04_min_games: Param
    def_04_min_targets: Param
    def_04_k_targets: Param
    def_04_prior_ratio: Param
    def_05_min_dropbacks: Param
    def_05_k: Param
    def_05_blitz_min_blitzers: Param
    def_06_min_plays: Param
    def_06_k: Param
    def_06_explosive_run_min_yards: Param
    def_06_explosive_pass_min_yards: Param
    def_07_min_trips: Param
    def_07_k_trips: Param
    def_07_red_zone_yardline_100: Param
    def_08_min_plays_each_way: Param
    def_08_k: Param
    def_08_starter_min_snap_share: Param
    def_08_starter_lookback_games: Param
    def_09_min_targets_per_cell: Param
    def_09_k: Param
    def_09_cells: Param
    def_10_min_play_action_dropbacks: Param
    def_10_k: Param
    def_11_min_receptions: Param
    def_11_k: Param
    def_12_min_carries_per_band: Param
    def_12_k: Param
    def_12_stacked_box_min: Param
    def_13_min_blitzed_dropbacks: Param
    def_13_k: Param
    def_14_min_dropbacks: Param
    def_14_k: Param
    def_15_min_carries_each: Param
    def_15_k: Param
    def_16_min_end_zone_targets: Param
    def_16_k: Param
    def_17_min_team_defensive_snaps: Param
    def_17_k_events_per_share: Param


class Player(_Group):
    ply_01_min_games: Param
    ply_01_k_games: Param
    ply_03_min_games: Param
    ply_03_k_team_targets: Param
    ply_04_min_games: Param
    ply_04_k_team_targets: Param
    ply_04_wopr_target_weight: Param
    ply_04_wopr_air_weight: Param
    ply_05_min_games: Param
    ply_05_k_team_carries: Param
    ply_06_min_team_opportunities: Param
    ply_06_k_team_opportunities: Param
    ply_06_zone_20_yardline_100: Param
    ply_06_zone_10_yardline_100: Param
    ply_06_zone_5_yardline_100: Param
    ply_07_min_team_opportunities: Param
    ply_07_k: Param
    ply_07_two_minute_seconds: Param
    ply_08_min_games: Param
    ply_08_k_team_dropbacks: Param
    ply_09_min_receptions: Param
    ply_09_k_receptions: Param
    ply_10_min_targets: Param
    ply_10_k_targets: Param
    ply_11_min_carries: Param
    ply_11_k_carries: Param
    ply_13_min_games: Param
    ply_13_short_window_games: Param
    ply_13_long_window_games: Param
    ply_13_role_change_sigmas: Param
    ply_13_opportunity_lookback_games: Param
    ply_13_flagged_half_life_games: Param
    ply_14_return_min_missed_games: Param
    ply_14_return_factor: Param
    ply_15_min_games_without: Param
    ply_15_k_games: Param
    ply_15_same_position_weight: Param
    ply_15_low_confidence_max_career_snaps: Param
    ply_15_low_confidence_stake_cap: Param
    ply_16_min_carries_per_cell: Param
    ply_16_k_carries: Param
    ply_17_min_blitzed_dropbacks: Param
    ply_17_k_blitzed_dropbacks: Param
    ply_17_blitz_min_blitzers: Param
    ply_17_no_blitz_blitzers: Param
    ply_18_min_attempts_per_band: Param
    ply_18_k_attempts: Param
    ply_19_min_play_action_dropbacks: Param
    ply_19_k: Param
    ply_20_min_attempts: Param
    ply_20_k: Param
    ply_21_min_dropbacks: Param
    ply_21_k: Param
    ply_22_min_rushes: Param
    ply_22_k: Param
    ply_23_min_attempts_per_side: Param
    ply_23_k: Param
    ply_24_min_carries_per_band: Param
    ply_24_k: Param
    ply_24_light_box_max: Param
    ply_24_standard_box: Param
    ply_24_stacked_box_min: Param
    ply_25_min_carries_each: Param
    ply_25_k: Param
    ply_26_min_carries: Param
    ply_26_k_explosive: Param
    ply_26_k_stuff: Param
    ply_26_explosive_min_yards: Param
    ply_26_stuff_max_yards: Param
    ply_27_min_targets: Param
    ply_27_k: Param
    ply_28_min_targets_per_band: Param
    ply_28_k: Param
    ply_29_min_targets_per_side: Param
    ply_29_k: Param
    ply_30_min_catchable: Param
    ply_30_min_contested: Param
    ply_30_k_catchable: Param
    ply_30_k_contested: Param
    ply_31_min_targets: Param
    ply_31_k: Param
    ply_32_min_team_end_zone_targets: Param
    ply_32_k: Param
    ply_33_min_targets_each: Param
    ply_33_k: Param


class Coaching(_Group):
    coa_02_min_fourth_downs: Param
    coa_02_k: Param
    coa_03_min_tds: Param
    coa_03_k: Param
    coa_04_min_plays_per_bucket: Param
    coa_04_k: Param
    coa_04_leading_min_wp: Param
    coa_04_trailing_max_wp: Param
    coa_06_min_games: Param


class Matchup(_Group):
    mtc_01_lambda: Param
    mtc_02_lambda: Param
    mtc_03_lambda: Param
    mtc_player_mean_adjustment_cap: Param
    mtc_01_min_carries_per_cell: Param
    mtc_02_beta: Param
    mtc_03_ol_absence_factor: Param
    mtc_07_multiplier_min: Param
    mtc_07_multiplier_max: Param
    mtc_07_log_offset: Param
    mtc_07_first_training_season: Param
    mtc_07_last_training_season: Param
    mtc_07_ftn_first_season: Param


class Environment(_Group):
    env_fit_first_season: Param
    env_fit_last_season: Param


class Projection(_Group):
    prj_01_model_half_life_games: Param
    prj_01_anchor_tolerance_points: Param
    prj_02_runs_per_game: Param
    prj_02_tol_points_per_team_game: Param
    prj_02_tol_plays_per_team_game: Param
    prj_02_tol_pass_rate: Param
    prj_02_tol_yards_per_pass_attempt: Param
    prj_03_first_td_crosscheck_max_gap: Param
    prj_06_season_runs: Param
    prj_07_bins: Param
    prj_07_min_forecasts_per_market_type: Param
    prj_07_min_forecasts_per_bin: Param


class Edge(_Group):
    edg_03_game_lines_min_edge_cc: CenticentParam
    edg_03_anytime_td_min_edge_cc: CenticentParam
    edg_03_anytime_td_min_roi: Param
    edg_03_yardage_min_edge_cc: CenticentParam
    edg_03_yardage_min_roi: Param
    edg_03_yardage_max_spread_cc: CenticentParam
    edg_03_first_or_2plus_td_min_edge_cc: CenticentParam
    edg_03_first_or_2plus_td_min_roi: Param
    edg_03_combos_min_edge_cc: CenticentParam
    edg_03_combos_min_roi: Param
    edg_03_futures_min_edge_cc: CenticentParam
    edg_03_futures_min_roi: Param
    edg_03_proxy_threshold_add_cc: CenticentParam
    edg_04_max_depth_share: Param
    edg_04_depth_window_cc: CenticentParam
    edg_04_recent_volume_window_hours: Param
    edg_04_thin_total_volume_cc: CenticentParam
    edg_04_ignore_book_spread_over_cc: CenticentParam
    edg_06_kelly_fraction: Param
    edg_06_stake_cap_before_go_live: Param
    edg_06_stake_cap_after_go_live: Param
    edg_06_go_live_min_live_positions: Param
    edg_06_min_stake: Param
    edg_06_combo_stake_cap: Param
    edg_07_max_stake_per_game: Param
    edg_07_weekly_stop: Param


class Backtest(_Group):
    bt_01_decision_hours_before_kickoff: Param
    bt_01_second_pass_minutes_before_kickoff: Param
    bt_01_first_training_season: Param
    bt_01_first_test_season: Param
    bt_01_last_test_season: Param
    bt_01_holdout_season: Param
    bt_01_ftn_first_season: Param
    bt_01_assumed_report_hour_et: Param
    bt_01_assumed_report_days_before_kickoff: Param
    bt_05_min_calibration_slope: Param
    bt_05_max_calibration_slope: Param
    bt_05_min_calibration_forecasts: Param
    bt_05_blend_max_p_value: Param
    bt_05_min_simulated_clv_cc: CenticentParam
    bt_05_min_simulated_positions: Param
    bt_05_simulated_clv_confidence: Param
    bt_05_paper_weeks: Param
    bt_05_min_paper_positions: Param
    bt_06_market_type_min_live_positions: Param
    bt_06_overall_min_live_positions: Param
    bt_06_overall_confidence: Param
    bt_07c_assumed_half_spread_cc: CenticentParam
    bt_07d_min_positions_per_cell: Param
    bt_07d_calibration_gap_max_abs_z: Param
    bt_07d_roi_bootstrap_confidence: Param
    bt_07e_start_units: Param
    bt_07e_max_share_of_hourly_volume: Param


class Params(_Strict):
    conventions: Conventions
    offense: Offense
    defense: Defense
    player: Player
    coaching: Coaching
    matchup: Matchup
    environment: Environment
    projection: Projection
    edge: Edge
    backtest: Backtest


class SeriesFees(_Strict):
    taker_multiplier: StrictInt
    maker_multiplier: StrictInt
    tickers: list[str]


class FeeSeries(_Strict):
    default: SeriesFees
    kxnflgame: SeriesFees = Field(alias="KXNFLGAME")
    kxmve: SeriesFees = Field(alias="KXMVE")
    futures_and_awards: SeriesFees


class ApiFeeType(_Strict):
    maker_multiplier: StrictInt


class ApiFeeTypes(_Strict):
    quadratic: ApiFeeType
    quadratic_with_maker_fees: ApiFeeType
    quadratic_with_combo_maker_fees: ApiFeeType


class AcknowledgedFee(_Strict):
    """A known fees.yaml-vs-API disagreement the user has reviewed (EDG-02)."""

    ticker: str
    field: Literal["taker", "maker"]
    fees_yaml_value: StrictInt | StrictFloat
    api_value: StrictInt | StrictFloat
    api_fee_type: str
    value_in_use: StrictInt | StrictFloat
    reason: Annotated[str, StringConstraints(min_length=1)]
    acknowledged_by: Annotated[str, StringConstraints(min_length=1)]
    acknowledged_on: Annotated[str, StringConstraints(min_length=1)]


class Fees(_Strict):
    spec_id: SpecId
    status: Status
    source_url: str | None
    schedule_effective_date: dt.date
    taker_rate: StrictFloat
    maker_rate: StrictFloat
    rounding: Literal["up_to_cent", "up_to_centicent"]
    api_fee_types: ApiFeeTypes
    series: FeeSeries
    acknowledged: list[AcknowledgedFee]


class IntSetting(_Entry):
    value: StrictInt


class StrSetting(_Entry):
    value: Annotated[str, StringConstraints(min_length=1)]


class HttpSettings(_Group):
    timeout_seconds: IntSetting
    max_attempts: IntSetting
    backoff_initial_seconds: IntSetting
    backoff_max_seconds: IntSetting


class NflverseSettings(_Group):
    first_season: IntSetting
    ftn_first_season: IntSetting
    combine_first_season: IntSetting


class KalshiSettings(_Group):
    base_url: StrSetting
    markets_page_limit: IntSetting
    events_page_limit: IntSetting
    trades_page_limit: IntSetting
    candle_period_minutes: IntSetting


class NwsSettings(_Group):
    base_url: StrSetting
    forecast_window_days: IntSetting


class WikidataSettings(_Group):
    api_url: StrSetting
    search_limit: IntSetting
    entities_batch_size: IntSetting
    coordinate_property: StrSetting
    elevation_property: StrSetting
    located_in_property: StrSetting
    item_url_prefix: StrSetting


class UnitSetting(_Entry):
    unit_qid: Annotated[str, StringConstraints(pattern=r"^Q\d+$")]
    value: StrictInt | StrictFloat  # metres per unit


class ElevationUnits(_Group):
    metre: UnitSetting
    foot: UnitSetting


class IngestConfig(_Strict):
    http: HttpSettings
    nflverse: NflverseSettings
    kalshi: KalshiSettings
    nws: NwsSettings
    wikidata_units: ElevationUnits
    wikidata: WikidataSettings


def _read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    return data


def load_params(path: Path = PARAMS_PATH) -> Params:
    """Load and validate config/params.yaml. Raises pydantic.ValidationError on any bad key."""
    return Params.model_validate(_read_yaml(path))


def load_fees(path: Path = FEES_PATH) -> Fees:
    """EDG-02 Kalshi fee multipliers. Raises pydantic.ValidationError on any bad key."""
    return Fees.model_validate(_read_yaml(path))


def load_ingest(path: Path = INGEST_PATH) -> IngestConfig:
    """Operational settings for `ge ingest`. Raises pydantic.ValidationError on any bad key."""
    return IngestConfig.model_validate(_read_yaml(path))
