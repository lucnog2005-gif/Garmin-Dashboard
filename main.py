from collector import collect_all_data
from metrics import extract_metrics

print("Baixando dados Garmin...")

data = collect_all_data()

metrics = extract_metrics(data)

print("\n===== DASHBOARD =====\n")

for key, value in metrics.items():

    print(f"{key}: {value}")

print("\n===== ANÁLISE =====\n")

if metrics["sleep_hours"] < 7:
    print("⚠️ Sono abaixo do ideal")

if metrics["stress_avg"] > 40:
    print("⚠️ Stress elevado")
else:
    print("✅ Stress controlado")

if metrics["training_effect"] > 4:
    print("⚠️ Treino muito intenso")
else:
    print("✅ Carga de treino adequada")

if metrics["vo2max"] >= 45:
    print("🔥 Excelente condicionamento aeróbico")