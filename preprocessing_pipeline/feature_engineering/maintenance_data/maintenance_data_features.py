# maintenance_features.py

import pandas as pd
import numpy as np

from maintenance_data_preparation import (

    prepare_maintenance_data,

    ASSET_COL,
    DATE_COL
)

# ======================
# CONSTANTS
# ======================

ROLLING_WINDOW = '90D'

FEATURE_COLS = [

    'days_since_last_pm',
    'days_since_last_us',
    'days_since_last_sc',
    'days_since_last_bo',

    'pm_count_90d',
    'us_count_90d',
    'sc_count_90d',
    'bo_count_90d',

    'electrical_fault_count_90d',

    'avg_pm_delay_90d',
    'max_pm_delay_90d',

    'avg_downtime_90d',
    'max_downtime_90d'
]

# ======================
# HELPER FUNCTIONS
# ======================

def create_maintenance_event_flags(df):

    df['is_pm'] = (
        df['maintenance_type'] == 'PM'
    ).astype(int)

    df['is_us'] = (
        df['maintenance_type'] == 'US'
    ).astype(int)

    df['is_sc'] = (
        df['maintenance_type'] == 'SC'
    ).astype(int)

    df['is_bo'] = (
        df['maintenance_type'] == 'BO'
    ).astype(int)

    return df

def create_days_since_features(df):

    event_types = ['PM', 'US', 'SC', 'BO']

    for event in event_types:

        last_event_col = f'last_{event.lower()}_date'

        days_col = f'days_since_last_{event.lower()}'

        df[last_event_col] = (
            df
            .where(
                df['maintenance_type'] == event
            )[DATE_COL]
        )

        df[last_event_col] = (
            df
            .groupby(ASSET_COL)[last_event_col]
            .ffill()
        )

        df[days_col] = (
            df[DATE_COL]
            -
            df[last_event_col]
        ).dt.days

    return df

def create_rolling_maintenance_counts(df):

    df = df.set_index(DATE_COL)

    maintenance_types = ['pm', 'us', 'sc', 'bo']

    for event in maintenance_types:

        flag_col = f'is_{event}'

        count_col = f'{event}_count_90d'

        df[count_col] = (

            df
            .groupby(ASSET_COL)[flag_col]
            .rolling(ROLLING_WINDOW)
            .sum()
            .reset_index(level=0, drop=True)
        )

    df = df.reset_index()

    return df

def create_fault_history_features(df):

    df['electrical_fault_flag'] = (
        df['electrical_fault_flag']
        .fillna(0)
    )

    df = df.set_index(DATE_COL)

    df['electrical_fault_count_90d'] = (

        df
        .groupby(ASSET_COL)['electrical_fault_flag']
        .rolling(ROLLING_WINDOW)
        .sum()
        .reset_index(level=0, drop=True)
    )

    df = df.reset_index()

    return df

def create_pm_delay_features(df):

    df['pm_delay_hours'] = np.where(

        df['maintenance_type'] == 'PM',

        df['delay_hours'],

        np.nan
    )

    df = df.set_index(DATE_COL)

    df['avg_pm_delay_90d'] = (

        df
        .groupby(ASSET_COL)['pm_delay_hours']
        .rolling(
            ROLLING_WINDOW,
            min_periods=1
        )
        .mean()
        .reset_index(level=0, drop=True)
    )

    df['max_pm_delay_90d'] = (

        df
        .groupby(ASSET_COL)['pm_delay_hours']
        .rolling(
            ROLLING_WINDOW,
            min_periods=1
        )
        .max()
        .reset_index(level=0, drop=True)
    )

    df = df.reset_index()

    return df

def create_downtime_features(df):

    df = df.set_index(DATE_COL)

    df['avg_downtime_90d'] = (

        df
        .groupby(ASSET_COL)['duration_hours']
        .rolling(ROLLING_WINDOW)
        .mean()
        .reset_index(level=0, drop=True)
    )

    df['max_downtime_90d'] = (

        df
        .groupby(ASSET_COL)['duration_hours']
        .rolling(ROLLING_WINDOW)
        .max()
        .reset_index(level=0, drop=True)
    )

    df = df.reset_index()

    return df

# ======================
# MAIN FUNCTION
# ======================

def build_maintenance_features(

    pm_df,
    us_df,
    sc_df,
    bo_df
):

    df = prepare_maintenance_data(

        pm_df,
        us_df,
        sc_df,
        bo_df
    )

    df = create_maintenance_event_flags(df)

    df = create_days_since_features(df)

    df = create_rolling_maintenance_counts(df)

    df = create_fault_history_features(df)

    df = create_pm_delay_features(df)

    df = create_downtime_features(df)

    df = df.sort_values(
        by=[ASSET_COL, DATE_COL]
    ).reset_index(drop=True)

    return df[
        [DATE_COL, ASSET_COL]
        + FEATURE_COLS
    ]
