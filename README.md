# AI 数据分析与报告生成 Agent

[![CI](https://github.com/zzyxiangnian-star/--Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/zzyxiangnian-star/--Agent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个本地优先的数据分析 MVP：导入 CSV/XLSX，自动生成数据概览，运行常用分析模板，并输出图表及 Markdown/HTML 报告。即使不配置大模型，核心分析流程也可以完整运行。

## 功能

- 上传 CSV/XLSX，或一键导入销售、生产质量和招聘漏斗示例数据。
- 自动识别字段类型、缺失值、分布和基础统计指标。
- 内置趋势、排行、Pareto、缺失值、异常值和招聘漏斗分析模板。
- 保存分析步骤、执行结果、审计日志、图表及 Markdown/HTML 报告。
- 提供可选的 OpenAI 兼容 API 配置入口，默认关闭 AI 功能。
- 对分析代码执行 AST 安全检查、危险调用限制和子进程超时控制。

## 技术架构

- 后端：FastAPI、SQLModel、Pandas、Matplotlib、Seaborn
- 前端：React、TypeScript、Vite、TanStack Query、Zustand
- 数据存储：本地 SQLite 与文件系统
- 测试：Pytest、TypeScript 编译与 Vite 生产构建

主要目录：

```text
backend/app/       FastAPI API、领域模型、分析服务与执行沙箱
backend/tests/     后端自动化测试
frontend/src/      React 数据分析工作台
sample_data/       可公开使用的演示数据
```

运行时产生的 `data/`、`uploads/`、`reports/` 和 `artifacts/` 不纳入版本控制。

## 环境要求

- Python 3.12
- Node.js 22 或更高版本
- npm 10 或更高版本

## 快速开始

### 1. 获取项目

```bash
git clone "https://github.com/zzyxiangnian-star/--Agent.git" data-analysis-report-agent
cd data-analysis-report-agent
```

### 2. 启动后端

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload
```

macOS/Linux：

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r backend/requirements.txt
./.venv/bin/python -m uvicorn app.main:app --app-dir backend --reload
```

后端 API 默认运行在 `http://127.0.0.1:8000`。

### 3. 启动前端

另开一个终端：

```bash
cd frontend
npm ci
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`。

## 模型 API 配置

项目默认使用无 AI 模式。需要启用 OpenAI 兼容服务时，复制示例配置：

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

macOS/Linux：

```bash
cp .env.example .env
```

然后编辑 `.env`：

```dotenv
LLM_ENABLED=true
LLM_PROVIDER=openai
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
```

不要提交 `.env` 或任何真实密钥。API Key 不会由普通接口明文返回，只会显示掩码。

## 测试与构建

运行后端测试：

```bash
python -m pytest backend/tests -q
```

检查前端生产构建：

```bash
cd frontend
npm ci
npm run build
```

相同检查会在每次推送和 Pull Request 中由 GitHub Actions 自动执行。

## 安全边界

分析沙箱会在执行前解析 Python AST，并拒绝 `os`、`subprocess`、`requests`、`open`、`eval`、`exec` 等危险导入或调用。代码在有超时限制的子进程中运行，并只暴露受控的数据分析对象。

该机制用于降低风险，但不应被视为强隔离容器。请勿在不受信任的多租户环境中直接运行未知代码。安全问题请按照 [SECURITY.md](SECURITY.md) 私下报告。

## 贡献

欢迎提交 Issue 和 Pull Request。参与前请阅读 [贡献指南](CONTRIBUTING.md) 与 [行为准则](CODE_OF_CONDUCT.md)。

## 许可证

本项目基于 [MIT License](LICENSE) 开源。
