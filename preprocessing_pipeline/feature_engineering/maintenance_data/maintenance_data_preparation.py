# maintenance_data_preparation.py

import pandas as pd
import numpy as np

# ======================
# CONSTANTS
# ======================

ASSET_COL = 'asset_id'
DATE_COL = 'date'

PM_DELAY_THRESHOLD = 24

STANDARD_COLUMNS = [

    'asset_id',
    'date',

    'maintenance_type',

    'duration_hours',

    'service_type',

    'fault_category',

    'source_table'
]

# ======================
# HELPER FUNCTIONS
# ======================

def prepare_raw_maintenance_tables(

    pm_df,
    us_df,
    sc_df,
    bo_df
):

    pm_df = pm_df.copy()
    us_df = us_df.copy()
    sc_df = sc_df.copy()
    bo_df = bo_df.copy()

    pm_df['date'] = pd.to_datetime(pm_df['date'])

    us_df['start_date'] = pd.to_datetime(
        us_df['start_date']
    )

    us_df['end_date'] = pd.to_datetime(
        us_df['end_date']
    )

    sc_df['date'] = pd.to_datetime(sc_df['date'])

    bo_df['date'] = pd.to_datetime(bo_df['date'])

    return pm_df, us_df, sc_df, bo_df

def create_source_specific_flags(

    pm_df,
    us_df,
    sc_df,
    bo_df
):

    # PM
    pm_df['last_pm_type'] = (

        pm_df
        .groupby('asset_id')['service_type']
        .shift(1)
    )

    pm_df['overdue_pm_flag'] = (

        pm_df['delay_hours']
        > PM_DELAY_THRESHOLD

    ).astype(int)

    # US
    us_df['critical_us_flag'] = (

        us_df['fault_category']
        .str.contains(
            'CRITICAL',
            case=False,
            na=False
        )

    ).astype(int)

    us_df['electrical_fault_flag'] = (

        us_df['fault_category']
        .str.contains(
            'EL',
            case=False,
            na=False
        )

    ).astype(int)

    # SC
    sc_df['recurring_sc_flag'] = (

        sc_df
        .duplicated(
            subset=['asset_id', 'fault_category'],
            keep=False
        )

    ).astype(int)

    # BO
    bo_df['critical_blackout_flag'] = (

        bo_df['fault_category']
        .str.contains(
            'CRITICAL',
            case=False,
            na=False
        )

    ).astype(int)

    return pm_df, us_df, sc_df, bo_df

def standardize_pm_events(pm_df):

    df = pm_df[[

        'asset_id',
        'date',

        'maintenance_type',
        'duration_hours',

        'service_type',
        'fault_category'

    ]].copy()

    df['source_table'] = 'PM'

    return df[STANDARD_COLUMNS]

def standardize_us_events(us_df):

    df = us_df[[

        'asset_id',

        'start_date',

        'total_downtime_hours',

        'fault_category'

    ]].copy()

    df = df.rename(columns={

        'start_date': 'date',

        'total_downtime_hours':
            'duration_hours'
    })

    df['maintenance_type'] = 'US'

    df['service_type'] = np.nan

    df['source_table'] = 'US'

    return df[STANDARD_COLUMNS]

def standardize_sc_events(sc_df):

    df = sc_df[[

        'asset_id',
        'date',

        'maintenance_type',
        'duration_hours',

        'service_type',
        'fault_category'

    ]].copy()

    df['source_table'] = 'SC'

    return df[STANDARD_COLUMNS]

def standardize_bo_events(bo_df):

    df = bo_df[[

        'asset_id',
        'date',

        'maintenance_type',
        'duration_hours',

        'service_type',
        'fault_category'

    ]].copy()

    df['source_table'] = 'BO'

    return df[STANDARD_COLUMNS]

def build_master_maintenance_df(pm_standardized, us_standardized, sc_standardized, bo_standardized):

    df = pd.concat([

        pm_standardized,
        us_standardized,
        sc_standardized,
        bo_standardized

    ], ignore_index=True)

    df['date'] = pd.to_datetime(
        df['date'],
        errors='coerce'
    )

    df = df.sort_values(

        by=['asset_id', 'date']

    ).reset_index(drop=True)

    return df

def merge_maintenance_metadata(master_df, pm_df, us_df, sc_df, bo_df):

    pm_extra = pm_df[[
    'asset_id',
    'date',
    'planned_hm',
    'actual_hm',
    'delay_hours',
    'last_pm_type',
    'overdue_pm_flag'
    ]].copy()

    us_extra = us_df[[
    'asset_id',
    'start_date',
    'event_id',
    'end_date',
    'initial_fault',
    'critical_us_flag',
    'electrical_fault_flag'
    ]].copy()

    # Standardize timestamp column name
    us_extra = us_extra.rename(columns={
        'start_date': 'date'
    })

    sc_extra = sc_df[[
    'asset_id',
    'date',
    'recurring_sc_flag'
    ]].copy()

    bo_extra = bo_df[[
    'asset_id',
    'date',
    'critical_blackout_flag'
    ]].copy()
    
    master_df = master_df.merge(
    pm_extra,
    on=['asset_id', 'date'],
    how='left'
    )
    master_df = master_df.merge(
        us_extra,
        on=['asset_id', 'date'],
        how='left'
    )
    master_df = master_df.merge(
        sc_extra,
        on=['asset_id', 'date'],
        how='left'
    )
    master_df = master_df.merge(
        bo_extra,
        on=['asset_id', 'date'],
        how='left'
    )
    master_df = master_df.sort_values(
        by=['asset_id', 'date']
    ).reset_index(drop=True)

    return master_df


def prepare_maintenance_data(pm_df, us_df, sc_df, bo_df):

    # Raw prep
    pm_df, us_df, sc_df, bo_df = (
        prepare_raw_maintenance_tables(
            pm_df,
            us_df,
            sc_df,
            bo_df
        )
    )

    # Flags
    pm_df, us_df, sc_df, bo_df = (
        create_source_specific_flags(
            pm_df,
            us_df,
            sc_df,
            bo_df
        )
    )

    # Standardization
    pm_standardized = standardize_pm_events(pm_df)

    us_standardized = standardize_us_events(us_df)

    sc_standardized = standardize_sc_events(sc_df)

    bo_standardized = standardize_bo_events(bo_df)

    # Master event table
    master_df = build_master_maintenance_df(

        pm_standardized,
        us_standardized,
        sc_standardized,
        bo_standardized
    )

    # Metadata enrichment
    master_df = merge_maintenance_metadata(

        master_df,

        pm_df,
        us_df,
        sc_df,
        bo_df
    )

    master_df = master_df.sort_values(
    by=[ASSET_COL, DATE_COL]
    ).reset_index(drop=True)

    return master_df

