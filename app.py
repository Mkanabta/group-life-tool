import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Group Life Reinsurance Tool", layout="wide")
st.title("📊 Group Life Reinsurance Analysis Tool")

# Input fields
scheme = st.text_input("Scheme Name")
country = st.selectbox("Country of Risk", ["Jordan", "Palestine", "Kuwait", "UAE", "Other"])
uploaded_file = st.file_uploader("Upload Census File (Excel)", type=["xlsx"])

# For session-based claim storage
if "claims" not in st.session_state:
    st.session_state["claims"] = []

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    if 'member_id' not in df.columns:
        df.insert(0, 'member_id', range(1, len(df) + 1))

    if 'dob' not in df.columns:
        st.error("Missing required column: 'dob'")
        st.stop()

    df['dob'] = pd.to_datetime(df['dob'], errors='coerce')
    df['age'] = df['dob'].apply(lambda d: (datetime.today() - d).days // 365 if pd.notnull(d) else None)
    df = df[df['age'] <= 70]

    # SA Basis selection
    st.subheader("🧮 Sum Assured Calculation Basis")
    sa_basis = st.selectbox("Select SA Basis", [
        "Use SA from file (if available)",
        "12 × Monthly Salary",
        "24 × Monthly Salary",
        "Flat amount (coming soon)"
    ])

    if 'sa' in df.columns and sa_basis == "Use SA from file (if available)":
        df['sum_assured'] = df['sa']
    elif 'salary' in df.columns and ("12 ×" in sa_basis or "24 ×" in sa_basis):
        multiplier = 12 if "12 ×" in sa_basis else 24
        df['sum_assured'] = df['salary'] * multiplier
    else:
        st.error("No valid SA or Salary column found for selected basis.")
        st.stop()

    df['weighted_age'] = df['age'] * df['sum_assured']
    total_sa = df['sum_assured'].sum()
    total_weighted_age = df['weighted_age'].sum()
    weighted_age = round(total_weighted_age / total_sa, 2) if total_sa > 0 else 0
    avg_age = round(df['age'].mean(), 2)

    st.subheader("📈 Scheme Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Members", len(df))
    col2.metric("Average Age", avg_age)
    col3.metric("Weighted Age", weighted_age)

    col4, col5 = st.columns(2)
    col4.metric("Average SA", f"${round(df['sum_assured'].mean(), 2):,}")
    col5.metric("Total SA", f"${round(df['sum_assured'].sum(), 2):,}")

    # Data quality
    st.subheader("⚠️ Data Quality Checks")
    gender_missing = df['gender'].isnull().sum() if 'gender' in df.columns else len(df)
    occ_missing = df['occupation'].isnull().sum() if 'occupation' in df.columns else len(df)

    st.write(f"🔹 Missing Gender: {gender_missing}")
    st.write(f"🔹 Missing Occupation: {occ_missing}")

    # Preview
    st.subheader("👥 Census Preview")
    st.dataframe(df.head(50), use_container_width=True)

    # FCL
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
    - 📌 **Group Size**: {len(df)}  
    - 📌 **FCL Factor**: {fcl_factor}  
    - 📌 **Base FCL**: ${base_fcl:,.2f}  
    - 📌 **Age Flag**: {"Yes → 25% reduction" if age_flag else "No reduction"}  
    """)
    st.success(f"✅ **Suggested FCL: ${final_fcl:,.2f}**")

    # --- CLAIMS SECTION ---
    st.subheader("📂 Claims Experience & Credibility")

    claim_option = st.radio("Select claims experience type:", [
        "Full Claims Data Provided",
        "Clean Record (No Claims)",
        "Virgin Scheme (First-Time Cover)"
    ])

    claims_df = pd.DataFrame(st.session_state["claims"])

    if claim_option == "Full Claims Data Provided":
        with st.form("claims_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            year = col1.number_input("Claim UWY", min_value=2000, max_value=datetime.today().year, step=1)
            amount = col2.number_input("Claim Amount Paid (USD)", min_value=0.0, step=100.0)
            benefit = col3.selectbox("Benefit Type", ["DAC", "AccDeath", "TPD", "PPD", "TTD", "MedEx", "Repatriation"])
            submitted = st.form_submit_button("Add Claim")
            if submitted and amount > 0:
                st.session_state["claims"].append({
                    "claim_uwy": year,
                    "claim_amount": amount,
                    "benefit_type": benefit
                })

        if not claims_df.empty:
            st.dataframe(claims_df, use_container_width=True)
            claim_years = claims_df["claim_uwy"].nunique()
            total_claims_paid = claims_df["claim_amount"].sum()
        else:
            st.info("➕ Add at least one claim record to compute credibility.")
            claim_years = 0
            total_claims_paid = 0

    elif claim_option == "Clean Record (No Claims)":
        claim_years = 3
        total_claims_paid = 0
        st.info("✅ Assuming 3 clean claim years for pricing.")

    elif claim_option == "Virgin Scheme (First-Time Cover)":
        claim_years = 0
        total_claims_paid = 0
        st.warning("🧪 Virgin scheme → No credibility (0%)")

    # --- CREDIBILITY CALC ---
    st.subheader("📊 Credibility Assessment")

    def credibility_table(n_lives, years):
        # Based on simplified table you shared
        if n_lives <= 500:
            if years == 1: return 0.02
            if years == 2: return 0.03
            if years == 3: return 0.05
            if years == 4: return 0.07
            if years >= 5: return 0.10
        return 0.10  # default max

    base_cred = credibility_table(len(df), claim_years)
    data_bonus = 0
    if gender_missing == 0:
        data_bonus += 0.02
    if occ_missing == 0:
        data_bonus += 0.02

    final_credibility = min(round((base_cred + data_bonus) * 100, 2), 100)

    st.markdown(f"""
    - 📌 **Members**: {len(df)}  
    - 📌 **Claim Years**: {claim_years}  
    - 📌 **Total Claims Paid**: ${total_claims_paid:,.2f}  
    - 📌 **Base Credibility**: {base_cred*100:.1f}%  
    - 🎁 **Data Bonus**: {data_bonus*100:.1f}%  
    """)
    st.success(f"✅ **Final Credibility Factor: {final_credibility}%**")

else:
    st.info("👈 Please upload a valid Excel census file (.xlsx) to begin.")
