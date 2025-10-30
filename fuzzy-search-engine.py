# fuzzy_engine.py
import re
import pandas as pd
import unidecode
from rapidfuzz import fuzz, process
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

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
