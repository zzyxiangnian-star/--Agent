from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.agent.runner import AgentRunner, MockLLMClient
from app.automation.templates import AutomationTemplateService
from app.core.config import ARTIFACT_DIR, REPORT_DIR, DATA_DIR
from app.core.db import get_session
from app.domain.models import AnalysisStep, AnalysisTask, AuditLog, ChartArtifact, Dataset, ExecutionResult, Report, utcnow
from app.domain.state import TaskStatus, transition_task
from app.services.datasets import DatasetService
from app.services.profiling import read_dataframe
from app.services.report import ReportService
from app.settings.service import SettingsService

router = APIRouter(prefix="/api")


class TaskCreate(BaseModel):
    dataset_id: int
    user_goal: str
    template_id: str | None = None


class SettingsPayload(BaseModel):
    llm_enabled: bool | None = None
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    request_timeout: int | None = None
    max_tokens: int | None = None
    default_mode: str | None = None


@router.post("/datasets/upload")
async def upload_dataset(file: UploadFile, session: Session = Depends(get_session)) -> dict:
    try:
        path, profile = await DatasetService().save_upload(file)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    dataset = Dataset(
        name=Path(file.filename or path.name).stem,
        original_filename=file.filename or path.name,
        file_type=path.suffix.lstrip("."),
        storage_path=str(path),
        row_count=profile["row_count"],
        column_count=profile["column_count"],
        profile_json=profile,
    )
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    _audit(session, "dataset.upload", "dataset", str(dataset.id), {"filename": dataset.original_filename})
    session.refresh(dataset)
    return dataset.model_dump()


@router.post("/datasets/seed/{sample_name}")
def seed_dataset(sample_name: str, session: Session = Depends(get_session)) -> dict:
    try:
        path, profile = DatasetService().seed_sample(sample_name)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    dataset = Dataset(
        name=sample_name,
        original_filename=f"{sample_name}.csv",
        file_type="csv",
        storage_path=str(path),
        row_count=profile["row_count"],
        column_count=profile["column_count"],
        profile_json=profile,
    )
    session.add(dataset)
    session.commit()
    session.refresh(dataset)
    _audit(session, "dataset.seed", "dataset", str(dataset.id), {"sample": sample_name})
    session.refresh(dataset)
    return dataset.model_dump()


@router.get("/datasets")
def list_datasets(session: Session = Depends(get_session)) -> list[dict]:
    return [item.model_dump() for item in session.exec(select(Dataset).order_by(Dataset.created_at.desc())).all()]


@router.get("/datasets/{dataset_id}")
def get_dataset_route(dataset_id: int, session: Session = Depends(get_session)) -> dict:
    return _dataset(dataset_id, session).model_dump()


def _dataset(dataset_id: int, session: Session) -> Dataset:
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/datasets/{dataset_id}/preview")
def preview_dataset(dataset_id: int, session: Session = Depends(get_session)) -> dict:
    dataset = _dataset(dataset_id, session)
    return DatasetService().preview(Path(dataset.storage_path))


@router.get("/datasets/{dataset_id}/profile")
def dataset_profile(dataset_id: int, session: Session = Depends(get_session)) -> dict:
    return _dataset(dataset_id, session).profile_json


@router.post("/tasks")
def create_task(payload: TaskCreate, session: Session = Depends(get_session)) -> dict:
    dataset = _dataset(payload.dataset_id, session)
    task = AnalysisTask(dataset_id=dataset.id, user_goal=payload.user_goal, status=TaskStatus.DRAFT.value)
    if payload.template_id:
        df = read_dataframe(Path(dataset.storage_path))
        task.plan_json = AutomationTemplateService().create_plan(payload.template_id, df, payload.user_goal)
        task.status = transition_task(TaskStatus.DRAFT, TaskStatus.PLANNED).value
    session.add(task)
    session.commit()
    session.refresh(task)
    _audit(session, "task.create", "task", str(task.id), {"goal": payload.user_goal})
    session.refresh(task)
    return task.model_dump()


