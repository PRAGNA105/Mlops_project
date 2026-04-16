from src.monitoring.drift_check import check_data_drift


def check_drift() -> dict:
    check_data_drift()
    return {"status": "ok", "message": "Drift report generated."}
