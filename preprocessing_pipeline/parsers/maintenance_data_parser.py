# maintenance_data_parser.py
import pandas as pd
import re
import zipfile
import os
from tqdm import tqdm
import shutil


# ======================
# CONSTANTS
# ======================


# ======================
# HELPER FUNCTIONS
# ======================
def load_monthly_report(file_name):
    df = pd.read_excel(
        file_name,
        sheet_name='Daily Breakdown',
        header=0
    )

    # Rename columns (adjust if structure shifts)
    df = df.rename(columns={
        'Unnamed: 4': 'date',
        'Unnamed: 5': 'asset_id',
        'Unnamed: 9': 'duration',
        'Unnamed: 10': 'bd_type',
        'Unnamed: 11': 'description',
        'Unnamed: 12': 'action'
    })

    df = df[['date', 'asset_id', 'duration', 'bd_type', 'description', 'action']]

    # Remove repeated headers
    df = df[df['date'] != 'Date']

    # Drop empty rows
    df = df.dropna(subset=['date', 'asset_id'])

    # Convert date
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Clean duration → float hours
    df['duration_hours'] = (
        df['duration']
        .astype(str)
        .str.replace(',', '.')
        .str.extract(r'(\d+\.?\d*)')[0]
        .astype(float)
    )

    # Remove DAILY INSPECTION noise
    df = df[~df['description'].str.contains('DAILY INSPECTION', na=False)]

    # Normalize text (important later)
    df['description'] = df['description'].astype(str).str.strip()
    df['action'] = df['action'].astype(str).str.strip()

    return df

# Important keep the df it contains all types of maintenance data
def region_limiter(df):
    df = df.copy()  # avoid mutating original df

    # Extract numeric part of asset_id
    df['asset_num'] = df['asset_id'].str.extract(r'(\d+)$').astype(float)

    # Filter range 018–023
    df = df[(df['asset_num'] >= 18) & (df['asset_num'] <= 23)]

    # Drop helper column
    df = df.drop(columns=['asset_num'])

    return df

def format_duration(hours):
    if pd.isna(hours):
        return None
    total_minutes = int(round(hours * 60))
    h = total_minutes // 60
    m = total_minutes % 60

    if h > 0:
        return f"{h}h {m}m"
    else:
        return f"{m}m"
    
def extract_service_type(desc):
    match = re.search(r'SERVICE.*?(\d+)', str(desc))
    if match:
        val = int(match.group(1))
        return val % 1000 or 1000
    return None

def extract_hm(action):
    match = re.search(r'PM\s+(\d+).*HM\s+(\d+)', str(action))
    if match:
        planned = int(match.group(1))
        actual = int(match.group(2))
        return planned, actual, actual - planned
    return None, None, None

def load_and_combine_reports(uploaded_files):

    all_df = []

    for file_name in uploaded_files.keys():
        df = load_monthly_report(file_name)
        all_df.append(df)

    combined_df = pd.concat(all_df, ignore_index=True)

    return combined_df

# it should generate 14 columns
def extract_pm(df):

    df = region_limiter(df)

    pm_df = df[df['bd_type'] == 'PM'].copy()

    # Duration formatting
    pm_df['duration_str'] = pm_df['duration_hours'].apply(format_duration)

    # Service type extraction
    pm_df['service_type'] = pm_df['description'].apply(extract_service_type)

    # HM extraction (cleaner + scalable)
    pm_df[['planned_hm', 'actual_hm', 'delay_hours']] = pd.DataFrame(
        pm_df['action'].apply(extract_hm).tolist(),
        index=pm_df.index
    )

    # Standard fields
    pm_df['maintenance_type'] = 'PM'
    pm_df['fault_category'] = None
    pm_df['fault_detail'] = None
    pm_df['source_sheet'] = 'Daily Breakdown'

    # Final schema (14 columns)
    pm_df = pm_df[[
        'asset_id',
        'date',
        'maintenance_type',
        'duration_hours',
        'duration_str',
        'description',
        'action',
        'service_type',
        'planned_hm',
        'actual_hm',
        'delay_hours',
        'fault_category',
        'fault_detail',
        'source_sheet'
    ]]

    return pm_df

