# app.py
import streamlit as st
import pandas as pd
import re
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from rapidfuzz import fuzz
import unidecode

# ------------------- CORE FUNCTIONS -------------------

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

# 2️⃣ Phonetic engine
INDIC_PHONETIC_MAP_V2 = {
    'अ': 'A','आ': 'A','इ': 'I','ई': 'I','उ': 'U','ऊ': 'U','ऋ': 'R','ए': 'E','ऐ': 'E','ओ': 'O','औ': 'O',
    'क': '1','ख': '1','ग': '1','घ': '1','ङ': '1',
    'च': '2','छ': '2','ज': '2','झ': '2','ञ': '2',
    'ट': '3','ठ': '3','ड': '3','ढ': '3','ण': '3','ड़': '3','ढ़': '3',
    'त': '4','थ': '4','द': '4','ध': '4','न': '4',
    'प': '5','फ': '5','ब': '5','भ': '5','म': '5',
    'य': '6','र': '6','ल': '6','व': '6',
    'श': '7','ष': '7','स': '7','ह': '7','ज्ञ': '1','क्ष': '1'
}

def generate_indic_phonetic_key(name_hindi, length=6):
    if not name_hindi or not isinstance(name_hindi, str):
        return ""
    first_char = name_hindi[0]
    phonetic_key = INDIC_PHONETIC_MAP_V2.get(first_char, '')
    last_code = phonetic_key
    for char in name_hindi[1:]:
        code = INDIC_PHONETIC_MAP_V2.get(char)
        if code and code.isdigit() and code != last_code:
            phonetic_key += code
            last_code = code
    if not phonetic_key:
        return "0" * length
    phonetic_key = (phonetic_key[0] + re.sub('[^0-9]', '', phonetic_key[1:]) + '0' * length)[:length]
    return phonetic_key

# 3️⃣ Transliteration
def transliterate_name_to_devanagari(name):
    try:
        return transliterate(name, sanscript.ITRANS, sanscript.DEVANAGARI)
    except Exception:
        return ""

# 4️⃣ Prepare dataframe
def prepare_dataframe(df):
    df['name_english'] = df['name_english'].fillna('').astype(str)
    df['name_hindi'] = df['name_hindi'].fillna('').astype(str)
    df['alias_names'] = df['alias_names'].fillna('').astype(str)
    df['normalized_english'] = df['name_english'].apply(normalize_name)
    df['phonetic_key'] = df['name_hindi'].apply(generate_indic_phonetic_key)
    df['normalized_aliases'] = df['alias_names'].apply(lambda s: [normalize_name(p) for p in re.split(r'[;,|]', s) if p.strip()])
    df['name_tokens'] = df['normalized_english'].apply(lambda x: x.split() if x else [])
    df['first_name'] = df['name_tokens'].apply(lambda t: t[0] if len(t) >= 1 else "")
    df['last_name'] = df['name_tokens'].apply(lambda t: t[-1] if len(t) >= 2 else "")
    df['all_normalized_forms'] = df.apply(
        lambda r: set([r['normalized_english'], r['first_name'], r['last_name']]) | set(r['normalized_aliases']),
        axis=1
    )
    if 'gender' not in df.columns:
        df['gender'] = 'idk'
    df['gender'] = df['gender'].fillna('idk').astype(str).str.lower()
    return df

