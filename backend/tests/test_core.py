from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import pytest

from app.agent.runner import AgentRunner, MockLLMClient
from app.automation.templates import AutomationTemplateService
from app.domain.state import InvalidTransitionError, TaskStatus, transition_task
from app.sandbox.executor import SandboxSecurityError, SandboxTimeoutError, execute_pandas_code
from app.services.profiling import ProfilingService
from app.services.report import ReportService
from app.settings.service import SettingsService, mask_secret


def test_profile_infers_columns_missing_and_stats(tmp_path: Path) -> None:
    csv_path = tmp_path / "sales.csv"
    pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02", None],
            "region": ["East", "West", "East"],
            "sales": [100.0, 150.0, None],
        }
    ).to_csv(csv_path, index=False)

    profile = ProfilingService().profile_file(csv_path)

    assert profile.row_count == 3
    assert profile.column_count == 3
    sales = next(col for col in profile.columns if col.name == "sales")
    assert sales.missing_count == 1
    assert sales.missing_rate == pytest.approx(1 / 3)
    assert sales.stats["mean"] == 125.0
    region = next(col for col in profile.columns if col.name == "region")
    assert region.unique_count == 2


def test_task_state_machine_allows_only_declared_transitions() -> None:
    assert transition_task(TaskStatus.DRAFT, TaskStatus.PLANNED) == TaskStatus.PLANNED
    assert transition_task(TaskStatus.PLANNED, TaskStatus.RUNNING) == TaskStatus.RUNNING
    assert transition_task(TaskStatus.RUNNING, TaskStatus.COMPLETED) == TaskStatus.COMPLETED

    with pytest.raises(InvalidTransitionError):
        transition_task(TaskStatus.COMPLETED, TaskStatus.RUNNING)
    with pytest.raises(InvalidTransitionError):
        transition_task(TaskStatus.FAILED, TaskStatus.COMPLETED)
    with pytest.raises(InvalidTransitionError):
        transition_task(TaskStatus.CANCELLED, TaskStatus.RUNNING)


def test_sandbox_executes_safe_pandas_and_blocks_danger(tmp_path: Path) -> None:
    df = pd.DataFrame({"region": ["East", "East", "West"], "sales": [10, 20, 5]})
    result = execute_pandas_code(
        "result = {'summary': 'ok', 'data': df.groupby('region')['sales'].sum().reset_index().to_dict('records')}",
        df=df,
        artifact_dir=tmp_path,
        timeout_seconds=3,
    )

    assert result.result_json["summary"] == "ok"
    assert {"region": "East", "sales": 30} in result.result_json["data"]

    for code in ["import os\nresult = {}", "open('x.txt', 'w')", "import subprocess\nresult = {}", "eval('1+1')"]:
        with pytest.raises(SandboxSecurityError):
            execute_pandas_code(code, df=df, artifact_dir=tmp_path, timeout_seconds=3)


def test_sandbox_times_out_long_running_code(tmp_path: Path) -> None:
    df = pd.DataFrame({"x": [1]})
    with pytest.raises(SandboxTimeoutError):
        execute_pandas_code("while True:\n    pass", df=df, artifact_dir=tmp_path, timeout_seconds=1)


def test_automation_templates_generate_plan_results_chart_and_findings(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "日期": pd.date_range("2026-01-01", periods=4, freq="MS"),
            "产品": ["A", "B", "A", "C"],
            "销售额": [100, 80, 120, 20],
            "利润": [30, 20, 50, 1],
        }
    )
    service = AutomationTemplateService()

    plan = service.create_plan("sales_trend", df, goal="按月份分析销售额趋势")
    assert plan["mode"] == "Template automation"
    assert plan["steps"]

    output = service.run_template("sales_trend", df, tmp_path)
    assert output.findings
    assert output.charts
    assert output.charts[0].image_path.exists()
    assert output.results[0]["metrics"]


def test_report_generation_is_grounded_and_downloadable(tmp_path: Path) -> None:
    report = ReportService(tmp_path).create_report(
        task_title="月度销售分析",
        dataset_name="sales.csv",
        goal="按月份分析销售额趋势",
        mode="Template automation",
        profile={"row_count": 4, "column_count": 4, "columns": [{"name": "销售额", "missing_rate": 0}]},
        steps=[{"name": "趋势分析", "code": "result = ...", "result_summary": "销售额增长"}],
        findings=["2026-03 销售额最高，为 120。"],
        charts=[],
        risks=["样本量较小。"],
    )

    markdown = report.markdown_path.read_text(encoding="utf-8")
    html = report.html_path.read_text(encoding="utf-8")
    assert "2026-03 销售额最高" in markdown
    assert "Template automation" in markdown
    assert "<html" in html


def test_settings_masks_api_key_and_falls_back_without_real_network(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")
    service.save_llm_settings(
        {
            "llm_enabled": True,
            "llm_provider": "openai-compatible",
            "llm_api_key": "sk-test123456",
            "llm_base_url": "http://127.0.0.1:9/v1",
            "llm_model": "demo-model",
            "request_timeout": 1,
            "max_tokens": 2000,
        }
    )

    settings = service.get_llm_settings()
    assert settings["has_api_key"] is True
    assert settings["llm_api_key"] == ""
    assert settings["masked_api_key"] == "sk-***3456"
    assert mask_secret("") == ""
    assert service.test_connection()["ok"] is False


def test_agent_runner_uses_profile_first_and_mock_llm_for_structured_plan(tmp_path: Path) -> None:
    df = pd.DataFrame({"region": ["East", "West"], "sales": [10, 20]})
    profile = {"row_count": 2, "columns": [{"name": "region"}, {"name": "sales"}]}
    client = MockLLMClient(
        plan={
            "title": "按区域销售分析",
            "steps": [
                {
                    "name": "区域汇总",
                    "description": "按区域汇总销售额",
                    "template": "group_summary",
                    "chart_type": "bar",
                }
            ],
        }
    )

    runner = AgentRunner(llm_client=client)
    plan = runner.create_plan("分析各区域销售额", profile)

    assert plan["title"] == "按区域销售分析"
    assert client.last_profile == profile
    assert "rows" not in json.dumps(client.last_profile).lower()
