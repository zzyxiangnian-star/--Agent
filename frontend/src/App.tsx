import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  BarChart3,
  Database,
  FileText,
  History,
  Languages,
  Play,
  Settings,
  Upload,
  Wand2
} from "lucide-react";
import { api, Chart, Dataset, Report, Task } from "./api";
import { useAppStore } from "./store";

type Locale = "zh" | "en";
type PageKey = "Dashboard" | "Datasets" | "Analysis Workspace" | "Charts" | "Reports" | "Runs / Audit" | "Settings";

const pageItems: Array<{ key: PageKey; icon: typeof Activity }> = [
  { key: "Dashboard", icon: Activity },
  { key: "Datasets", icon: Database },
  { key: "Analysis Workspace", icon: Wand2 },
  { key: "Charts", icon: BarChart3 },
  { key: "Reports", icon: FileText },
  { key: "Runs / Audit", icon: History },
  { key: "Settings", icon: Settings }
];

const copy = {
  zh: {
    appSubtitle: "报告工作台",
    nav: {
      Dashboard: "仪表盘",
      Datasets: "数据集",
      "Analysis Workspace": "分析工作台",
      Charts: "图表",
      Reports: "报告",
      "Runs / Audit": "运行 / 审计",
      Settings: "设置"
    },
    dashboard: {
      eyebrow: "本地数据分析闭环",
      datasets: "数据集",
      tasks: "分析任务",
      reports: "报告",
      failed: "失败任务",
      recentTasks: "最近任务"
    },
    datasets: {
      eyebrow: "上传、示例数据与字段画像",
      upload: "上传 CSV/XLSX",
      import: "导入",
      list: "数据集列表",
      preview: "预览",
      enterAnalysis: "进入分析",
      choose: "选择或导入一个数据集",
      rows: "行",
      columns: "列",
      missingRate: "缺失率",
      unique: "唯一值"
    },
    analysis: {
      eyebrow: "计划确认、执行步骤、图表与报告",
      input: "分析输入",
      dataset: "数据集",
      chooseDataset: "选择数据集",
      template: "模板",
      create: "创建任务",
      plan: "生成计划",
      execute: "确认执行",
      result: "执行结果",
      task: "任务",
      download: "下载",
      defaultGoal: "按月份分析销售额、利润和利润率趋势。",
      templates: {
        sales_trend: "销售趋势分析",
        ranking: "排行榜分析",
        pareto: "Pareto 分析",
        missing_values: "缺失值检查",
        outliers: "异常值检查",
        recruiting_funnel: "招聘漏斗分析"
      }
    },
    charts: { eyebrow: "生成图表资产" },
    reports: {
      eyebrow: "Markdown / HTML 报告",
      list: "报告列表",
      preview: "报告预览",
      choose: "选择一份报告"
    },
    audit: {
      eyebrow: "任务、执行与文件生成日志",
      title: "审计日志"
    },
    settings: {
      eyebrow: "OpenAI 兼容模型配置",
      mode: "当前模式",
      enableAi: "启用 AI",
      model: "模型名",
      notConfigured: "未配置",
      timeout: "超时",
      save: "保存设置",
      test: "测试连接"
    },
    empty: "暂无数据",
    samples: {
      sales_orders: "销售订单",
      production_quality: "生产质量",
      recruiting_funnel: "招聘漏斗"
    }
  },
  en: {
    appSubtitle: "Report Workspace",
    nav: {
      Dashboard: "Dashboard",
      Datasets: "Datasets",
      "Analysis Workspace": "Analysis",
      Charts: "Charts",
      Reports: "Reports",
      "Runs / Audit": "Runs / Audit",
      Settings: "Settings"
    },
    dashboard: {
      eyebrow: "Local data analysis loop",
      datasets: "Datasets",
      tasks: "Analysis tasks",
      reports: "Reports",
      failed: "Failed tasks",
      recentTasks: "Recent tasks"
    },
    datasets: {
      eyebrow: "Upload, sample data, and field profiles",
      upload: "Upload CSV/XLSX",
      import: "Import",
      list: "Dataset list",
      preview: "Preview",
      enterAnalysis: "Analyze",
      choose: "Select or import a dataset",
      rows: "rows",
      columns: "columns",
      missingRate: "Missing",
      unique: "Unique"
    },
    analysis: {
      eyebrow: "Plan review, execution, charts, and reports",
      input: "Analysis input",
      dataset: "Dataset",
      chooseDataset: "Choose dataset",
      template: "Template",
      create: "Create task",
      plan: "Generate plan",
      execute: "Run",
      result: "Execution result",
      task: "Task",
      download: "Download",
      defaultGoal: "Analyze monthly sales, profit, and profit margin trends.",
      templates: {
        sales_trend: "Sales trend",
        ranking: "Ranking",
        pareto: "Pareto analysis",
        missing_values: "Missing values",
        outliers: "Outlier check",
        recruiting_funnel: "Recruiting funnel"
      }
    },
    charts: { eyebrow: "Generated chart assets" },
    reports: {
      eyebrow: "Markdown / HTML reports",
      list: "Report list",
      preview: "Report preview",
      choose: "Select a report"
    },
    audit: {
      eyebrow: "Tasks, execution, and generated file logs",
      title: "Audit log"
    },
    settings: {
      eyebrow: "OpenAI-compatible model configuration",
      mode: "Current mode",
      enableAi: "Enable AI",
      model: "Model",
      notConfigured: "Not configured",
      timeout: "Timeout",
      save: "Save settings",
      test: "Test connection"
    },
    empty: "No data",
    samples: {
      sales_orders: "Sales orders",
      production_quality: "Production quality",
      recruiting_funnel: "Recruiting funnel"
    }
  }
} satisfies Record<Locale, Record<string, unknown>>;

