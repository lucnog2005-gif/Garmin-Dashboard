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


def get_future_schedule(client, days=35):
    """
    Busca treinos agendados no calendário da Garmin para os próximos dias.
    """
    if not client:
        return []

    future_events = []
    today = datetime.now().date()
    future_date = today + timedelta(days=days)

    try:
        # Busca eventos do calendário
        calendar_events = client.get_calendar(today.isoformat(), future_date.isoformat())
        
        # Pode vir como lista de eventos ou dicionário envelopado dependendo da resposta da API
        events_list = calendar_events.get("calendarItems", []) if isinstance(calendar_events, dict) else (calendar_events or [])

        for item in events_list:
            event_date = item.get("date") or item.get("startDate")
            if not event_date:
                continue

            # Se for data passada/hoje, ignora para não duplicar com o histórico real
            item_date = datetime.strptime(event_date[:10], "%Y-%m-%d").date()
            if item_date <= today:
                continue

            # Tenta pegar a carga estimada ou calcula com base na duração/distância estipulada
            est_load = item.get("estimatedTrainingLoad") or 0
            if est_load == 0:
                duration_min = (item.get("durationInSeconds") or 0) / 60
                distance_km = (item.get("distanceInMeters") or 0) / 1000
                # Estimativa genérica de carga caso o Garmin não retorne o valor pronto
                est_load = round((duration_min * 0.8) + (distance_km * 2.0), 1)

            future_events.append({
                "date": item_date.strftime("%Y-%m-%d"),
                "item_name": item.get("title", "Treino Agendado"),
                "training_load": est_load,
                "is_future": True
            })

    except Exception:
        pass

    return sorted(future_events, key=lambda x: x["date"])


# ============================================
# HISTÓRICO DE ATIVIDADES (180 DIAS - 6 MESES)
# ============================================

@st.cache_data(ttl=1800)
def get_historical_activities(_client, days=180):
    if not _client:
        return []

    history = []

    # Otimização contra Rate Limit (429): Busca um lote das últimas 200 atividades de uma vez só
    try:
        all_activities = _client.get_activities(0, 200)
        # Agrupa atividades por data para acesso rápido em O(1)
        activities_by_day = {}
        for act in all_activities:
            act_date = act.get("startTimeLocal", "")[:10]
            if act_date and act_date not in activities_by_day:
                activities_by_day[act_date] = act
    except Exception:
        activities_by_day = {}

    for i in range(days):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")

        try:
            # Busca resumo diário do usuário (Passos, Sono, Stress, FC)
            try:
                stats = _client.get_user_summary(day)
            except Exception:
                stats = {}

            # Busca HRV se disponível
            try:
                hrv_data = _client.get_hrv_data(day)
            except Exception:
                hrv_data = {}

            # Atividade do dia reaproveitada da busca em lote
            last_activity = activities_by_day.get(day, {})

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

            if (not sleep_seconds or sleep_seconds == 0) and i == 0:
                yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                sleep_seconds = fetch_valid_sleep_seconds(_client, yesterday_str)

            sleep_hours = round(float(sleep_seconds) / 3600, 2)

            # ====================================
            # PASSOS / STRESS / REPOUSO
            # ====================================
            steps = get_first_valid(stats, ["totalSteps", "steps", "dailySteps"], 0)
            stress = get_first_valid(stats, ["averageStressLevel", "stressAverage", "avgStressLevel"], 0)
            resting_hr = get_first_valid(stats, ["restingHeartRate", "restingHR"], 0)

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
            training_effect = float(last_activity.get("aerobicTrainingEffect", 0) or 0)
            distance_km = round(last_activity.get("distance", 0) / 1000, 2)

            # ====================================
            # TRAINING LOAD
            # ====================================
            training_load = round((training_effect * 8) + (distance_km * 1.5), 1)

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
        return {"stats": {}, "activities": [], "history": [], "future_schedule": []}

    today = datetime.now().strftime("%Y-%m-%d")

    try:
        stats = client.get_user_summary(today)
    except Exception:
        stats = {}

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
        "history": get_historical_activities(client, days=180),
        "future_schedule": get_future_schedule(client, days=35)
    }