# 5️⃣ Match score
def calculate_match_score(user_data, row):
    if user_data['normalized'] and user_data['normalized'] in row['all_normalized_forms']:
        return 100.0, "Exact Match"

    roman_full_w = fuzz.WRatio(user_data['normalized'], row['normalized_english'])
    roman_partial = fuzz.partial_ratio(user_data['normalized'], row['normalized_english'])
    roman_token_set = fuzz.token_set_ratio(user_data['normalized'], row['normalized_english'])
    roman_token_sort = fuzz.token_sort_ratio(user_data['normalized'], row['normalized_english'])
    best_roman = max(roman_full_w, roman_partial, roman_token_set, roman_token_sort)

    best_alias = max([fuzz.WRatio(user_data['normalized'], a) for a in row['normalized_aliases']] + [0])

    first_name_score = fuzz.WRatio(user_data['normalized'], row['first_name']) if user_data['single_token'] else 0

    substring_boost = 15 if user_data['normalized'] in row['normalized_english'] or row['normalized_english'] in user_data['normalized'] else 0

    phonetic_score = fuzz.ratio(user_data.get('phonetic_key',''), row.get('phonetic_key','')) if user_data.get('phonetic_key') else 0
    hindi_wr = fuzz.WRatio(user_data.get('devanagari',''), row.get('name_hindi','')) if user_data.get('devanagari') else 0

    if user_data['single_token']:
        weights = {'roman':0.35,'partial':0.25,'first_name':0.2,'alias':0.1,'phonetic':0.05,'hindi':0.05}
        roman_component = max(roman_full_w, roman_token_set, roman_token_sort)
        combined = (roman_component * weights['roman'] +
                    roman_partial * weights['partial'] +
                    first_name_score * weights['first_name'] +
                    best_alias * weights['alias'] +
                    phonetic_score * weights['phonetic'] +
                    hindi_wr * weights['hindi'])
    else:
        weights = {'roman':0.55,'alias':0.10,'phonetic':0.20,'hindi':0.15}
        combined = (best_roman * weights['roman'] +
                    best_alias * weights['alias'] +
                    phonetic_score * weights['phonetic'] +
                    hindi_wr * weights['hindi'])

    final_score = min(100.0, combined + substring_boost)
    reasons = {
        'String Similarity': round(best_roman,1),
        'Alias Similarity': round(best_alias,1),
        'FirstName Similarity': round(first_name_score,1),
        'Phonetic Similarity': round(phonetic_score,1),
        'Hindi Match': round(hindi_wr,1),
        'SubstringBoost': substring_boost
    }
    match_reason = max(reasons, key=lambda k: (reasons[k], k))
    return round(final_score,2), match_reason

# 6️⃣ Search
def search_database(user_input, df, min_score=60, top_n=3, allow_fallback=False):
    user_data = {}
    if is_devanagari(user_input):
        user_data['devanagari'] = user_input.strip()
        try:
            roman_equiv = transliterate(user_data['devanagari'], sanscript.DEVANAGARI, sanscript.ITRANS)
            user_data['normalized'] = normalize_name(roman_equiv)
        except:
            user_data['normalized'] = normalize_name(user_input)
    else:
        user_data['normalized'] = normalize_name(user_input)
        user_data['devanagari'] = transliterate_name_to_devanagari(user_input)

    user_data['phonetic_key'] = generate_indic_phonetic_key(user_data.get('devanagari',''))
    user_data['single_token'] = len(user_data['normalized'].split()) <= 1

    results = df.apply(lambda row: calculate_match_score(user_data, row), axis=1)
    df['match_score'], df['match_reason'] = zip(*results)

    # Strict threshold filtering
    matches = df[df['match_score'] >= min_score].sort_values(by='match_score', ascending=False).head(top_n)

    if matches.empty and allow_fallback:
        # Only return fallback if explicitly allowed
        matches = df.sort_values(by='match_score', ascending=False).head(top_n)

    return matches


# app.py
import streamlit as st
import pandas as pd
import re
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from rapidfuzz import fuzz
import unidecode

# ------------------- CORE FUNCTIONS -------------------

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

# 2️⃣ Phonetic engine
INDIC_PHONETIC_MAP_V2 = {
    'अ': 'A','आ': 'A','इ': 'I','ई': 'I','उ': 'U','ऊ': 'U','ऋ': 'R','ए': 'E','ऐ': 'E','ओ': 'O','औ': 'O',
    'क': '1','ख': '1','ग': '1','घ': '1','ङ': '1',
    'च': '2','छ': '2','ज': '2','झ': '2','ञ': '2',
    'ट': '3','ठ': '3','ड': '3','ढ': '3','ण': '3','ड़': '3','ढ़': '3',
    'त': '4','थ': '4','द': '4','ध': '4','न': '4',
    'प': '5','फ': '5','ब': '5','भ': '5','म': '5',
    'य': '6','र': '6','ल': '6','व': '6',
    'श': '7','ष': '7','स': '7','ह': '7','ज्ञ': '1','क्ष': '1'
}

def generate_indic_phonetic_key(name_hindi, length=6):
    if not name_hindi or not isinstance(name_hindi, str):
        return ""
    first_char = name_hindi[0]
    phonetic_key = INDIC_PHONETIC_MAP_V2.get(first_char, '')
    last_code = phonetic_key
    for char in name_hindi[1:]:
        code = INDIC_PHONETIC_MAP_V2.get(char)
        if code and code.isdigit() and code != last_code:
            phonetic_key += code
            last_code = code
    if not phonetic_key:
        return "0" * length
    phonetic_key = (phonetic_key[0] + re.sub('[^0-9]', '', phonetic_key[1:]) + '0' * length)[:length]
    return phonetic_key

