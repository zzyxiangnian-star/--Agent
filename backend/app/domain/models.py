from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Dataset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    original_filename: str
    file_type: str
    storage_path: str
    row_count: int
    column_count: int
    profile_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class AnalysisTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    dataset_id: int = Field(foreign_key="dataset.id")
    user_goal: str
    status: str = "draft"
    plan_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AnalysisStep(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="analysistask.id")
    step_order: int
    name: str
    description: str
    code: str = ""
    status: str = "draft"
    result_summary: str = ""
    created_at: datetime = Field(default_factory=utcnow)


class ExecutionResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    step_id: int = Field(foreign_key="analysisstep.id")
    stdout: str = ""
    stderr: str = ""
    result_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    artifact_paths: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class ChartArtifact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="analysistask.id")
    step_id: Optional[int] = Field(default=None, foreign_key="analysisstep.id")
    title: str
    chart_type: str
    image_path: str
    spec_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class Report(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="analysistask.id")
    title: str
    format: str
    content_path: str
    created_at: datetime = Field(default_factory=utcnow)


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    actor: str
    action: str
    target_type: str
    target_id: str
    detail_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class AppSetting(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=utcnow)
