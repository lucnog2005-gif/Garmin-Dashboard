import pandas as pd


# ============================================
# SLEEP DEBT
# ============================================

def calculate_sleep_debt(history_df, ideal_sleep=7.5):
    if history_df.empty or "sleep_hours" not in history_df.columns:
        return 0.0

    sleep_debt = 0.0
    recent_sleep = history_df.tail(7)

    for sleep in recent_sleep["sleep_hours"]:
        if sleep is None or sleep <= 0:
            continue

        debt = ideal_sleep - sleep
        if debt > 0:
            sleep_debt += debt

    # Cap no débito máximo calculável para evitar distorções no Readiness
    return round(min(sleep_debt, 8.0), 1)


# ============================================
# STRAIN SCORE
# ============================================

def calculate_strain_score(metrics):
    training_load = metrics.get("training_load", 0)
    training_effect = metrics.get("training_effect", 0)
    stress = metrics.get("stress_avg", 0)

    strain = (training_load / 100) + (training_effect * 2) + (stress / 15)
    strain = max(0, min(strain, 21))

    return round(strain, 1)


# ============================================
# READINESS SCORE
# ============================================

def calculate_readiness_score(recovery_score, sleep_debt, form):
    readiness = recovery_score

    # Penalidade ponderada e mais suave para o débito de sono acumulado
    readiness -= sleep_debt * 1.2

    # Bônus/penalidade limitada pelo Form (TSB)
    form_bonus = max(-15, min(form * 0.2, 15))

    readiness += form_bonus
    readiness = max(0, min(readiness, 100))

    return round(readiness, 1)


# ============================================
# BODY BATTERY
# ============================================

def calculate_body_battery(recovery_score, stress_avg, sleep_hours):
    if not sleep_hours or sleep_hours <= 0:
        sleep_hours = 7.0

    battery = (recovery_score * 0.6) + (sleep_hours * 5) - (stress_avg * 0.5)
    battery = max(0, min(battery, 100))

    return round(battery, 1)


# ============================================
# RECOVERY TREND
# ============================================

def recovery_trend(history_df):
    if len(history_df) < 7 or "sleep_hours" not in history_df.columns:
        return "Sem dados"

    sleep_df = history_df[history_df["sleep_hours"] > 0]

    if len(sleep_df) < 4:
        return "Sem dados"

    recent_sleep = sleep_df["sleep_hours"].tail(3).mean()
    older_sleep = sleep_df["sleep_hours"].tail(6).head(3).mean()

    if recent_sleep > older_sleep + 0.2:
        return "Melhorando"
    elif recent_sleep < older_sleep - 0.2:
        return "Piorando"
    else:
        return "Estável"


# ============================================
# RECOVERY STATUS
# ============================================

def recovery_status(readiness):
    if readiness >= 80:
        return "🟢 Ready to perform"
    elif readiness >= 60:
        return "🟡 Moderate readiness"
    else:
        return "🔴 Recovery compromised"