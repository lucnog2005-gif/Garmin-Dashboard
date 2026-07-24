import pandas as pd


def calculate_performance_trend(history_df):

    if history_df.empty or len(history_df) < 14:

        return {

            "trend": "Sem dados",

            "fitness_change": 0,

            "vo2_change": 0,

            "volume_change": 0
        }

    df = history_df.copy()

    # ==========================================
    # LIMPEZA
    # ==========================================

    df["training_load"] = pd.to_numeric(
        df["training_load"],
        errors="coerce"
    )

    df["vo2max"] = pd.to_numeric(
        df["vo2max"],
        errors="coerce"
    )

    df["vo2max"] = df["vo2max"].replace(
        0,
        pd.NA
    )

    df = df.sort_values("date")

    # ==========================================
    # SEMANAS
    # ==========================================

    recent = df.tail(7)

    previous = df.tail(14).head(7)

    # ==========================================
    # VOLUME (7 dias)
    # ==========================================

    recent_volume = (
        recent["training_load"]
        .mean()
    )

    previous_volume = (
        previous["training_load"]
        .mean()
    )

    volume_change = round(
        recent_volume - previous_volume,
        1
    )

    # ==========================================
    # FITNESS (42 dias - EWMA)
    # ==========================================

    current_fitness = (
        df["training_load"]
        .ewm(
            span=42,
            adjust=False
        )
        .mean()
        .iloc[-1]
    )

    previous_df = df.iloc[:-7]

    if len(previous_df) > 0:

        previous_fitness = (
            previous_df["training_load"]
            .ewm(
                span=42,
                adjust=False
            )
            .mean()
            .iloc[-1]
        )

    else:

        previous_fitness = current_fitness

    fitness_change = round(
        current_fitness -
        previous_fitness,
        1
    )

    # ==========================================
    # VO2
    # ==========================================

    recent_vo2_series = (
        recent["vo2max"]
        .dropna()
    )

    previous_vo2_series = (
        previous["vo2max"]
        .dropna()
    )

    if len(recent_vo2_series) == 0:

        vo2_change = 0

    else:

        recent_vo2 = (
            recent_vo2_series.mean()
        )

        if len(previous_vo2_series) == 0:

            previous_vo2 = recent_vo2

        else:

            previous_vo2 = (
                previous_vo2_series.mean()
            )

        vo2_change = round(
            recent_vo2 - previous_vo2,
            1
        )

    # ==========================================
    # SCORE
    # ==========================================

    score = 0

    if fitness_change > 2:
        score += 1

    if vo2_change > 0.3:
        score += 1

    if volume_change > 20:
        score += 1

    # ==========================================
    # TREND
    # ==========================================

    if score >= 2:

        trend = "🟢 Improving"

    elif score == 1:

        trend = "🟡 Stable"

    else:

        trend = "🔴 Declining"

    return {

        "trend": trend,

        "fitness_change": round(
            fitness_change,
            1
        ),

        "vo2_change": round(
            vo2_change,
            1
        ),

        "volume_change": round(
            volume_change,
            1
        )
    }