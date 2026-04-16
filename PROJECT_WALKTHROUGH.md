# Ecommerce Recsys Project Walkthrough

This document explains what was built in this project from start to finish, what each important file does, how DVC is used, how the model is trained, how Kafka and FastAPI are wired, how drift monitoring works, and the commands used to run everything.

## 1. What Was Done From Start

The project was built in this order:

1. Initialized a local Git repository.
2. Initialized DVC for data versioning.
3. Added `data/raw/events.csv` to DVC tracking.
4. Created a standard MLOps project structure.
5. Added EDA, feature engineering, training, prediction, API, Kafka, Docker, CI, and monitoring files.
6. Defined a DVC pipeline for feature generation and training.
7. Trained a recommendation model and saved it as `models/als_model.joblib`.
8. Added a FastAPI service with recommendation, health, event, and trending endpoints.
9. Added Kafka producer and consumer support for live event simulation.
10. Added Prometheus metrics and drift-check scripts.
11. Fixed Docker and Kafka startup issues so the stack can run locally.

## 2. Project Structure

Important folders:

- `data/raw/`
  Contains the original RetailRocket event file `events.csv`.

- `data/processed/`
  Stores generated files such as `interaction_matrix.csv` and `item_features.csv`.

- `data/versioned/`
  Reserved for future versioned artifacts.

- `notebooks/`
  Contains the EDA notebook.

- `src/ingestion/`
  Loads raw event data from CSV.

- `src/features/`
  Builds features from raw event data.

- `src/model/`
  Trains the model and performs recommendation logic.

- `src/api/`
  FastAPI service for serving recommendations.

- `src/kafka/`
  Kafka producer and consumer code.

- `src/monitoring/`
  Data drift and model drift scripts.

- `models/`
  Stores the trained model file.

- `docker/`
  Dockerfile and Prometheus config.

- `.github/workflows/`
  GitHub Actions workflow. This only matters if the repo is pushed to GitHub.

## 3. Important Files And What They Do

### Root files

- `requirements.txt`
  Python dependencies for the full stack: model training, API, Kafka, Prometheus integration, DVC, and monitoring.

- `dvc.yaml`
  Defines the two DVC stages:
  - `build_features`
  - `train_model`

- `docker-compose.yml`
  Starts Zookeeper, Kafka, FastAPI API, and Prometheus together.

- `.gitignore`
  Prevents local environment and generated artifacts from being committed accidentally.

## 4. Data Versioning With DVC

### Raw data tracking

The raw dataset is tracked with DVC instead of Git directly.

Commands used:

```cmd
git init
dvc init
dvc add data\raw\events.csv
```

This created:

- `data/raw/events.csv.dvc`
  A pointer file telling DVC where the data artifact is.

- `data/raw/.gitignore`
  Prevents the raw CSV from being stored directly in Git.

### DVC pipeline

The DVC pipeline is:

```yaml
stages:
  build_features:
    cmd: python src/features/build_features.py
  train_model:
    cmd: python src/model/train.py
```

How to run it:

```cmd
dvc repro
```

What it does:

1. Reads `data/raw/events.csv`
2. Creates processed feature files
3. Trains the model
4. Saves `models/als_model.joblib`

## 5. EDA And Feature Engineering

### Notebook

- `notebooks/01_eda.ipynb`
  Used to inspect the raw dataset:
  - check column types
  - count events
  - convert timestamp to datetime
  - plot event distributions and daily activity

### Ingestion helper

- `src/ingestion/load_events.py`
  Reads the raw CSV and converts the Unix timestamp into a datetime column.

### Feature builder

- `src/features/build_features.py`
  This is the main feature engineering script.

It does the following:

1. Reads `data/raw/events.csv`
2. Maps event types to weights:
   - `view -> 1`
   - `addtocart -> 3`
   - `transaction -> 5`
3. Aggregates events into one row per user-item pair
4. Creates `interaction_score`
5. Builds item-level features such as:
   - total events
   - total weight
   - unique users
   - view/add-to-cart/transaction ratios
   - popularity score
   - trend score based on recent activity

Outputs:

- `data/processed/interaction_matrix.csv`
- `data/processed/item_features.csv`

Command:

```cmd
python src\features\build_features.py
```

## 6. Model Training

### Training file

- `src/model/train.py`

### Model used

The base model is:

- `implicit.als.AlternatingLeastSquares`

This is an implicit-feedback collaborative filtering model. It is appropriate because the data does not contain explicit ratings. Instead, it contains user behavior signals:

- views
- add-to-cart actions
- transactions

### Training logic

The script:

1. Reads `interaction_matrix.csv`
2. Builds user and item index mappings
3. Creates a sparse item-user interaction matrix
4. Trains ALS
5. Loads item feature data from `item_features.csv`
6. Stores extra artifacts for hybrid recommendation scoring

### Hybrid scoring

The project does not rely only on raw ALS scores. It also stores additional signals for ranking:

- `affinity`
- `category`
- `popularity`
- `trend`
- `item_similarity`

Raw weights used in training code:

```text
affinity = 0.35
category = 0.30
popularity = 0.20
trend = 0.15
item_similarity = 0.25
```

These are normalized before scoring.

### Training command

```cmd
python src\model\train.py
```

### Output

- `models/als_model.joblib`

This artifact stores:

- trained ALS model
- user mapping
- item mapping
- reverse item mapping
- user-item sparse matrix
- item feature vectors
- normalized item factors
- popularity scores
- trend scores
- user profiles
- user history
- score weights

## 7. Prediction Logic

- `src/model/predict.py`

This file:

1. Loads the saved model artifact
2. Recommends items for an existing user
3. Handles cold-start users using popularity and trend
4. Computes final ranking scores
5. Exposes a `trending_items()` helper

### Important note

For known users, the final ranking is a blended score, not just pure ALS output.

For new users:

- the system falls back to a popularity + trend strategy

## 8. FastAPI Service

- `src/api/main.py`

### What FastAPI does

FastAPI exposes the recommendation system as HTTP endpoints.

Endpoints:

- `GET /health`
  Returns API health and number of live users in memory.

- `POST /event`
  Accepts a manual event payload and updates the in-memory live store.

- `GET /recommend/{user_id}`
  Returns recommendations for the user.

- `GET /trending`
  Returns trending items for new or cold-start users.

- `GET /metrics`
  Prometheus metrics endpoint.

### Important clarification

`POST /event` does **not** send data to Kafka in the current implementation.

It directly updates the in-memory `live_store` by calling `apply_event()` from the Kafka consumer module.

So:

- manual API input -> direct memory update
- Kafka producer -> Kafka topic -> Kafka consumer -> memory update

### FastAPI run commands

Local:

```cmd
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Docker:

```cmd
docker compose up -d --build
```

## 9. Kafka Integration

### Producer

- `src/kafka/producer.py`

This script simulates live e-commerce traffic by replaying events from the CSV file into Kafka.

What it sends:

```json
{
  "user_id": "257597",
  "item_id": "355908",
  "event": "view",
  "timestamp": 1433221332117
}
```

It publishes these messages to the topic:

- `user-events`

### Producer command

On Windows host:

```cmd
set KAFKA_BOOTSTRAP=localhost:29092
venv\Scripts\python.exe src\kafka\producer.py
```

### Consumer

- `src/kafka/consumer.py`

This file:

1. Connects to topic `user-events`
2. Reads JSON messages
3. Maps event types to weights
4. Updates the in-memory dictionary:

```text
live_store = {
  user_id: {
    item_id: score
  }
}
```

### Event weights used by Kafka consumer

- `view = 1`
- `addtocart = 3`
- `transaction = 5`

### Kafka data flow

Normal Kafka path:

```text
events.csv -> producer.py -> Kafka topic user-events -> consumer.py -> live_store
```

Manual API path:

```text
POST /event -> apply_event() -> live_store
```

## 10. Docker Setup

### Docker files

- `docker/Dockerfile`
  Builds the API image.

- `docker-compose.yml`
  Orchestrates:
  - zookeeper
  - kafka
  - api
  - prometheus

### Important Docker fixes made

The local Docker stack needed a few fixes:

1. Added `libgomp1` to the Docker image because `implicit` needed it.
2. Changed Kafka listener config so internal and external listeners use different ports.
3. Added host mapping `29092:29092` so Windows host tools can connect to Kafka.

### Main Docker commands used

Build and run:

```cmd
docker compose up -d --build
```

Stop containers:

```cmd
docker compose stop
```

Stop and remove containers:

```cmd
docker compose down
```

Force recreation:

```cmd
docker compose up -d --force-recreate
```

See running services:

```cmd
docker compose ps
docker ps
```

See logs:

```cmd
docker compose logs --tail=100 api
docker compose logs --tail=100 kafka
docker compose logs --tail=100 zookeeper
docker compose logs --tail=100 prometheus
```

## 11. Monitoring With Prometheus

### Files

- `docker/prometheus.yml`
  Prometheus scrape config.

### What Prometheus scrapes

Prometheus scrapes the API at:

- `api:8000`

### Metrics exposed by the API

- `rec_requests_total`
- `rec_latency_seconds`
- `rec_unique_users`

### How to open Prometheus

Browser:

- `http://localhost:9090`