def extract_us(df):

    df = region_limiter(df)

    us_df = df[df['bd_type'] == 'US'].copy()

    us_df['maintenance_type'] = 'US'
    us_df['fault_detail'] = us_df['action']

    # keep consistent with PM
    us_df['duration_str'] = us_df['duration_hours'].apply(format_duration)

    # PM-only fields → NULL
    us_df['service_type'] = None
    us_df['planned_hm'] = None
    us_df['actual_hm'] = None
    us_df['delay_hours'] = None
    us_df['fault_category'] = None
    us_df['source_sheet'] = 'Daily Breakdown'

    # match PM schema (14 columns)
    us_df = us_df[[
        'asset_id',
        'date',
        'maintenance_type',
        'duration_hours',
        'duration_str',
        'description',
        'action',
        'service_type',
        'planned_hm',
        'actual_hm',
        'delay_hours',
        'fault_category',
        'fault_detail',
        'source_sheet'
    ]]

    return us_df

def prepare_us_data(us_df):

    us_df = us_df.copy()

    us_df = us_df.sort_values(['asset_id', 'date'])

    # previous date per asset
    us_df['prev_date'] = us_df.groupby('asset_id')['date'].shift(1)

    # gap in days
    us_df['date_diff'] = (us_df['date'] - us_df['prev_date']).dt.days

    return us_df

def assign_event_ids(us_df):

    us_df = us_df.copy()

    # new event if gap > 1 day OR first record
    us_df['new_event'] = (
        us_df['date_diff'].isna() |
        (us_df['date_diff'] > 1)
    )

    # cumulative event id per asset
    us_df['event_id'] = us_df.groupby('asset_id')['new_event'].cumsum()

    return us_df

def classify_us_system(text):

    if any(k in text for k in [
        "ecu", "alternator", "voltage", "sensor", "relay", "sinkron"
    ]):
        return "EL"

    elif any(k in text for k in [
        "radiator", "overheat", "water pump", "coolant"
    ]):
        return "CO"

    elif any(k in text for k in [
        "oil", "gasket", "o-ring", "cylinder", "liner"
    ]):
        return "EN"

    elif any(k in text for k in [
        "fuel", "solar", "injector", "pump"
    ]):
        return "FU"

    return "OT"

def classify_us_category(text):

    # LEAK
    if "bocor" in text:
        return "LEAK"

    # OVERHEAT / TEMP
    elif "overheat" in text:
        return "OVERHEAT"

    # ELECTRICAL INSTABILITY
    elif any(k in text for k in ["over voltage", "overcharge", "sinkron"]):
        return "INSTABILITY"

    # CONTAMINATION
    elif any(k in text for k in ["bercampur", "kontaminasi"]):
        return "CONTAMINATION"

    # WEAR / DAMAGE
    elif any(k in text for k in ["aus", "rusak"]):
        return "WEAR"

    # ECU SPECIFIC
    elif "ecu" in text:
        return "ECU"

    return "GENERAL"

def classify_us_severity(text):

    if "tidak dapat running" in text:
        return "CRITICAL"

    elif any(k in text for k in ["overheat", "over voltage"]):
        return "HIGH"

    elif any(k in text for k in ["indikasi", "temuan"]):
        return "EARLY"

    return "MEDIUM"

def classify_us_event(full_text):
    text = str(full_text).lower()

    system = classify_us_system(text)
    category = classify_us_category(text)
    severity = classify_us_severity(text)

    return f"{system}-{category}-{severity}"

def build_us_events(us_df):

    events = us_df.groupby(['asset_id', 'event_id']).agg({
        'date': ['min', 'max'],
        'duration_hours': 'sum',
        'fault_detail': 'first',
        'fault_category': 'first'
    }).reset_index()

    events.columns = [
        'asset_id',
        'event_id',
        'start_date',
        'end_date',
        'total_downtime_hours',
        'initial_fault',
        'fault_category'
    ]

    return events

def extract_us_events_from_df(df):

    us_df = extract_us(df)

    us_df['full_text'] = (
        us_df['description'].fillna('') + ' | ' + us_df['fault_detail'].fillna('')
    )

    us_df['fault_category'] = us_df['full_text'].apply(classify_us_event)

    us_df = prepare_us_data(us_df)
    us_df = assign_event_ids(us_df)

    us_events = build_us_events(us_df)

    # final clean
    us_df = us_df[[
        'asset_id','date','maintenance_type','duration_hours','duration_str',
        'description','action','service_type','planned_hm','actual_hm',
        'delay_hours','fault_category','fault_detail','source_sheet'
    ]]

    return us_df, us_events

