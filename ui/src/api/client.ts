// API base: empty in dev (vite proxy), injected by Tauri in production.
export const API_BASE = window.__MDTX_API_BASE__ ?? "";

export interface AppConfig {
  target_languages: string[];
  provider: {
    name: string;
    base_url: string;
    api_key: string;
    api_key_env: string;
    model: string;
    temperature: number;
    max_tokens: number;
    structured_outputs: string;
    max_retries: number;
  };
  pipeline: {
    mode: string;
    enable_review: boolean;
    enable_format_guard: boolean;
    fail_on_validation_error: boolean;
  };
  segmentation: { max_bundle_chars: number; max_bundle_segments: number };
  input: { file_pattern: string };
  style: {
    tone: string;
    audience: string;
    preserve_terms: string[];
    instructions: string[];
  };
  output: { directory: string; file_suffix_template: string; write_report: boolean };
  execution: { max_parallel_translations: number };
  memory: { enabled: boolean; path: string };
}

export interface JobParams {
  paths: string[];
  target_langs: string[];
  output_dir?: string | null;
  mode?: string | null;
  tone?: string | null;
  model?: string | null;
  evaluate?: boolean;
  resume?: boolean;
}

export interface JobSummary {
  id: string;
  status: string;
  created_at: number;
  finished_at: number | null;
  error: string | null;
  pairs: string[];
  usage: { prompt: number; completion: number; total: number; cached: number; calls: number };
  result_count: number;
}

export interface SegmentPair {
  segment_id: string;
  context_path: string[];
  source: string;
  translated: string;
  confidence: number;
}

export interface JobResult {
  input_path: string;
  output_path: string | null;
  target_lang: string;
  translated_markdown: string;
  validation: { passed: boolean; errors: string[]; warnings: string[] };
  usage: { prompt: number; completion: number; total: number; cached: number; calls: number };
  segments: SegmentPair[];
  judge: {
    target_lang?: string;
    overall?: number;
    scores?: Record<string, number>;
    comments?: string[];
    error?: string;
  } | null;
}

export interface JobDetail extends JobSummary {
  results: JobResult[];
}

export interface FsEntry {
  name: string;
  path: string;
  is_dir: boolean;
  is_markdown: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      /* keep status code */
    }
    throw new Error(String(detail));
  }
  return (await response.json()) as T;
}

export const api = {
  getConfig: () => request<{ config: AppConfig; config_path: string }>("/api/config"),
  patchConfig: (patch: Partial<AppConfig>) =>
    request<{ config: AppConfig; config_path: string }>("/api/config", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }),
  listDir: (path: string) => {
    const query = new URLSearchParams({ path }).toString();
    return request<{ path: string; parent: string | null; entries: FsEntry[] }>(`/api/fs?${query}`);
  },
  createJob: (params: JobParams) =>
    request<JobSummary>("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    }),
  listJobs: () => request<JobSummary[]>("/api/jobs"),
  getJob: (id: string) => request<JobDetail>(`/api/jobs/${id}`),
  cancelJob: (id: string) =>
    request<{ id: string; cancel_requested: boolean }>(`/api/jobs/${id}/cancel`, { method: "POST" }),
  memoryStats: () => request<{ hits: number; misses: number; entries: number }>("/api/memory/stats"),
  clearMemory: () => request<{ removed: number }>("/api/memory", { method: "DELETE" }),
  listCheckpoints: () =>
    request<{ file: string; fingerprint: string; bundles: number }[]>("/api/checkpoints"),
};

export function jobEventsUrl(id: string, last = 0): string {
  return `${API_BASE}/api/jobs/${id}/events?last=${last}`;
}
