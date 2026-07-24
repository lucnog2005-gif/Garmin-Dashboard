import time
import schedule
import traceback

from collector import collect_all_data

from metrics import (
    extract_metrics,
    prepare_metrics
)

from database import (
    init_db,
    save_metrics
)

from analysis import (
    calculate_acwr,
    calculate_recovery_score,
    recovery_status,
    daily_recommendation
)

from notifier import send_telegram_message


# ============================================
# INIT DATABASE
# ============================================

init_db()


# ============================================
# DAILY REPORT
# ============================================

def run_daily_report():

    try:

        print("🚀 Coletando dados Garmin...")

        # ====================================
        # COLETA
        # ====================================

        data = collect_all_data()

        if not data:
            raise Exception("collect_all_data retornou vazio")

        # ====================================
        # MÉTRICAS
        # ====================================

        metrics = extract_metrics(data)

        metrics = prepare_metrics(metrics)

        # ====================================
        # SAVE DATABASE
        # ====================================

        save_metrics(metrics)

        # ====================================
        # PERFORMANCE
        # ====================================

        history = data.get("history", [])

        acwr = calculate_acwr(history)

        recovery_score = calculate_recovery_score(
            metrics
        )

        recovery = recovery_status(
            recovery_score
        )

        recommendation = daily_recommendation(
            recovery_score,
            acwr
        )

        # ====================================
        # LOAD STATUS
        # ====================================

        if acwr > 1.5:
            load_status = "🔴 Alta"

        elif acwr > 1.2:
            load_status = "🟡 Moderada"

        else:
            load_status = "🟢 Controlada"

        # ====================================
        # PERFORMANCE STATUS
        # ====================================

        if recovery_score >= 80:
            perf_status = "🟢 Excelente"

        elif recovery_score >= 60:
            perf_status = "🟡 Moderada"

        else:
            perf_status = "🔴 Fadiga acumulada"

        # ====================================
        # TELEGRAM MESSAGE
        # ====================================

        message = f"""
🏃 Garmin AI Coach

{perf_status}

🟢 Recuperação: {recovery}
{load_status} Carga

😴 Sono: {metrics.get('sleep_hours', 0)}h
❤️ FC repouso: {metrics.get('resting_hr', 0)}
🔥 Stress: {metrics.get('stress_avg', 0)}
👣 Passos: {metrics.get('steps', 0)}
🏃 VO2max: {metrics.get('vo2max', 0)}

📈 ACWR: {round(acwr, 2)}

🎯 Ação do dia:
{recommendation}
"""

        # ====================================
        # SEND TELEGRAM
        # ====================================

        send_telegram_message(message)

        print("✅ Relatório enviado!")

    except Exception as e:

        error_text = traceback.format_exc()

        print("❌ Erro scheduler:")
        print(error_text)

        try:

            send_telegram_message(
                f"""
⚠️ Garmin AI Coach falhou

Erro:
{str(e)}
"""
            )

        except:
            print("❌ Falha ao enviar erro Telegram")


# ============================================
# SCHEDULE
# ============================================

schedule.every().day.at("09:00").do(
    run_daily_report
)

print("🚀 Scheduler iniciado...")


# ============================================
# LOOP
# ============================================

while True:

    schedule.run_pending()

    time.sleep(60)