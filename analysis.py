import numpy as np
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


# ============================================
# FASE 1: HRV STATUS & EFFICIENCY FACTOR (EF)
# ============================================

def calculate_hrv_status(metrics, history_df):
    """
    Calcula o estado da Variabilidade da Frequência Cardíaca (HRV).
    Compara o valor recente com a linha de base (baseline de 28 dias).
    """
    current_hrv = metrics.get("hrv_last_night") or metrics.get("hrv_avg")
    
    if not current_hrv and not history_df.empty and "hrv" in history_df.columns:
        valid_hrv = history_df[history_df["hrv"] > 0]["hrv"]
        if not valid_hrv.empty:
            current_hrv = float(valid_hrv.iloc[-1])
            
    if not current_hrv:
        return {
            "status": "Sem dados",
            "hrv_value": 0,
            "baseline_avg": 0,
            "message": "Dados de HRV indisponíveis na sincronização."
        }
        
    # Cálculo da linha de base (Média móvel de 28 dias)
    if not history_df.empty and "hrv" in history_df.columns and len(history_df) >= 7:
        valid_history = history_df[history_df["hrv"] > 0]["hrv"]
        baseline_avg = valid_history.tail(28).mean() if len(valid_history) >= 28 else valid_history.mean()
        std_dev = valid_history.tail(28).std() if len(valid_history) >= 28 else 5.0
    else:
        baseline_avg = current_hrv
        std_dev = 5.0

    # Faixa normal de variação (baseline range ± 0.75 desvio padrão)
    lower_bound = baseline_avg - (0.75 * std_dev)
    upper_bound = baseline_avg + (0.75 * std_dev)

    if current_hrv >= lower_bound:
        status = "🟢 Equilibrado"
        message = "Sistema Nervoso Autônomo recuperado e pronto para absorver carga."
    elif current_hrv < lower_bound and current_hrv >= lower_bound - 5:
        status = "🟡 Desbalanço leve"
        message = "Sinal inicial de fadiga central ou estresse residual."
    else:
        status = "🔴 Baixo / Desbalanceado"
        message = "Fadiga do Sistema Nervoso Autônomo alta. Atenção ao descanso."

    return {
        "status": status,
        "hrv_value": round(current_hrv, 1),
        "baseline_avg": round(baseline_avg, 1),
        "lower_bound": round(lower_bound, 1),
        "upper_bound": round(upper_bound, 1),
        "message": message
    }


def calculate_efficiency_factor(history_df):
    """
    Calcula o Fator de Eficiência Aeróbica (EF = Normalization Pace / Heart Rate Média).
    Para corrida: EF = (Velocidade em m/min) / FC_média.
    """
    if history_df.empty:
        return pd.DataFrame()

    df = history_df.copy()

    # Tratamento para identificar Pace (min/km) ou Velocidade (km/h)
    if "avg_pace_min_km" in df.columns and "avg_hr" in df.columns:
        def pace_to_m_per_min(pace):
            try:
                if isinstance(pace, str) and ":" in pace:
                    m, s = map(float, pace.split(":"))
                    total_min = m + (s / 60.0)
                else:
                    total_min = float(pace)
                return 1000.0 / total_min if total_min > 0 else 0
            except:
                return 0

        df["speed_m_min"] = df["avg_pace_min_km"].apply(pace_to_m_per_min)
        df["efficiency_factor"] = np.where(
            df["avg_hr"] > 0,
            df["speed_m_min"] / df["avg_hr"],
            0
        )
    elif "avg_speed_kmh" in df.columns and "avg_hr" in df.columns:
        df["speed_m_min"] = (df["avg_speed_kmh"] * 1000.0) / 60.0
        df["efficiency_factor"] = np.where(
            df["avg_hr"] > 0,
            df["speed_m_min"] / df["avg_hr"],
            0
        )
    else:
        df["efficiency_factor"] = 0.0

    df["efficiency_factor"] = df["efficiency_factor"].round(3)
    return df