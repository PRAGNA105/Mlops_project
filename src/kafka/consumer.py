import json
import os
import threading

from kafka import KafkaConsumer


EVENT_WEIGHTS = {"view": 1, "addtocart": 3, "transaction": 5}
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "user-events")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "recsys-group")
API_VERSION = (2, 8, 0)
live_store: dict[str, dict[str, int]] = {}


def apply_event(event: dict) -> dict[str, int]:
    user_id = str(event["user_id"])
    item_id = str(event["item_id"])
    weight = EVENT_WEIGHTS.get(event["event"], 1)

    live_store.setdefault(user_id, {})
    live_store[user_id][item_id] = live_store[user_id].get(item_id, 0) + weight
    return live_store[user_id]


def consume_events() -> None:
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        api_version=API_VERSION,
        value_deserializer=lambda message: json.loads(message.decode("utf-8")),
        auto_offset_reset="latest",
        group_id=GROUP_ID,
    )
    for message in consumer:
        apply_event(message.value)


def start_consumer_thread() -> threading.Thread:
    thread = threading.Thread(target=consume_events, daemon=True, name="kafka-consumer")
    thread.start()
    return thread
