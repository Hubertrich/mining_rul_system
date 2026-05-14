# pressure_features.py

import pandas as pd
import numpy as np

from sensor_preparation import (
    prepare_sensor_df,
    MACHINE_COL,
    WINDOW,
    PRESSURE_COLS
)

# ======================
# CONSTANTS
# ======================

PRESSURE_FEATURES = [
    'avg_pressure',
    'pressure_std',
    'fuel_pressure_fluctuation',
    'oil_filter_pressure_rise',

    'oil_pressure_avg_7_window',
    'oil_pressure_std_7_window',
    'crankcase_pressure_avg_7_window',
    'diff_fuel_pressure_avg_7_window',

    'oil_pressure_rise_rate',
    'diff_fuel_pressure_trend',
    'crankcase_pressure_trend',

    'low_oil_pressure_event',
    'low_oil_pressure_events_7_window'
]

# ======================
# HELPER FUNCTIONS
# ======================
def create_base_pressure_features(df):

    df['avg_pressure'] = (
        df[PRESSURE_COLS]
        .mean(axis=1)
    )

    df['pressure_std'] = (
        df[PRESSURE_COLS]
        .std(axis=1)
    )

    return df

def create_pressure_relationship_features(df):

    # Fuel system instability
    df['fuel_pressure_fluctuation'] = (
        df['fuel_pressure']
        -
        df['diff_fuel_pressure']
    ).abs()

    # Oil filter restriction indicator
    df['oil_filter_pressure_rise'] = (
        df['oil_filter_pressure']
        -
        df['oil_pressure']
    )

    return df

def create_pressure_rolling_features(df):

    df['oil_pressure_avg_7_window'] = (
        df
        .groupby(MACHINE_COL)['oil_pressure']
        .transform(
            lambda x: x.rolling(
                WINDOW,
                min_periods=3
            ).mean()
        )
    )

    df['oil_pressure_std_7_window'] = (
        df
        .groupby(MACHINE_COL)['oil_pressure']
        .transform(
            lambda x: x.rolling(
                WINDOW,
                min_periods=3
            ).std()
        )
    )

    df['crankcase_pressure_avg_7_window'] = (
        df
        .groupby(MACHINE_COL)['crankcase_pressure']
        .transform(
            lambda x: x.rolling(
                WINDOW,
                min_periods=3
            ).mean()
        )
    )

    df['diff_fuel_pressure_avg_7_window'] = (
        df
        .groupby(MACHINE_COL)['diff_fuel_pressure']
        .transform(
            lambda x: x.rolling(
                WINDOW,
                min_periods=3
            ).mean()
        )
    )

    return df

def create_pressure_trend_features(df):

    df['oil_pressure_rise_rate'] = (
        df
        .groupby(MACHINE_COL)['oil_pressure']
        .diff()
    )

    df['diff_fuel_pressure_trend'] = (
        df
        .groupby(MACHINE_COL)['diff_fuel_pressure']
        .diff()
    )

    df['crankcase_pressure_trend'] = (
        df
        .groupby(MACHINE_COL)['crankcase_pressure']
        .diff()
    )

    return df

def create_low_oil_pressure_features(df):

    low_oil_threshold = (
        df['oil_pressure']
        .quantile(0.05)
    )

    df['low_oil_pressure_event'] = (
        df['oil_pressure']
        < low_oil_threshold
    ).astype(int)

    df['low_oil_pressure_events_7_window'] = (
        df
        .groupby(MACHINE_COL)['low_oil_pressure_event']
        .transform(
            lambda x: x.rolling(
                WINDOW,
                min_periods=1
            ).sum()
        )
    )

    return df

# ======================
# MAIN FUNCTION
# ======================

def build_pressure_features(sensor_df):

    df = prepare_sensor_df(sensor_df)

    df = create_base_pressure_features(df)

    df = create_pressure_relationship_features(df)

    df = create_pressure_rolling_features(df)

    df = create_pressure_trend_features(df)

    df = create_low_oil_pressure_features(df)

    return df[
        ['timestamp', 'generator_id']
        + PRESSURE_FEATURES
    ]