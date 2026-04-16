from pathlib import Path
import tempfile

import mlflow
import pandas as pd


EXPERIMENT_NAME = "ecommerce-recsys"
TRACKING_DB = Path(tempfile.gettempdir()) / "ecommerce-recsys-mlflow" / "mlflow.db"
TRACKING_URI = f"sqlite:///{TRACKING_DB.as_posix()}"
ARTIFACT_ROOT = Path("mlruns").resolve()


def configure_mlflow() -> None:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    TRACKING_DB.parent.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(TRACKING_URI)
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        mlflow.create_experiment(EXPERIMENT_NAME, artifact_location=ARTIFACT_ROOT.as_uri())
    mlflow.set_experiment(EXPERIMENT_NAME)


def log_common_tags(stage: str, dataset_name: str = "kaggle_ecommerce_events") -> None:
    mlflow.set_tags(
        {
            "project": "ecommerce-recsys",
            "mlops_stage": stage,
            "dataset": dataset_name,
            "data_versioning": "DVC",
            "serving": "FastAPI",
            "streaming": "Kafka",
            "tracking_backend": TRACKING_URI,
        }
    )


def log_table_profile(frame: pd.DataFrame, prefix: str) -> None:
    mlflow.log_metric(f"{prefix}_rows", int(len(frame)))
    mlflow.log_metric(f"{prefix}_columns", int(len(frame.columns)))


def log_event_profile(events: pd.DataFrame, prefix: str) -> None:
    log_table_profile(events, prefix)
    if "visitorid" in events:
        mlflow.log_metric(f"{prefix}_users", int(events["visitorid"].nunique()))
    if "itemid" in events:
        mlflow.log_metric(f"{prefix}_items", int(events["itemid"].nunique()))
    if "event" in events:
        for event_name, count in events["event"].value_counts().items():
            mlflow.log_metric(f"{prefix}_event_{event_name}", int(count))
