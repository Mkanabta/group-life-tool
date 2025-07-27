import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Group Life Reinsurance Tool", layout="wide")

st.title("📊 Group Life Reinsurance Analysis Tool")

# --- Input fields ---
scheme = st.text_input("Scheme Name")
country = st.selectbox("Country of Risk", ["Jordan", "UAE", "KSA", "Other"])

uploaded_file = st.file_uploader("Upload Census File (Excel)", type=["xlsx"])

# --- Main processing ---
if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Clean column names
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    # Assign Member ID if not present
    if 'member_id' not in df.columns:
        df.insert(0, 'member_id', range(1, len(df)+1))

    # Ensure DOB and SA columns exist
    if 'dob' not in df.columns or 'sum_assured' not in df.columns:
        st.error("Missing required columns: 'dob' or 'sum_assured'")
        st.stop()

    # Convert DOB to datetime
    df['dob'] = pd.to_datetime(df['dob'], errors='coerce')
    df['age'] = df['dob'].apply(lambda d: (datetime.today() - d).days // 365 if pd.notnull(d) else None)

    # Filter out invalid or old members
    df = df[df['age'] <= 70]

    # Weighted Age Calculation
    df['weighted_age'] = df['age'] * df['sum_assured']
    total_sa = df['sum_assured'].sum()
    total_weighted_age = df['weighted_age'].sum()
    weighted_age = round(total_weighted_age / total_sa, 2) if total_sa > 0 else 0

    # Summary stats
    st.subheader("🧾 Summary Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Members", len(df))
    col2.metric("Average Age", round(df['age'].mean(), 2))
    col3.metric("Weighted Age", weighted_age)

    col4, col5 = st.columns(2)
    col4.metric("Average SA", f"${round(df['sum_assured'].mean(), 2):,}")
    col5.metric("Total SA", f"${round(df['sum_assured'].sum(), 2):,}")

    # Data completeness
    st.subheader("⚠️ Data Quality Checks")
    missing_gender = df['gender'].isnull().sum() if 'gender' in df.columns else 'N/A'
    missing_occupation = df['occupation'].isnull().sum() if 'occupation' in df.columns else 'N/A'

    st.write(f"🔹 Missing Gender: {missing_gender}")
    st.write(f"🔹 Missing Occupation: {missing_occupation}")

    # Display table
    st.subheader("👥 Census Preview")
    st.dataframe(df.head(50), use_container_width=True)

else:
    st.info("👈 Please upload a valid Excel census file (.xlsx) to begin.")
