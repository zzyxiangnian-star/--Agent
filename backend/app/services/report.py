from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

from jinja2 import Template


@dataclass
class ReportFiles:
    markdown_path: Path
    html_path: Path


class ReportService:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_report(
        self,
        task_title: str,
        dataset_name: str,
        goal: str,
        mode: str,
        profile: dict[str, Any],
        steps: list[dict[str, Any]],
        findings: list[str],
        charts: list[Any],
        risks: list[str],
    ) -> ReportFiles:
        safe_name = "".join(ch if ch.isalnum() else "_" for ch in task_title)[:60] or "report"
        markdown_path = self.output_dir / f"{safe_name}.md"
        html_path = self.output_dir / f"{safe_name}.html"
        markdown = self._markdown(task_title, dataset_name, goal, mode, profile, steps, findings, charts, risks)
        markdown_path.write_text(markdown, encoding="utf-8")
        html_path.write_text(self._html(task_title, markdown), encoding="utf-8")
        return ReportFiles(markdown_path=markdown_path, html_path=html_path)

    def _markdown(
        self,
        title: str,
        dataset_name: str,
        goal: str,
        mode: str,
        profile: dict[str, Any],
        steps: list[dict[str, Any]],
        findings: list[str],
        charts: list[Any],
        risks: list[str],
    ) -> str:
        lines = [
            f"# {title}",
            "",
            f"- 生成模式：`{mode}`",
            f"- 数据来源：`{dataset_name}`",
            f"- 分析目标：{goal}",
            "",
            "## 数据概览",
            "",
            f"- 行数：{profile.get('row_count', 0)}",
            f"- 列数：{profile.get('column_count', 0)}",
            "",
            "## 分析方法",
            "",
        ]
        for step in steps:
            lines.append(f"- {step.get('name', '步骤')}：{step.get('result_summary') or step.get('description', '')}")
        lines.extend(["", "## 核心发现", ""])
        for finding in findings:
            lines.append(f"- {finding}")
        if charts:
            lines.extend(["", "## 图表", ""])
            for chart in charts:
                title_text = getattr(chart, "title", chart.get("title", "图表") if isinstance(chart, dict) else "图表")
                image_path = getattr(chart, "image_path", chart.get("image_path", "") if isinstance(chart, dict) else "")
                lines.append(f"![{title_text}]({image_path})")
                lines.append("")
        lines.extend(["## 风险与限制", ""])
        for risk in risks:
            lines.append(f"- {risk}")
        lines.extend(["", "## 可复现摘要", ""])
        for step in steps:
            code = step.get("code")
            if code:
                lines.extend([f"### {step.get('name', '步骤')}", "", "```python", code, "```", ""])
        return "\n".join(lines).strip() + "\n"

    def _html(self, title: str, markdown: str) -> str:
        body = _markdown_to_basic_html(markdown)
        return Template(
            """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{{ title }}</title>
  <style>
    body { font-family: "Microsoft YaHei", "Segoe UI", sans-serif; margin: 40px; color: #1f2937; line-height: 1.65; }
    h1, h2, h3 { color: #111827; }
    code { background: #eef2f7; padding: 2px 5px; border-radius: 4px; }
    pre { background: #101827; color: #e5e7eb; padding: 16px; border-radius: 8px; overflow: auto; }
    img { max-width: 100%; border: 1px solid #d8dee9; border-radius: 8px; }
  </style>
</head>
<body>{{ body }}</body>
</html>"""
        ).render(title=title, body=body)


def _markdown_to_basic_html(markdown: str) -> str:
    html: list[str] = []
    in_code = False
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            html.append("<pre><code>" if not in_code else "</code></pre>")
            in_code = not in_code
            continue
        if in_code:
            html.append(escape(line))
        elif line.startswith("# "):
            html.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            html.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("### "):
            html.append(f"<h3>{escape(line[4:])}</h3>")
        elif line.startswith("- "):
            html.append(f"<p>• {escape(line[2:])}</p>")
        elif line.startswith("![") and "](" in line:
            alt = line[2:line.index("]")]
            src = line[line.index("(") + 1 : line.rindex(")")]
            html.append(f'<figure><img src="{escape(src)}" alt="{escape(alt)}"><figcaption>{escape(alt)}</figcaption></figure>')
        elif line:
            html.append(f"<p>{escape(line)}</p>")
    return "\n".join(html)
