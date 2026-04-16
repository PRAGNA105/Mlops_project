# Ecommerce Recommendation System - Pipeline Documentation

This document explains what was changed in the project, what each important file does, how the DVC pipeline runs, which models were trained, how Kafka/FastAPI fit together, and how drift monitoring is generated.

## 1. What Was Done From The Start

The original project used a very sparse ecommerce event dataset. The event distribution showed that most users had almost no interaction history, which made recommendation metrics very poor. The previous evaluation result was approximately:

```json
{
  "precision_at_k": 0.00004,
  "recall_at_k": 0.0002
}
```

During debugging, two issues were found:

1. The original data was too sparse for strong user-level recommendation.
2. The `implicit` interaction matrix was built in the wrong orientation. The model was trained with item rows and user columns, but `implicit` recommendation expects user rows and item columns.

The fix involved:

- Importing a better ecommerce event dataset from Kaggle.
- Normalizing that dataset into the same schema used by this project.
- Fixing the ALS matrix orientation.
- Adding selectable model training for ALS, BPR, and Logistic Matrix Factorization.
- Updating evaluation to use the same hybrid scoring path used by prediction.
- Removing old heavy data files.
- Rebuilding DVC around the new Kaggle dataset.
- Updating FastAPI manual event ingestion to publish to Kafka when Kafka is available.
- Updating monitoring defaults to use the new Kaggle files.

## 2. Dataset Used

The new dataset is:

```text
mkechinov/ecommerce-events-history-in-electronics-store
```

Kaggle page:

```text
https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-electronics-store
```

The imported data was normalized into:

```text
data/raw/kaggle_events.csv
```

Final normalized columns:

```text
timestamp, visitorid, event, itemid, transactionid
```

Event type mapping:

```text
view     -> view
cart     -> addtocart
purchase -> transaction
```

The imported dataset summary was:

```text
Events: 618,746
Users: 140,900
Items: 40,583
```

Event counts:

```text
view           527,725
addtocart       54,035
transaction     36,986
```

## 3. Files Created Or Changed

### `src/ingestion/import_kaggle_dataset.py`

Downloads a Kaggle dataset, extracts the first CSV file, and converts it into this project's expected event schema.

Important functions:

- `download_dataset()` downloads the dataset using Kaggle CLI.
- `extract_first_csv()` extracts the CSV from the downloaded zip.
- `normalize_events()` converts Kaggle columns to project columns.
- `import_dataset()` runs the full import process.

Command used:

```powershell
venv\Scripts\python.exe -B src\ingestion\import_kaggle_dataset.py --output-csv data/raw/kaggle_events.csv --min-events-per-user 2
```

### `src/features/split_data.py`

Splits events into train and test using user-time holdout logic.

For every eligible user, the most recent interacted item is held out for testing. This means the model trains on earlier user behavior and is evaluated on whether it can recommend the user's later item.

Current DVC command:

```powershell
.\venv\Scripts\python.exe -B src/features/split_data.py --input-path data/raw/kaggle_events.csv --train-output-path data/processed/kaggle_train_events.csv --test-output-path data/processed/kaggle_test_events.csv --min-unique-items 2
```

Outputs:

```text
data/processed/kaggle_train_events.csv
data/processed/kaggle_test_events.csv
```

### `src/features/build_features.py`

Builds model-ready features from training events.

It creates:

- User-item interaction scores.
- Item-level statistics.
- Event-rate item features.
- Popularity score.
- Trend score.

Event weights:

```python
EVENT_WEIGHTS = {
    "view": 1,
    "addtocart": 3,
    "transaction": 5,
}
```

Outputs:

```text
data/processed/kaggle_interaction_matrix.csv
data/processed/kaggle_item_features.csv
```

Current DVC command:

```powershell
.\venv\Scripts\python.exe -B src/features/build_features.py --input-path data/processed/kaggle_train_events.csv --matrix-output-path data/processed/kaggle_interaction_matrix.csv --item-features-output-path data/processed/kaggle_item_features.csv
```

### `src/model/train.py`

Trains the recommendation model.

Models currently supported:

- `als`: Alternating Least Squares from `implicit`.
- `bpr`: Bayesian Personalized Ranking from `implicit`.
- `lmf`: Logistic Matrix Factorization from `implicit`.