def classify_system(text):

    # ENGINE (EN)
    if any(k in text for k in [
        "engine", "radiator", "fan", "belt", "coolant", "overheat"
    ]):
        return "EN"

    # ELECTRICAL (EL)
    elif any(k in text for k in [
        "baterry", "accu", "alternator", "voltage", "sensor", "relay", "solenoid"
    ]):
        return "EL"

    # FUEL SYSTEM (FU)
    elif any(k in text for k in [
        "fuel", "solar", "filter", "injektor", "injector", "pump", "rakor"
    ]):
        return "FU"

    # AIR / INTAKE (AR)
    elif any(k in text for k in [
        "air filter", "intake", "turbo"
    ]):
        return "AR"

    return "OT"  # OTHER

def classify_action(text):

    if "clean" in text:
        return "CLEANING"

    elif "replace" in text or "mengganti" in text or "penggantian" in text or "ganti" in text:
        return "REPLACEMENT"

    elif "adjust" in text or "kencang" in text or "pengencangan" in text:
        return "ADJUSTMENT"

    elif "troubleshoot" in text:
        return "TROUBLESHOOTING"

    elif "repair" in text:
        return "REPAIR"

    return "OTHER"

def classify_sc_action(action):
    text = str(action).lower()

    system = classify_system(text)
    action_type = classify_action(text)

    return f"{system}-{action_type}"

def extract_sc(df):

    df = region_limiter(df)

    sc_df = df[df['bd_type'] == 'SC'].copy()

    # Classification
    sc_df['service_type'] = sc_df['action'].apply(classify_sc_action)

    # Standard structure
    sc_df['maintenance_type'] = 'SC'

    sc_df['fault_category'] = None
    sc_df['fault_detail'] = None   # 🔥 remove redundancy

    sc_df['planned_hm'] = None
    sc_df['actual_hm'] = None
    sc_df['delay_hours'] = None

    sc_df['source_sheet'] = 'Daily Breakdown'

    sc_df['duration_str'] = sc_df['duration_hours'].apply(format_duration)

    sc_df = sc_df[[
        'asset_id',
        'date',
        'maintenance_type',
        'duration_hours',
        'duration_str',
        'description',
        'action',
        'service_type',
        'planned_hm',
        'actual_hm',
        'delay_hours',
        'fault_category',
        'fault_detail',
        'source_sheet'
    ]]

    return sc_df

def build_sc_table(sc_df):

    sc_table = sc_df.groupby(['asset_id', 'date', 'service_type']).agg({
        'duration_hours': 'sum',
        'fault_detail': 'first'
    }).reset_index()

    sc_table.columns = [
        'asset_id',
        'date',
        'sc_code',
        'total_duration_hours',
        'initial_action'
    ]

    return sc_table

def classify_bo_event(text):
    text = str(text).lower()

    # ---------------- KEYWORDS (centralized) ----------------
    el_keywords = [
        "voltage", "current", "frequency", "kw", "kva", "acb", "gcb",
        "bus", "sync", "load","short","singkron"
    ]

    en_keywords = [
        "engine", "overheat", "rpm", "radiator", "fuel", "belt"
    ]

    ot_keywords = [
        "switching", "request", "pemasangan", "pengambungan",
        "sampling", "pengerjaan", "top up", "purifikasi","instalasi"
    ]

    # ---------------- SYSTEM ----------------
    if any(k in text for k in el_keywords):
        system = "EL"
    elif any(k in text for k in en_keywords):
        system = "EN"
    else:
        system = "OT"

    # ---------------- CATEGORY ----------------
    if "black out" in text:
        category = "BLACKOUT"

    elif "trip" in text:
        category = "TRIP"

    elif any(k in text for k in [
        "overload", "over current", "over voltage",
        "under voltage", "drop voltage",
        "under frekuency", "low frequency", "high frekuency",
        "unbalance", "out of sync", "singkron"
    ]):
        category = "INSTABILITY"

    elif any(k in text for k in [
        "overheat", "engine fault", "rpm", "fuel", "belt"
    ]):
        category = "ENGINE"

    elif any(k in text for k in ot_keywords):
        category = "OPERATIONAL"

    else:
        category = "GENERAL"

    # ---------------- 🔥 CONDITIONAL OVERRIDE ----------------
    if category == "TRIP":
        has_en = any(k in text for k in en_keywords)
        has_ot = any(k in text for k in ot_keywords)

        # ONLY override if it's not clearly EN or OT
        if not has_en and not has_ot:
            system = "EL"

    # ---------------- SEVERITY ----------------
    if category == "BLACKOUT":
        severity = "CRITICAL"

    elif category == "TRIP":
        severity = "HIGH"

    elif category in ["INSTABILITY", "ENGINE"]:
        severity = "MEDIUM"

    else:
        severity = "LOW"

    return f"{system}-{category}-{severity}"

