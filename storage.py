import os
import pandas as pd
from datetime import datetime

HISTORY_FILE = "history.csv"

def save_metrics(metrics):
    """
    Salva ou atualiza as métricas diárias no arquivo history.csv.
    Garante deduplicação por data e mantém o alinhamento de colunas.
    """
    if not metrics or not isinstance(metrics, dict):
        return

    clean_metrics = {}

    # 1. Filtra apenas tipos primitivos válidos (int, float, str)
    for key, value in metrics.items():
        if isinstance(value, (int, float, str)) and value is not None:
            clean_metrics[key] = value

    # 2. Define a data (usa a data do dict ou a data atual do sistema)
    if "date" not in clean_metrics or not clean_metrics["date"]:
        clean_metrics["date"] = datetime.now().strftime("%Y-%m-%d")

    new_df = pd.DataFrame([clean_metrics])

    # 3. Se o arquivo history.csv já existir, faz o merge sem duplicar
    if os.path.exists(HISTORY_FILE):
        try:
            old_df = pd.read_csv(HISTORY_FILE)

            # Combina o histórico antigo com a nova métrica
            combined_df = pd.concat([old_df, new_df], ignore_index=True)

            # Remove duplicatas mantendo SEMPRE a versão mais recente gravada para cada dia
            if "date" in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=["date"], keep="last")

            # Garante ordenação cronológica por data
            combined_df = combined_df.sort_values("date").reset_index(drop=True)
            combined_df.to_csv(HISTORY_FILE, index=False)
            return
        except Exception as e:
            print(f"⚠️ Erro ao atualizar {HISTORY_FILE}: {e}")

    # 4. Se o arquivo não existia, cria um novo history.csv limpo
    new_df.to_csv(HISTORY_FILE, index=False)