from pathlib import Path
import sys

import pandas as pd

try:
    from evidently.metric_preset import DataDriftPreset
    from evidently.report import Report
except ModuleNotFoundError:
    from evidently.legacy.metric_preset import DataDriftPreset
    from evidently.legacy.report import Report

try:
    from src.monitoring.monitoring_metrics import update_monitoring_metrics
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.monitoring.monitoring_metrics import update_monitoring_metrics


def extract_drift_summary(report: Report) -> tuple[int, int]:
    try:
        report_data = report.as_dict()
        metrics = report_data.get("metrics", [])
        for metric in metrics:
            result = metric.get("result", {})
            if "dataset_drift" in result:
                drift_detected = int(bool(result.get("dataset_drift")))
                drifted_features_count = int(result.get("number_of_drifted_columns", 0))
                return drift_detected, drifted_features_count
    except Exception:
        pass

    return 0, 0


def calculate_fallback_drift(reference: pd.DataFrame, current: pd.DataFrame, threshold: float = 0.10) -> tuple[int, int]:
    drifted_features_count = 0
    for column in reference.columns:
        reference_dist = reference[column].value_counts(normalize=True)
        current_dist = current[column].value_counts(normalize=True)
        all_values = reference_dist.index.union(current_dist.index)
        total_variation = (reference_dist.reindex(all_values, fill_value=0) - current_dist.reindex(all_values, fill_value=0)).abs().sum() / 2
        if total_variation > threshold:
            drifted_features_count += 1

    return int(drifted_features_count > 0), drifted_features_count


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
    data_drift_detected, drifted_features_count = extract_drift_summary(report)
    if not data_drift_detected and not drifted_features_count:
        data_drift_detected, drifted_features_count = calculate_fallback_drift(reference, current)

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(target))
    update_monitoring_metrics(
        data_drift_detected=data_drift_detected,
        drifted_features_count=drifted_features_count,
    )
    print(f"Drift report saved to {target}")
    print(f"data_drift_detected={data_drift_detected}")
    print(f"drifted_features_count={drifted_features_count}")


if __name__ == "__main__":
    check_data_drift()
