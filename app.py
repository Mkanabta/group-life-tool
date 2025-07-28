import streamlit as st
import pandas as pd
from datetime import datetime
import datetime
import numpy as np

st.set_page_config(page_title="Group Life Tool", layout="wide")

st.title("Group Life Reinsurance Analysis Tool")

# Input: Scheme info
scheme_name = st.text_input("Scheme Name")
country = st.selectbox("Country of Risk", ["Jordan", "Palestine", "Kuwait", "UAE", "Other"])
sa_basis = st.radio("Sum Assured Basis", ["Flat SA", "Multiple of Salary"])
if sa_basis == "Flat SA":
    flat_sa = st.number_input("Flat Sum Assured", min_value=0)
else:
    multiple = st.number_input("Salary Multiple", min_value=1, max_value=60, value=24)

# Input: Uploaded Census
uploaded_file = st.file_uploader("Upload Census Excel File", type=["xlsx"])

# Input: Requested Benefits
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

# Input: Claims History
st.subheader("Claims Experience")
claims_provided = st.radio("Claims Data Provided?", ["Yes", "No"])
if claims_provided == "Yes":
    years_of_claims = st.selectbox("Years of Claims Data", [1, 2, 3, 4, 5])
    number_of_lives = st.number_input("Number of Members", min_value=0)
    if number_of_lives < 500:
        credibility = [2, 3, 5, 7, 10][years_of_claims - 1]
    else:
        credibility = min(50, 2 * years_of_claims)
else:
    scheme_type = st.radio("Scheme Status", ["Virgin Scheme", "Clean Claims Record"])
    credibility = 0

st.write(f"**Credibility Assigned:** {credibility}%")

# --- Rates (sample) ---
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

        # Get SA
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

# ----------------------
# Run if file uploaded
# ----------------------
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

            result = pd.DataFrame([calculate_member_premium(r) for _, r in df.iterrows()])
            st.subheader("Premium Results")
            st.dataframe(result)

            premium_cols = [col for col in result.columns if col not in ['Member ID', 'Age', 'Gender', 'Occupation', 'SA']]
            st.write("### Total Premium Summary")
            st.write(result[premium_cols].sum())

    except Exception as e:
        st.error("Error processing file.")
        st.exception(e)
