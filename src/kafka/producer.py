import json
import os
import time

import pandas as pd
from kafka import KafkaProducer


BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "user-events")
API_VERSION = (2, 8, 0)


def build_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        api_version=API_VERSION,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )


def publish_event(event: dict, producer: KafkaProducer | None = None) -> dict:
    owned_producer = producer is None
    producer = producer or build_producer()
    producer.send(TOPIC, value=event)
    producer.flush()
    if owned_producer:
        producer.close()
    return {"status": "sent", "topic": TOPIC, "event": event}


def replay_events(path: str = "data/raw/kaggle_events.csv", delay_seconds: float = 0.05) -> None:
    producer = build_producer()
    df = pd.read_csv(path)

    try:
        for _, row in df.iterrows():
            event = {
                "user_id": str(row["visitorid"]),
                "item_id": str(row["itemid"]),
                "event": row["event"],
                "timestamp": int(row["timestamp"]),
            }
            producer.send(TOPIC, value=event)
            print(f"Sent: {event['event']} user={event['user_id']} item={event['item_id']}")
            time.sleep(delay_seconds)
        producer.flush()
    finally:
        producer.close()


if __name__ == "__main__":
    replay_events()
