import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import datetime

st.set_page_config(page_title="Group Life Reinsurance Tool", layout="wide")
st.title("Group Life Reinsurance Analysis Tool")

# --- Input: Scheme Details ---
scheme_name = st.text_input("Scheme Name")
country = st.selectbox("Country of Risk", ["Jordan", "Palestine", "Kuwait", "UAE", "Other"])
sa_basis = st.radio("Sum Assured Basis", ["Flat SA", "Multiple of Salary"])

if sa_basis == "Flat SA":
    flat_sa = st.number_input("Flat Sum Assured", min_value=0)
else:
    multiple = st.number_input("Salary Multiple", min_value=1, max_value=60, value=24)

# --- Upload Census File ---
uploaded_file = st.file_uploader("Upload Census Excel File", type=["xlsx"])

# --- Benefits Selection ---
st.subheader("Benefits Selection")
st.markdown("DAC is mandatory. Select additional benefits:")

optional_benefits = {
    "Accidental Death": 100,
    "PTD – Accident": 200,
    "PTD – Sickness": 200,
    "PPD – Accident/Sickness": 200,
    "TTD – Accident/Sickness": 100,
    "Medical Expenses (Accident)": 10000,
    "Repatriation Expenses": 5000
}

requested_benefits = {"DAC": 100}
for benefit, default in optional_benefits.items():
    if st.checkbox(f"{benefit}"):
        if "Expenses" in benefit:
            amt = st.number_input(f"Max {benefit} (USD)", min_value=0, max_value=default, value=default)
            requested_benefits[benefit] = amt
        else:
            pct = st.number_input(f"{benefit} (% of DAC)", min_value=0, max_value=default, value=default)
            requested_benefits[benefit] = pct

# --- Claims Entry ---
st.subheader("Claims Experience")
claims_data = []

add_claims = st.checkbox("Add Past Claims")
if add_claims:
    st.markdown("#### Enter Claims Manually")
    num_claims = st.number_input("How many claims to enter?", min_value=1, max_value=50, value=1)

    for i in range(num_claims):
        st.markdown(f"**Claim #{i + 1}**")
        col1, col2, col3 = st.columns(3)
        with col1:
            uwy = st.text_input(f"UWY (Underwriting Year) - Claim #{i + 1}", key=f"uwy_{i}")
        with col2:
            amount = st.number_input(f"Claim Amount Paid - Claim #{i + 1}", min_value=0, key=f"amt_{i}")
        with col3:
            benefit = st.selectbox(
                f"Benefit Type - Claim #{i + 1}",
                ["Death", "TPD", "WC", "MedEx", "TTD"],
                key=f"ben_{i}"
            )
        claims_data.append({"UWY": uwy, "Amount": amount, "Benefit": benefit})
else:
    scheme_type = st.radio("Scheme Type", ["Virgin Scheme", "Clean Claims Record"])

# --- Rates & Mappings (Samples or Placeholders) ---
dac_rates_male = {age: rate for age, rate in zip(range(18, 70), [0.41]*52)}
dac_rates_female = {age: rate for age, rate in zip(range(18, 70), [0.38]*52)}
ptd_rates = {age: rate for age, rate in zip(range(18, 65), [0.041]*47)}
occupation_load = {"class 1": 0.0, "class 2": 0.10, "class 3": 0.25, "class 4": 0.40}

occupation_map = {
    "class 1": ["admin", "bank", "clerk", "engineer", "doctor", "dentist", "sales", "office"],
    "class 2": ["catering", "carpenter", "electrician", "nurse", "retail", "kitchen"],
    "class 3": ["driver", "labour", "porter", "mechanic", "welder", "police"],
    "class 4": ["scaffold", "quarry", "diver", "army", "cement", "armed"]
}

def get_class(title):
    t = str(title).lower()
    for c, kws in occupation_map.items():
        for kw in kws:
            if kw in t:
                return c
    return "class 1"

def nearest_age(dob):
    if isinstance(dob, pd.Timestamp):
        dob = dob.date()
    today = datetime.date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    if abs(today.month - dob.month) >= 6:
        age += 1
    return min(age, 65)

