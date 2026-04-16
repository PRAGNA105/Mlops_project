from pathlib import Path
import argparse

import pandas as pd

CSV_DTYPES = {
    "timestamp": "int64",
    "visitorid": "int64",
    "event": "string",
    "itemid": "int64",
    "transactionid": "float64",
}


def split_events_by_user_time(
    input_path: str = "data/raw/events.csv",
    train_output_path: str = "data/processed/train_events.csv",
    test_output_path: str = "data/processed/test_events.csv",
    min_unique_items: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    print(f"Reading data from {input_path}...")
    df = pd.read_csv(input_path, dtype=CSV_DTYPES)
    df = df.sort_values(["visitorid", "timestamp", "itemid"]).reset_index(drop=True)

    print("Identifying holdout items (vectorized)...")

    unique_counts = df.groupby("visitorid")["itemid"].nunique()

    last_ts_per_item = df.groupby(["visitorid", "itemid"])["timestamp"].max().reset_index()
    last_ts_sorted = last_ts_per_item.sort_values(["visitorid", "timestamp", "itemid"])
    holdout_items = last_ts_sorted.groupby("visitorid").tail(1).set_index("visitorid")["itemid"]

    eligible_visitor_ids = unique_counts[unique_counts >= min_unique_items].index

    visitor_to_holdout = pd.Series(index=unique_counts.index, dtype="float64")
    visitor_to_holdout.loc[eligible_visitor_ids] = holdout_items.loc[eligible_visitor_ids]

    is_test = df["visitorid"].map(visitor_to_holdout).eq(df["itemid"])
    train_df = df.loc[~is_test].copy()
    test_df = df.loc[is_test].copy()

    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Saving train data to {train_output_path}...")
    train_df.to_csv(train_output_path, index=False)
    print(f"Saving test data to {test_output_path}...")
    test_df.to_csv(test_output_path, index=False)

    print(f"Train events shape: {train_df.shape}")
    print(f"Test events shape: {test_df.shape}")
    return train_df, test_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", default="data/raw/events.csv")
    parser.add_argument("--train-output-path", default="data/processed/train_events.csv")
    parser.add_argument("--test-output-path", default="data/processed/test_events.csv")
    parser.add_argument("--min-unique-items", type=int, default=2)
    args = parser.parse_args()
    split_events_by_user_time(
        input_path=args.input_path,
        train_output_path=args.train_output_path,
        test_output_path=args.test_output_path,
        min_unique_items=args.min_unique_items,
    )