const samples = ["sales_orders", "production_quality", "recruiting_funnel"] as const;
const templates = ["sales_trend", "ranking", "pareto", "missing_values", "outliers", "recruiting_funnel"] as const;

export function App() {
  const { page, setPage, locale, setLocale } = useAppStore();
  const t = copy[locale];

  return (
    <main className="app-shell" lang={locale} data-locale={locale}>
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">DA</span>
          <div>
            <strong>Data Agent</strong>
            <small>{t.appSubtitle}</small>
          </div>
        </div>
        <nav>
          {pageItems.map((item) => {
            const Icon = item.icon;
            return (
              <button className={page === item.key ? "nav active" : "nav"} key={item.key} onClick={() => setPage(item.key)}>
                <Icon size={18} />
                <span>{t.nav[item.key]}</span>
              </button>
            );
          })}
        </nav>
        <div className="language-card">
          <Languages size={16} />
          <div className="segmented" aria-label="Language">
            <button className={locale === "zh" ? "selected" : ""} onClick={() => setLocale("zh")}>中文</button>
            <button className={locale === "en" ? "selected" : ""} onClick={() => setLocale("en")}>EN</button>
          </div>
        </div>
      </aside>
      <section className="workspace">
        {page === "Dashboard" && <Dashboard locale={locale} />}
        {page === "Datasets" && <Datasets locale={locale} />}
        {page === "Analysis Workspace" && <Analysis locale={locale} />}
        {page === "Charts" && <Charts locale={locale} />}
        {page === "Reports" && <Reports locale={locale} />}
        {page === "Runs / Audit" && <Audit locale={locale} />}
        {page === "Settings" && <SettingsPage locale={locale} />}
      </section>
    </main>
  );
}

