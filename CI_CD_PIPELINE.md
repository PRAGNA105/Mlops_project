# CI/CD Pipeline Commands

This project uses GitHub Actions for CI/CD. The workflow file is:

```text
.github/workflows/ci.yml
```

## What The Pipeline Does

The pipeline has four jobs:

1. `python-checks`
   - installs Python dependencies
   - compiles all files in `src`
   - runs `pytest` only if a `tests/` folder exists

2. `dvc-pipeline`
   - restores `data/raw/kaggle_events.csv` from DVC remote if configured
   - otherwise downloads the Kaggle dataset if Kaggle secrets exist
   - runs `dvc repro evaluate_model`
   - uploads `data/processed/kaggle_evaluation_metrics.json` as a workflow artifact

3. `docker-build`
   - builds the FastAPI Docker image from `docker/Dockerfile`

4. `publish-image`
   - runs only on push to `main` or `master`
   - publishes the Docker image to GitHub Container Registry

## Required GitHub Secrets

For the DVC stage, use one of these options.

### Option A: Use Kaggle Secrets

Add these repository secrets in GitHub:

```text
KAGGLE_USERNAME
KAGGLE_KEY
```

The workflow will download the Kaggle dataset automatically by running:

```bash
python -B src/ingestion/import_kaggle_dataset.py --output-csv data/raw/kaggle_events.csv --min-events-per-user 2
```

### Option B: Use DVC Remote

Configure a DVC remote locally, push your data, and let CI run:

```bash
dvc pull data/raw/kaggle_events.csv.dvc
```

Example local commands for a local/shared remote:

```powershell
venv\Scripts\dvc.exe remote add -d storage C:\path\to\dvc-remote
venv\Scripts\dvc.exe push
git add .dvc/config data/raw/kaggle_events.csv.dvc dvc.yaml dvc.lock
git commit -m "Configure DVC remote and pipeline"
git push
```

For cloud remotes like S3, GCS, Azure, or Google Drive, add the provider credentials as GitHub secrets and configure the remote in `.dvc/config`.

## Local Commands Before Pushing

Run these locally before pushing to GitHub:

```powershell
venv\Scripts\python.exe -B -m compileall src
venv\Scripts\dvc.exe status
venv\Scripts\dvc.exe repro evaluate_model
docker build -f docker/Dockerfile -t ecommerce-recsys-api:local .
```

Because `dvc.yaml` uses the portable command `python`, make sure your virtual environment is active before local DVC repro:

```powershell
.\venv\Scripts\Activate.ps1
dvc repro evaluate_model
```

Alternative without activation:

```powershell
$env:Path = "$PWD\venv\Scripts;$env:Path"
venv\Scripts\dvc.exe repro evaluate_model
```

## GitHub Actions Workflow Code

The workflow is already created at:

```text
.github/workflows/ci.yml
```

It runs automatically on:

```text
push to main/master
pull_request
manual workflow_dispatch
```

## Docker Image Output

On push to `main` or `master`, the image is pushed to GHCR:

```text
ghcr.io/<your-github-username-or-org>/ecommerce-recsys-api:latest
ghcr.io/<your-github-username-or-org>/ecommerce-recsys-api:<commit-sha>
```

Pull command:

```bash
docker pull ghcr.io/<your-github-username-or-org>/ecommerce-recsys-api:latest
```

Run command:

```bash
docker run -p 8000:8000 ghcr.io/<your-github-username-or-org>/ecommerce-recsys-api:latest
```

## Manual Deployment Command

On a server, deploy the latest image:

```bash
docker pull ghcr.io/<your-github-username-or-org>/ecommerce-recsys-api:latest
docker stop ecommerce-recsys-api || true
docker rm ecommerce-recsys-api || true
docker run -d --name ecommerce-recsys-api -p 8000:8000 ghcr.io/<your-github-username-or-org>/ecommerce-recsys-api:latest
```

## Important Note

The repository does not store the full raw CSV in Git. CI must get the data through either:

1. DVC remote, or
2. Kaggle secrets.

Without one of those, the `dvc-pipeline` job will fail with a clear message saying `data/raw/kaggle_events.csv is missing`.
