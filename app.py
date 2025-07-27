# --- BENEFIT SELECTION ---
st.subheader("🛡️ Select Scheme Benefits")

st.markdown("**Death Any Cause (DAC)** is mandatory and always included.")
selected_benefits = {"DAC": 100}

# Optional benefits with percentage input
optional_benefits = {
    "Accidental Death (AccDeath)": 100,
    "PTD – Accident": 200,
    "PTD – Sickness": 200,
    "PPD – Acc/Sick": 200,
    "TTD – Acc/Sick": 100
}

st.markdown("### ☑️ Optional Benefits (% of DAC)")
for benefit, max_pct in optional_benefits.items():
    col1, col2 = st.columns([2, 1])
    enable = col1.checkbox(f"{benefit} (up to {max_pct}%)")
    if enable:
        pct = col2.number_input(f"% of DAC for {benefit}", min_value=0.0, max_value=float(max_pct), value=0.0, step=5.0)
        if pct > 0:
            selected_benefits[benefit] = pct

# MedEx & Repatriation (manual input)
st.markdown("### 🏥 Medical / Repatriation Benefits")
medex_enabled = st.checkbox("Include Medical Expenses due to Accident (Max $10,000)")
if medex_enabled:
    medex_limit = st.number_input("Medical Expense Limit (USD)", min_value=0, max_value=10000, value=10000, step=500)
    selected_benefits["MedEx"] = medex_limit

repat_enabled = st.checkbox("Include Repatriation Expenses (Max $5,000)")
if repat_enabled:
    repat_limit = st.number_input("Repatriation Limit (USD)", min_value=0, max_value=5000, value=5000, step=500)
    selected_benefits["Repatriation"] = repat_limit

# Show selected
st.markdown("### 📋 Selected Benefits Summary")
for k, v in selected_benefits.items():
    st.write(f"🔹 {k}: {'$'+str(v) if k in ['MedEx', 'Repatriation'] else str(v)+'% of DAC'}")
