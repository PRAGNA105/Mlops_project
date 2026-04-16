from pathlib import Path
import argparse

import numpy as np
import pandas as pd

EVENT_WEIGHTS = {
    "view": 1,
    "addtocart": 3,
    "transaction": 5,
}

CSV_DTYPES = {
    "timestamp": "int64",
    "visitorid": "int64",
    "event": "string",
    "itemid": "int64",
    "transactionid": "float64",
}


def min_max_scale(series: pd.Series) -> pd.Series:
    if series.empty:
        return series

    min_value = series.min()
    max_value = series.max()
    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        return pd.Series(np.zeros(len(series)), index=series.index, dtype=float)
    return (series - min_value) / (max_value - min_value)


def build_interaction_matrix(
    path: str = "data/processed/train_events.csv",
    matrix_output_path: str = "data/processed/interaction_matrix.csv",
    item_features_output_path: str = "data/processed/item_features.csv",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(path, dtype=CSV_DTYPES, usecols=["timestamp", "visitorid", "event", "itemid"])
    df["weight"] = df["event"].map(EVENT_WEIGHTS).fillna(0).astype("float32")

    print("Pre-calculating event type indicators (vectorized)...")
    df["is_view"] = df["event"].eq("view").astype("int8")
    df["is_addtocart"] = df["event"].eq("addtocart").astype("int8")
    df["is_transaction"] = df["event"].eq("transaction").astype("int8")

    print("Building interaction matrix (vectorized)...")
    interaction_matrix = (
        df.groupby(["visitorid", "itemid"], as_index=False)
        .agg(
            interaction_score=("weight", "sum"),
            view_count=("is_view", "sum"),
            addtocart_count=("is_addtocart", "sum"),
            transaction_count=("is_transaction", "sum"),
            last_event_ts=("timestamp", "max"),
        )
        .rename(columns={"visitorid": "user_id", "itemid": "item_id"})
    )

    print("Building item features (vectorized)...")
    item_stats = (
        df.groupby("itemid", as_index=False)
        .agg(
            total_events=("event", "size"),
            total_weight=("weight", "sum"),
            unique_users=("visitorid", "nunique"),
            views=("is_view", "sum"),
            addtocarts=("is_addtocart", "sum"),
            transactions=("is_transaction", "sum"),
            last_event_ts=("timestamp", "max"),
        )
        .rename(columns={"itemid": "item_id"})
    )

    event_mix = item_stats[["views", "addtocarts", "transactions"]].sum(axis=1).replace(0, 1)
    item_stats["view_rate"] = item_stats["views"] / event_mix
    item_stats["addtocart_rate"] = item_stats["addtocarts"] / event_mix
    item_stats["transaction_rate"] = item_stats["transactions"] / event_mix

    latest_ts = df["timestamp"].max()
    recent_cutoff_ts = latest_ts - int(pd.Timedelta(days=30).total_seconds() * 1000)
    recent_events = df[df["timestamp"] >= recent_cutoff_ts]

    recent_counts = (
        recent_events.groupby("itemid")
        .size()
        .rename("recent_events")
        .reset_index()
        .rename(columns={"itemid": "item_id"})
    )

    item_features = item_stats.merge(recent_counts, how="left", on="item_id")
    item_features["recent_events"] = item_features["recent_events"].fillna(0)
    item_features["popularity_score"] = min_max_scale(item_features["total_weight"])
    item_features["trend_score"] = min_max_scale(item_features["recent_events"])

    interaction_matrix["interaction_score"] = interaction_matrix["interaction_score"].astype("float32")
    item_features["popularity_score"] = item_features["popularity_score"].astype("float32")
    item_features["trend_score"] = item_features["trend_score"].astype("float32")

    matrix_path = Path(matrix_output_path)
    item_features_path = Path(item_features_output_path)
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    item_features_path.parent.mkdir(parents=True, exist_ok=True)
    interaction_matrix.to_csv(matrix_path, index=False)
    item_features.to_csv(item_features_path, index=False)

    print(f"Interaction matrix shape: {interaction_matrix.shape}")
    print(f"Item feature table shape: {item_features.shape}")
    return interaction_matrix, item_features


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", default="data/processed/train_events.csv")
    parser.add_argument("--matrix-output-path", default="data/processed/interaction_matrix.csv")
    parser.add_argument("--item-features-output-path", default="data/processed/item_features.csv")
    args = parser.parse_args()
    build_interaction_matrix(
        path=args.input_path,
        matrix_output_path=args.matrix_output_path,
        item_features_output_path=args.item_features_output_path,
    )
