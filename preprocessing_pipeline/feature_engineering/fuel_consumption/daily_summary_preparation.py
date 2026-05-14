# daily_summary_preparation.py

import pandas as pd

# ======================
# CONSTANTS
# ======================

MACHINE_COL = 'generator_id'
DATE_COL = 'date'

WINDOW = 7

SUMMARY_NUMERIC_COLS = [

    'kwh_daily',

    'fuel_fm_total',
    'fuel_ge_total'
]


# ======================
# HELPER FUNCTIONS
# ======================

def prepare_daily_summary_df(summary_df):

    df = summary_df.copy()

    # Convert datetime
    df[DATE_COL] = pd.to_datetime(
        df[DATE_COL]
    )

    # Convert numeric columns safely
    for col in SUMMARY_NUMERIC_COLS:

        df[col] = pd.to_numeric(
            df[col],
            errors='coerce'
        )

    # Sort correctly
    df = df.sort_values(
        by=[MACHINE_COL, DATE_COL]
    )

    df = df.reset_index(drop=True)

    return df