def extract_bo(df):

    # df = region_limiter(df)

    bo_df = df[df['bd_type'] == 'BO'].copy()

    # Classification
    bo_df['fault_category'] = bo_df['action'].apply(classify_bo_event)

    # Structure (aligned with US)
    bo_df['maintenance_type'] = 'BO'

    bo_df['fault_detail'] = bo_df['action']
    bo_df['action'] = None

    bo_df['service_type'] = None
    bo_df['planned_hm'] = None
    bo_df['actual_hm'] = None
    bo_df['delay_hours'] = None

    bo_df['source_sheet'] = 'Daily Breakdown'

    bo_df['duration_str'] = bo_df['duration_hours'].apply(format_duration)

    bo_df = bo_df[[
        'asset_id',
        'date',
        'maintenance_type',
        'duration_hours',
        'duration_str',
        'description',
        'action',
        'service_type',
        'planned_hm',
        'actual_hm',
        'delay_hours',
        'fault_category',
        'fault_detail',
        'source_sheet'
    ]]

    return bo_df

# ======================
# MAIN PARSER
# ======================

def process_maintenance_zip(zip_path):

    # ---------------- STEP 1: Upload ZIP ----------------
    zip_name = zip_path

    # ---------------- STEP 2: Extract ZIP ----------------
    extract_path = "temp_extracted_files"

    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)

    with zipfile.ZipFile(zip_name, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    # ---------------- STEP 3: Collect Excel files ----------------
    excel_files = []

    for root, _, files_list in os.walk(extract_path):
        for file in files_list:
            if file.endswith(".xlsx"):
                excel_files.append(os.path.join(root, file))

    print(f"📂 Total files found: {len(excel_files)}")

    # ---------------- STEP 4: Combine all reports ----------------
    combined_list = []

    for file_path in tqdm(excel_files, desc="📊 Loading Excel files"):
        try:
            df = load_monthly_report(file_path)
            combined_list.append(df)
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")

    if not combined_list:
        raise ValueError("No valid Excel files found in ZIP.")

    combined_df = pd.concat(combined_list, ignore_index=True)
    # ---------------- CLEAN + SORT (IMPORTANT) ----------------
    print("🔄 Sorting by asset_id and date...")

    # ensure proper datetime
    combined_df["date"] = pd.to_datetime(combined_df["date"], errors="coerce")

    # normalize asset_id (important if strings have spaces like "PSPWGE 18")
    combined_df["asset_id"] = combined_df["asset_id"].astype(str).str.strip()

    # sort
    combined_df = combined_df.sort_values(
        by=["asset_id", "date"],
        ascending=[True, True]
    ).reset_index(drop=True)

    print("📦 Combined DF shape:", combined_df.shape)



    # ---------------- STEP 5: Run all extractors ----------------
    print("\n⚙️ Running extractors...")

    pm_df = extract_pm(combined_df)
    us_df, us_events = extract_us_events_from_df(combined_df)
    sc_df = extract_sc(combined_df)
    sc_table = build_sc_table(sc_df)
    bo_df = extract_bo(combined_df)

    return {
    "pm_df": pm_df,
    "us_df": us_df,
    "us_events": us_events,
    "sc_df": sc_df,
    "sc_table": sc_table,
    "bo_df": bo_df
    }

# output_path = process_maintenance_zip()

if __name__ == "__main__":

    results = process_maintenance_zip("sample.zip")

    print(results.keys())