### Helpful Prometheus queries

Request count:

```promql
rec_requests_total
```

Request rate over 5 minutes:

```promql
rate(rec_requests_total[5m])
```

Latency histogram:

```promql
rec_latency_seconds_count
```

Active live users:

```promql
rec_unique_users
```

Direct metrics check from terminal:

```cmd
curl http://127.0.0.1:8000/metrics
```

## 12. Drift Monitoring

### Data drift

Files:

- `src/monitoring/drift_check.py`
- `src/monitoring/drift.py`

How it works:

1. Reads `data/raw/events.csv`
2. Converts event types into numeric codes:
   - view -> 1
   - addtocart -> 2
   - transaction -> 3
3. Splits the dataset into:
   - first half = reference
   - second half = current
4. Uses Evidently `DataDriftPreset`
5. Saves an HTML report

Command:

```cmd
python src\monitoring\drift_check.py
```

Generated report:

- `monitoring/drift_report.html`

### Model drift

File:

- `src/monitoring/model_drift.py`

How it works:

1. Loads `models/als_model.joblib`
2. Loads `data/processed/interaction_matrix.csv`
3. Samples a test subset
4. Computes `Precision@5`
5. Logs the metric to MLflow
6. Prints an alert if the metric drops below threshold

Command:

```cmd
python src\monitoring\model_drift.py
```

## 13. Manual API Examples

Examples for `POST /event`:

```json
{
  "user_id": "257597",
  "item_id": "355908",
  "event": "view"
}
```

```json
{
  "user_id": "257597",
  "item_id": "248676",
  "event": "addtocart"
}
```

```json
{
  "user_id": "111016",
  "item_id": "318965",
  "event": "transaction"
}
```

### What happens when you call `POST /event`

1. FastAPI receives the JSON body
2. It validates the payload using `EventInput`
3. It calls `apply_event()`
4. `apply_event()` updates `live_store`
5. The API returns the updated per-user store

Again, this does not publish to Kafka in the current code.

## 14. Main Commands Used During Development

### Setup

```cmd
git init
dvc init
dvc add data\raw\events.csv
```

### Environment

```cmd
py -3.10 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Feature generation and training

```cmd
python src\features\build_features.py
python src\model\train.py
dvc repro
```

### API

```cmd
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
```

### Docker

```cmd
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 api
docker compose logs --tail=100 kafka
docker compose stop
docker compose down
```

### Kafka producer

```cmd
set KAFKA_BOOTSTRAP=localhost:29092
venv\Scripts\python.exe src\kafka\producer.py
```

### Monitoring

```cmd
python src\monitoring\drift_check.py
python src\monitoring\model_drift.py
curl http://127.0.0.1:8000/metrics
```

## 15. What To Run For A Full Local Demo

### Step 1: Build features

```cmd
python src\features\build_features.py
```

### Step 2: Train model

```cmd
python src\model\train.py
```

### Step 3: Start Docker stack

```cmd
docker compose up -d --build
```

### Step 4: Check API

```cmd
curl http://127.0.0.1:8000/health
```

### Step 5: Open docs

- `http://127.0.0.1:8000/docs`

### Step 6: Send Kafka events

```cmd
set KAFKA_BOOTSTRAP=localhost:29092
venv\Scripts\python.exe src\kafka\producer.py
```

### Step 7: Query endpoints

- `GET /trending`
- `GET /recommend/{user_id}`
- `POST /event`

## 16. Current Known Behavior

- FastAPI is working and serves health, metrics, docs, trending, manual event, and recommendation endpoints.
- Kafka is configured to serve:
  - internal Docker traffic on `kafka:9092`
  - host traffic on `localhost:29092`
- Manual API events update memory directly.
- Kafka events follow the producer -> topic -> consumer -> memory path.
- Prometheus scrapes the API successfully.
- GitHub is optional. The project works locally without any GitHub remote.

## 17. Short Summary

This project is a local MLOps recommendation system built around:

- RetailRocket event data
- DVC for data pipeline reproducibility
- ALS for implicit-feedback recommendation
- hybrid reranking with popularity/trend/similarity signals
- FastAPI for serving
- Kafka for live event simulation
- Prometheus for metrics
- Evidently and Precision@K checks for drift monitoring

If you extend this later, the next most useful improvements would be:

1. make `POST /event` optionally publish to Kafka instead of only updating memory
2. persist `live_store` in Redis instead of process memory
3. add real tests for API and training
4. push to GitHub only if you want remote backup or CI/CD
