from pathlib import Path

import pandas as pd
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report


def check_data_drift(
    data_path: str = "data/raw/kaggle_events.csv",
    output_path: str = "monitoring/drift_report.html",
) -> None:
    df = pd.read_csv(data_path)
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["event_code"] = df["event"].map({"view": 1, "addtocart": 2, "transaction": 3})

    midpoint = len(df) // 2
    reference = df.iloc[:midpoint][["event_code", "itemid"]]
    current = df.iloc[midpoint:][["event_code", "itemid"]]

    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference, current_data=current)

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(target))
    print(f"Drift report saved to {target}")


if __name__ == "__main__":
    check_data_drift()