def calculate_member_premium(row):
    try:
        age = nearest_age(row["dob"])
        gender = str(row.get("gender", "male")).lower()
        occ_class = get_class(row.get("job_title", "admin"))
        loading = occupation_load.get(occ_class, 0.4)

        if sa_basis == "Flat SA":
            sa = flat_sa
        else:
            sa = row["salary"] * multiple

        premiums = {}
        dac = dac_rates_male if gender == "male" else dac_rates_female
        dac_rate = dac.get(age, 0)
        premiums["DAC"] = round((dac_rate * sa) / 1000, 2)

        if "PTD – Accident" in requested_benefits or "PTD – Sickness" in requested_benefits:
            ptd_rate = ptd_rates.get(age, 0) * (1 + loading)
            ptd_pct = max(requested_benefits.get("PTD – Accident", 0), requested_benefits.get("PTD – Sickness", 0))
            premiums["PTD"] = round((ptd_rate * (ptd_pct/100) * sa) / 1000, 2)

        return {
            "Member ID": row.get("id", ""),
            "Age": age,
            "Gender": gender,
            "Occupation": occ_class,
            "SA": sa,
            **premiums
        }

    except Exception as e:
        return {"Error": str(e)}

# --- Main Execution ---
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [c.strip().lower() for c in df.columns]

        if "dob" not in df.columns or ("salary" not in df.columns and "sa" not in df.columns):
            st.error("Missing required columns: 'dob' and 'salary' or 'sa'")
        else:
            if "salary" not in df.columns:
                df["salary"] = 0
            if "gender" not in df.columns:
                df["gender"] = "male"
            if "job_title" not in df.columns:
                df["job_title"] = "Admin Staff"
            if "id" not in df.columns:
                df["id"] = df.index + 1

            df["age"] = df["dob"].apply(nearest_age)
            df["sa"] = df["salary"] * multiple if sa_basis != "Flat SA" else flat_sa

            def weighted_age(df):
                df["weight"] = df["sa"]
                return round(np.average(df["age"], weights=df["weight"]), 1)

            avg_age = df["age"].mean()
            w_age = weighted_age(df)

            def get_fcl_factor(group_size):
                if group_size <= 5:
                    return 0.5
                elif group_size <= 25:
                    return 1
                elif group_size <= 100:
                    return 2
                elif group_size <= 300:
                    return 3
                else:
                    return 4

            fcl = get_fcl_factor(len(df)) * df["sa"].mean()
            adjusted_fcl = round(fcl * 0.75, 2) if avg_age > 45 or w_age > 45 else round(fcl, 2)
            st.markdown(f"### Free Cover Limit (FCL): **USD {adjusted_fcl:,.2f}**")

            result = pd.DataFrame([calculate_member_premium(r) for _, r in df.iterrows()])
            st.subheader("Premium Results")
            st.dataframe(result)

            # --- Rate per Mille ---
            if "DAC" in result.columns:
                total_dac = result["DAC"].sum()
                total_sa = result["SA"].sum()
                if total_sa > 0:
                    suggested_rate_per_mille = round((total_dac / total_sa) * 1000, 3)
                    st.markdown(f"**Suggested DAC Rate per Mille:** {suggested_rate_per_mille}")

            # --- Total Premiums ---
            premium_cols = [col for col in result.columns if col not in ['Member ID', 'Age', 'Gender', 'Occupation', 'SA']]
            if premium_cols:
                st.write("### Total Premium Summary")
                st.write(result[premium_cols].sum())

            # --- Credibility from Claims ---
            def calculate_credibility(lives, years_of_claims):
                if lives < 500:
                    table = {1: 2, 2: 3, 3: 5, 4: 7, 5: 10}
                else:
                    table = {1: 10, 2: 15, 3: 20, 4: 25, 5: 30}
                return table.get(years_of_claims, 0)

            if add_claims:
                try:
                    years = len(set([c["UWY"] for c in claims_data if c["UWY"]]))
                    credibility = calculate_credibility(len(df), years)
                    st.success(f"Claims data spans {years} year(s). Assigned Credibility: {credibility}%")
                except:
                    st.warning("Could not determine credibility from entered claims.")
            else:
                credibility = 0 if scheme_type == "Virgin Scheme" else 5
                st.info(f"Assigned Credibility: {credibility}%")

    except Exception as e:
        st.error("Error processing file.")
        st.exception(e)
