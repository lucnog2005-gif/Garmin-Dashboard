from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from garminconnect import GarminConnectTooManyRequestsError

# Importação da função do garmin_auth.py
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
        calendar_events = client.get_calendar(today.isoformat(), future_date.isoformat())
        events_list = calendar_events.get("calendarItems", []) if isinstance(calendar_events, dict) else (calendar_events or [])

        for item in events_list:
            event_date = item.get("date") or item.get("startDate")
            if not event_date:
                continue

            item_date = datetime.strptime(event_date[:10], "%Y-%m-%d").date()
            if item_date <= today:
                continue

            est_load = item.get("estimatedTrainingLoad") or 0
            if est_load == 0:
                duration_min = (item.get("durationInSeconds") or 0) / 60
                distance_km = (item.get("distanceInMeters") or 0) / 1000
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


def extract_hrv_value(hrv_raw, stats=None):
    """
    Varre recursivamente ou testa todas as chaves conhecidas onde o Garmin costuma guardar o HRV.
    """
    if not hrv_raw and not stats:
        return 0

    val = 0

    # 1. Tenta extrair de hrv_raw (get_hrv_data)
    if isinstance(hrv_raw, dict):
        # hrvSummary
        summary = hrv_raw.get("hrvSummary") or hrv_raw.get("hrvSummaries") or {}
        if isinstance(summary, list) and len(summary) > 0:
            summary = summary[0]
        
        if isinstance(summary, dict):
            val = (
                summary.get("lastNightAvg") 
                or summary.get("weeklyAvg") 
                or summary.get("lastNight5MinHigh")
                or summary.get("baseline", {}).get("balancedLow")
                or 0
            )

        if not val:
            val = hrv_raw.get("lastNightAvg") or hrv_raw.get("weeklyAvg") or 0

    # 2. Fallback de busca em stats
    if not val and isinstance(stats, dict):
        val = (
            stats.get("lastNightAvgHrv") 
            or stats.get("hrvValue") 
            or stats.get("lastNightAvg") 
            or stats.get("avgWakingHrv") 
            or stats.get("hrvSummary", {}).get("lastNightAvg")
            or 0
        )

    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0


# ============================================
# HISTÓRICO DE ATIVIDADES (180 DIAS - 6 MESES)
# ============================================

@st.cache_data(ttl=1800)
def get_historical_activities(_client, days=180):
    if not _client:
        return []

    history = []

    # Busca lote de atividades recentes para otimizar chamadas
    try:
        all_activities = _client.get_activities(0, 200)
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
            # Resumo do usuário
            try:
                stats = _client.get_user_summary(day)
            except Exception:
                stats = {}

            last_activity = activities_by_day.get(day, {})

            # Sono
            sleep_seconds = get_first_valid(
                stats,
                ["measurableAsleepDuration", "sleepingSeconds", "sleepSeconds", "dailySleepSeconds", "sleepDuration"],
                0
            )

            if (not sleep_seconds or sleep_seconds == 0) and i == 0:
                yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                sleep_seconds = fetch_valid_sleep_seconds(_client, yesterday_str)

            sleep_hours = round(float(sleep_seconds) / 3600, 2)

            # Passos, Estresse e FC Repouso
            steps = get_first_valid(stats, ["totalSteps", "steps", "dailySteps"], 0)
            stress = get_first_valid(stats, ["averageStressLevel", "stressAverage", "avgStressLevel"], 0)
            resting_hr = get_first_valid(stats, ["restingHeartRate", "restingHR"], 0)

            # HRV
            hrv_raw = None
            try:
                hrv_raw = _client.get_hrv_data(day)
            except Exception:
                pass

            hrv = extract_hrv_value(hrv_raw, stats)

            # Métricas da Atividade
            training_effect = float(last_activity.get("aerobicTrainingEffect", 0) or 0)
            distance_km = round(last_activity.get("distance", 0) / 1000, 2)
            avg_hr = last_activity.get("averageHR") or last_activity.get("averageHeartRate") or 0
            
            speed_ms = last_activity.get("averageSpeed", 0) or 0
            avg_speed_kmh = round(speed_ms * 3.6, 2)
            
            if avg_speed_kmh > 0:
                pace_decimal = 60.0 / avg_speed_kmh
                minutes = int(pace_decimal)
                seconds = int((pace_decimal - minutes) * 60)
                avg_pace_str = f"{minutes}:{seconds:02d}"
            else:
                avg_pace_str = "0:00"

            training_load = round((training_effect * 8) + (distance_km * 1.5), 1)

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
                "training_load": training_load,
                "avg_hr": avg_hr,
                "avg_speed_kmh": avg_speed_kmh,
                "avg_pace_min_km": avg_pace_str,
                "aerobic_te": training_effect,
                "anaerobic_te": float(last_activity.get("anaerobicTrainingEffect", 0) or 0)
            })

        except GarminConnectTooManyRequestsError:
            st.warning("⚠️ Garmin Rate Limit (429) atingido ao construir histórico.")
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

    history = get_historical_activities(client, days=180)

    # Imprime no terminal para sabermos se há dados no histórico
    if history:
        recent_hrvs = [h["hrv"] for h in history if h.get("hrv", 0) > 0]
        print(f"[DEBUG HRV] Valores de HRV encontrados nos últimos dias: {recent_hrvs[:10]}")

    return {
        "stats": stats,
        "activities": activities,
        "history": history,
        "future_schedule": get_future_schedule(client, days=35)
    }