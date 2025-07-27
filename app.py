import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Group Life Reinsurance Tool", layout="wide")
st.title("📊 Group Life Reinsurance Analysis Tool")

# --- Input fields ---
scheme = st.text_input("Scheme Name")
country = st.selectbox("Country of Risk", ["Jordan", "Palestine", "Kuwait", "UAE", "Other"])

uploaded_file = st.file_uploader("Upload Census File (Excel)", type=["xlsx"])

# --- Main logic if file is uploaded ---
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    # Assign Member ID if missing
    if 'member_id' not in df.columns:
        df.insert(0, 'member_id', range(1, len(df) + 1))

    # Check required fields
    if 'dob' not in df.columns:
        st.error("Missing required column: 'dob'")
        st.stop()

    # Convert DOB and calculate age
    df['dob'] = pd.to_datetime(df['dob'], errors='coerce')
    df['age'] = df['dob'].apply(lambda d: (datetime.today() - d).days // 365 if pd.notnull(d) else None)
    df = df[df['age'] <= 70]

    # --- SA BASIS SELECTION ---
    st.subheader("🧮 Sum Assured Calculation Basis")

    sa_basis = st.selectbox("Select SA Basis", [
        "Use SA from file (if available)",
        "12 × Monthly Salary",
        "24 × Monthly Salary",
        "Flat amount (coming soon)"
    ])

    # Calculate or fetch SA
    if 'sa' in df.columns and sa_basis == "Use SA from file (if available)":
        df['sum_assured'] = df['sa']
    elif 'salary' in df.columns and ("12 ×" in sa_basis or "24 ×" in sa_basis):
        multiplier = 12 if "12 ×" in sa_basis else 24
        df['sum_assured'] = df['salary'] * multiplier
    else:
        st.error("No valid SA or Salary column found for selected basis.")
        st.stop()

    # --- Calculations ---
    df['weighted_age'] = df['age'] * df['sum_assured']
    total_sa = df['sum_assured'].sum()
    total_weighted_age = df['weighted_age'].sum()
    weighted_age = round(total_weighted_age / total_sa, 2) if total_sa > 0 else 0
    avg_age = round(df['age'].mean(), 2)

    # --- Summary Statistics ---
    st.subheader("📈 Scheme Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Members", len(df))
    col2.metric("Average Age", avg_age)
    col3.metric("Weighted Age", weighted_age)

    col4, col5 = st.columns(2)
    col4.metric("Average SA", f"${round(df['sum_assured'].mean(), 2):,}")
    col5.metric("Total SA", f"${round(df['sum_assured'].sum(), 2):,}")

    # --- Data Quality ---
    st.subheader("⚠️ Data Quality Checks")
    gender_missing = df['gender'].isnull().sum() if 'gender' in df.columns else 'N/A'
    job_missing = df['occupation'].isnull().sum() if 'occupation' in df.columns else 'N/A'

    st.write(f"🔹 Missing Gender: {gender_missing}")
    st.write(f"🔹 Missing Occupation: {job_missing}")

    # --- Census Table Preview ---
    st.subheader("👥 Census Preview")
    st.dataframe(df[['member_id', 'age', 'sum_assured'] + 
                    [col for col in df.columns if col not in ['member_id', 'age', 'sum_assured']]].head(50), 
                 use_container_width=True)

    # --- FCL CALCULATION ---
    st.subheader("🧮 Suggested Free Cover Limit (FCL)")

    def get_fcl_factor(size):
        if size <= 50:
            return 1
        elif size <= 100:
            return 1.5
        elif size <= 250:
            return 2
        elif size <= 500:
            return 3
        else:
            return 4

    fcl_factor = get_fcl_factor(len(df))
    base_fcl = round(fcl_factor * df['sum_assured'].mean(), 2)
    age_flag = avg_age > 45 or weighted_age > 45
    final_fcl = round(base_fcl * 0.75, 2) if age_flag else base_fcl

    st.markdown(f"""
    - 📌 **Group Size**: {len(df)} members  
    - 📌 **Average SA**: ${round(df['sum_assured'].mean(), 2):,}  
    - 📌 **FCL Factor**: {fcl_factor}  
    - 📌 **Base FCL**: ${base_fcl:,.2f}  
    - 📌 **Avg Age**: {avg_age}, Weighted Age: {weighted_age}  
    - ⚠️ {"One or both ages > 45 → Reduction applied (25%)" if age_flag else "Both ages ≤ 45 → No reduction"}  
    """)

    st.success(f"✅ **Suggested FCL: ${final_fcl:,.2f}**")

else:
    st.info("👈 Please upload a valid Excel census file (.xlsx) to begin.")
