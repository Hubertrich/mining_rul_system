# utilization_features.py

import pandas as pd
import numpy as np

from load_preparation import (
    prepare_load_df,
    ASSET_COL,
    DATE_COL,
    LOAD_COL,
    WINDOW_7,
    WINDOW_30,
    HIGH_LOAD_THRESHOLD
)

# ======================
# CONSTANTS
# ======================

OPERATIONAL_FEATURES = [

    'avg_load_7_window',
    'avg_load_30_window',
    'total_load_generated_30_window',

    'high_load_flag',
    'high_load_runtime_ratio_30_window',

    'load_rise_rate',
    'rolling_load_std_7_window',

    'consecutive_high_load_days',

    'site_total_load_daily',
    'load_share_daily',
    'fleet_avg_load',
    'fleet_avg_load_diff',
    'runtime_rank_daily',

    'demand_variability_7_window',
    'peak_demand_flag'
]

# ======================
# HELPER FUNCTIONS
# ======================

def create_rolling_load_features(df):

    df['avg_load_7_window'] = (
        df
        .groupby(ASSET_COL)[LOAD_COL]
        .transform(
            lambda x: x.rolling(
                WINDOW_7,
                min_periods=3
            ).mean()
        )
    )

    df['avg_load_30_window'] = (
        df
        .groupby(ASSET_COL)[LOAD_COL]
        .transform(
            lambda x: x.rolling(
                WINDOW_30,
                min_periods=7
            ).mean()
        )
    )

    df['total_load_generated_30_window'] = (
        df
        .groupby(ASSET_COL)[LOAD_COL]
        .transform(
            lambda x: x.rolling(
                WINDOW_30,
                min_periods=7
            ).sum()
        )
    )

    return df

def create_high_load_features(df):

    df['high_load_flag'] = (
        df[LOAD_COL]
        >= HIGH_LOAD_THRESHOLD
    ).astype(int)

    df['high_load_runtime_ratio_30_window'] = (
        df
        .groupby(ASSET_COL)['high_load_flag']
        .transform(
            lambda x: x.rolling(
                WINDOW_30,
                min_periods=7
            ).mean()
        )
    )

    return df

def create_load_stability_features(df):

    df['load_rise_rate'] = (
        df
        .groupby(ASSET_COL)[LOAD_COL]
        .diff()
    )

    df['rolling_load_std_7_window'] = (
        df
        .groupby(ASSET_COL)[LOAD_COL]
        .transform(
            lambda x: x.rolling(
                WINDOW_7,
                min_periods=3
            ).std()
        )
    )

    df['demand_variability_7_window'] = (
        df
        .groupby(ASSET_COL)[LOAD_COL]
        .transform(
            lambda x: x.rolling(
                WINDOW_7,
                min_periods=3
            ).std()
        )
    )

    return df

def create_consecutive_load_features(df):

    df['consecutive_high_load_days'] = (
        df['high_load_flag']
        .groupby(
            (
                df['high_load_flag']
                !=
                df['high_load_flag'].shift()
            ).cumsum()
        )
        .cumsum()
    )

    return df

def create_fleet_context_features(df):

    # Site total demand
    daily_total_load = (
        df
        .groupby(DATE_COL)[LOAD_COL]
        .sum()
    )

    df['site_total_load_daily'] = (
        df[DATE_COL]
        .map(daily_total_load)
    )

    # Relative burden share
    df['load_share_daily'] = (
        df[LOAD_COL]
        /
        (df['site_total_load_daily'] + 1e-6)
    )

    # Fleet average
    daily_fleet_avg = (
        df
        .groupby(DATE_COL)[LOAD_COL]
        .mean()
    )

    df['fleet_avg_load'] = (
        df[DATE_COL]
        .map(daily_fleet_avg)
    )

    # Deviation from fleet average
    df['fleet_avg_load_diff'] = (
        df[LOAD_COL]
        -
        df['fleet_avg_load']
    )

    return df

def create_utilization_ranking_features(df):

    df['runtime_rank_daily'] = (
        df
        .groupby(DATE_COL)[LOAD_COL]
        .rank(
            ascending=False,
            method='dense'
        )
    )

    return df

def create_peak_demand_features(df):

    peak_threshold = (
        df['site_total_load_daily']
        .quantile(0.90)
    )

    df['peak_demand_flag'] = (
        df['site_total_load_daily']
        >= peak_threshold
    ).astype(int)

    return df

# ======================
# MAIN FUNCTION
# ======================

def build_operational_features(load_df):

    df = prepare_load_df(load_df)

    df = create_rolling_load_features(df)

    df = create_high_load_features(df)

    df = create_load_stability_features(df)

    df = create_consecutive_load_features(df)

    df = create_fleet_context_features(df)

    df = create_utilization_ranking_features(df)

    df = create_peak_demand_features(df)

    return df[
        [DATE_COL, ASSET_COL]
        + OPERATIONAL_FEATURES
    ]