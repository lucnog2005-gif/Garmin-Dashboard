import pandas as pd


# ============================================
# INSIGHTS
# ============================================

def generate_insights(metrics):

    insights = []

    if metrics["sleep_hours"] >= 7:

        insights.append(
            "Qualidade de sono adequada"
        )

    else:

        insights.append(
            "Sono insuficiente"
        )

    if metrics["stress_avg"] <= 25:

        insights.append(
            "Stress controlado"
        )

    else:

        insights.append(
            "Stress elevado"
        )

    if metrics["training_effect"] >= 3:

        insights.append(
            "Carga de treino adequada"
        )

    else:

        insights.append(
            "Treino leve hoje"
        )

    if metrics["vo2max"] >= 45:

        insights.append(
            "Excelente condicionamento aeróbico"
        )

    return insights


# ============================================
# ACWR
# ============================================

def calculate_acwr(history):

    if len(history) < 7:
        return 1.0

    df = pd.DataFrame(history)

    acute = (
        df["training_load"]
        .tail(7)
        .mean()
    )

    chronic = (
        df["training_load"]
        .tail(28)
        .mean()
    )

    if chronic == 0:
        return 1.0

    return round(
        acute / chronic,
        2
    )


# ============================================
# RECOVERY SCORE
# ============================================

def calculate_recovery_score(metrics):

    score = 100

    if metrics["sleep_hours"] < 7:
        score -= 15

    if metrics["stress_avg"] > 30:
        score -= 20

    if metrics["resting_hr"] > 70:
        score -= 10

    return max(score, 0)


# ============================================
# RECOVERY STATUS
# ============================================

def recovery_status(score):

    if score >= 80:
        return "Excelente"

    elif score >= 60:
        return "Moderada"

    else:
        return "Ruim"


# ============================================
# DAILY RECOMMENDATION
# ============================================

def daily_recommendation(
    recovery_score,
    acwr
):

    if recovery_score < 60:

        return (
            "Recuperação ativa "
            "+ mobilidade"
        )

    if acwr > 1.5:

        return (
            "Reduzir carga hoje"
        )

    if recovery_score >= 80 and acwr < 1.2:

        return (
            "Treino intenso liberado"
        )

    return "Treino moderado"


# ============================================
# FITNESS (CTL)
# ============================================

def calculate_fitness(df):

    if df.empty:
        return 0

    load = pd.to_numeric(
        df["training_load"],
        errors="coerce"
    ).fillna(0)

    fitness = (
        load
        .ewm(span=42, adjust=False)
        .mean()
        .iloc[-1]
    )

    return round(fitness, 1)


# ============================================
# FATIGUE (ATL)
# ============================================

def calculate_fatigue(df):

    if df.empty:
        return 0

    load = pd.to_numeric(
        df["training_load"],
        errors="coerce"
    ).fillna(0)

    fatigue = (
        load
        .ewm(span=7, adjust=False)
        .mean()
        .iloc[-1]
    )

    return round(fatigue, 1)


# ============================================
# FORM (TSB)
# ============================================

def calculate_form(
    fitness,
    fatigue
):

    form = fitness - fatigue

    return round(form, 1)


# ============================================
# AI COACH
# ============================================

def ai_coach_messages(
    metrics,
    recovery_score,
    acwr,
    form
):

    messages = []

    # ========================================
    # RECOVERY
    # ========================================

    if recovery_score >= 80:

        messages.append(
            "🟢 Recuperação adequada"
        )

    elif recovery_score >= 60:

        messages.append(
            "🟡 Recuperação moderada"
        )

    else:

        messages.append(
            "🔴 Recuperação comprometida"
        )

    # ========================================
    # LOAD
    # ========================================

    if acwr > 1.5:

        messages.append(
            "🔴 Carga excessiva"
        )

    elif acwr > 1.2:

        messages.append(
            "🟡 Carga elevada"
        )

    else:

        messages.append(
            "🟢 Carga controlada"
        )

# ========================================
# FORM
# ========================================

    if form >= 10:

        messages.append(
        "🟢 Recuperado e pronto para intensidade"
    )   

    elif form >= -10:

        messages.append(
        "🟡 Treino normal recomendado"
    )

    elif form >= -25:

        messages.append(
        "🟠 Fadiga moderada"
    )

    else:

        messages.append(
        "🔴 Necessidade de recuperação"
    )

    # ========================================
    # SLEEP
    # ========================================

    if metrics["sleep_hours"] < 7:

        messages.append(
            "🟡 Sono insuficiente"
        )

    else:

        messages.append(
            "🟢 Sono adequado"
        )

    # ========================================
    # VO2
    # ========================================

    if metrics["vo2max"] >= 45:

        messages.append(
            "🟢 Excelente capacidade aeróbica"
        )

    elif metrics["vo2max"] >= 38:

        messages.append(
            "🟡 Condicionamento moderado"
        )

    else:

        messages.append(
            "🔴 Capacidade aeróbica baixa"
        )

    return messages