import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

from src.kafka.consumer import EVENT_WEIGHTS, apply_event, live_store, start_consumer_thread
from src.kafka.producer import publish_event
from src.model.predict import recommend, trending_items


REQ_COUNT = Counter("rec_requests_total", "Total recommendation requests")
LATENCY = Histogram("rec_latency_seconds", "Recommendation latency")
UNIQUE_USERS = Gauge("rec_unique_users", "Active users in live store")


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


class EventInput(BaseModel):
    user_id: str
    item_id: str
    event: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "live_users": len(live_store)}


@app.post("/event")
def manual_event(event: EventInput) -> dict:
    event_payload = event.model_dump()
    try:
        sent = publish_event(event_payload)
        return {
            "status": "sent_to_kafka",
            "weight": EVENT_WEIGHTS.get(event.event, 1),
            "kafka": sent,
        }
    except Exception as exc:
        # Keep the API useful during local development when Kafka is not running.
        stored = apply_event(event_payload)
        return {
            "status": "stored_locally",
            "reason": str(exc),
            "weight": EVENT_WEIGHTS.get(event.event, 1),
            "stored": stored,
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
