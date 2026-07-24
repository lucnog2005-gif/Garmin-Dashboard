import pandas as pd
import os
from datetime import datetime


def save_metrics(metrics):

    clean_metrics = {}

    for key, value in metrics.items():

        if isinstance(value, (int, float, str)):
            clean_metrics[key] = value

    clean_metrics["date"] = datetime.now().strftime("%Y-%m-%d")

    df = pd.DataFrame([clean_metrics])

    file_exists = os.path.exists("history = get_historical_activities(client, days=90)")

    df.to_csv(
        "history = get_historical_activities(client, days=90)",
        mode="a",
        header=not file_exists,
        index=False
    )