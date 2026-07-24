import os
import json
import streamlit as st
from garminconnect import Garmin

TOKEN_DIR = os.path.expanduser("~/.garminconnect")
TOKENS_FILE = os.path.join(TOKEN_DIR, "garmin_tokens.json")

@st.cache_resource
def get_garmin_client():
    """Gerencia a autenticação no Garmin Connect via Secrets ou tokens locais."""
    os.makedirs(TOKEN_DIR, exist_ok=True)

    tokens_raw = None

    # 1. Tenta carregar do st.secrets (ambiente de nuvem / Streamlit Cloud)
    try:
        if "GARMIN_TOKENS_JSON" in st.secrets:
            tokens_raw = st.secrets["GARMIN_TOKENS_JSON"]
    except Exception:
        # Se st.secrets não estiver configurado localmente, continua sem interromper
        pass

    # 2. Se encontrou nos secrets, salva/atualiza no diretório local do servidor
    if tokens_raw:
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

    # 3. Tenta realizar o login reutilizando os tokens salvos em TOKEN_DIR
    try:
        garmin = Garmin()
        garmin.login(TOKEN_DIR)
        return garmin
    except Exception as err:
        st.error(
            f"Sessão expirada, token ausente ou inválido ({err}). "
            "Gere novos tokens executando 'python gerar_tokens.py' no PC."
        )
        return None