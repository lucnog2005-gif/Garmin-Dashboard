import os
import json
import streamlit as st
from garminconnect import Garmin

TOKEN_DIR = os.path.expanduser("~/.garminconnect")
TOKENS_FILE = os.path.join(TOKEN_DIR, "garmin_tokens.json")

@st.cache_resource
def get_garmin_client():
    os.makedirs(TOKEN_DIR, exist_ok=True)

    # Diagnóstico visual de chaves carregadas
    chaves_encontradas = list(st.secrets.keys())
    st.write(f"🔍 Chaves detectadas nos Secrets: `{chaves_encontradas}`")

    if "GARMIN_TOKENS_JSON" not in st.secrets:
        st.error("A chave GARMIN_TOKENS_JSON continua ausente dos Secrets.")
        return None

    tokens_raw = st.secrets["GARMIN_TOKENS_JSON"]

    try:
        tokens_data = json.loads(tokens_raw.strip()) if isinstance(tokens_raw, str) else tokens_raw
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens_data, f)
    except Exception as err:
        st.error(f"Erro ao converter JSON: {err}")
        return None

    try:
        garmin = Garmin()
        garmin.login(TOKEN_DIR)
        return garmin
    except Exception as err:
        st.error(f"Erro ao autenticar com token: {err}")
        return None