function Dashboard({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: api.datasets });
  const tasks = useQuery({ queryKey: ["tasks"], queryFn: api.tasks });
  const reports = useQuery({ queryKey: ["reports"], queryFn: api.reports });
  const failed = tasks.data?.filter((task) => task.status === "failed").length ?? 0;

  return (
    <Page title={t.nav.Dashboard} eyebrow={t.dashboard.eyebrow}>
      <div className="metric-grid">
        <Metric label={t.dashboard.datasets} value={datasets.data?.length ?? 0} />
        <Metric label={t.dashboard.tasks} value={tasks.data?.length ?? 0} />
        <Metric label={t.dashboard.reports} value={reports.data?.length ?? 0} />
        <Metric label={t.dashboard.failed} value={failed} danger={failed > 0} />
      </div>
      <Panel title={t.dashboard.recentTasks}>
        <TaskTable tasks={tasks.data ?? []} locale={locale} />
      </Panel>
    </Page>
  );
}

function Datasets({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const queryClient = useQueryClient();
  const { setDataset, setPage } = useAppStore();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: api.datasets });
  const seed = useMutation({ mutationFn: api.seedDataset, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }) });
  const upload = useMutation({ mutationFn: api.uploadDataset, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] }) });
  const [active, setActive] = useState<Dataset | undefined>();
  const preview = useQuery({ queryKey: ["preview", active?.id], queryFn: () => api.preview(active!.id), enabled: Boolean(active) });

  return (
    <Page title={t.nav.Datasets} eyebrow={t.datasets.eyebrow}>
      <div className="toolbar">
        <label className="file-button">
          <Upload size={16} />
          {t.datasets.upload}
          <input type="file" accept=".csv,.xlsx,.xls" onChange={(event) => event.target.files?.[0] && upload.mutate(event.target.files[0])} />
        </label>
        {samples.map((sample) => (
          <button key={sample} onClick={() => seed.mutate(sample)}>
            {t.datasets.import} {t.samples[sample]}
          </button>
        ))}
      </div>
      <div className="split-layout">
        <Panel title={t.datasets.list}>
          <div className="list">
            {(datasets.data ?? []).map((dataset) => (
              <button className="list-row" key={dataset.id} onClick={() => setActive(dataset)}>
                <strong>{dataset.name}</strong>
                <span>{dataset.row_count} {t.datasets.rows} · {dataset.column_count} {t.datasets.columns}</span>
              </button>
            ))}
          </div>
        </Panel>
        <Panel title={active ? `${active.name} Profile` : "Profile"}>
          {active ? (
            <>
              <div className="profile-grid">
                {active.profile_json.columns.map((col) => (
                  <div className="field-card" key={col.name}>
                    <strong>{col.name}</strong>
                    <span>{col.semantic_type} · {col.dtype}</span>
                    <small>{t.datasets.missingRate} {(col.missing_rate * 100).toFixed(1)}% · {t.datasets.unique} {col.unique_count}</small>
                  </div>
                ))}
              </div>
              <h3>{t.datasets.preview}</h3>
              <DataTable rows={preview.data?.rows ?? []} locale={locale} />
              <button onClick={() => { setDataset(active.id); setPage("Analysis Workspace"); }}>{t.datasets.enterAnalysis}</button>
            </>
          ) : <Empty text={t.datasets.choose} />}
        </Panel>
      </div>
    </Page>
  );
}

