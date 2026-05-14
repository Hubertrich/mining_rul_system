# fuel_consumption_features.py

import pandas as pd
import numpy as np

from daily_summary_preparation import (

    prepare_daily_summary_df,

    MACHINE_COL,
    DATE_COL,
    WINDOW
)

# ======================
# CONSTANTS
# ======================

FUEL_FEATURES = [

    'fuel_per_kwh_fm',
    'fuel_per_kwh_ge',

    'kwh_per_fuel_fm',
    'kwh_per_fuel_ge',

    'fuel_measurement_diff',
    'fuel_measurement_ratio',

    'abnormal_fuel_gap_flag',

    'fuel_efficiency_trend_7_window',
    'fuel_efficiency_std_7_window',

    'site_total_kwh_daily',
    'location_load_share'
]

GLOBAL_FEATURES = [

    'fuel_fm_total',
    'fuel_ge_total',

    'fuel_measurement_diff',
    'fuel_measurement_ratio',

    'abnormal_fuel_gap_flag',

    'site_total_kwh_daily'
]

PIVOT_FEATURES = [

    'kwh_prev_month',
    'kwh_daily',
    'kwh_cumulative',

    'fuel_per_kwh_fm',
    'fuel_per_kwh_ge',

    'kwh_per_fuel_fm',
    'kwh_per_fuel_ge',

    'fuel_efficiency_trend_7_window',
    'fuel_efficiency_std_7_window',

    'location_load_share'
]

# ======================
# HELPER FUNCTIONS
# ======================

def create_fuel_efficiency_features(df):

    # Fuel per kWh
    df['fuel_per_kwh_fm'] = (
        df['fuel_fm_total']
        /
        (df['kwh_daily'] + 1e-6)
    )

    df['fuel_per_kwh_ge'] = (
        df['fuel_ge_total']
        /
        (df['kwh_daily'] + 1e-6)
    )

    # Output efficiency
    df['kwh_per_fuel_fm'] = (
        df['kwh_daily']
        /
        (df['fuel_fm_total'] + 1e-6)
    )

    df['kwh_per_fuel_ge'] = (
        df['kwh_daily']
        /
        (df['fuel_ge_total'] + 1e-6)
    )

    return df

def create_fuel_consistency_features(df):

    df['fuel_measurement_diff'] = (
        df['fuel_fm_total']
        -
        df['fuel_ge_total']
    )

    df['fuel_measurement_ratio'] = (
        df['fuel_ge_total']
        /
        (df['fuel_fm_total'] + 1e-6)
    )

    return df

def create_fuel_anomaly_features(df):

    diff_threshold = (
        df['fuel_measurement_diff']
        .quantile(0.95)
    )

    df['abnormal_fuel_gap_flag'] = (
        df['fuel_measurement_diff']
        >
        diff_threshold
    ).astype(int)

    return df

def create_rolling_fuel_features(df):

    df['fuel_efficiency_trend_7_window'] = (
        df
        .groupby(MACHINE_COL)['fuel_per_kwh_fm']
        .transform(
            lambda x: x.rolling(
                WINDOW,
                min_periods=3
            ).mean()
        )
    )

    df['fuel_efficiency_std_7_window'] = (
        df
        .groupby(MACHINE_COL)['fuel_per_kwh_fm']
        .transform(
            lambda x: x.rolling(
                WINDOW,
                min_periods=3
            ).std()
        )
    )

    return df

def create_site_context_features(df):

    daily_total_kwh = (
        df
        .groupby(DATE_COL)['kwh_daily']
        .sum()
    )

    df['site_total_kwh_daily'] = (
        df[DATE_COL]
        .map(daily_total_kwh)
    )

    df['location_load_share'] = (
        df['kwh_daily']
        /
        (df['site_total_kwh_daily'] + 1e-6)
    )

    return df

def pivot_location_features(df):

    df = df.rename(
        columns={
            'generator_id': 'asset_id'
        }
    )

    pivot_df = df.pivot_table(

        index=['date', 'asset_id'],

        columns='location',

        values=PIVOT_FEATURES
    )

    pivot_df.columns = [

        f'{location}_{feature}'

        for feature, location
        in pivot_df.columns
    ]

    pivot_df = pivot_df.reset_index()

    return pivot_df

def create_global_summary_features(df):

    global_df = df[[

        'date',
        'asset_id',

        *GLOBAL_FEATURES

    ]].drop_duplicates()

    return global_df

def merge_pivot_and_global_features(

    pivot_df,
    global_df
):

    final_df = pivot_df.merge(

        global_df,

        on=['date', 'asset_id'],

        how='left'
    )

    return final_df

# ======================
# MAIN FUNCTION
# ======================

def build_fuel_consumption_features(summary_df):

    df = prepare_daily_summary_df(summary_df)

    # ======================
    # FEATURE ENGINEERING
    # ======================

    df = create_fuel_efficiency_features(df)

    df = create_fuel_consistency_features(df)

    df = create_fuel_anomaly_features(df)

    df = create_rolling_fuel_features(df)

    df = create_site_context_features(df)

    # ======================
    # RESHAPING
    # ======================

    pivot_df = pivot_location_features(df)

    global_df = create_global_summary_features(df)

    final_df = merge_pivot_and_global_features(

        pivot_df,
        global_df
    )

    return final_df