@router.post("/tasks/{task_id}/plan")
def plan_task(task_id: int, session: Session = Depends(get_session)) -> dict:
    task = _task(task_id, session)
    dataset = _dataset(task.dataset_id, session)
    settings = SettingsService(DATA_DIR / "settings.json").get_llm_settings()
    if settings["active_mode"] == "AI-assisted":
        plan = AgentRunner(MockLLMClient()).create_plan(task.user_goal, dataset.profile_json)
    else:
        df = read_dataframe(Path(dataset.storage_path))
        template_id = _guess_template(task.user_goal)
        plan = AutomationTemplateService().create_plan(template_id, df, task.user_goal)
    task.plan_json = plan
    task.status = transition_task(TaskStatus(task.status), TaskStatus.PLANNED).value
    session.add(task)
    session.commit()
    session.refresh(task)
    _audit(session, "task.plan", "task", str(task.id), {"mode": plan.get("mode")})
    session.refresh(task)
    return task.model_dump()


@router.post("/tasks/{task_id}/execute")
def execute_task(task_id: int, session: Session = Depends(get_session)) -> dict:
    task = _task(task_id, session)
    dataset = _dataset(task.dataset_id, session)
    df = read_dataframe(Path(dataset.storage_path))
    task.status = transition_task(TaskStatus(task.status), TaskStatus.RUNNING).value
    task.started_at = utcnow()
    session.add(task)
    session.commit()
    template_id = task.plan_json.get("template_id") or _guess_template(task.user_goal)
    artifact_dir = ARTIFACT_DIR / f"task_{task.id}"
    try:
        output = AutomationTemplateService().run_template(template_id, df, artifact_dir)
        step = AnalysisStep(
            task_id=task.id,
            step_order=1,
            name=task.plan_json.get("title", "自动化分析"),
            description=task.user_goal,
            code=output.code,
            status="completed",
            result_summary="; ".join(output.findings),
        )
        session.add(step)
        session.commit()
        session.refresh(step)
        result = ExecutionResult(
            step_id=step.id,
            stdout="",
            stderr="",
            result_json={"results": output.results, "findings": output.findings, "risks": output.risks},
            artifact_paths=[str(c.image_path) for c in output.charts],
            duration_ms=0,
        )
        session.add(result)
        for chart in output.charts:
            session.add(
                ChartArtifact(
                    task_id=task.id,
                    step_id=step.id,
                    title=chart.title,
                    chart_type=chart.chart_type,
                    image_path=str(chart.image_path),
                    spec_json=chart.spec,
                )
            )
        report_files = ReportService(REPORT_DIR / f"task_{task.id}").create_report(
            task_title=task.plan_json.get("title", "分析报告"),
            dataset_name=dataset.original_filename,
            goal=task.user_goal,
            mode=task.plan_json.get("mode", "Template automation"),
            profile=dataset.profile_json,
            steps=[step.model_dump()],
            findings=output.findings,
            charts=output.charts,
            risks=output.risks,
        )
        session.add(Report(task_id=task.id, title=task.plan_json.get("title", "分析报告"), format="markdown", content_path=str(report_files.markdown_path)))
        session.add(Report(task_id=task.id, title=task.plan_json.get("title", "分析报告"), format="html", content_path=str(report_files.html_path)))
        task.status = transition_task(TaskStatus.RUNNING, TaskStatus.COMPLETED).value
        task.completed_at = utcnow()
        session.add(task)
        session.commit()
        _audit(session, "task.execute", "task", str(task.id), {"status": task.status})
        session.refresh(task)
    except Exception as exc:
        task.status = transition_task(TaskStatus.RUNNING, TaskStatus.FAILED).value
        task.error_message = str(exc)
        task.completed_at = utcnow()
        session.add(task)
        session.commit()
    session.refresh(task)
    return task.model_dump()


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: int, session: Session = Depends(get_session)) -> dict:
    task = _task(task_id, session)
    task.status = transition_task(TaskStatus(task.status), TaskStatus.CANCELLED).value
    session.add(task)
    session.commit()
    session.refresh(task)
    return task.model_dump()


