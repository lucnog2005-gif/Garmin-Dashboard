import pandas as pd


# ============================================
# INSIGHTS
# ============================================

def generate_insights(metrics):
    insights = []

    sleep = metrics.get("sleep_hours") or 0

    if sleep >= 7.5:
        insights.append("Qualidade de sono excelente")
    elif sleep >= 6.5:
        insights.append("Qualidade de sono adequada")
    elif sleep >= 5.5:
        insights.append("Sono moderado (atenção na recuperação)")
    else:
        insights.append("Sono insuficiente")

    if metrics.get("stress_avg", 0) <= 25:
        insights.append("Stress controlado")
    else:
        insights.append("Stress elevado")

    if metrics.get("training_effect", 0) >= 3:
        insights.append("Carga de treino adequada")
    else:
        insights.append("Treino leve hoje")

    if metrics.get("vo2max", 0) >= 45:
        insights.append("Excelente condicionamento aeróbico")

    return insights


# ============================================
# ACWR
# ============================================

def calculate_acwr(history):
    if len(history) < 7:
        return 1.0

    df = pd.DataFrame(history)

    acute = df["training_load"].tail(7).mean()
    chronic = df["training_load"].tail(28).mean()

    if chronic == 0:
        return 1.0

    return round(acute / chronic, 2)


# ============================================
# RECOVERY SCORE
# ============================================

def calculate_recovery_score(metrics):
    score = 100
    sleep = metrics.get("sleep_hours") or 0

    if sleep < 5.5:
        score -= 20
    elif sleep < 6.5:
        score -= 10

    if metrics.get("stress_avg", 0) > 30:
        score -= 20

    if metrics.get("resting_hr", 0) > 70:
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

def daily_recommendation(recovery_score, acwr):
    if recovery_score < 60:
        return "Recuperação ativa + mobilidade"

    if acwr > 1.5:
        return "Reduzir carga hoje"

    if recovery_score >= 80 and acwr < 1.2:
        return "Treino intenso liberado"

    return "Treino moderado"


# ============================================
# FITNESS (CTL)
# ============================================

def calculate_fitness(df):
    if df.empty or "training_load" not in df.columns:
        return 0.0

    load = pd.to_numeric(df["training_load"], errors="coerce").fillna(0)
    fitness = load.ewm(span=42, adjust=False).mean().iloc[-1]

    return round(fitness, 1)


# ============================================
# FATIGUE (ATL)
# ============================================

def calculate_fatigue(df):
    if df.empty or "training_load" not in df.columns:
        return 0.0

    load = pd.to_numeric(df["training_load"], errors="coerce").fillna(0)
    fatigue = load.ewm(span=7, adjust=False).mean().iloc[-1]

    return round(fatigue, 1)


# ============================================
# FORM (TSB)
# ============================================

def calculate_form(fitness, fatigue):
    return round(fitness - fatigue, 1)


# ============================================
# AI COACH
# ============================================

def ai_coach_messages(metrics, recovery_score, acwr, form):
    messages = []

    # RECOVERY
    if recovery_score >= 80:
        messages.append("🟢 Recuperação adequada")
    elif recovery_score >= 60:
        messages.append("🟡 Recuperação moderada")
    else:
        messages.append("🔴 Recuperação comprometida")

    # LOAD
    if acwr > 1.5:
        messages.append("🔴 Carga excessiva")
    elif acwr > 1.2:
        messages.append("🟡 Carga elevada")
    else:
        messages.append("🟢 Carga controlada")

    # FORM
    if form >= 10:
        messages.append("🟢 Recuperado e pronto para intensidade")
    elif form >= -10:
        messages.append("🟡 Treino normal recomendado")
    elif form >= -25:
        messages.append("🟠 Fadiga moderada")
    else:
        messages.append("🔴 Necessidade de recuperação")

    # SLEEP
    sleep = metrics.get("sleep_hours") or 0
    if sleep >= 7.0:
        messages.append("🟢 Sono excelente")
    elif sleep >= 6.2:
        messages.append("🟢 Sono adequado")
    elif sleep >= 5.5:
        messages.append("🟡 Sono levemente abaixo do ideal")
    else:
        messages.append("🔴 Sono insuficiente")

    # VO2
    vo2 = metrics.get("vo2max", 0)
    if vo2 >= 45:
        messages.append("🟢 Excelente capacidade aeróbica")
    elif vo2 >= 38:
        messages.append("🟡 Condicionamento moderado")
    else:
        messages.append("🔴 Capacidade aeróbica baixa")

    return messages