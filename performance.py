import pandas as pd


# =========================================
# ACWR
# =========================================

def calculate_acwr(history):

    df = pd.DataFrame(history)

    if "training_load" not in df.columns:
        return None

    acute = df["training_load"].tail(7).mean()
    chronic = df["training_load"].tail(28).mean()

    if chronic == 0 or pd.isna(chronic):
        return None

    acwr = acute / chronic

    return round(acwr, 2)


# =========================================
# RECOVERY SCORE
# =========================================

def calculate_recovery_score(metrics):

    score = 100

    # Sono
    if metrics["sleep_hours"] < 7:
        score -= 20

    # Stress
    if metrics["stress_avg"] > 40:
        score -= 20

    # FC repouso
    if metrics["resting_hr"] > 65:
        score -= 15

    # Training Effect
    if metrics["training_effect"] > 4:
        score -= 20

    return max(score, 0)


# =========================================
# STATUS
# =========================================

def recovery_status(score):

    if score >= 80:
        return "🟢 Recuperado"

    elif score >= 60:
        return "🟡 Moderado"

    return "🔴 Fatigado"


# =========================================
# TREINO DO DIA
# =========================================

def daily_recommendation(score, acwr):

    if acwr is not None and acwr > 1.5:
        return "🚨 Recuperação ativa + mobilidade"

    if score < 60:
        return "😴 Descanso"

    if score < 80:
        return "🏃 Z2 leve"

    return "🔥 Treino intenso"