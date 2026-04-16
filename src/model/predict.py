import joblib
import numpy as np


_artifacts = None


def load_model(path: str = "models/als_model.joblib") -> dict:
    global _artifacts
    _artifacts = joblib.load(path)
    return _artifacts


def _require_artifacts() -> dict:
    if _artifacts is None:
        return load_model()
    return _artifacts


def _normalize(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    min_value = values.min()
    max_value = values.max()
    if min_value == max_value:
        return np.zeros_like(values, dtype=float)
    return (values - min_value) / (max_value - min_value)


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    denom = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
    if denom == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / denom)


def _coerce_user_id(user_id: int | str):
    if isinstance(user_id, str):
        stripped = user_id.strip()
        if stripped.isdigit():
            return int(stripped)
        return stripped
    return user_id


def _user_profile_from_history(
    history: list,
    item_lookup: dict,
    item_feature_vectors: np.ndarray,
) -> np.ndarray | None:
    item_indexes = [item_lookup[item_id] for item_id in history if item_id in item_lookup]
    if not item_indexes:
        return None
    return item_feature_vectors[item_indexes].mean(axis=0)


def trending_items(top_n: int = 10) -> list[dict]:
    artifacts = _require_artifacts()
    idx_to_item = artifacts["idx_to_item"]
    popularity_scores = artifacts["popularity_scores"]
    trend_scores = artifacts["trend_scores"]
    final_scores = (0.6 * popularity_scores) + (0.4 * trend_scores)
    ranking = np.argsort(-final_scores)[:top_n]
    return [
        {
            "item_id": int(idx_to_item[int(item_idx)]),
            "score": round(float(final_scores[int(item_idx)]), 6),
        }
        for item_idx in ranking
    ]


def recommend_from_artifacts(
    artifacts: dict,
    user_id: int | str,
    top_n: int = 5,
    candidate_multiplier: int = 50,
) -> list[dict]:
    user_id = _coerce_user_id(user_id)
    users = artifacts["users"]
    items = artifacts["items"]
    idx_to_item = artifacts["idx_to_item"]
    user_items = artifacts["user_items"]
    score_weights = artifacts["score_weights"]
    popularity_scores = artifacts["popularity_scores"]
    trend_scores = artifacts["trend_scores"]
    item_feature_vectors = artifacts["item_feature_vectors"]
    normalized_item_factors = artifacts["normalized_item_factors"]
    user_profiles = artifacts.get("user_profiles", {})
    user_history = artifacts["user_history"]

    if user_id not in users:
        ranking = np.argsort(-(0.6 * popularity_scores + 0.4 * trend_scores))[:top_n]
        return [
            {
                "item_id": int(idx_to_item[item_idx]),
                "score": float((0.6 * popularity_scores[item_idx]) + (0.4 * trend_scores[item_idx])),
                "reason": "cold_start_popularity_trend",
            }
            for item_idx in ranking
        ]

    user_idx = users[user_id]
    history = user_history.get(user_id, [])
    seen_items = set(history)
    candidate_count = min(max(top_n * candidate_multiplier, 100), len(items))

    ids, affinity_scores = artifacts["model"].recommend(user_idx, user_items[user_idx], N=candidate_count)
    affinity_scores = _normalize(np.asarray(affinity_scores, dtype=float))

    history_indexes = [items[item_id] for item_id in history if item_id in items]
    user_profile = user_profiles.get(user_id)
    if user_profile is None:
        user_profile = _user_profile_from_history(history, items, item_feature_vectors)

    ranked = []
    for rank_idx, item_idx in enumerate(ids):
        item_id = idx_to_item[int(item_idx)]
        if item_id in seen_items:
            continue

        category_score = 0.0
        if user_profile is not None:
            category_score = _cosine_similarity(user_profile, item_feature_vectors[item_idx])

        similarity_score = 0.0
        if history_indexes:
            similarity_scores = normalized_item_factors[history_indexes] @ normalized_item_factors[item_idx]
            similarity_score = float(np.max(similarity_scores))

        final_score = (
            score_weights["affinity"] * float(affinity_scores[rank_idx])
            + score_weights["category"] * category_score
            + score_weights["popularity"] * float(popularity_scores[item_idx])
            + score_weights["trend"] * float(trend_scores[item_idx])
            + score_weights["item_similarity"] * similarity_score
        )

        ranked.append(
            {
                "item_id": int(item_id),
                "score": round(final_score, 6),
                "components": {
                    "affinity": round(float(affinity_scores[rank_idx]), 6),
                    "category": round(category_score, 6),
                    "popularity": round(float(popularity_scores[item_idx]), 6),
                    "trend": round(float(trend_scores[item_idx]), 6),
                    "item_similarity": round(similarity_score, 6),
                },
            }
        )

    ranked.sort(key=lambda record: record["score"], reverse=True)
    return ranked[:top_n]


def recommend(user_id: int | str, top_n: int = 5) -> list[dict]:
    return recommend_from_artifacts(_require_artifacts(), user_id=user_id, top_n=top_n)