The production model currently uses ALS because it performed best.

Important fix:

The sparse matrix is now created as:

```python
shape=(len(users), len(items))
```

with rows as users and columns as items. This is the correct orientation for `implicit`.

Current ALS training command:

```powershell
.\venv\Scripts\python.exe -B src/model/train.py --model-type als --factors 32 --iterations 10 --regularization 0.05 --alpha 20 --matrix-path data/processed/kaggle_interaction_matrix.csv --feature-path data/processed/kaggle_item_features.csv --model-path models/als_model.joblib
```

The trained model artifact contains:

- trained model object
- user id to index mapping
- item id to index mapping
- reverse item mapping
- user-item sparse matrix
- item feature vectors
- normalized item factors
- popularity scores
- trend scores
- user history
- hybrid score weights

Output:

```text
models/als_model.joblib
```

### `src/model/predict.py`

Loads the trained model and returns recommendations.

Important functions:

- `load_model()` loads `models/als_model.joblib`.
- `recommend()` gives personalized recommendations.
- `recommend_from_artifacts()` allows evaluation code to reuse the exact same recommendation logic.
- `trending_items()` returns popularity/trend-based recommendations.

The final recommendation score is hybrid. It combines:

- ALS affinity score
- item feature/category similarity
- item popularity
- item trend
- item similarity to user's history

### `src/model/evaluate.py`

Evaluates recommendations using precision, recall, and hit rate at `k`.

Important change:

Evaluation now uses `recommend_from_artifacts()`, so offline metrics match the same hybrid recommendation logic used by the API.

Current DVC evaluation command:

```powershell
.\venv\Scripts\python.exe -B src/model/evaluate.py --model-path models/als_model.joblib --test-events-path data/processed/kaggle_test_events.csv --metrics-path data/processed/kaggle_evaluation_metrics.json --k 5 --max-users 5000 --mode hybrid --candidate-multiplier 50
```

Output:

```text
data/processed/kaggle_evaluation_metrics.json
```

Current metrics:

```json
{
  "precision_at_k": 0.02868,
  "recall_at_k": 0.1434,
  "hit_rate_at_k": 0.1434,
  "k": 5,
  "mode": "hybrid",
  "candidate_multiplier": 50,
  "evaluated_users": 5000
}
```

### `src/model/compare_models.py`

Trains and compares ALS, BPR, and LMF on the same processed Kaggle data.

Current command:

```powershell
.\venv\Scripts\python.exe -B src/model/compare_models.py --models als,bpr,lmf --k 5 --max-users 5000 --matrix-path data/processed/kaggle_interaction_matrix.csv --feature-path data/processed/kaggle_item_features.csv --test-events-path data/processed/kaggle_test_events.csv --output-path data/processed/kaggle_model_comparison.json
```

Output:

```text
data/processed/kaggle_model_comparison.json
```

Latest comparison:

```text
ALS  precision@5=0.02868  recall@5=0.1434
BPR  precision@5=0.00096  recall@5=0.0048
LMF  precision@5=0.00364  recall@5=0.0182
```

ALS is currently the best model.

## 4. DVC Pipeline

DVC tracks the dataset and reproduces the ML pipeline.

Important DVC files:

```text
dvc.yaml
dvc.lock
data/raw/kaggle_events.csv.dvc
.dvc/config
```

### Why `.dvc/config` Was Updated

The project is inside OneDrive. DVC was failing with:

```text
unable to open database file
```

This was caused by DVC's site cache/database being created in a synced OneDrive location. The fix was to configure DVC to use a temp folder outside OneDrive:

```text
C:\Users\DELL\AppData\Local\Temp\dvc-site-cache-ecommerce-recsys
```

The config is stored in:

```text
.dvc/config
```

### DVC Stages

The pipeline stages in `dvc.yaml` are:

1. `split_data`
2. `build_features`
3. `train_model`
4. `evaluate_model`
5. `compare_models`

### Check DVC Status

```powershell
venv\Scripts\dvc.exe status
```

Expected output:

```text
Data and pipelines are up to date.
```

### Reproduce Main Training And Evaluation

```powershell
venv\Scripts\dvc.exe repro evaluate_model
```

This runs:

```text
kaggle_events.csv -> split -> features -> ALS training -> evaluation
```

