import os
import json
import streamlit as st
from garminconnect import Garmin

TOKEN_DIR = os.path.expanduser("~/.garminconnect")
TOKENS_FILE = os.path.join(TOKEN_DIR, "garmin_tokens.json")

@st.cache_resource
def get_garmin_client():
    """Gerencia a autenticação no Garmin Connect via token salvo nos Secrets."""
    os.makedirs(TOKEN_DIR, exist_ok=True)

    if "GARMIN_TOKENS_JSON" not in st.secrets:
        st.error("A chave GARMIN_TOKENS_JSON não foi encontrada nos Secrets.")
        return None

    tokens_raw = st.secrets["GARMIN_TOKENS_JSON"]

    # 1. Escreve o garmin_tokens.json no ambiente do servidor
    try:
        if isinstance(tokens_raw, str):
            tokens_data = json.loads(tokens_raw.strip())
        else:
            tokens_data = tokens_raw

        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump(tokens_data, f)
    except Exception as err:
        st.error(f"Erro ao processar o formato JSON dos Secrets: {err}")
        return None

    # 2. Login reutilizando a sessão salva (sem bater no login por senha)
    try:
        garmin = Garmin()
        garmin.login(TOKEN_DIR)
        return garmin
    except Exception as err:
        st.error(f"Sessão expirada ou inválida ({err}). Gere novos tokens executando 'python gerar_tokens.py' no PC.")
        return None