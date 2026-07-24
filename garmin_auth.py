import os
import json
import streamlit as st
from garminconnect import Garmin

TOKEN_DIR = os.path.expanduser("~/.garminconnect")
TOKENS_FILE = os.path.join(TOKEN_DIR, "garmin_tokens.json")

@st.cache_resource
def get_garmin_client():
    """Inicializa a conexão utilizando estritamente os tokens salvos nos Secrets."""
    os.makedirs(TOKEN_DIR, exist_ok=True)

    # 1. Verifica se os tokens estão definidos nos Secrets
    if "GARMIN_TOKENS_JSON" not in st.secrets:
        st.error("Secret 'GARMIN_TOKENS_JSON' não encontrada no Streamlit Cloud.")
        return None

    tokens_raw = st.secrets["GARMIN_TOKENS_JSON"]

    # 2. Escreve o arquivo garmin_tokens.json no disco do servidor
    try:
        if isinstance(tokens_raw, str):
            tokens_data = json.loads(tokens_raw.strip())
        else:
            tokens_data = tokens_raw

        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens_data, f)
    except Exception as err:
        st.error(f"Erro ao processar JSON dos Secrets: {err}")
        return None

    # 3. Tenta autenticação via token
    try:
        garmin = Garmin()
        garmin.login(TOKEN_DIR)
        return garmin
    except Exception as err:
        st.error(f"O token expirou ou é inválido ({err}). Gere um novo token no PC rodando 'python gerar_tokens.py'.")
        return None