import sqlite3
import pandas as pd

DB_NAME = "garmin_ai.db"


def init_db():

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        date TEXT PRIMARY KEY,
        sleep_hours REAL,
        resting_hr INTEGER,
        stress_avg INTEGER,
        steps INTEGER,
        vo2max REAL,
        training_effect REAL
    )
    """)

    conn.commit()

    conn.close()


def save_metrics(metrics):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO metrics VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        metrics["date"],
        metrics["sleep_hours"],
        metrics["resting_hr"],
        metrics["stress_avg"],
        metrics["steps"],
        metrics["vo2max"],
        metrics["training_effect"]
    ))

    conn.commit()

    conn.close()


def load_history():

    conn = sqlite3.connect(DB_NAME)

    df = pd.read_sql(
        "SELECT * FROM metrics ORDER BY date",
        conn
    )

    conn.close()

    return df