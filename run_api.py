"""Launch the FastAPI app via uvicorn.

INHERITED from ai-sql-query-observability-service/run_api.py. CHANGED: default
API_APP_PATH points at this service's app (src.api.main:app).
"""

import os

import uvicorn


def main() -> None:
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "true").lower() == "true"
    workers = int(os.getenv("API_WORKERS", "1"))
    log_level = os.getenv("API_LOG_LEVEL", "info")
    app_path = os.getenv("API_APP_PATH", "src.api.main:app")

    uvicorn.run(app_path, host=host, port=port, reload=reload, workers=workers, log_level=log_level)


if __name__ == "__main__":
    main()
