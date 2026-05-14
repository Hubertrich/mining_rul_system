# load_parser.py

import pandas as pd
import os


# ======================
# CONSTANTS
# ======================


# ======================
# HELPER FUNCTIONS
# ======================
def preprocess_load_file(df):
    # --- Clean column names ---
    df.columns = [str(col).strip() for col in df.columns]

    # Drop completely empty columns
    df = df.dropna(axis=1, how='all')

    # --- Detect date column ---
    date_col = None

    for col in df.columns:
        col_clean = str(col).strip().lower()

        if col_clean in ['date', 'tanggal']:
            date_col = col
            break

    if date_col is None:
        raise ValueError("No date/tanggal column found")

    # --- Drop index column like "No" ---
    df = df.drop(
    columns=[col for col in df.columns if 'no' in str(col).lower()],
    errors='ignore'
    )

    # --- Remove junk rows (blank / AVERAGE / TOTAL) ---
    df = df[df[date_col].notna()]
    if df.empty:
        raise ValueError("No valid date rows found after cleaning.")

    # Convert date
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    # Remove invalid dates (e.g., "AVERAGE")
    df = df[df[date_col].notna()]

    # --- Melt (wide → long) ---
    value_cols = [col for col in df.columns if col != date_col]

    df_long = df.melt(
        id_vars=[date_col],
        value_vars=value_cols,
        var_name='asset_id',
        value_name='load_pct'
    )

    # --- Clean fields ---
    df_long['asset_id'] = df_long['asset_id'].astype(str).str.strip()
    df_long['load_pct'] = pd.to_numeric(df_long['load_pct'], errors='coerce')

    df_long = df_long.rename(columns={date_col: 'date'})

    # Final safety (should already be clean)
    df_long = df_long[df_long['date'].notna()]

    return df_long


# ======================
# MAIN PARSER
# ======================

def preprocess_folder(folder_path):

    all_data = []

    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.xlsx') or file.endswith('.xls'):
                file_path = os.path.join(root, file)
                print(f"Processing: {file}")

                try:
                    xls = pd.read_excel(file_path, sheet_name=None, header=3)
                    for sheet_name, df in xls.items():
                        print(f"  → Sheet: {sheet_name}")

                        try:
                            df_clean = preprocess_load_file(df)
                            all_data.append(df_clean)
                        except Exception as e:
                            print(f"  Skipped sheet {sheet_name}: {e}")
                except Exception as e:
                    print(f"Skipped {file}: {e}")

    if not all_data:
        raise ValueError("No valid files processed.")

    load_df = pd.concat(all_data, ignore_index=True)
    load_df = load_df.sort_values(
        by=['asset_id', 'date']
    ).reset_index(drop=True)

    # Round for output
    load_df['load_pct'] = load_df['load_pct'].round(2)
    return load_df

# df_final = preprocess_folder("load_data_folder")

# df_final.to_csv("load_data_clean.csv", index=False)

# print("Done. Rows:", len(df_final))
# print("Saved as:", output_file)




