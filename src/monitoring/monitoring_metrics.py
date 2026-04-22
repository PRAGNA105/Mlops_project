import json
from pathlib import Path


METRICS_PATH = Path("monitoring/latest_metrics.json")
DEFAULT_METRICS = {
    "data_drift_detected": 0,
    "data_drift_score": 0.0,
    "drifted_features_count": 0,
    "model_drift_detected": 0,
    "model_drift_score": 0.0,
    "precision_at_5": 0.0,
}


def read_monitoring_metrics() -> dict:
    if not METRICS_PATH.exists():
        return DEFAULT_METRICS.copy()

    try:
        stored = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DEFAULT_METRICS.copy()

    metrics = DEFAULT_METRICS.copy()
    metrics.update({key: stored.get(key, value) for key, value in DEFAULT_METRICS.items()})
    return metrics


def update_monitoring_metrics(**updates) -> dict:
    metrics = read_monitoring_metrics()
    metrics.update({key: value for key, value in updates.items() if key in DEFAULT_METRICS})
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
