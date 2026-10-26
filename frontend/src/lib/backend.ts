/* One interface, two implementations: the live FastAPI backend, and an in-memory demo
   used when the API isn't reachable (e.g. the published preview). */
import type { Analytics, Draft, Overview, Page } from "./types";


export interface ApproveBody { caption?: string; thread?: string[]; scheduled_at?: string; publish_now?: boolean }
export interface Backend {
  demo: boolean;
  pages(): Promise<Page[]>;
  overview(): Promise<Overview>;
  drafts(): Promise<Draft[]>;
  analytics(pageId: string): Promise<Analytics>;
  approve(id: number, body: ApproveBody): Promise<void>;
  reject(id: number): Promise<void>;
  retry(id: number): Promise<void>;
  regenerate(id: number): Promise<void>;
  generate(pageId: string, format?: string): Promise<void>;
  runJob(job: "plan" | "publish" | "engage" | "metrics" | "digest"): Promise<void>;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try { msg = (await r.json()).detail || msg; } catch { /* keep status text */ }
    throw new Error(msg);
  }
  return r.json() as Promise<T>;
}

const live: Backend = {
  demo: false,
  pages: () => call("/api/pages"),
  overview: () => call("/api/overview"),
  drafts: () => call("/api/drafts"),
  analytics: (id) => call(`/api/analytics/${id}`),
  approve: (id, body) => call(`/api/drafts/${id}/approve`, { method: "POST", body: JSON.stringify(body) }),
  reject: (id) => call(`/api/drafts/${id}/reject`, { method: "POST" }),
  retry: (id) => call(`/api/drafts/${id}/retry`, { method: "POST" }),
  regenerate: (id) => call(`/api/drafts/${id}/regenerate`, { method: "POST" }),
  generate: (page_id, format) => call("/api/generate", { method: "POST", body: JSON.stringify({ page_id, format: format || null }) }),
  runJob: (job) => call(`/api/jobs/${job}`, { method: "POST" }),
};

export async function connect(): Promise<Backend> {
  if (!__DEMO_ONLY__) {
    try {
      const r = await fetch("/api/overview", { credentials: "include" });
      if (r.ok && (r.headers.get("content-type") || "").includes("json")) return live;
    } catch { /* fall through to demo */ }
  }
  const { createDemoBackend } = await import("./demo");
  return createDemoBackend();
}
