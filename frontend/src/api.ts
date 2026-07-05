export type Dataset = {
  id: number;
  name: string;
  original_filename: string;
  row_count: number;
  column_count: number;
  profile_json: Profile;
  created_at: string;
};

export type Profile = {
  row_count: number;
  column_count: number;
  columns: Array<{
    name: string;
    dtype: string;
    semantic_type: string;
    missing_count: number;
    missing_rate: number;
    unique_count: number;
    sample_values: unknown[];
    stats: Record<string, unknown>;
  }>;
};

export type Task = {
  id: number;
  dataset_id: number;
  user_goal: string;
  status: string;
  plan_json: Record<string, unknown>;
  error_message?: string;
};

export type Chart = {
  id: number;
  title: string;
  chart_type: string;
  image_path: string;
  created_at: string;
};

export type Report = {
  id: number;
  task_id: number;
  title: string;
  format: string;
  content_path: string;
  created_at: string;
};

const jsonHeaders = { "Content-Type": "application/json" };

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || response.statusText);
  }
  return response.json() as Promise<T>;
}

export const api = {
  datasets: () => request<Dataset[]>("/api/datasets"),
  seedDataset: (name: string) => request<Dataset>(`/api/datasets/seed/${name}`, { method: "POST" }),
  uploadDataset: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Dataset>("/api/datasets/upload", { method: "POST", body: form });
  },
  preview: (id: number) => request<{ columns: string[]; rows: Record<string, unknown>[] }>(`/api/datasets/${id}/preview`),
  tasks: () => request<Task[]>("/api/tasks"),
  taskDetail: (id: number) => request<{ task: Task; steps: unknown[]; results: unknown[]; charts: Chart[]; reports: Report[] }>(`/api/tasks/${id}`),
  createTask: (datasetId: number, userGoal: string, templateId?: string) =>
    request<Task>("/api/tasks", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ dataset_id: datasetId, user_goal: userGoal, template_id: templateId })
    }),
  planTask: (id: number) => request<Task>(`/api/tasks/${id}/plan`, { method: "POST" }),
  executeTask: (id: number) => request<Task>(`/api/tasks/${id}/execute`, { method: "POST" }),
  charts: () => request<Chart[]>("/api/charts"),
  reports: () => request<Report[]>("/api/reports"),
  report: (id: number) => request<{ report: Report; content: string }>(`/api/reports/${id}`),
  audit: () => request<Array<Record<string, unknown>>>("/api/audit"),
  settings: () => request<Record<string, unknown>>("/api/settings/llm"),
  saveSettings: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/settings/llm", {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify(payload)
    }),
  testSettings: () => request<Record<string, unknown>>("/api/settings/llm/test", { method: "POST" })
};
