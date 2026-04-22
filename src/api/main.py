import json
import time
from csv import DictWriter
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

from src.kafka.consumer import EVENT_WEIGHTS, apply_event, live_store, start_consumer_thread
from src.kafka.producer import publish_event
from src.model.predict import recommend, trending_items
from src.monitoring.drift_check import update_data_drift_from_production
from src.monitoring.monitoring_metrics import read_monitoring_metrics


REQ_COUNT = Counter("rec_requests_total", "Total recommendation requests")
LATENCY = Histogram("rec_latency_seconds", "Recommendation latency")
UNIQUE_USERS = Gauge("rec_unique_users", "Active users in live store")
DATA_DRIFT_DETECTED = Gauge("data_drift_detected", "Whether data drift was detected by the latest Evidently check")
DATA_DRIFT_SCORE = Gauge("data_drift_score", "Average data drift score from the latest data drift check")
DRIFTED_FEATURES_COUNT = Gauge("drifted_features_count", "Number of drifted features from the latest data drift check")
MODEL_DRIFT_DETECTED = Gauge("model_drift_detected", "Whether model drift was detected by the latest model drift check")
MODEL_DRIFT_SCORE = Gauge("model_drift_score", "Relative Precision@5 drop below the model drift threshold")
PRECISION_AT_5 = Gauge("precision_at_5", "Latest offline model Precision@5 used for model drift monitoring")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        start_consumer_thread()
    except Exception:
        # Allow the API to start even if Kafka is not available yet.
        pass
    yield


app = FastAPI(title="Ecommerce Recsys API", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())
BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models"
PRODUCTION_EVENTS_PATH = BASE_DIR / "data" / "production" / "live_production.csv"


@app.middleware("http")
async def refresh_metrics_before_request(request, call_next):
    refresh_prometheus_monitoring_metrics()
    return await call_next(request)


class EventInput(BaseModel):
    user_id: str
    item_id: str
    event: str


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def append_production_event(event_payload: dict) -> dict:
    PRODUCTION_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": int(time.time() * 1000),
        "visitorid": event_payload["user_id"],
        "event": event_payload["event"],
        "itemid": event_payload["item_id"],
        "transactionid": "",
    }
    file_exists = PRODUCTION_EVENTS_PATH.exists() and PRODUCTION_EVENTS_PATH.stat().st_size > 0
    with PRODUCTION_EVENTS_PATH.open("a", newline="", encoding="utf-8") as output:
        writer = DictWriter(output, fieldnames=["timestamp", "visitorid", "event", "itemid", "transactionid"])
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    return row


def refresh_prometheus_monitoring_metrics() -> dict:
    metrics = read_monitoring_metrics()
    DATA_DRIFT_DETECTED.set(metrics["data_drift_detected"])
    DATA_DRIFT_SCORE.set(metrics["data_drift_score"])
    DRIFTED_FEATURES_COUNT.set(metrics["drifted_features_count"])
    MODEL_DRIFT_DETECTED.set(metrics["model_drift_detected"])
    MODEL_DRIFT_SCORE.set(metrics["model_drift_score"])
    PRECISION_AT_5.set(metrics["precision_at_5"])
    return metrics


@app.get("/health")
def health() -> dict:
    refresh_prometheus_monitoring_metrics()
    return {"status": "ok", "live_users": len(live_store)}


@app.get("/", response_class=HTMLResponse)
def dashboard_home() -> HTMLResponse:
    return dashboard()


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    html_path = Path(__file__).with_name("dashboard.html")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/results")
def project_results() -> dict:
    monitoring_metrics = refresh_prometheus_monitoring_metrics()
    evaluation = _read_json(PROCESSED_DIR / "kaggle_evaluation_metrics.json", {})
    comparison = _read_json(PROCESSED_DIR / "kaggle_model_comparison.json", [])
    return {
        "project": "Ecommerce Recommendation MLOps",
        "dataset": {
            "name": "Kaggle ecommerce events history in electronics store",
            "raw_path": "data/raw/kaggle_events.csv",
            "train_path": "data/processed/kaggle_train_events.csv",
            "test_path": "data/processed/kaggle_test_events.csv",
            "schema": ["timestamp", "visitorid", "event", "itemid", "transactionid"],
        },
        "pipeline": [
            {"stage": "split_data", "output": "kaggle_train_events.csv + kaggle_test_events.csv"},
            {"stage": "build_features", "output": "kaggle_interaction_matrix.csv + kaggle_item_features.csv"},
            {"stage": "train_model", "output": "models/als_model.joblib"},
            {"stage": "evaluate_model", "output": "kaggle_evaluation_metrics.json"},
            {"stage": "compare_models", "output": "kaggle_model_comparison.json"},
        ],
        "evaluation": evaluation,
        "model_comparison": comparison,
        "serving": {
            "api": "FastAPI",
            "event_stream": "Kafka topic user-events",
            "live_users": len(live_store),
            "model_exists": (MODEL_DIR / "als_model.joblib").exists(),
        },
        "monitoring": monitoring_metrics,
    }


@app.post("/event")
def manual_event(event: EventInput) -> dict:
    event_payload = event.model_dump()
    production_row = append_production_event(event_payload)
    try:
        drift_metrics = update_data_drift_from_production()
    except Exception as exc:
        drift_metrics = {"status": "drift_update_failed", "reason": str(exc)}
    try:
        sent = publish_event(event_payload)
        return {
            "status": "sent_to_kafka",
            "weight": EVENT_WEIGHTS.get(event.event, 1),
            "kafka": sent,
            "production_event": production_row,
            "drift": drift_metrics,
        }
    except Exception as exc:
        # Keep the API useful during local development when Kafka is not running.
        stored = apply_event(event_payload)
        return {
            "status": "stored_locally",
            "reason": str(exc),
            "weight": EVENT_WEIGHTS.get(event.event, 1),
            "stored": stored,
            "production_event": production_row,
            "drift": drift_metrics,
        }


@app.get("/recommend/{user_id}")
def get_recommendations(user_id: str, top_n: int = 5) -> dict:
    REQ_COUNT.inc()
    start_time = time.time()
    recommendations = recommend(user_id=user_id, top_n=top_n)
    LATENCY.observe(time.time() - start_time)
    UNIQUE_USERS.set(len(live_store))
    return {"user_id": user_id, "recommended_items": recommendations}


@app.get("/trending")
def get_trending(top_n: int = 10) -> dict:
    return {"trending_items": trending_items(top_n=top_n)}
