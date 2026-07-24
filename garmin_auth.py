import os
import json
import streamlit as st
from garminconnect import Garmin, GarminConnectTooManyRequestsError

TOKEN_DIR = os.path.expanduser("~/.garminconnect")

@st.cache_resource
def get_garmin_client():
    """Gerencia a conexão do Garmin Connect usando o garmin_tokens.json pré-autenticado."""
    os.makedirs(TOKEN_DIR, exist_ok=True)
    tokens_path = os.path.join(TOKEN_DIR, "garmin_tokens.json")

    # 1. Escreve o arquivo no servidor se a variável existir nos Secrets
    if "GARMIN_TOKENS_JSON" in st.secrets:
        try:
            tokens_raw = st.secrets["GARMIN_TOKENS_JSON"]
            # Se vier como string, converte e salva formatado
            if isinstance(tokens_raw, str):
                tokens_data = json.loads(tokens_raw)
            else:
                tokens_data = tokens_raw

            with open(tokens_path, "w", encoding="utf-8") as f:
                json.dump(tokens_data, f)
        except Exception as e:
            st.warning(f"Aviso ao salvar os tokens: {e}")

    # 2. Faz login usando o token em disco (sem bater no form de login da Garmin)
    try:
        garmin = Garmin()
        garmin.login(TOKEN_DIR)
        return garmin
    except Exception as e:
        st.error(f"Falha na autenticação por Token: {e}")
        return None