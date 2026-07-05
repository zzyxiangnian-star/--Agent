from __future__ import annotations

from typing import Any, Protocol


class LLMClient(Protocol):
    def create_analysis_plan(self, goal: str, profile: dict[str, Any]) -> dict[str, Any]:
        ...


class MockLLMClient:
    def __init__(self, plan: dict[str, Any] | None = None):
        self.plan = plan or {
            "title": "自动分析计划",
            "steps": [{"name": "数据概览", "description": "检查数据结构和基础指标。", "template": "missing_values"}],
        }
        self.last_goal: str | None = None
        self.last_profile: dict[str, Any] | None = None

    def create_analysis_plan(self, goal: str, profile: dict[str, Any]) -> dict[str, Any]:
        self.last_goal = goal
        self.last_profile = profile
        return self.plan


class AgentRunner:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or MockLLMClient()

    def create_plan(self, goal: str, profile: dict[str, Any]) -> dict[str, Any]:
        lightweight_profile = {key: profile[key] for key in ("row_count", "column_count", "columns") if key in profile}
        plan = self.llm_client.create_analysis_plan(goal, lightweight_profile)
        plan.setdefault("mode", "AI-assisted")
        plan.setdefault("goal", goal)
        return plan
