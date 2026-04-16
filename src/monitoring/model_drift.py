import sys
from pathlib import Path

import joblib
import mlflow
import pandas as pd

try:
    from src.model.mlflow_utils import configure_mlflow, log_common_tags, log_event_profile
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.model.mlflow_utils import configure_mlflow, log_common_tags, log_event_profile


def precision_at_k(model_artifacts: dict, test_df: pd.DataFrame, k: int = 5) -> float:
    model = model_artifacts["model"]
    users = model_artifacts["users"]
    items = model_artifacts["items"]
    idx_to_item = {value: key for key, value in items.items()}
    user_items = model_artifacts["user_items"]

    hits = 0
    total = 0
    for uid_raw, group in test_df.groupby("user_id"):
        if uid_raw not in users:
            continue

        actual = set(group["item_id"])
        user_idx = users[uid_raw]
        recommended, _ = model.recommend(user_idx, user_items[user_idx], N=k)
        predicted = {idx_to_item[item_idx] for item_idx in recommended if item_idx in idx_to_item}
        hits += len(predicted & actual)
        total += k

    return hits / total if total else 0.0


def run_drift_check(
    model_path: str = "models/als_model.joblib",
    data_path: str = "data/processed/kaggle_test_events.csv",
    threshold: float = 0.05,
) -> float:
    configure_mlflow()
    artifacts = joblib.load(model_path)
    df = pd.read_csv(data_path)
    test_df = (
        df.groupby(["visitorid", "itemid"], as_index=False)
        .size()
        .rename(columns={"visitorid": "user_id", "itemid": "item_id", "size": "event_count"})
    )

    p_at_5 = precision_at_k(artifacts, test_df, k=5)
    print(f"Precision@5 = {p_at_5:.4f}")

    with mlflow.start_run(run_name="drift_check"):
        log_common_tags(stage="model_drift_check")
        mlflow.set_tags(
            {
                "model_path": model_path,
                "data_path": data_path,
                "drift_signal": "precision_at_5_threshold",
            }
        )
        log_event_profile(df, "drift_check_events")
        mlflow.log_param("precision_threshold", threshold)
        mlflow.log_metric("precision_at_5", p_at_5)
        mlflow.log_metric("model_drift_detected", int(p_at_5 < threshold))

    if p_at_5 < threshold:
        print("ALERT: model drift detected - retraining needed!")

    return p_at_5


if __name__ == "__main__":
    run_drift_check()
