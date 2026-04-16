import json
import argparse
from pathlib import Path

import joblib
import mlflow
import pandas as pd

try:
    from src.model.predict import recommend_from_artifacts
except ModuleNotFoundError:
    from predict import recommend_from_artifacts


def configure_mlflow() -> None:
    tracking_dir = Path("mlruns").resolve()
    tracking_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(tracking_dir.as_uri())
    mlflow.set_experiment("ecommerce-recsys")


def als_recommendations(
    model_artifacts: dict,
    user_id: int,
    k: int = 5,
) -> set:
    model = model_artifacts["model"]
    users = model_artifacts["users"]
    idx_to_item = model_artifacts["idx_to_item"]
    user_items = model_artifacts["user_items"]

    if user_id not in users:
        return set()

    user_idx = users[user_id]
    recommended_ids, _ = model.recommend(user_idx, user_items[user_idx], N=k)
    return {
        idx_to_item[int(item_idx)]
        for item_idx in recommended_ids
        if int(item_idx) in idx_to_item
    }


def hybrid_recommendations(
    model_artifacts: dict,
    user_id: int,
    k: int = 5,
    candidate_multiplier: int = 50,
) -> set:
    records = recommend_from_artifacts(
        model_artifacts,
        user_id=user_id,
        top_n=k,
        candidate_multiplier=candidate_multiplier,
    )
    return {record["item_id"] for record in records}


def ranking_metrics_at_k(
    model_artifacts: dict,
    test_df: pd.DataFrame,
    k: int = 5,
    mode: str = "hybrid",
    candidate_multiplier: int = 50,
    progress_every: int = 1000,
) -> tuple[float, float, float, int]:
    users = model_artifacts["users"]

    hits = 0
    total_predictions = 0
    recall_sum = 0.0
    hit_users = 0
    evaluated_users = 0

    for user_id, group in test_df.groupby("user_id"):
        if user_id not in users:
            continue

        actual_items = set(group["item_id"])
        if not actual_items:
            continue

        if mode == "als":
            predicted_items = als_recommendations(model_artifacts, user_id=user_id, k=k)
        else:
            predicted_items = hybrid_recommendations(
                model_artifacts,
                user_id=user_id,
                k=k,
                candidate_multiplier=candidate_multiplier,
            )

        user_hits = len(predicted_items & actual_items)
        hits += user_hits
        total_predictions += k
        recall_sum += user_hits / len(actual_items)
        if user_hits:
            hit_users += 1
        evaluated_users += 1
        if evaluated_users and evaluated_users % progress_every == 0:
            print(f"Evaluation progress: evaluated {evaluated_users} users")

    precision = hits / total_predictions if total_predictions else 0.0
    recall = recall_sum / evaluated_users if evaluated_users else 0.0
    hit_rate = hit_users / evaluated_users if evaluated_users else 0.0
    return precision, recall, hit_rate, evaluated_users


def evaluate(
    model_path: str = "models/als_model.joblib",
    test_events_path: str = "data/processed/test_events.csv",
    metrics_path: str = "data/processed/evaluation_metrics.json",
    k: int = 5,
    max_users: int | None = None,
    mode: str = "hybrid",
    candidate_multiplier: int = 50,
) -> dict:
    configure_mlflow()
    artifacts = joblib.load(model_path)
    test_events = pd.read_csv(test_events_path)

    test_interactions = (
        test_events.groupby(["visitorid", "itemid"], as_index=False)
        .size()
        .rename(columns={"visitorid": "user_id", "itemid": "item_id", "size": "event_count"})
    )
    if max_users is not None:
        selected_users = test_interactions["user_id"].drop_duplicates().head(max_users)
        test_interactions = test_interactions[test_interactions["user_id"].isin(selected_users)]
        print(f"Running quick evaluation on first {len(selected_users)} users")

    precision, recall, hit_rate, evaluated_users = ranking_metrics_at_k(
        artifacts,
        test_interactions,
        k=k,
        mode=mode,
        candidate_multiplier=candidate_multiplier,
    )

    metrics = {
        "precision_at_k": round(float(precision), 6),
        "recall_at_k": round(float(recall), 6),
        "hit_rate_at_k": round(float(hit_rate), 6),
        "k": k,
        "mode": mode,
        "candidate_multiplier": candidate_multiplier if mode == "hybrid" else None,
        "evaluated_users": evaluated_users,
    }

    output_path = Path(metrics_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    with mlflow.start_run(run_name="offline_evaluation"):
        mlflow.log_params(
            {
                "evaluation_k": k,
                "evaluation_mode": mode,
                "candidate_multiplier": candidate_multiplier if mode == "hybrid" else None,
            }
        )
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                mlflow.log_metric(key, value)
        mlflow.log_artifact(str(output_path))

    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default="models/als_model.joblib")
    parser.add_argument("--test-events-path", default="data/processed/test_events.csv")
    parser.add_argument("--metrics-path", default="data/processed/evaluation_metrics.json")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--max-users", type=int, default=None)
    parser.add_argument("--mode", choices=["hybrid", "als"], default="hybrid")
    parser.add_argument("--candidate-multiplier", type=int, default=50)
    args = parser.parse_args()
    evaluate(
        model_path=args.model_path,
        test_events_path=args.test_events_path,
        metrics_path=args.metrics_path,
        k=args.k,
        max_users=args.max_users,
        mode=args.mode,
        candidate_multiplier=args.candidate_multiplier,
    )
