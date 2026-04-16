import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import mlflow
from implicit.als import AlternatingLeastSquares
from implicit.bpr import BayesianPersonalizedRanking
from implicit.lmf import LogisticMatrixFactorization
from numpy.linalg import norm
from scipy.sparse import csr_matrix

try:
    from src.model.mlflow_utils import configure_mlflow, log_common_tags, log_table_profile
except ModuleNotFoundError:
    from mlflow_utils import configure_mlflow, log_common_tags, log_table_profile


RAW_SCORE_WEIGHTS = {
    "affinity": 0.35,
    "category": 0.30,
    "popularity": 0.20,
    "trend": 0.15,
    "item_similarity": 0.25,
}


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {key: value / total for key, value in weights.items()}


def normalize_array(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    min_value = values.min()
    max_value = values.max()
    if min_value == max_value:
        return np.zeros_like(values, dtype=float)
    return (values - min_value) / (max_value - min_value)


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    denom = norm(vec_a) * norm(vec_b)
    if denom == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / denom)


def build_model(
    model_type: str,
    factors: int,
    iterations: int,
    regularization: float,
    alpha: float,
    learning_rate: float,
):
    if model_type == "als":
        return AlternatingLeastSquares(
            factors=factors,
            iterations=iterations,
            regularization=regularization,
            alpha=alpha,
            random_state=42,
        )
    if model_type == "bpr":
        return BayesianPersonalizedRanking(
            factors=factors,
            iterations=iterations,
            regularization=regularization,
            learning_rate=learning_rate,
            random_state=42,
        )
    if model_type == "lmf":
        return LogisticMatrixFactorization(
            factors=factors,
            iterations=iterations,
            regularization=regularization,
            learning_rate=learning_rate,
            random_state=42,
        )
    raise ValueError(f"Unknown model type: {model_type}")


def train(
    matrix_path: str = "data/processed/interaction_matrix.csv",
    feature_path: str = "data/processed/item_features.csv",
    model_path: str = "models/als_model.joblib",
    factors: int = 32,
    iterations: int = 10,
    regularization: float = 0.05,
    alpha: float = 20.0,
    learning_rate: float = 0.01,
    model_type: str = "als",
) -> dict:
    configure_mlflow()
    interactions = pd.read_csv(matrix_path)
    item_features = pd.read_csv(feature_path)

    users = {user_id: idx for idx, user_id in enumerate(interactions["user_id"].unique())}
    items = {item_id: idx for idx, item_id in enumerate(interactions["item_id"].unique())}
    idx_to_item = {idx: item_id for item_id, idx in items.items()}

    interactions["u"] = interactions["user_id"].map(users)
    interactions["i"] = interactions["item_id"].map(items)

    sparse = csr_matrix(
        (interactions["interaction_score"], (interactions["u"], interactions["i"])),
        shape=(len(users), len(items)),
    )

    score_weights = normalize_weights(RAW_SCORE_WEIGHTS)

    with mlflow.start_run(run_name=f"{model_type}_hybrid_v1"):
        log_common_tags(stage="training")
        mlflow.set_tags(
            {
                "model_family": model_type,
                "matrix_path": matrix_path,
                "feature_path": feature_path,
                "model_path": model_path,
            }
        )
        mlflow.log_params(
            {
                "model_type": model_type,
                "factors": factors,
                "iterations": iterations,
                "regularization": regularization,
                "alpha": alpha,
                "learning_rate": learning_rate,
                **{f"weight_{key}": value for key, value in score_weights.items()},
            }
        )
        log_table_profile(interactions, "train_interactions")
        log_table_profile(item_features, "item_features")
        mlflow.log_metric("train_users", len(users))
        mlflow.log_metric("train_items", len(items))
        mlflow.log_metric("sparse_matrix_non_zero", int(sparse.nnz))
        mlflow.log_metric("sparse_matrix_density", float(sparse.nnz / (sparse.shape[0] * sparse.shape[1])))

        model = build_model(
            model_type=model_type,
            factors=factors,
            iterations=iterations,
            regularization=regularization,
            alpha=alpha,
            learning_rate=learning_rate,
        )
        model.fit(sparse)

        feature_columns = ["view_rate", "addtocart_rate", "transaction_rate"]
        feature_frame = item_features[item_features["item_id"].isin(items)].copy()
        feature_frame["item_idx"] = feature_frame["item_id"].map(items)
        feature_frame = feature_frame.sort_values("item_idx")

        item_feature_vectors = feature_frame[feature_columns].fillna(0).to_numpy(dtype=float)
        popularity_scores = feature_frame["popularity_score"].fillna(0).to_numpy(dtype=float)
        trend_scores = feature_frame["trend_score"].fillna(0).to_numpy(dtype=float)

        item_factors = np.asarray(model.item_factors, dtype=float)
        normalized_item_factors = item_factors / np.clip(norm(item_factors, axis=1, keepdims=True), 1e-12, None)

        user_history = (
            interactions.sort_values(["user_id", "last_event_ts"])
            .groupby("user_id")["item_id"]
            .agg(list)
            .to_dict()
        )

        artifact = {
            "model": model,
            "model_type": model_type,
            "users": users,
            "items": items,
            "idx_to_item": idx_to_item,
            "user_items": sparse.tocsr(),
            "item_feature_vectors": item_feature_vectors,
            "normalized_item_factors": normalized_item_factors,
            "popularity_scores": popularity_scores,
            "trend_scores": trend_scores,
            "user_history": user_history,
            "score_weights": score_weights,
        }

        output_path = Path(model_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(artifact, output_path)
        mlflow.log_artifact(str(output_path))
        print(f"Hybrid {model_type.upper()} model saved to {output_path}")

    return artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--factors", type=int, default=32)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--regularization", type=float, default=0.05)
    parser.add_argument("--alpha", type=float, default=20.0)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--model-type", choices=["als", "bpr", "lmf"], default="als")
    parser.add_argument("--matrix-path", default="data/processed/interaction_matrix.csv")
    parser.add_argument("--feature-path", default="data/processed/item_features.csv")
    parser.add_argument("--model-path", default="models/als_model.joblib")
    args = parser.parse_args()
    train(
        matrix_path=args.matrix_path,
        feature_path=args.feature_path,
        model_path=args.model_path,
        factors=args.factors,
        iterations=args.iterations,
        regularization=args.regularization,
        alpha=args.alpha,
        learning_rate=args.learning_rate,
        model_type=args.model_type,
    )
