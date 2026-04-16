from pathlib import Path

import pandas as pd


def load_events(path: str = "data/raw/kaggle_events.csv") -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find events file at {csv_path}")

    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df
