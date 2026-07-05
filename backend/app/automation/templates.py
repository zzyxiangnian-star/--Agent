from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


@dataclass
class ChartOutput:
    title: str
    chart_type: str
    image_path: Path
    spec: dict[str, Any]


@dataclass
class AutomationOutput:
    results: list[dict[str, Any]]
    charts: list[ChartOutput]
    findings: list[str]
    risks: list[str]
    code: str


class AutomationTemplateService:
    templates = {
        "missing_values": "缺失值检查",
        "outliers": "异常值检查",
        "group_summary": "分组汇总",
        "trend": "趋势分析",
        "ranking": "排行榜分析",
        "pareto": "Pareto 分析",
        "sales_trend": "销售趋势分析",
        "quality_pareto": "质量 Pareto 分析",
        "recruiting_funnel": "招聘漏斗分析",
    }

    def create_plan(self, template_id: str, df: pd.DataFrame, goal: str = "") -> dict[str, Any]:
        title = self.templates.get(template_id, "自动化分析")
        return {
            "mode": "Template automation",
            "template_id": template_id,
            "title": title,
            "goal": goal or title,
            "steps": [
                {"name": "数据检查", "description": "读取字段类型、缺失值和基础统计。"},
                {"name": title, "description": f"使用规则模板执行{title}并生成图表。"},
                {"name": "报告生成", "description": "根据真实计算结果生成 Markdown/HTML 报告。"},
            ],
        }

    def run_template(self, template_id: str, df: pd.DataFrame, artifact_dir: Path) -> AutomationOutput:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        if template_id in {"sales_trend", "trend"}:
            return self._trend(df, artifact_dir)
        if template_id in {"ranking", "group_summary"}:
            return self._ranking(df, artifact_dir)
        if template_id in {"pareto", "quality_pareto"}:
            return self._pareto(df, artifact_dir)
        if template_id == "recruiting_funnel":
            return self._recruiting(df, artifact_dir)
        if template_id == "outliers":
            return self._outliers(df, artifact_dir)
        return self._missing(df, artifact_dir)

    def _trend(self, df: pd.DataFrame, artifact_dir: Path) -> AutomationOutput:
        date_col = _find_col(df, ["日期", "date", "month", "月份", "时间"])
        value_col = _find_col(df, ["销售额", "sales", "revenue", "amount", "利润", "profit"])
        if date_col and value_col:
            temp = df.copy()
            temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
            temp = temp.dropna(subset=[date_col])
            temp["period"] = temp[date_col].dt.to_period("M").astype(str)
            grouped = temp.groupby("period", as_index=False)[value_col].sum()
            chart = artifact_dir / "trend.png"
            plt.figure(figsize=(8, 4.5))
            sns.lineplot(data=grouped, x="period", y=value_col, marker="o")
            plt.title(f"{value_col} 月度趋势")
            plt.xlabel("月份")
            plt.ylabel(value_col)
            plt.xticks(rotation=30)
            plt.tight_layout()
            plt.savefig(chart, dpi=150)
            plt.close()
            top = grouped.sort_values(value_col, ascending=False).iloc[0]
            findings = [f"{top['period']} 的 {value_col} 最高，为 {top[value_col]:,.2f}。"]
            return AutomationOutput(
                results=[{"name": "trend", "metrics": grouped.to_dict("records")}],
                charts=[ChartOutput(f"{value_col} 月度趋势", "line", chart, {"x": "period", "y": value_col})],
                findings=findings,
                risks=_basic_risks(df),
                code="grouped = df.groupby(month)[value].sum()",
            )
        return self._ranking(df, artifact_dir)

    def _ranking(self, df: pd.DataFrame, artifact_dir: Path) -> AutomationOutput:
        category = _first_category(df)
        value = _first_numeric(df)
        if not category or not value:
            return self._missing(df, artifact_dir)
        grouped = df.groupby(category, as_index=False)[value].sum().sort_values(value, ascending=False).head(10)
        chart = artifact_dir / "ranking.png"
        plt.figure(figsize=(8, 4.5))
        sns.barplot(data=grouped, x=value, y=category)
        plt.title(f"{category} 按 {value} 排行")
        plt.xlabel(value)
        plt.ylabel(category)
        plt.tight_layout()
        plt.savefig(chart, dpi=150)
        plt.close()
        leader = grouped.iloc[0]
        return AutomationOutput(
            results=[{"name": "ranking", "metrics": grouped.to_dict("records")}],
            charts=[ChartOutput(f"{category} 按 {value} 排行", "bar", chart, {"x": value, "y": category})],
            findings=[f"{leader[category]} 排名第一，{value} 为 {leader[value]:,.2f}。"],
            risks=_basic_risks(df),
            code=f"grouped = df.groupby('{category}')['{value}'].sum().sort_values(ascending=False)",
        )

    def _pareto(self, df: pd.DataFrame, artifact_dir: Path) -> AutomationOutput:
        category = _find_col(df, ["缺陷类型", "defect", "产品", "品类", "category"]) or _first_category(df)
        value = _find_col(df, ["不良数", "defects", "数量", "count", "sales", "销售额"]) or _first_numeric(df)
        if not category or not value:
            return self._missing(df, artifact_dir)
        grouped = df.groupby(category, as_index=False)[value].sum().sort_values(value, ascending=False)
        total = grouped[value].sum()
        grouped["累计占比"] = grouped[value].cumsum() / total if total else 0
        chart = artifact_dir / "pareto.png"
        fig, ax1 = plt.subplots(figsize=(8, 4.5))
        ax1.bar(grouped[category].astype(str), grouped[value])
        ax1.set_ylabel(value)
        ax2 = ax1.twinx()
        ax2.plot(grouped[category].astype(str), grouped["累计占比"], color="#d1495b", marker="o")
        ax2.set_ylabel("累计占比")
        ax1.set_title(f"{category} Pareto 分析")
        ax1.tick_params(axis="x", rotation=30)
        fig.tight_layout()
        fig.savefig(chart, dpi=150)
        plt.close(fig)
        top = grouped.iloc[0]
        return AutomationOutput(
            results=[{"name": "pareto", "metrics": grouped.head(20).to_dict("records")}],
            charts=[ChartOutput(f"{category} Pareto 分析", "pareto", chart, {"category": category, "value": value})],
            findings=[f"{top[category]} 贡献最高，{value} 为 {top[value]:,.2f}。"],
            risks=_basic_risks(df),
            code=f"grouped = df.groupby('{category}')['{value}'].sum(); grouped['累计占比'] = grouped.cumsum()/total",
        )

    def _recruiting(self, df: pd.DataFrame, artifact_dir: Path) -> AutomationOutput:
        cols = [_find_col(df, names) for names in [["简历数", "resume"], ["面试数", "interview"], ["offer"], ["入职数", "hire"]]]
        metrics = {col: float(df[col].sum()) for col in cols if col}
        if not metrics:
            return self._ranking(df, artifact_dir)
        chart = artifact_dir / "funnel.png"
        labels = list(metrics.keys())
        values = list(metrics.values())
        plt.figure(figsize=(7, 4))
        sns.barplot(x=values, y=labels)
        plt.title("招聘漏斗")
        plt.xlabel("人数")
        plt.tight_layout()
        plt.savefig(chart, dpi=150)
        plt.close()
        return AutomationOutput(
            results=[{"name": "recruiting_funnel", "metrics": metrics}],
            charts=[ChartOutput("招聘漏斗", "bar", chart, {"stages": labels})],
            findings=[f"招聘漏斗起点为 {values[0]:,.0f}，终点为 {values[-1]:,.0f}。"],
            risks=_basic_risks(df),
            code="metrics = df[funnel_columns].sum()",
        )

    def _outliers(self, df: pd.DataFrame, artifact_dir: Path) -> AutomationOutput:
        metrics = []
        for col in df.select_dtypes(include="number").columns:
            q1, q3 = df[col].quantile([0.25, 0.75])
            iqr = q3 - q1
            low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            count = int(((df[col] < low) | (df[col] > high)).sum())
            metrics.append({"column": col, "outlier_count": count, "lower": low, "upper": high})
        return AutomationOutput(
            results=[{"name": "outliers", "metrics": metrics}],
            charts=[],
            findings=[f"共检查 {len(metrics)} 个数值字段的 IQR 异常值。"],
            risks=_basic_risks(df),
            code="outliers = values outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR]",
        )

    def _missing(self, df: pd.DataFrame, artifact_dir: Path) -> AutomationOutput:
        metrics = [
            {"column": col, "missing_count": int(df[col].isna().sum()), "missing_rate": float(df[col].isna().mean())}
            for col in df.columns
        ]
        affected = [m for m in metrics if m["missing_count"] > 0]
        return AutomationOutput(
            results=[{"name": "missing_values", "metrics": metrics}],
            charts=[],
            findings=[f"发现 {len(affected)} 个字段存在缺失值。"],
            risks=_basic_risks(df),
            code="missing = df.isna().mean()",
        )


def _find_col(df: pd.DataFrame, names: list[str]) -> str | None:
    lowered = {str(col).lower(): col for col in df.columns}
    for name in names:
        needle = name.lower()
        for lower, original in lowered.items():
            if needle in lower:
                return str(original)
    return None


def _first_numeric(df: pd.DataFrame) -> str | None:
    cols = list(df.select_dtypes(include="number").columns)
    return str(cols[0]) if cols else None


def _first_category(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]) and df[col].nunique(dropna=True) <= 50:
            return str(col)
    return str(df.columns[0]) if len(df.columns) else None


def _basic_risks(df: pd.DataFrame) -> list[str]:
    risks = []
    if len(df) < 30:
        risks.append("样本量较小，趋势和排序结论需要谨慎解读。")
    missing = df.isna().mean().max() if len(df.columns) else 0
    if missing > 0:
        risks.append("数据存在缺失值，可能影响部分指标口径。")
    return risks or ["当前分析未发现明显数据质量限制，但仍需结合业务口径复核。"]
