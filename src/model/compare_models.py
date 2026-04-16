import argparse
import json
from pathlib import Path

try:
    from src.model.evaluate import evaluate
    from src.model.train import train
except ModuleNotFoundError:
    from evaluate import evaluate
    from train import train


MODEL_CONFIGS = {
    "als": {
        "factors": 32,
        "iterations": 10,
        "regularization": 0.05,
        "alpha": 20.0,
        "learning_rate": 0.01,
    },
    "bpr": {
        "factors": 32,
        "iterations": 40,
        "regularization": 0.01,
        "alpha": 1.0,
        "learning_rate": 0.01,
    },
    "lmf": {
        "factors": 32,
        "iterations": 20,
        "regularization": 0.6,
        "alpha": 1.0,
        "learning_rate": 1.0,
    },
}


def compare_models(
    model_types: list[str],
    matrix_path: str = "data/processed/interaction_matrix.csv",
    feature_path: str = "data/processed/item_features.csv",
    test_events_path: str = "data/processed/test_events.csv",
    output_path: str = "data/processed/model_comparison.json",
    k: int = 5,
    max_users: int = 5000,
) -> list[dict]:
    results = []
    model_dir = Path("models/experiments")
    model_dir.mkdir(parents=True, exist_ok=True)

    for model_type in model_types:
        config = MODEL_CONFIGS[model_type]
        model_path = model_dir / f"{model_type}_model.joblib"
        print(f"Training {model_type} with {config}")
        train(
            matrix_path=matrix_path,
            feature_path=feature_path,
            model_path=str(model_path),
            model_type=model_type,
            **config,
        )
        metrics = evaluate(
            model_path=str(model_path),
            test_events_path=test_events_path,
            metrics_path=f"data/processed/kaggle_evaluation_metrics_{model_type}.json",
            k=k,
            max_users=max_users,
            mode="hybrid",
        )
        Path(f"data/processed/kaggle_evaluation_metrics_{model_type}.json").unlink(missing_ok=True)
        results.append({"model_type": model_type, **metrics})

    Path(output_path).write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="als,bpr,lmf")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--max-users", type=int, default=5000)
    parser.add_argument("--matrix-path", default="data/processed/interaction_matrix.csv")
    parser.add_argument("--feature-path", default="data/processed/item_features.csv")
    parser.add_argument("--test-events-path", default="data/processed/test_events.csv")
    parser.add_argument("--output-path", default="data/processed/model_comparison.json")
    args = parser.parse_args()
    compare_models(
        model_types=[model.strip() for model in args.models.split(",") if model.strip()],
        matrix_path=args.matrix_path,
        feature_path=args.feature_path,
        test_events_path=args.test_events_path,
        output_path=args.output_path,
        k=args.k,
        max_users=args.max_users,
    )
