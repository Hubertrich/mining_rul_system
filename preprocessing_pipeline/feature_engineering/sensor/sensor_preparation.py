# sensor_preparation.py

import pandas as pd

# ======================
# CONSTANTS
# ======================

MACHINE_COL = 'generator_id'
TIMESTAMP_COL = 'timestamp'

NUMERIC_COLS = [
    'hour_meter',

    'oil_pressure',

    'cyl_1_temp',
    'cyl_2_temp',
    'cyl_3_temp',
    'cyl_4_temp',
    'cyl_5_temp',
    'cyl_6_temp',
    'cyl_7_temp',
    'cyl_8_temp',
    'cyl_9_temp',
    'cyl_10_temp',
    'cyl_11_temp',
    'cyl_12_temp',
    'cyl_13_temp',
    'cyl_14_temp',
    'cyl_15_temp',
    'cyl_16_temp',

    'front_bearing_temp',
    'rear_bearing_temp',

    'oil_temp',
    'coolant_temp',

    'fuel_pressure',
    'diff_fuel_pressure',
    'oil_filter_pressure',
    'air_filter_pressure',
    'crankcase_pressure',

    'kw',
    'kva',
    'cos_phi',

    'amp_r',
    'amp_s',
    'amp_t',

    'load_percent'
]

CYLINDER_TEMP_COLS = [
    'cyl_1_temp',
    'cyl_2_temp',
    'cyl_3_temp',
    'cyl_4_temp',
    'cyl_5_temp',
    'cyl_6_temp',
    'cyl_7_temp',
    'cyl_8_temp',
    'cyl_9_temp',
    'cyl_10_temp',
    'cyl_11_temp',
    'cyl_12_temp',
    'cyl_13_temp',
    'cyl_14_temp',
    'cyl_15_temp',
    'cyl_16_temp'
]

PRESSURE_COLS = [
    'oil_pressure',
    'fuel_pressure',
    'diff_fuel_pressure',
    'oil_filter_pressure',
    'crankcase_pressure'
]

WINDOW = 7


# ======================
# HELPER FUNCTIONS
# ======================

def prepare_sensor_df(sensor_df):

    df = sensor_df.copy()

    # Convert numeric columns safely
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(
            df[col],
            errors='coerce'
        )

    # Remove missing rows
    df = df[
        df['is_missing'] == False
    ].copy()

    # Convert timestamp
    df[TIMESTAMP_COL] = pd.to_datetime(
        df[TIMESTAMP_COL]
    )

    # Sort properly
    df = df.sort_values(
        by=[MACHINE_COL, TIMESTAMP_COL]
    )

    df = df.reset_index(drop=True)

    # Fill missing numeric values
    df[NUMERIC_COLS] = (
        df
        .groupby(MACHINE_COL)[NUMERIC_COLS]
        .transform(
            lambda x: x.ffill().bfill()
        )
    )

    return df