function Analysis({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const queryClient = useQueryClient();
  const { selectedDatasetId, selectedTaskId, setTask } = useAppStore();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: api.datasets });
  const [datasetId, setDatasetId] = useState<number | undefined>(selectedDatasetId);
  const [goal, setGoal] = useState(t.analysis.defaultGoal);
  const [templateId, setTemplateId] = useState<(typeof templates)[number]>("sales_trend");
  const create = useMutation({
    mutationFn: () => api.createTask(datasetId!, goal, templateId),
    onSuccess: (task) => {
      setTask(task.id);
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    }
  });
  const plan = useMutation({ mutationFn: (id: number) => api.planTask(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["task", selectedTaskId] }) });
  const execute = useMutation({
    mutationFn: (id: number) => api.executeTask(id),
    onSuccess: (task) => {
      setTask(task.id);
      queryClient.invalidateQueries();
    }
  });
  const taskId = create.data?.id ?? selectedTaskId;
  const detail = useQuery({ queryKey: ["task", taskId], queryFn: () => api.taskDetail(taskId!), enabled: Boolean(taskId) });
  const activeTask = detail.data?.task ?? create.data;

  return (
    <Page title={t.nav["Analysis Workspace"]} eyebrow={t.analysis.eyebrow}>
      <Panel title={t.analysis.input}>
        <div className="form-grid">
          <label>
            {t.analysis.dataset}
            <select value={datasetId ?? ""} onChange={(event) => setDatasetId(Number(event.target.value))}>
              <option value="">{t.analysis.chooseDataset}</option>
              {(datasets.data ?? []).map((dataset) => <option value={dataset.id} key={dataset.id}>{dataset.name}</option>)}
            </select>
          </label>
          <label>
            {t.analysis.template}
            <select value={templateId} onChange={(event) => setTemplateId(event.target.value as (typeof templates)[number])}>
              {templates.map((template) => <option value={template} key={template}>{t.analysis.templates[template]}</option>)}
            </select>
          </label>
        </div>
        <textarea value={goal} onChange={(event) => setGoal(event.target.value)} />
        <div className="toolbar">
          <button disabled={!datasetId} onClick={() => create.mutate()}><Wand2 size={16} />{t.analysis.create}</button>
          <button disabled={!activeTask} onClick={() => plan.mutate(activeTask!.id)}>{t.analysis.plan}</button>
          <button disabled={!activeTask || activeTask.status === "running"} onClick={() => execute.mutate(activeTask!.id)}><Play size={16} />{t.analysis.execute}</button>
        </div>
      </Panel>
      {activeTask && (
        <div className="split-layout">
          <Panel title={`${t.analysis.task} #${activeTask.id} · ${activeTask.status}`}>
            <pre>{JSON.stringify(activeTask.plan_json, null, 2)}</pre>
          </Panel>
          <Panel title={t.analysis.result}>
            {(detail.data?.steps ?? []).map((step, index) => <pre key={index}>{JSON.stringify(step, null, 2)}</pre>)}
            {(detail.data?.charts ?? []).map((chart) => <img key={chart.id} src={`/api/charts/${chart.id}/image`} alt={chart.title} />)}
            {(detail.data?.reports ?? []).map((report) => (
              <a className="download-link" key={report.id} href={`/api/reports/${report.id}/download?format=${report.format}`}>
                {t.analysis.download} {report.format}
              </a>
            ))}
          </Panel>
        </div>
      )}
    </Page>
  );
}

