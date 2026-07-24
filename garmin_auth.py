import os
import json
import streamlit as st
from garminconnect import Garmin, GarminConnectTooManyRequestsError

TOKEN_DIR = os.path.expanduser("~/.garminconnect")

@st.cache_resource
def get_garmin_client():
    """Gerencia a conexão do Garmin Connect utilizando tokens salvos nos Secrets."""
    os.makedirs(TOKEN_DIR, exist_ok=True)

    # 1. Tenta carregar e aplicar o JSON de tokens salvo no st.secrets
    if "GARMIN_TOKENS_JSON" in st.secrets:
        try:
            tokens_data = st.secrets["GARMIN_TOKENS_JSON"]
            if isinstance(tokens_data, str):
                tokens_data = json.loads(tokens_data)

            # Salva no arquivo padrão esperado pelo garth/garminconnect
            tokens_path = os.path.join(TOKEN_DIR, "garmin_tokens.json")
            with open(tokens_path, "w") as f:
                json.dump(tokens_data, f)
                
        except Exception as e:
            st.warning(f"Aviso ao processar GARMIN_TOKENS_JSON: {e}")

    # 2. Tenta autenticar usando a sessão/tokens já gravados
    try:
        garmin = Garmin()
        garmin.login(TOKEN_DIR)
        return garmin
    except Exception as err_token:
        # Se os tokens não funcionarem, tenta usar as credenciais se não estivemos em nuvem
        email = st.secrets.get("GARMIN_EMAIL") or os.getenv("GARMIN_EMAIL")
        password = st.secrets.get("GARMIN_PASSWORD") or os.getenv("GARMIN_PASSWORD")

        if not email or not password:
            st.error("Sessão expirada e nenhuma credencial configurada.")
            return None

        try:
            garmin = Garmin(email, password)
            garmin.login(TOKEN_DIR)
            return garmin
        except GarminConnectTooManyRequestsError:
            st.error("Garmin Rate Limit (429). Aguarde alguns minutos.")
            return None
        except Exception as e:
            st.error(f"Erro na autenticação: {e}")
            return None