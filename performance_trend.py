import pandas as pd


def calculate_performance_trend(history_df):
    if history_df.empty or len(history_df) < 7:
        return {
            "trend": "Sem dados",
            "fitness_change": 0.0,
            "vo2_change": 0.0,
            "volume_change": 0.0,
        }

    df = history_df.copy()

    # Garantir ordenação por data
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

    # Variações dos últimos 7 dias comparados aos 7 anteriores
    recent_7 = df.tail(7)
    previous_7 = df.tail(14).head(7)

    # Fitness (CTL)
    fit_recent = (
        recent_7["training_load"].mean() if "training_load" in recent_7 else 0
    )
    fit_prev = (
        previous_7["training_load"].mean()
        if "training_load" in previous_7
        else 0
    )
    fitness_change = round(fit_recent - fit_prev, 1)

    # VO2max
    vo2_recent = recent_7["vo2max"].mean() if "vo2max" in recent_7 else 0
    vo2_prev = previous_7["vo2max"].mean() if "vo2max" in previous_7 else 0
    vo2_change = round(vo2_recent - vo2_prev, 1)

    # Volume (distância ou carga)
    vol_recent = recent_7["steps"].mean() if "steps" in recent_7 else 0
    vol_prev = previous_7["steps"].mean() if "steps" in previous_7 else 0
    volume_change = round((vol_recent - vol_prev) / 1000, 1)

    # Lógica inteligente de tendência
    # Se a carga caiu ligeiramente mas a recuperação/form está alta (cenário de Tapering)
    if fitness_change < 0 and abs(fitness_change) <= 5.0:
        trend = "🟢 Polimento (Tapering)"
    elif fitness_change > 1.0:
        trend = "🟢 Evoluindo"
    elif fitness_change >= -1.0:
        trend = "🟢 Estável"
    else:
        trend = "🟡 Carga em Queda"

    return {
        "trend": trend,
        "fitness_change": fitness_change,
        "vo2_change": vo2_change,
        "volume_change": volume_change,
    }