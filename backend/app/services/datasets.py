from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from fastapi import UploadFile

from app.core.config import MAX_UPLOAD_BYTES, SAMPLE_DATA_DIR, UPLOAD_DIR
from app.services.profiling import ProfilingService, read_dataframe


class DatasetService:
    def __init__(self, upload_dir: Path = UPLOAD_DIR):
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.profiler = ProfilingService()

    async def save_upload(self, file: UploadFile) -> tuple[Path, dict]:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".csv", ".xlsx", ".xls"}:
            raise ValueError("Only .csv and .xlsx files are supported")
        target = self.upload_dir / f"{Path(file.filename or 'dataset').stem}_{_counter()}{suffix}"
        size = 0
        with target.open("wb") as fh:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise ValueError("Uploaded file is too large")
                fh.write(chunk)
        profile = self.profiler.profile_file(target).to_dict()
        return target, profile

    def seed_sample(self, sample_name: str) -> tuple[Path, dict]:
        source = SAMPLE_DATA_DIR / f"{sample_name}.csv"
        if not source.exists():
            raise FileNotFoundError(f"Sample dataset not found: {sample_name}")
        target = self.upload_dir / f"{sample_name}_{_counter()}.csv"
        shutil.copyfile(source, target)
        profile = self.profiler.profile_file(target).to_dict()
        return target, profile

    def preview(self, path: Path, limit: int = 20) -> dict:
        df = read_dataframe(path).head(limit)
        return {"columns": list(df.columns), "rows": df.where(pd.notna(df), None).to_dict("records")}


def _counter() -> int:
    import time

    return int(time.time() * 1000)
