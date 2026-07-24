import os
import streamlit as st
from garminconnect import Garmin, GarminConnectTooManyRequestsError

TOKEN_DIR = os.path.expanduser("~/.garminconnect")

@st.cache_resource
def get_garmin_client():
    """Gerencia a conexão e reutiliza os tokens em disco para evitar erro 429."""
    # Garante que o diretório de tokens exista
    os.makedirs(TOKEN_DIR, exist_ok=True)

    try:
        # Tenta reusar sessão existente pelos tokens
        garmin = Garmin()
        garmin.login(TOKEN_DIR)
        return garmin
    except Exception:
        # Fallback para credenciais do .env ou st.secrets
        email = st.secrets.get("GARMIN_EMAIL") or os.getenv("GARMIN_EMAIL")
        password = st.secrets.get("GARMIN_PASSWORD") or os.getenv("GARMIN_PASSWORD")
        
        if not email or not password:
            st.error("Credenciais não encontradas no .env ou st.secrets.")
            return None
            
        try:
            garmin = Garmin(email, password)
            garmin.login()
            # Salva tokens em disco para requisições futuras
            garmin.garth.dump(TOKEN_DIR)
            return garmin
        except GarminConnectTooManyRequestsError:
            st.error("Garmin Rate Limit (429). Aguarde alguns minutos.")
            return None
        except Exception as e:
            st.error(f"Erro na autenticação: {e}")
            return None