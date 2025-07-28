import streamlit as st
import pandas as pd
from datetime import datetime
import datetime
import numpy as np

# ---------------------------------
# UI SETUP
# ---------------------------------

st.title("Group Life Reinsurance Analysis Tool")

scheme_name = st.text_input("Scheme Name")
country = st.selectbox("Country of Risk", ["Jordan", "Palestine", "Kuwait", "UAE", "Other"])

uploaded_file = st.file_uploader("Upload Census File (.xlsx)", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Standardize column names
    df.columns = [col.strip().lower() for col in df.columns]
    
    # Rename columns to expected
    if "sa" not in df.columns and "salary" in df.columns:
        df["sa"] = None
    if "gender" not in df.columns:
        df["gender"] = "male"
    if "job_title" not in df.columns:
        df["job_title"] = "Administration Staff"

    # ---------------------------------
    # CONFIGURATION INPUTS
    # ---------------------------------

    sa_basis = st.radio("Sum Assured Basis", ["Flat SA", "Multiple of Salary"])
    if sa_basis == "Flat SA":
        flat_sa = st.number_input("Enter Flat SA Amount", min_value=0)
    else:
        multiple = st.number_input("Enter Salary Multiple", min_value=1, max_value=60, value=24)

    st.write("### Select Benefits")
    selected_benefits = st.multiselect("Optional Benefits (DAC is mandatory)", [
        "PTD – Accident", "PTD – Sickness"
    ])
    selected_benefits.append("DAC")

    # ---------------------------------
    # RATE TABLES
    # ---------------------------------

    dac_rates = {
        "male": {age: rate for age, rate in zip(range(18, 70), [
            0.41, 0.41, 0.41, 0.41, 0.38, 0.38, 0.38, 0.38, 0.37, 0.37, 0.37, 0.37, 0.39, 0.41, 0.45,
            0.48, 0.52, 0.58, 0.65, 0.72, 0.8, 0.9, 1.02, 1.15, 1.3, 1.47, 1.66, 1.88, 2.12, 2.39, 2.63,
            3.02, 3.4, 3.82, 4.28, 4.68, 5.24, 5.85, 6.53, 7.28, 8.1, 9, 10.01, 11.11, 12.33, 13.66,
            15.12, 16.73, 18.5, 20.45
        ])},
        "female": {age: rate for age, rate in zip(range(18, 70), [
            0.41, 0.41, 0.41, 0.41, 0.38, 0.38, 0.38, 0.38, 0.37, 0.37, 0.37, 0.37, 0.37, 0.37, 0.37,
            0.37, 0.39, 0.41, 0.45, 0.48, 0.52, 0.58, 0.65, 0.72, 0.8, 0.9, 1.02, 1.15, 1.3, 1.47, 1.66,
            1.88, 2.12, 2.39, 2.63, 3.02, 3.4, 3.82, 4.28, 4.68, 5.24, 5.85, 6.53, 7.28, 8.1, 9, 10.01,
            11.11, 12.33, 13.66
        ])}
    }

    ptd_class1_rates = {age: rate for age, rate in zip(range(18, 65), [
        0.041, 0.041, 0.041, 0.041, 0.038, 0.038, 0.038, 0.038, 0.037, 0.037, 0.037, 0.037, 0.039, 0.041,
        0.045, 0.042, 0.052, 0.058, 0.065, 0.072, 0.08, 0.09, 0.102, 0.115, 0.13, 0.147, 0.166, 0.188,
        0.212, 0.239, 0.263, 0.302, 0.34, 0.382, 0.428, 0.468, 0.524, 0.585, 0.653, 0.728, 0.81, 0.9,
        1.001, 1.111, 1.233
    ])}

    occupation_class_map = {
        "class 1": ["administration", "banking", "clerical", "doctor", "dentist", "engineer", "sales"],
        "class 2": ["catering", "electrician", "nurse", "retail", "kitchen", "carpenter"],
        "class 3": ["driver", "labour", "mechanic", "porter", "police", "cleaner", "welder"],
        "class 4": ["scaffolder", "armed", "diver", "quarry", "cement"]
    }

    def classify_occupation(title):
        title = title.strip().lower()
        for k, v in occupation_class_map.items():
            for t in v:
                if t in title:
                    return k
        return "class 1"

    occupation_loadings = {
        "class 1": 0.0,
        "class 2": 0.10,
        "class 3": 0.25,
        "class 4": 0.40
    }

    def calculate_age(dob):
        ref = datetime.date.today()
        age = ref.year - dob.year
        if (ref.month, ref.day) < (dob.month, dob.day):
            age -= 1
        months_diff = (dob.month - ref.month) + 12 * (dob.year - ref.year)
        if abs(months_diff) >= 6:
            age += 1
        return min(age, 65)

    def calculate_premium(row, sa, selected_benefits):
        age = calculate_age(row["dob"])
        gender = str(row.get("gender", "male")).lower()
        occ_class = classify_occupation(str(row.get("job_title", "")))
        loading = occupation_loadings.get(occ_class, 0.4)

        premiums = {}
        dac_rate = dac_rates.get(gender, dac_rates["male"]).get(age, 0)
        ptd_rate = ptd_class1_rates.get(age, 0) * (1 + loading)

        if "DAC" in selected_benefits:
            premiums["DAC"] = round((dac_rate * sa) / 1000, 2)
        if "PTD – Accident" in selected_benefits or "PTD – Sickness" in selected_benefits:
            premiums["PTD"] = round((ptd_rate * sa) / 1000, 2)
        return premiums

    results = []

try:
    for i, row in df.iterrows():
        sa = row["sa"]
        if sa_basis == "Flat SA":
            sa = flat_sa
        else:
            sa = row["salary"] * multiple
        premiums = calculate_premium(row, sa, selected_benefits)
        results.append({
            "Member": i + 1,
            "Age": calculate_age(row["dob"]),
            "Occupation": classify_occupation(row["job_title"]),
            "SA": sa,
            **premiums
        })

    result_df = pd.DataFrame(results)
    st.write("### Member Level Premiums")
    st.dataframe(result_df)

    st.write("### Total Premium Summary")
    premium_cols = [col for col in ["DAC", "PTD"] if col in result_df.columns]
    if premium_cols:
        st.write(result_df[premium_cols].sum(numeric_only=True))
    else:
        st.write("No premium calculated. Please select benefits.")

except Exception as e:
    st.error("Something went wrong. Please check that DOB and salary/SA are correctly provided.")
    st.exception(e)
