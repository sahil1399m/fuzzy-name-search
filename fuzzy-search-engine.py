# app.py
import streamlit as st
import pandas as pd
import re
import unidecode
from rapidfuzz import fuzz, process
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# ------------------- Fuzzy Engine Functions -------------------

# 1️⃣ Script detection & normalization
def is_devanagari(text):
    return bool(re.search(r'[\u0900-\u097F]', str(text)))

def normalize_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower().strip()
    name = re.sub(r'^(mr|mrs|ms|smt|shri|dr|prof)\.?\s*', '', name)
    name = unidecode.unidecode(name)
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

# 2️⃣ Transliteration helper
def transliterate_name_to_devanagari(name):
    try:
        return transliterate(name, sanscript.ITRANS, sanscript.DEVANAGARI)
    except Exception:
        return ""

# 3️⃣ Prepare DataFrame
def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df["name_normalized"] = df["name_english"].astype(str).apply(lambda x: unidecode.unidecode(x).lower())
    return df

# 4️⃣ Fuzzy Search
def search_database(query, df, min_score=60, top_n=5, allow_fallback=True):
    query_norm = unidecode.unidecode(query).lower()
    choices = df["name_normalized"].tolist()

    results = process.extract(query_norm, choices, scorer=fuzz.WRatio, limit=top_n * 2)
    matches = []
    for match, score, idx in results:
        if score >= min_score:
            row = df.iloc[idx].to_dict()
            row["match_score"] = score
            matches.append(row)

    return pd.DataFrame(matches).head(top_n)

# ------------------- Streamlit UI -------------------

st.set_page_config(page_title="Fuzzy Search App", layout="wide")

st.markdown("""
<style>
/* Common button styles */
.stButton>button {
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: bold;
    transition: 0.3s;
    cursor: pointer;
}

/* Dark theme */
[data-theme='dark'] .stButton>button {
    background: linear-gradient(45deg, #6a11cb, #2575fc);
    color: white;
}
[data-theme='dark'] .stButton>button:hover {
    transform: scale(1.05);
    box-shadow: 0 0 10px #2575fc;
}
[data-theme='dark'] .stSlider>div>div>div>div {
    background-color: #6a11cb !important;
}

/* Light theme */
[data-theme='light'] .stButton>button {
    background: linear-gradient(45deg, #0366d6, #005cc5);
    color: white;
}
[data-theme='light'] .stButton>button:hover {
    transform: scale(1.05);
    box-shadow: 0 0 10px #0366d6;
}
[data-theme='light'] .stSlider>div>div>div>div {
    background-color: #0366d6 !important;
}
</style>
""", unsafe_allow_html=True)


# ------------------- Main App -------------------

st.title("Fuzzy Name Search")

# Example dataset
data = {
    "name_english": ["Sahil Desai", "Rahul Sharma", "Anjali Mehta", "Priya Singh", "Rohan Kapoor"]
}
df = pd.DataFrame(data)
df = prepare_dataframe(df)

query = st.text_input("Enter name to search:")

if st.button("Search"):
    if query.strip() == "":
        st.warning("Please enter a name!")
    else:
        results = search_database(query, df)
        if results.empty:
            st.info("No matches found.")
        else:
            st.dataframe(results)

