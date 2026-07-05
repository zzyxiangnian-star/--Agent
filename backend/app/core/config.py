from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
ARTIFACT_DIR = BASE_DIR / "artifacts"
REPORT_DIR = BASE_DIR / "reports"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
DB_PATH = DATA_DIR / "app.db"

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 200


def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, UPLOAD_DIR, ARTIFACT_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)
