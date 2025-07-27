import streamlit as st

st.title("Group Life Reinsurance Tool")

scheme = st.text_input("Scheme Name")
country = st.selectbox("Country of Risk", ["Jordan", "UAE", "KSA", "Other"])

uploaded_file = st.file_uploader("Upload Census File (Excel)", type=["xlsx"])

if uploaded_file:
    st.success("Census uploaded successfully.")
    st.write("Coming soon: Full pricing logic, FCL, credibility, and more.")
