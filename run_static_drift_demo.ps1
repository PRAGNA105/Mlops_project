$scenarios = @(
  "data/production/static_prod_low_drift.csv",
  "data/production/static_prod_moderate_drift.csv",
  "data/production/static_prod_high_drift.csv",
  "data/production/static_prod_moderate_drift.csv",
  "data/production/static_prod_low_drift.csv"
)

foreach ($scenario in $scenarios) {
  Write-Host "Running drift check for $scenario"
  venv\Scripts\python.exe -B -c "from src.monitoring.drift_check import update_data_drift_from_production; print(update_data_drift_from_production(production_path='$scenario'))"
  Write-Host "Waiting 35 seconds for Prometheus scrape..."
  Start-Sleep -Seconds 35
}
