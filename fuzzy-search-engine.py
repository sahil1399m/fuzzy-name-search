# app.py
import streamlit as st
import pandas as pd
import re
import unidecode
from rapidfuzz import fuzz, process
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# ------------------- Fuzzy Engine Functions -------------------

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

def transliterate_name_to_devanagari(name):
    try:
        return transliterate(name, sanscript.ITRANS, sanscript.DEVANAGARI)
    except Exception:
        return ""

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df["name_normalized"] = df["name_english"].astype(str).apply(lambda x: unidecode.unidecode(x).lower())
    return df

def search_database(query, df, min_score=60, top_n=5):
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

st.markdown("""
<style>
/* ---------- Buttons ---------- */
.stButton>button {
    border: none;
    border-radius: 15px;
    padding: 12px 25px;
    font-weight: 600;
    font-size: 16px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    transition: 0.4s all;
    cursor: pointer;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}

/* Dark theme buttons */
[data-theme='dark'] .stButton>button {
    background: linear-gradient(135deg, #6a11cb, #2575fc);
    color: white;
}
[data-theme='dark'] .stButton>button:hover {
    transform: scale(1.08);
    box-shadow: 0 0 20px #2575fc;
}

/* Light theme buttons */
[data-theme='light'] .stButton>button {
    background: linear-gradient(135deg, #0366d6, #005cc5);
    color: white;
}
[data-theme='light'] .stButton>button:hover {
    transform: scale(1.08);
    box-shadow: 0 0 20px #0366d6;
}

/* ---------- Sliders ---------- */
.stSlider>div>div>div>div {
    height: 12px !important;
    border-radius: 6px !important;
}

/* Slider thumbs */
.stSlider>div>div>div>div>div {
    width: 22px !important;
    height: 22px !important;
    border-radius: 50% !important;
    border: 2px solid white !important;
    background-color: #2575fc !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    transition: 0.3s all;
}

/* ---------- Text Input ---------- */
.stTextInput>div>div>input {
    border-radius: 12px;
    border: 2px solid #ccc;
    padding: 10px 15px;
    font-size: 15px;
    transition: 0.3s all;
}

/* Dark theme input */
[data-theme='dark'] .stTextInput>div>div>input {
    background-color: #1e1e1e;
    color: #f0f0f0;
    border: 2px solid #444;
}
[data-theme='dark'] .stTextInput>div>div>input:focus {
    border-color: #2575fc;
    box-shadow: 0 0 8px #2575fc;
}

/* Light theme input */
[data-theme='light'] .stTextInput>div>div>input {
    background-color: #ffffff;
    color: #111;
    border: 2px solid #ccc;
}
[data-theme='light'] .stTextInput>div>div>input:focus {
    border-color: #0366d6;
    box-shadow: 0 0 8px #0366d6;
}

/* ---------- Cards / Sections ---------- */
.stContainer {
    border-radius: 15px;
    padding: 15px;
    margin-bottom: 20px;
    transition: 0.3s all;
}

[data-theme='dark'] .stContainer {
    background-color: #252525;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}

[data-theme='light'] .stContainer {
    background-color: #f9f9f9;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}

/* ---------- Radio buttons ---------- */
.stRadio>div>label {
    padding: 6px 12px;
    border-radius: 8px;
    transition: 0.3s all;
}
.stRadio>div>input:checked + label {
    font-weight: bold;
}
[data-theme='dark'] .stRadio>div>input:checked + label {
    background: #2575fc33;
}
[data-theme='light'] .stRadio>div>input:checked + label {
    background: #0366d633;
}
</style>
""", unsafe_allow_html=True)


