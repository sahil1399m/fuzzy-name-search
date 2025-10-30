# app.py
import streamlit as st
import pandas as pd
import importlib.util, sys, os

# Dynamically load the file fuzzy-search-engine.py
spec = importlib.util.spec_from_file_location("fuzzy_search_engine", os.path.join(os.path.dirname(__file__), "fuzzy-search-engine.py"))
fuzzy_search_engine = importlib.util.module_from_spec(spec)
sys.modules["fuzzy_search_engine"] = fuzzy_search_engine
spec.loader.exec_module(fuzzy_search_engine)

prepare_dataframe = fuzzy_search_engine.prepare_dataframe
search_database = fuzzy_search_engine.search_database


st.set_page_config(page_title="Fuzzy Name Search | Police Database", layout="wide")

# ========== LOAD CSS ==========
def load_css(theme="light"):
    with open("styles.css") as f:
        css = f"<style>[data-theme='{theme}'] {{}}</style>" + f"<style>{f.read()}</style>"
        st.markdown(css, unsafe_allow_html=True)

# ========== SIDEBAR THEME ==========
theme = st.sidebar.radio("🌗 Theme Mode", ["light", "dark"]).lower()
load_css(theme)

# ========== HEADER ==========
st.markdown(
    "<h1 style='text-align:center; color:#2575fc;'>🔍 Gender-Aware Police Fuzzy Name Search</h1>",
    unsafe_allow_html=True
)

# ========== LOAD DATA ==========
@st.cache_data
def load_data():
    males_df = prepare_dataframe(pd.read_csv("malesf.csv", encoding='utf-8-sig'))
    females_df = prepare_dataframe(pd.read_csv("fdata.csv", encoding='utf-8-sig'))
    return males_df, females_df

males_df, females_df = load_data()

# ========== INPUTS ==========
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    user_name = st.text_input("Enter Name:", placeholder="e.g., Priya Sharma")
with col2:
    gender = st.radio("Select Gender:", ['Male', 'Female', "Don't Know"])
with col3:
    threshold = st.slider("Match Threshold %", 0, 100, 60)

# ========== SEARCH ==========
if user_name:
    if gender == "Male":
        results_df = search_database(user_name, males_df, threshold)
    elif gender == "Female":
        results_df = search_database(user_name, females_df, threshold)
    else:
        male_results = search_database(user_name, males_df, threshold)
        female_results = search_database(user_name, females_df, threshold)
        results_df = pd.concat([male_results, female_results]).drop_duplicates(subset=["person_id"]).head(5)

    if not results_df.empty:
        st.markdown("### 📊 Top Matches")
        st.dataframe(results_df, use_container_width=True)
    else:
        st.warning("⚠️ No matches found.")


