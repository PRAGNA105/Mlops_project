import argparse
import shutil
import subprocess
import zipfile
from pathlib import Path

import pandas as pd


DEFAULT_DATASET = "mkechinov/ecommerce-events-history-in-electronics-store"
EVENT_MAP = {
    "view": "view",
    "cart": "addtocart",
    "add_to_cart": "addtocart",
    "addtocart": "addtocart",
    "purchase": "transaction",
    "transaction": "transaction",
}


def download_dataset(dataset: str, download_dir: Path, force: bool = False) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)
    zip_path = download_dir / f"{dataset.split('/')[-1]}.zip"
    if zip_path.exists() and not force:
        return zip_path

    command = [
        "kaggle",
        "datasets",
        "download",
        "-d",
        dataset,
        "-p",
        str(download_dir),
        "--force",
    ]
    subprocess.run(command, check=True)

    downloaded_zips = sorted(download_dir.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not downloaded_zips:
        raise FileNotFoundError(f"No zip file was downloaded into {download_dir}")
    return downloaded_zips[0]


def extract_first_csv(zip_path: Path, extract_dir: Path) -> Path:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_members:
            raise FileNotFoundError(f"No CSV file found inside {zip_path}")
        member = csv_members[0]
        archive.extract(member, extract_dir)
    return extract_dir / member


def normalize_events(input_csv: Path, output_csv: Path, min_events_per_user: int = 2) -> pd.DataFrame:
    df = pd.read_csv(input_csv)
    required_columns = {"event_time", "event_type", "product_id", "user_id"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns in {input_csv}: {sorted(missing_columns)}")

    normalized = pd.DataFrame()
    normalized["timestamp"] = (
        pd.to_datetime(df["event_time"], utc=True, errors="coerce").astype("int64") // 1_000_000
    )
    normalized["visitorid"] = pd.to_numeric(df["user_id"], errors="coerce")
    normalized["event"] = df["event_type"].astype("string").str.lower().map(EVENT_MAP)
    normalized["itemid"] = pd.to_numeric(df["product_id"], errors="coerce")
    normalized["transactionid"] = pd.NA

    purchase_mask = normalized["event"].eq("transaction")
    normalized.loc[purchase_mask, "transactionid"] = normalized.index[purchase_mask]

    normalized = normalized.dropna(subset=["timestamp", "visitorid", "event", "itemid"])
    normalized["timestamp"] = normalized["timestamp"].astype("int64")
    normalized["visitorid"] = normalized["visitorid"].astype("int64")
    normalized["itemid"] = normalized["itemid"].astype("int64")

    if min_events_per_user > 1:
        user_counts = normalized["visitorid"].value_counts()
        keep_users = user_counts[user_counts >= min_events_per_user].index
        normalized = normalized[normalized["visitorid"].isin(keep_users)]

    normalized = normalized.sort_values(["visitorid", "timestamp", "itemid"]).reset_index(drop=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(output_csv, index=False)
    return normalized


def import_dataset(
    dataset: str = DEFAULT_DATASET,
    output_csv: str = "data/raw/events.csv",
    work_dir: str = "data/raw/kaggle",
    min_events_per_user: int = 2,
    force: bool = False,
) -> pd.DataFrame:
    work_path = Path(work_dir)
    if force and work_path.exists():
        shutil.rmtree(work_path)

    zip_path = download_dataset(dataset, work_path / "downloads", force=force)
    csv_path = extract_first_csv(zip_path, work_path / "extracted")
    normalized = normalize_events(csv_path, Path(output_csv), min_events_per_user=min_events_per_user)
    print(f"Imported {len(normalized):,} events from {dataset} into {output_csv}")
    print(f"Users: {normalized['visitorid'].nunique():,}")
    print(f"Items: {normalized['itemid'].nunique():,}")
    print(normalized["event"].value_counts().to_string())
    return normalized


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--output-csv", default="data/raw/events.csv")
    parser.add_argument("--work-dir", default="data/raw/kaggle")
    parser.add_argument("--min-events-per-user", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    import_dataset(
        dataset=args.dataset,
        output_csv=args.output_csv,
        work_dir=args.work_dir,
        min_events_per_user=args.min_events_per_user,
        force=args.force,
    )
