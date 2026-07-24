from datetime import datetime, date

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_first_available(source_dict, keys, default=0):
    """Retorna o primeiro valor encontrado na lista de chaves dentro do dicionário."""
    if not isinstance(source_dict, dict):
        return default
    for key in keys:
        if key in source_dict and source_dict[key] is not None:
            return source_dict[key]
    return default


def process_daily_stats(raw_stats):
    if not raw_stats:
        return {}

    today_str = str(date.today())
    is_today = raw_stats.get('calendarDate') == today_str
    
    sleep_sec = raw_stats.get('measurableAsleepDuration') or 0
    sleep_hours = round(sleep_sec / 3600, 2)
    
    # Se for hoje e ainda der 0 horas (madrugada), marca como em andamento
    sleep_display = f"{sleep_hours}h" if not (is_today and sleep_hours == 0) else "Sincronizando..."

    return {
        "date": raw_stats.get('calendarDate'),
        "sleep_hours": sleep_hours,
        "sleep_display": sleep_display,
        "steps": raw_stats.get('totalSteps') or 0,
        "resting_hr": raw_stats.get('restingHeartRate'),
        "stress": raw_stats.get('averageStressLevel'),
        "is_today": is_today
    }


# ============================================
# EXTRACT METRICS
# ============================================

def extract_metrics(data):
    stats = data.get("stats", {})
    activities = data.get("activities", [])

    last_activity = activities[0] if activities else {}

    # ========================================
    # ACTIVITY DATA
    # ========================================

    avg_hr = get_first_available(
        last_activity,
        ["averageHR", "averageHeartRate"],
        0
    )

    duration = get_first_available(
        last_activity,
        ["duration", "elapsedDuration"],
        0
    )

    training_effect = get_first_available(
        last_activity,
        ["aerobicTrainingEffect"],
        0
    )

    # ========================================
    # SLEEP
    # ========================================

    sleeping_seconds = get_first_available(
        stats,
        ["sleepingSeconds", "sleepSeconds", "totalSleepSeconds"],
        0
    )

    sleep_hours = round(sleeping_seconds / 3600, 2)

    # Se ainda é madrugada e a Garmin não consolidou o sono
    if sleeping_seconds == 0 and datetime.now().hour < 5:
        sleep_hours = None

    # ========================================
    # STEPS
    # ========================================

    steps = get_first_available(
        stats,
        ["totalSteps", "steps"],
        0
    )

    # ========================================
    # STRESS
    # ========================================

    stress_avg = get_first_available(
        stats,
        ["averageStressLevel", "avgStressLevel"],
        0
    )

    # ========================================
    # HRV
    # ========================================

    hrv = get_first_available(
        stats,
        ["hrvAverage", "lastNightAvg", "weeklyAvg"],
        0
    )

    # ========================================
    # RESTING HR
    # ========================================

    resting_hr = get_first_available(
        stats,
        ["restingHeartRate", "restingHR"],
        0
    )

    # ========================================
    # VO2
    # ========================================

    vo2max = (
        get_first_available(
            last_activity,
            ["vO2MaxValue", "vo2Max"],
            0
        )
        or get_first_available(
            stats,
            ["vO2MaxValue", "vo2Max"],
            0
        )
    )

    # ========================================
    # TRAINING LOAD
    # ========================================

    activity_load = get_first_available(
        last_activity,
        ["trainingLoad", "activityTrainingLoad"],
        0
    )

    if activity_load > 0:
        training_load = activity_load
    else:
        training_load = round(
            (avg_hr * 0.6) + (duration / 60) + (training_effect * 50),
            1
        )

    # ========================================
    # DISTANCE
    # ========================================

    distance_km = round(
        get_first_available(last_activity, ["distance"], 0) / 1000,
        2
    )

    # ========================================
    # METRICS BUILD
    # ========================================

    metrics = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "sleep_hours": sleep_hours,
        "steps": steps,
        "stress_avg": stress_avg,
        "resting_hr": resting_hr,
        "hrv": hrv,
        "calories": get_first_available(
            stats,
            ["totalKilocalories", "activeKilocalories"],
            0
        ),
        "vigorous_minutes": get_first_available(
            stats,
            ["vigorousIntensityMinutes"],
            0
        ),
        "last_activity": last_activity.get("activityName", "Sem atividade"),
        "last_distance_km": distance_km,
        "last_avg_hr": avg_hr,
        "last_duration_min": round(duration / 60, 1),
        "vo2max": vo2max,
        "training_effect": round(training_effect, 1),
        "training_load": training_load
    }

    return metrics


# ============================================
# PREPARE METRICS
# ============================================

def prepare_metrics(metrics):
    defaults = {
        "sleep_hours": 0,
        "steps": 0,
        "resting_hr": 0,
        "stress_avg": 0,
        "vo2max": 0,
        "training_effect": 0,
        "training_load": 0,
        "hrv": 0
    }

    for key, value in defaults.items():
        if key not in metrics or metrics[key] is None:
            metrics[key] = value

    return metrics