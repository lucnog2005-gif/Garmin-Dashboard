import os
import streamlit as st
from garminconnect import Garmin, GarminConnectTooManyRequestsError

TOKEN_DIR = os.path.expanduser("~/.garminconnect")

@st.cache_resource
def get_garmin_client():
    """Gerencia a conexão e reutiliza os tokens do arquivo garmin_tokens.json."""
    os.makedirs(TOKEN_DIR, exist_ok=True)

    # Se os tokens estiverem nos Secrets, grava o arquivo garmin_tokens.json na nuvem
    if "GARMIN_TOKENS_JSON" in st.secrets:
        try:
            tokens_path = os.path.join(TOKEN_DIR, "garmin_tokens.json")
            with open(tokens_path, "w") as f:
                f.write(st.secrets["GARMIN_TOKENS_JSON"])
        except Exception as e:
            st.warning(f"Não foi possível gravar os tokens: {e}")

    try:
        # Tenta login reutilizando a sessão salva
        garmin = Garmin()
        garmin.login(TOKEN_DIR)
        return garmin
    except Exception:
        # Fallback para login direto por credenciais
        email = st.secrets.get("GARMIN_EMAIL") or os.getenv("GARMIN_EMAIL")
        password = st.secrets.get("GARMIN_PASSWORD") or os.getenv("GARMIN_PASSWORD")
        
        if not email or not password:
            st.error("Credenciais ou tokens não encontrados no st.secrets.")
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