@router.get("/tasks/{task_id}")
def get_task(task_id: int, session: Session = Depends(get_session)) -> dict:
    task = _task(task_id, session)
    steps = session.exec(select(AnalysisStep).where(AnalysisStep.task_id == task.id)).all()
    results = []
    for step in steps:
        results.extend(session.exec(select(ExecutionResult).where(ExecutionResult.step_id == step.id)).all())
    charts = session.exec(select(ChartArtifact).where(ChartArtifact.task_id == task.id)).all()
    reports = session.exec(select(Report).where(Report.task_id == task.id)).all()
    return {
        "task": task.model_dump(),
        "steps": [item.model_dump() for item in steps],
        "results": [item.model_dump() for item in results],
        "charts": [item.model_dump() for item in charts],
        "reports": [item.model_dump() for item in reports],
    }


@router.get("/tasks")
def list_tasks(session: Session = Depends(get_session)) -> list[dict]:
    return [item.model_dump() for item in session.exec(select(AnalysisTask).order_by(AnalysisTask.created_at.desc())).all()]


@router.get("/charts")
def list_charts(session: Session = Depends(get_session)) -> list[dict]:
    return [item.model_dump() for item in session.exec(select(ChartArtifact).order_by(ChartArtifact.created_at.desc())).all()]


@router.get("/charts/{chart_id}/image")
def chart_image(chart_id: int, session: Session = Depends(get_session)) -> FileResponse:
    chart = session.get(ChartArtifact, chart_id)
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    return FileResponse(chart.image_path)


@router.post("/reports/{task_id}")
def create_report_for_task(task_id: int, session: Session = Depends(get_session)) -> dict:
    task = _task(task_id, session)
    if task.status != "completed":
        execute_task(task_id, session)
    return get_task(task_id, session)


@router.get("/reports")
def list_reports(session: Session = Depends(get_session)) -> list[dict]:
    return [item.model_dump() for item in session.exec(select(Report).order_by(Report.created_at.desc())).all()]


@router.get("/reports/{report_id}")
def get_report(report_id: int, session: Session = Depends(get_session)) -> dict:
    report = session.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    content = Path(report.content_path).read_text(encoding="utf-8")
    return {"report": report.model_dump(), "content": content}


@router.get("/reports/{report_id}/download")
def download_report(report_id: int, format: str = "markdown", session: Session = Depends(get_session)) -> FileResponse:
    report = session.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    path = Path(report.content_path)
    if format == "html" and report.format != "html":
        path = path.with_suffix(".html")
    return FileResponse(path, filename=path.name)


@router.get("/audit")
def list_audit(session: Session = Depends(get_session)) -> list[dict]:
    return [item.model_dump() for item in session.exec(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(200)).all()]


@router.get("/settings/llm")
def get_settings() -> dict[str, Any]:
    return SettingsService(DATA_DIR / "settings.json").get_llm_settings()


@router.put("/settings/llm")
def put_settings(payload: SettingsPayload) -> dict[str, Any]:
    return SettingsService(DATA_DIR / "settings.json").save_llm_settings(payload.model_dump(exclude_none=True))


@router.post("/settings/llm/test")
def test_settings() -> dict[str, Any]:
    return SettingsService(DATA_DIR / "settings.json").test_connection()


def _task(task_id: int, session: Session) -> AnalysisTask:
    task = session.get(AnalysisTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _audit(session: Session, action: str, target_type: str, target_id: str, detail: dict[str, Any]) -> None:
    session.add(AuditLog(actor="local-user", action=action, target_type=target_type, target_id=target_id, detail_json=detail))
    session.commit()


def _guess_template(goal: str) -> str:
    text = goal.lower()
    if "pareto" in text or "帕累托" in text or "缺陷" in text:
        return "pareto"
    if "招聘" in text or "漏斗" in text:
        return "recruiting_funnel"
    if "排行" in text or "top" in text or "最高" in text:
        return "ranking"
    if "异常" in text:
        return "outliers"
    if "缺失" in text:
        return "missing_values"
    return "sales_trend"