### Reproduce Model Comparison

```powershell
venv\Scripts\dvc.exe repro compare_models
```

This compares:

```text
ALS, BPR, LMF
```

### DVC Commands Used During Setup

```powershell
venv\Scripts\dvc.exe add data\raw\kaggle_events.csv
venv\Scripts\dvc.exe repro evaluate_model
venv\Scripts\dvc.exe repro compare_models
venv\Scripts\dvc.exe status
venv\Scripts\dvc.exe config core.site_cache_dir C:\Users\DELL\AppData\Local\Temp\dvc-site-cache-ecommerce-recsys
```

## 5. Model Training Explanation

The model is trained on implicit feedback, not explicit ratings.

Events are converted into weighted interactions:

```text
view        = 1
addtocart   = 3
transaction = 5
```

The interaction table groups events by:

```text
user_id, item_id
```

and sums the interaction score.

ALS then factorizes the user-item matrix into:

```text
user factors
item factors
```

The project does not use pure ALS score only. It uses a hybrid reranking step that combines ALS with business/item signals.

Hybrid score weights:

```python
RAW_SCORE_WEIGHTS = {
    "affinity": 0.35,
    "category": 0.30,
    "popularity": 0.20,
    "trend": 0.15,
    "item_similarity": 0.25,
}
```

These weights are normalized before use.

## 6. Kafka Flow

Kafka is configured in:

```text
docker-compose.yml
```

Services:

- `zookeeper`
- `kafka`
- `api`
- `prometheus`

Kafka topic:

```text
user-events
```

Default Kafka bootstrap server for local Python:

```text
localhost:9092
```

Default Kafka bootstrap server inside Docker:

```text
kafka:9092
```

### `src/kafka/producer.py`

This file sends events to Kafka.

Important functions:

- `build_producer()` creates a Kafka producer.
- `publish_event()` sends one event to Kafka.
- `replay_events()` reads a CSV and streams rows into Kafka.

Replay command:

```powershell
venv\Scripts\python.exe -B src\kafka\producer.py
```

By default, it replays:

```text
data/raw/kaggle_events.csv
```

Each Kafka message looks like:

```json
{
  "user_id": "1515915625353230683",
  "item_id": "885572",
  "event": "view",
  "timestamp": 1570123456789
}
```

### `src/kafka/consumer.py`

This file consumes Kafka events and updates an in-memory live store.

Important functions:

- `apply_event()` updates a user's live item scores.
- `consume_events()` listens to Kafka topic `user-events`.
- `start_consumer_thread()` starts the consumer in the background.

The live store is:

```python
live_store: dict[str, dict[str, int]] = {}
```

Example after events:

```python
{
    "user_1": {
        "item_10": 1,
        "item_20": 3
    }
}
```

## 7. FastAPI Application

FastAPI code is in:

```text
src/api/main.py
```

Start locally:

