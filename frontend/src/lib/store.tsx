import * as React from "react";
import { toast } from "sonner";
import { connect, type ApproveBody, type Backend } from "./backend";
import type { Draft, Overview, Page } from "./types";

interface Store {
  ready: boolean;
  error: string | null;
  backend: Backend | null;
  pages: Page[];
  pageById: Record<string, Page>;
  overview: Overview | null;
  drafts: Draft[];
  busy: Record<string, boolean>;
  refresh(): Promise<void>;
  approve(d: Draft, body: ApproveBody): Promise<void>;
  reject(d: Draft): Promise<void>;
  retry(d: Draft): Promise<void>;
  regenerate(d: Draft): Promise<void>;
  generate(pageId: string, format?: string): Promise<void>;
  runJob(job: "plan" | "publish" | "engage" | "metrics" | "digest"): Promise<void>;
}

const Ctx = React.createContext<Store | null>(null);
export const useStore = () => {
  const s = React.useContext(Ctx);
  if (!s) throw new Error("useStore outside provider");
  return s;
};

const JOB_LABEL = { plan: "Filling the queue", publish: "Publishing due posts", engage: "Scanning comments", metrics: "Pulling metrics", digest: "Sending today's Slack report" };

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const [backend, setBackend] = React.useState<Backend | null>(null);
  const [pages, setPages] = React.useState<Page[]>([]);
  const [overview, setOverview] = React.useState<Overview | null>(null);
  const [drafts, setDrafts] = React.useState<Draft[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<Record<string, boolean>>({});

  const load = React.useCallback(async (b: Backend) => {
    const [p, o, d] = await Promise.all([b.pages(), b.overview(), b.drafts()]);
    setPages(p); setOverview(o); setDrafts(d); setError(null);
  }, []);

  React.useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    connect().then(async (b) => {
      setBackend(b);
      await load(b);
      if (!b.demo) timer = setInterval(() => load(b).catch(() => {}), 15000);
    }).catch((e) => setError(String(e)));
    return () => clearInterval(timer);
  }, [load]);

  const act = React.useCallback(async (key: string, fn: () => Promise<unknown>, ok: string) => {
    if (!backend) return;
    setBusy((b) => ({ ...b, [key]: true }));
    try {
      await fn();
      await load(backend);
      toast.success(ok);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy((b) => ({ ...b, [key]: false }));
    }
  }, [backend, load]);

  const pageById = React.useMemo(() => Object.fromEntries(pages.map((p) => [p.id, p])), [pages]);

  const store: Store = {
    ready: !!backend && !!overview, error, backend, pages, pageById, overview, drafts, busy,
    refresh: async () => { if (backend) await load(backend); },
    approve: (d, body) => act(`d${d.id}`, async () => {
      await backend!.approve(d.id, body);
      if (!backend!.demo && body.publish_now !== false) setTimeout(() => load(backend!).catch(() => {}), 4000);
    }, body.publish_now === false ? "Approved and scheduled." : backend?.demo ? "Posted (sample data: nothing really went out)." :
      d.kind === "reply" ? "Reply approved and sending now." : "Approved. Posting now; Slack will confirm."),
    reject: (d) => act(`d${d.id}`, () => backend!.reject(d.id), "Draft rejected."),
    retry: (d) => act(`d${d.id}`, () => backend!.retry(d.id), "Queued to retry."),
    regenerate: (d) => act(`d${d.id}`, () => backend!.regenerate(d.id), "Agents are writing a new version."),
    generate: (pageId, format) => act(`gen${pageId}`, () => backend!.generate(pageId, format),
      backend?.demo ? "New draft added to the queue." : "Agents started. The draft appears in the queue in about a minute."),
    runJob: (job) => act(`job${job}`, () => backend!.runJob(job), `${JOB_LABEL[job]}: started.`),
  };
  return <Ctx.Provider value={store}>{children}</Ctx.Provider>;
}
