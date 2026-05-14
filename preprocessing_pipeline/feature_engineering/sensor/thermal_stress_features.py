# thermal_features.py

import pandas as pd
import numpy as np

from sensor_preparation import (
    prepare_sensor_df,
    CYLINDER_TEMP_COLS
)
# ======================
# CONSTANTS
# ======================
WINDOW = 7
MACHINE_COL = 'generator_id'

THERMAL_FEATURES = [
    'avg_cyl_temp',
    'max_cyl_temp',
    'cyl_temp_std',
    'cyl_temp_range',
    'bearing_temp_diff',
    'oil_coolant_temp_ratio',
    'coolant_temp_avg_7_window',
    'coolant_temp_std_7_window',
    'max_cyl_temp_avg_7_window',
    'avg_cyl_temp_trend_7_window',
    'cyl_temp_std_trend_7_window',
    'avg_cyl_temp_slope_7_window',
    'coolant_temp_rise_rate',
    'max_cyl_temp_rise_rate',
    'overheat_event',
    'overheat_event_count_7_window'
]

# ======================
# HELPER FUNCTIONS
# ======================
def create_base_thermal_features(sensor_df):

    df = sensor_df.copy()

    df['avg_cyl_temp'] = (
        df[CYLINDER_TEMP_COLS]
        .mean(axis=1)
    )

    df['max_cyl_temp'] = (
        df[CYLINDER_TEMP_COLS]
        .max(axis=1)
    )

    df['cyl_temp_std'] = (
        df[CYLINDER_TEMP_COLS]
        .std(axis=1)
    )

    df['cyl_temp_range'] = (
        df[CYLINDER_TEMP_COLS].max(axis=1)
        -
        df[CYLINDER_TEMP_COLS].min(axis=1)
    )

    return df

def create_bearing_features(df):

    df['bearing_temp_diff'] = (
        df['front_bearing_temp']
        - df['rear_bearing_temp']
    ).abs()

    return df

def create_thermal_ratio_features(df):

    df['oil_coolant_temp_ratio'] = (
        df['oil_temp']
        /
        (df['coolant_temp'] + 1e-6)
    )

    return df

def create_thermal_rolling_features(df):

    df['coolant_temp_avg_7_window'] = (
        df
        .groupby(MACHINE_COL)['coolant_temp']
        .transform(
            lambda x: x.rolling(
                WINDOW,
                min_periods=3
            ).mean()
        )
    )

    df['coolant_temp_std_7_window'] = (
        df
        .groupby(MACHINE_COL)['coolant_temp']
        .transform(
            lambda x: x.rolling(
                WINDOW,
                min_periods=3
            ).std()
        )
    )

    return df

def create_thermal_trend_features(df):

    df['avg_cyl_temp_slope_7_window'] = (
        df
        .groupby(MACHINE_COL)['avg_cyl_temp']
        .transform(
            lambda x: x.rolling(
                WINDOW,
                min_periods=3
            ).apply(
                lambda y: (
                    y.iloc[-1] - y.iloc[0]
                ) / len(y)
            )
        )
    )

    return df

def create_rise_rate_features(df):

    df['coolant_temp_rise_rate'] = (
        df
        .groupby(MACHINE_COL)['coolant_temp']
        .diff()
    )

    df['max_cyl_temp_rise_rate'] = (
        df
        .groupby(MACHINE_COL)['max_cyl_temp']
        .diff()
    )

    return df

def create_overheat_features(df):

    threshold = df['max_cyl_temp'].quantile(0.95)

    df['overheat_event'] = (
        df['max_cyl_temp'] > threshold
    ).astype(int)

    df['overheat_event_count_7_window'] = (
        df
        .groupby(MACHINE_COL)['overheat_event']
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
def build_thermal_features(sensor_df):

    df = prepare_sensor_df(sensor_df)

    df = create_base_thermal_features(df)

    df = create_bearing_features(df)

    df = create_thermal_ratio_features(df)

    df = create_thermal_rolling_features(df)

    df = create_thermal_trend_features(df)

    df = create_rise_rate_features(df)

    df = create_overheat_features(df)

    return df[
        ['timestamp', 'generator_id']
        + THERMAL_FEATURES
    ]

