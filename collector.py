from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from garminconnect import GarminConnectTooManyRequestsError

# Importação correta da função presente no seu garmin_auth.py
from garmin_auth import get_garmin_client


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def get_first_valid(data, fields, default=0):
    if not isinstance(data, dict):
        return default
    for field in fields:
        value = data.get(field)
        if value not in [None, "", 0]:
            return value
    return default


def fetch_valid_sleep_seconds(client, day_str):
    """
    Busca os segundos de sono para uma data. 
    Se a data não tiver registro (como o dia de hoje), busca a noite anterior.
    """
    try:
        sleep_data = client.get_sleep_data(day_str)
        if isinstance(sleep_data, dict):
            dto = sleep_data.get("dailySleepDTO", {})
            if dto and dto.get("totalSleepSeconds"):
                return dto.get("totalSleepSeconds")
    except Exception:
        pass
    return 0


# ============================================
# HISTÓRICO DE ATIVIDADES
# ============================================

@st.cache_data(ttl=1800)
def get_historical_activities(_client, days=30):
    if not _client:
        return []

    history = []

    for i in range(days):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")

        try:
            # Busca resumo diário do usuário
            try:
                stats = _client.get_user_summary(day)
            except Exception:
                stats = {}

            # Busca HRV se disponível
            try:
                hrv_data = _client.get_hrv_data(day)
            except Exception:
                hrv_data = {}

            # Busca atividades do dia
            try:
                activities = _client.get_activities_by_date(day, day, "")
            except Exception:
                activities = []

            last_activity = activities[0] if activities else {}

            # ====================================
            # SONO (COM FALLBACK PARA O DIA DE HOJE)
            # ====================================
            sleep_seconds = get_first_valid(
                stats,
                [
                    "measurableAsleepDuration",
                    "sleepingSeconds",
                    "sleepSeconds",
                    "dailySleepSeconds",
                    "sleepDuration"
                ],
                0
            )

            # Se for hoje (i = 0) e o registro de sono ainda for 0, busca a noite recém-concluída (ontem)
            if (not sleep_seconds or sleep_seconds == 0) and i == 0:
                yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                sleep_seconds = fetch_valid_sleep_seconds(_client, yesterday_str)

            sleep_hours = round(float(sleep_seconds) / 3600, 2)

            # ====================================
            # PASSOS
            # ====================================
            steps = get_first_valid(
                stats,
                ["totalSteps", "steps", "dailySteps"],
                0
            )

            # ====================================
            # STRESS
            # ====================================
            stress = get_first_valid(
                stats,
                ["averageStressLevel", "stressAverage", "avgStressLevel"],
                0
            )

            # ====================================
            # FC REPOUSO
            # ====================================
            resting_hr = get_first_valid(
                stats,
                ["restingHeartRate", "restingHR"],
                0
            )

            # ====================================
            # HRV
            # ====================================
            hrv = (
                hrv_data.get("lastNightAvg")
                or hrv_data.get("weeklyAvg")
                or hrv_data.get("hrvValue")
                or 0
            )

            # ====================================
            # TRAINING EFFECT & DISTÂNCIA
            # ====================================
            training_effect = float(
                last_activity.get("aerobicTrainingEffect", 0) or 0
            )

            distance_km = round(
                last_activity.get("distance", 0) / 1000,
                2
            )

            # ====================================
            # TRAINING LOAD
            # ====================================
            training_load = round(
                (training_effect * 8) + (distance_km * 1.5),
                1
            )

            # ====================================
            # VO2 MAX
            # ====================================
            vo2 = (
                last_activity.get("vO2MaxValue")
                or stats.get("vO2MaxValue")
                or stats.get("vo2Max")
                or None
            )

            history.append({
                "date": day,
                "sleep_hours": sleep_hours,
                "steps": steps,
                "stress_avg": stress,
                "resting_hr": resting_hr,
                "hrv": hrv,
                "vo2max": vo2,
                "training_effect": round(training_effect, 1),
                "training_load": training_load
            })

        except GarminConnectTooManyRequestsError:
            st.warning("⚠️ Garmin Rate Limit (429) atingido ao construir histórico. Retornando dados parciais.")
            break
        except Exception:
            continue

    df = pd.DataFrame(history)

    if not df.empty:
        df = df.sort_values("date").reset_index(drop=True)
        df["vo2max"] = pd.to_numeric(df["vo2max"].replace(0, pd.NA), errors="coerce").ffill()
        return df.to_dict("records")

    return []


# ============================================
# COLETA PRINCIPAL
# ============================================

def collect_all_data():
    client = get_garmin_client()

    if not client:
        return {"stats": {}, "activities": [], "history": []}

    today = datetime.now().strftime("%Y-%m-%d")

    try:
        stats = client.get_user_summary(today)
    except Exception:
        stats = {}

    # Garante que o stats de hoje contenha as horas de sono caso venha 0
    current_sleep = get_first_valid(
        stats,
        ["measurableAsleepDuration", "sleepingSeconds", "sleepSeconds", "dailySleepSeconds", "sleepDuration"],
        0
    )
    if not current_sleep or current_sleep == 0:
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        valid_seconds = fetch_valid_sleep_seconds(client, yesterday_str)
        if valid_seconds:
            stats["sleepSeconds"] = valid_seconds

    try:
        activities = client.get_activities(0, 5)
    except Exception:
        activities = []

    return {
        "stats": stats,
        "activities": activities,
        "history": get_historical_activities(client, days=30)
    }