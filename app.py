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
# ========== LOAD CSS (Improved UI) ==========
def load_css(theme="light"):
    # Load Google Font
    st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

    # Load custom CSS file
    with open("style.css") as f:
        css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    # Add theme class to body (light or dark)
    st.markdown(f"<script>document.body.classList.add('{theme}');</script>", unsafe_allow_html=True)


# ========== SIDEBAR THEME ==========
import streamlit.components.v1 as components

theme = st.sidebar.radio("🌗 Theme Mode", ["light", "dark"]).lower()
st.markdown(f"<script>document.body.setAttribute('data-theme', '{theme}');</script>", unsafe_allow_html=True)
load_css(theme)

# ========== HEADER ==========
st.markdown(
    "<h1 style='text-align:center; color:#2575fc;'>🔍Fuzzy Name Search Engine</h1>",
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






