from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import MAX_COLUMNS, MAX_ROWS


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    semantic_type: str
    missing_count: int
    missing_rate: float
    unique_count: int
    sample_values: list[Any]
    stats: dict[str, Any]


@dataclass
class DatasetProfile:
    row_count: int
    column_count: int
    columns: list[ColumnProfile]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_dataframe(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(path)
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="gbk")
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file type: {suffix}")


class ProfilingService:
    def profile_file(self, path: Path) -> DatasetProfile:
        df = read_dataframe(path)
        return self.profile_dataframe(df)

    def profile_dataframe(self, df: pd.DataFrame) -> DatasetProfile:
        if len(df) > MAX_ROWS:
            raise ValueError(f"Dataset exceeds max row limit: {MAX_ROWS}")
        if len(df.columns) > MAX_COLUMNS:
            raise ValueError(f"Dataset exceeds max column limit: {MAX_COLUMNS}")

        columns: list[ColumnProfile] = []
        for name in df.columns:
            series = df[name]
            missing_count = int(series.isna().sum())
            non_null = series.dropna()
            stats: dict[str, Any] = {}
            if pd.api.types.is_numeric_dtype(series):
                desc = series.describe()
                stats = {
                    key: _safe_scalar(desc.get(key))
                    for key in ("mean", "std", "min", "25%", "50%", "75%", "max")
                    if key in desc
                }
            elif pd.api.types.is_datetime64_any_dtype(series) or _looks_datetime(non_null):
                parsed = pd.to_datetime(non_null, errors="coerce").dropna()
                if not parsed.empty:
                    stats = {"min": parsed.min().isoformat(), "max": parsed.max().isoformat()}
            else:
                top = non_null.astype(str).value_counts().head(5)
                stats = {"top_values": top.to_dict()}

            columns.append(
                ColumnProfile(
                    name=str(name),
                    dtype=str(series.dtype),
                    semantic_type=_semantic_type(str(name), series),
                    missing_count=missing_count,
                    missing_rate=missing_count / len(df) if len(df) else 0.0,
                    unique_count=int(non_null.nunique(dropna=True)),
                    sample_values=[_safe_scalar(v) for v in non_null.head(5).tolist()],
                    stats=stats,
                )
            )
        return DatasetProfile(row_count=len(df), column_count=len(df.columns), columns=columns)


def _safe_scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _looks_datetime(series: pd.Series) -> bool:
    if series.empty:
        return False
    parsed = pd.to_datetime(series.head(20), errors="coerce")
    return parsed.notna().mean() > 0.8


def _semantic_type(name: str, series: pd.Series) -> str:
    lowered = name.lower()
    if any(token in lowered for token in ["date", "time", "日期", "时间"]):
        return "temporal"
    if pd.api.types.is_numeric_dtype(series):
        return "measure"
    if series.nunique(dropna=True) <= 30:
        return "category"
    return "text"
