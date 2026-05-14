# load_preparation.py

import pandas as pd

# ======================
# CONSTANTS
# ======================

ASSET_COL = 'asset_id'
DATE_COL = 'date'

LOAD_COL = 'load_pct'

WINDOW_7 = 7
WINDOW_30 = 30

HIGH_LOAD_THRESHOLD = 68


# ======================
# HELPER FUNCTIONS
# ======================

def prepare_load_df(load_df):

    df = load_df.copy()

    # Convert date column
    df[DATE_COL] = pd.to_datetime(
        df[DATE_COL]
    )

    # Convert load column safely
    df[LOAD_COL] = pd.to_numeric(
        df[LOAD_COL],
        errors='coerce'
    )

    # Sort correctly
    df = df.sort_values(
        by=[ASSET_COL, DATE_COL]
    )

    df = df.reset_index(drop=True)

    return df