```powershell
venv\Scripts\uvicorn.exe src.api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

### API Endpoints

#### `GET /health`

Checks whether the API is running.

Example:

```powershell
curl http://127.0.0.1:8000/health
```

#### `GET /recommend/{user_id}`

Returns personalized recommendations.

Example:

```powershell
curl "http://127.0.0.1:8000/recommend/1515915625353230683?top_n=5"
```

#### `GET /trending`

Returns popularity/trend-based recommendations.

Example:

```powershell
curl "http://127.0.0.1:8000/trending?top_n=10"
```

#### `POST /event`

This is the manual event API.

It now tries to publish the event to Kafka using `publish_event()`.

If Kafka is running:

```text
API -> Kafka topic user-events -> Kafka consumer -> live_store
```

If Kafka is not running:

```text
API -> local fallback -> live_store
```

Example:

```powershell
curl -X POST "http://127.0.0.1:8000/event" -H "Content-Type: application/json" -d "{\"user_id\":\"1515915625353230683\",\"item_id\":\"885572\",\"event\":\"addtocart\"}"
```

### Prometheus Metrics

Metrics are exposed at:

```text
http://127.0.0.1:8000/metrics
```

Metrics defined:

- `rec_requests_total`
- `rec_latency_seconds`
- `rec_unique_users`

Prometheus config is:

```text
docker/prometheus.yml
```

## 8. Docker Commands

Start Kafka, API, and Prometheus:

```powershell
docker compose up --build
```

API:

```text
http://localhost:8000
```

Prometheus:

```text
http://localhost:9090
```

Stop services:

```powershell
docker compose down
```

## 9. Data Drift Monitoring

There are two drift-related files:

```text
src/monitoring/drift_check.py
src/monitoring/model_drift.py
```

### `src/monitoring/drift_check.py`

This creates a data drift HTML report using Evidently.

Current default data:

```text
data/raw/kaggle_events.csv
```

How drift is created:

1. Load event data.
2. Convert timestamp into datetime.
3. Convert event names into numeric event codes.
4. Split data into two halves:
   - first half = reference data
   - second half = current data
5. Compare distributions using Evidently `DataDriftPreset`.
6. Save HTML report.

Command:

```powershell
venv\Scripts\python.exe -B src\monitoring\drift_check.py
```

Output:

```text
monitoring/drift_report.html
```

### `src/monitoring/drift.py`

Thin wrapper around `check_data_drift()`.

It returns:

```python
{"status": "ok", "message": "Drift report generated."}
```

### `src/monitoring/model_drift.py`

Checks model drift using recommendation quality.

Current default data:

```text
data/processed/kaggle_test_events.csv
```

It computes `precision@5` and logs the result to MLflow. If precision is below the threshold, it prints:

```text
ALERT: model drift detected - retraining needed!
```

Command:

```powershell
venv\Scripts\python.exe -B src\monitoring\model_drift.py
```

## 10. MLflow

Training and evaluation use MLflow.

MLflow tracking folder:

```text
mlruns/
```

Experiment name:

```text
ecommerce-recsys
```

Training logs:

- model type
- factors
- iterations
- regularization
- alpha
- hybrid weights
- model artifact

Evaluation logs:

- precision
- recall
- hit rate
- evaluated users

Start MLflow UI:

```powershell
venv\Scripts\mlflow.exe ui --backend-store-uri mlruns
```

Open:

```text
http://127.0.0.1:5000
```

## 11. Files Removed

The old RetailRocket data and stale outputs were removed:

```text
data/raw/events.csv
data/raw/events.csv.dvc
data/processed/train_events.csv
data/processed/test_events.csv
data/processed/interaction_matrix.csv
data/processed/item_features.csv
data/processed/evaluation_metrics.json
data/processed/model_comparison.json
models/als_model_old_retailrocket.joblib
```

The active dataset is now:

```text
data/raw/kaggle_events.csv
```

## 12. What To Run Now

### Check pipeline health

```powershell
venv\Scripts\dvc.exe status
```

### Rebuild train/evaluation pipeline

```powershell
venv\Scripts\dvc.exe repro evaluate_model
```

### Compare models

```powershell
venv\Scripts\dvc.exe repro compare_models
```

### Start API locally

```powershell
venv\Scripts\uvicorn.exe src.api.main:app --reload
```

### Test recommendation

```powershell
curl "http://127.0.0.1:8000/recommend/1515915625353230683?top_n=5"
```

### Start Kafka/API/Prometheus with Docker

```powershell
docker compose up --build
```

### Send manual event to API

```powershell
curl -X POST "http://127.0.0.1:8000/event" -H "Content-Type: application/json" -d "{\"user_id\":\"1515915625353230683\",\"item_id\":\"885572\",\"event\":\"addtocart\"}"
```

### Replay CSV events into Kafka

```powershell
venv\Scripts\python.exe -B src\kafka\producer.py
```

### Generate data drift report

```powershell
venv\Scripts\python.exe -B src\monitoring\drift_check.py
```

### Run model drift check

```powershell
venv\Scripts\python.exe -B src\monitoring\model_drift.py
```

## 13. Future Improvements

Recommended next improvements:

1. Add LightFM for hybrid recommendation using item metadata.
2. Add SVD++ using `scikit-surprise` as an experiment, but it may not beat ALS because this dataset is implicit feedback.
3. Add DVC remote storage and run `dvc push`.
4. Add `params.yaml` so ALS parameters can be tuned cleanly through DVC.
5. Store Kafka events in a durable database instead of only in-memory `live_store`.
6. Use live Kafka interactions to rerank recommendations in real time.