# 3️⃣ Transliteration
def transliterate_name_to_devanagari(name):
    try:
        return transliterate(name, sanscript.ITRANS, sanscript.DEVANAGARI)
    except Exception:
        return ""

# 4️⃣ Prepare dataframe
def prepare_dataframe(df):
    df['name_english'] = df['name_english'].fillna('').astype(str)
    df['name_hindi'] = df['name_hindi'].fillna('').astype(str)
    df['alias_names'] = df['alias_names'].fillna('').astype(str)
    df['normalized_english'] = df['name_english'].apply(normalize_name)
    df['phonetic_key'] = df['name_hindi'].apply(generate_indic_phonetic_key)
    df['normalized_aliases'] = df['alias_names'].apply(lambda s: [normalize_name(p) for p in re.split(r'[;,|]', s) if p.strip()])
    df['name_tokens'] = df['normalized_english'].apply(lambda x: x.split() if x else [])
    df['first_name'] = df['name_tokens'].apply(lambda t: t[0] if len(t) >= 1 else "")
    df['last_name'] = df['name_tokens'].apply(lambda t: t[-1] if len(t) >= 2 else "")
    df['all_normalized_forms'] = df.apply(
        lambda r: set([r['normalized_english'], r['first_name'], r['last_name']]) | set(r['normalized_aliases']),
        axis=1
    )
    if 'gender' not in df.columns:
        df['gender'] = 'idk'
    df['gender'] = df['gender'].fillna('idk').astype(str).str.lower()
    return df

# 5️⃣ Match score
def calculate_match_score(user_data, row):
    if user_data['normalized'] == row['normalized_english']:
        return 100.0, "Exact Match"

    roman_full_w = fuzz.WRatio(user_data['normalized'], row['normalized_english'])
    roman_partial = fuzz.partial_ratio(user_data['normalized'], row['normalized_english'])
    roman_token_set = fuzz.token_set_ratio(user_data['normalized'], row['normalized_english'])
    roman_token_sort = fuzz.token_sort_ratio(user_data['normalized'], row['normalized_english'])
    best_roman = max(roman_full_w, roman_partial, roman_token_set, roman_token_sort)

    best_alias = max([fuzz.WRatio(user_data['normalized'], a) for a in row['normalized_aliases']] + [0])

    first_name_score = fuzz.WRatio(user_data['normalized'], row['first_name']) if user_data['single_token'] else 0

    substring_boost = 15 if user_data['normalized'] in row['normalized_english'] or row['normalized_english'] in user_data['normalized'] else 0

    phonetic_score = fuzz.ratio(user_data.get('phonetic_key',''), row.get('phonetic_key','')) if user_data.get('phonetic_key') else 0
    hindi_wr = fuzz.WRatio(user_data.get('devanagari',''), row.get('name_hindi','')) if user_data.get('devanagari') else 0

    if user_data['single_token']:
        weights = {'roman':0.35,'partial':0.25,'first_name':0.2,'alias':0.1,'phonetic':0.05,'hindi':0.05}
        roman_component = max(roman_full_w, roman_token_set, roman_token_sort)
        combined = (roman_component * weights['roman'] +
                    roman_partial * weights['partial'] +
                    first_name_score * weights['first_name'] +
                    best_alias * weights['alias'] +
                    phonetic_score * weights['phonetic'] +
                    hindi_wr * weights['hindi'])
    else:
        weights = {'roman':0.55,'alias':0.10,'phonetic':0.20,'hindi':0.15}
        combined = (best_roman * weights['roman'] +
                    best_alias * weights['alias'] +
                    phonetic_score * weights['phonetic'] +
                    hindi_wr * weights['hindi'])

    final_score = min(100.0, combined + substring_boost)
    reasons = {
        'String Similarity': round(best_roman,1),
        'Alias Similarity': round(best_alias,1),
        'FirstName Similarity': round(first_name_score,1),
        'Phonetic Similarity': round(phonetic_score,1),
        'Hindi Match': round(hindi_wr,1),
        'SubstringBoost': substring_boost
    }
    match_reason = max(reasons, key=lambda k: (reasons[k], k))
    return round(final_score,2), match_reason