function Charts({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const charts = useQuery({ queryKey: ["charts"], queryFn: api.charts });
  return (
    <Page title={t.nav.Charts} eyebrow={t.charts.eyebrow}>
      <div className="card-grid">
        {(charts.data ?? []).map((chart) => <ChartCard key={chart.id} chart={chart} />)}
      </div>
    </Page>
  );
}

function Reports({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const reports = useQuery({ queryKey: ["reports"], queryFn: api.reports });
  const [active, setActive] = useState<Report | undefined>();
  const detail = useQuery({ queryKey: ["report", active?.id], queryFn: () => api.report(active!.id), enabled: Boolean(active) });
  return (
    <Page title={t.nav.Reports} eyebrow={t.reports.eyebrow}>
      <div className="split-layout">
        <Panel title={t.reports.list}>
          {(reports.data ?? []).map((report) => (
            <button className="list-row" key={report.id} onClick={() => setActive(report)}>
              <strong>{report.title}</strong><span>{report.format}</span>
            </button>
          ))}
        </Panel>
        <Panel title={t.reports.preview}>
          {detail.data ? <pre>{detail.data.content}</pre> : <Empty text={t.reports.choose} />}
        </Panel>
      </div>
    </Page>
  );
}

function Audit({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const audit = useQuery({ queryKey: ["audit"], queryFn: api.audit });
  return (
    <Page title={t.nav["Runs / Audit"]} eyebrow={t.audit.eyebrow}>
      <Panel title={t.audit.title}>
        <DataTable rows={audit.data ?? []} locale={locale} />
      </Panel>
    </Page>
  );
}

function SettingsPage({ locale }: { locale: Locale }) {
  const t = copy[locale];
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const [form, setForm] = useState<Record<string, unknown>>({});
  const merged = { ...(settings.data ?? {}), ...form };
  const save = useMutation({ mutationFn: api.saveSettings, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }) });
  const test = useMutation({ mutationFn: api.testSettings });

  return (
    <Page title={t.nav.Settings} eyebrow={t.settings.eyebrow}>
      <Panel title={`${t.settings.mode}: ${String(merged.active_mode ?? "Template automation")}`}>
        <div className="form-grid">
          <label className="check-row">
            <input type="checkbox" checked={Boolean(merged.llm_enabled)} onChange={(event) => setForm({ ...form, llm_enabled: event.target.checked, llm_provider: event.target.checked ? "openai-compatible" : "disabled" })} />
            {t.settings.enableAi}
          </label>
          <label>Base URL<input value={String(merged.llm_base_url ?? "")} onChange={(event) => setForm({ ...form, llm_base_url: event.target.value })} /></label>
          <label>{t.settings.model}<input value={String(merged.llm_model ?? "")} onChange={(event) => setForm({ ...form, llm_model: event.target.value })} /></label>
          <label>API Key<input type="password" placeholder={String(merged.masked_api_key ?? t.settings.notConfigured)} onChange={(event) => setForm({ ...form, llm_api_key: event.target.value })} /></label>
          <label>{t.settings.timeout}<input type="number" value={Number(merged.request_timeout ?? 20)} onChange={(event) => setForm({ ...form, request_timeout: Number(event.target.value) })} /></label>
          <label>Max Tokens<input type="number" value={Number(merged.max_tokens ?? 2000)} onChange={(event) => setForm({ ...form, max_tokens: Number(event.target.value) })} /></label>
        </div>
        <div className="toolbar">
          <button onClick={() => save.mutate(form)}>{t.settings.save}</button>
          <button onClick={() => test.mutate()}>{t.settings.test}</button>
        </div>
        {test.data && <pre>{JSON.stringify(test.data, null, 2)}</pre>}
      </Panel>
    </Page>
  );
}

function Page({ title, eyebrow, children }: { title: string; eyebrow: string; children: React.ReactNode }) {
  return (
    <div className="page">
      <header className="page-header">
        <span>{eyebrow}</span>
        <h1>{title}</h1>
      </header>
      {children}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="panel"><h2>{title}</h2>{children}</section>;
}

function Metric({ label, value, danger }: { label: string; value: number; danger?: boolean }) {
  return <div className={danger ? "metric danger" : "metric"}><span>{label}</span><strong>{value}</strong></div>;
}

function TaskTable({ tasks, locale }: { tasks: Task[]; locale: Locale }) {
  return <DataTable rows={tasks.map((task) => ({ id: task.id, goal: task.user_goal, status: task.status }))} locale={locale} />;
}

function ChartCard({ chart }: { chart: Chart }) {
  return <article className="chart-card"><img src={`/api/charts/${chart.id}/image`} alt={chart.title} /><strong>{chart.title}</strong><span>{chart.chart_type}</span></article>;
}

function DataTable({ rows, locale }: { rows: Array<Record<string, unknown>>; locale: Locale }) {
  const columns = useMemo(() => Object.keys(rows[0] ?? {}).slice(0, 8), [rows]);
  if (!rows.length) return <Empty text={copy[locale].empty} />;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map((col) => <th key={col}>{col}</th>)}</tr></thead>
        <tbody>{rows.slice(0, 30).map((row, index) => <tr key={index}>{columns.map((col) => <td key={col}>{String(row[col] ?? "")}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <div className="empty">{text}</div>;
}