# 6️⃣ Search
def search_database(user_input, df, min_score=60, top_n=3, allow_fallback=False):
    user_data = {}
    if is_devanagari(user_input):
        user_data['devanagari'] = user_input.strip()
        try:
            roman_equiv = transliterate(user_data['devanagari'], sanscript.DEVANAGARI, sanscript.ITRANS)
            user_data['normalized'] = normalize_name(roman_equiv)
        except:
            user_data['normalized'] = normalize_name(user_input)
    else:
        user_data['normalized'] = normalize_name(user_input)
        user_data['devanagari'] = transliterate_name_to_devanagari(user_input)

    user_data['phonetic_key'] = generate_indic_phonetic_key(user_data.get('devanagari',''))
    user_data['single_token'] = len(user_data['normalized'].split()) <= 1

    results = df.apply(lambda row: calculate_match_score(user_data, row), axis=1)
    df['match_score'], df['match_reason'] = zip(*results)

    # Strict threshold filtering
    matches = df[df['match_score'] >= min_score].sort_values(by='match_score', ascending=False).head(top_n)

    if matches.empty and allow_fallback:
        # Only return fallback if explicitly allowed
        matches = df.sort_values(by='match_score', ascending=False).head(top_n)

    return matches


# ------------------- STREAMLIT UI -------------------
import streamlit as st

# Dark/Light Mode Toggle
mode = st.sidebar.radio("Theme Mode", ["Dark", "Light"])

# Apply CSS based on mode
if mode == "Dark":
    st.markdown(
        """
        <style>
        /* General background & text */
        .stApp, .stTextInput, .stButton, .stRadio, .stSlider {
            background-color: #121212;
            color: #f5f5f5;
        }
        .stDataFrame div.row_widget {
            background-color: #1e1e1e;
            color: #f5f5f5;
        }
        /* Headers */
        .st-h1, .st-h2, .st-h3 {
            color: #f5f5f5;
        }
        /* Table styling */
        .dataframe tbody tr:nth-child(even) {background-color: #1e1e1e;}
        .dataframe tbody tr:nth-child(odd) {background-color: #222222;}
        .dataframe thead {background-color: #333333; color: #ffffff;}
        /* Input boxes */
        .stTextInput>div>div>input {background-color:#1e1e1e; color:#f5f5f5; border:1px solid #444;}
        /* Buttons */
        .stButton>button {background-color:#333; color:#f5f5f5; border-radius:8px; padding:5px 12px;}
        </style>
        """, unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <style>
        /* Light theme resets default colors */
        .stApp, .stTextInput, .stButton, .stRadio, .stSlider {background-color: #f0f0f0; color: #000000;}
        .stDataFrame div.row_widget {background-color: #ffffff; color: #000000;}
        .dataframe tbody tr:nth-child(even) {background-color: #f9f9f9;}
        .dataframe tbody tr:nth-child(odd) {background-color: #ffffff;}
        .dataframe thead {background-color: #d9d9d9; color: #000000;}
        .stTextInput>div>div>input {background-color:#ffffff; color:#000; border:1px solid #ccc;}
        .stButton>button {background-color:#ddd; color:#000; border-radius:8px; padding:5px 12px;}
        </style>
        """, unsafe_allow_html=True
    )

# Now keep your original title and inputs
st.title("🔍 Gender Aware Police Fuzzy Name Search Demo")

# Load CSVs once
@st.cache_data
def load_data():
    males_df = prepare_dataframe(pd.read_csv("malesf.csv", encoding='utf-8-sig'))
    females_df = prepare_dataframe(pd.read_csv("fdata.csv", encoding='utf-8-sig'))
    return males_df, females_df

males_df, females_df = load_data()

# Inputs
user_name = st.text_input("Enter Name:")
gender = st.radio("Select Gender:", options=['Male','Female',"Don't Know"])
threshold = st.slider("Minimum Match %", min_value=0, max_value=100, value=60)

# Rest of your search logic
if user_name:
    if gender == "Male":
        results_df = search_database(user_name, males_df.copy(), min_score=threshold, allow_fallback=False)
    elif gender == "Female":
        results_df = search_database(user_name, females_df.copy(), min_score=threshold, allow_fallback=False)
    else:
        male_results = search_database(user_name, males_df.copy(), min_score=threshold, top_n=5, allow_fallback=False)
        female_results = search_database(user_name, females_df.copy(), min_score=threshold, top_n=5, allow_fallback=False)
        results_df = pd.concat([male_results, female_results])
        results_df = results_df.drop_duplicates(subset=['person_id'])
        results_df = results_df.sort_values(by='match_score', ascending=False).head(3)

    st.subheader("Top Matches")
    st.dataframe(results_df)




