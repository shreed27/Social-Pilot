/* In-memory backend over sample data, so the dashboard is fully clickable without the API. */
import raw from "@/demo-data.json";
import type { Backend } from "./backend";
import type { Analytics, Draft, Overview, Page, Status } from "./types";

const wait = (ms = 250) => new Promise((r) => setTimeout(r, ms));
const clone = <T,>(x: T): T => JSON.parse(JSON.stringify(x));

export function createDemoBackend(): Backend {
  const pages = raw.pages as unknown as Page[];
  const drafts = clone(raw.drafts) as unknown as Draft[];
  const base = raw.overview as unknown as Overview;
  const analytics = raw.analytics as unknown as Record<string, Analytics>;
  let nextId = Math.max(...drafts.map((d) => d.id)) + 1;

  const touch = (d: Draft, status: Status) => { d.status = status; d.updated_at = new Date().toISOString(); };
  const find = (id: number) => { const d = drafts.find((x) => x.id === id); if (!d) throw new Error("Draft not found"); return d; };

  function overview(): Overview {
    const counts = { pending: 0, approved: 0, publishing: 0, published: 0, failed: 0, rejected: 0 } as Record<Status, number>;
    drafts.forEach((d) => counts[d.status]++);
    const pagesStats = clone(base.pages);
    Object.keys(pagesStats).forEach((pid) => {
      pagesStats[pid].pending = drafts.filter((d) => d.page_id === pid && d.status === "pending").length;
    });
    const activity = [...drafts].sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 12)
      .map((d) => ({ id: d.id, page_id: d.page_id, platform: d.platform, kind: d.kind, format: d.format, topic: d.topic, status: d.status, at: d.updated_at }));
    const upcoming = drafts.filter((d) => d.status === "approved" && d.scheduled_at)
      .sort((a, b) => a.scheduled_at!.localeCompare(b.scheduled_at!)).slice(0, 6);
    return { ...base, counts, pages: pagesStats, activity, upcoming: clone(upcoming) };
  }

  return {
    demo: true,
    pages: async () => clone(pages),
    overview: async () => overview(),
    drafts: async () => clone(drafts),
    analytics: async (id) => clone(analytics[id]),
    approve: async (id, body) => {
      await wait();
      const d = find(id);
      if (body.thread?.length) { d.content.thread = body.thread; d.content.caption = body.thread[0]; }
      else if (body.caption != null) d.content.caption = body.caption;
      if (body.publish_now !== false) { d.scheduled_at = new Date().toISOString(); touch(d, "published"); return; }
      if (body.scheduled_at) d.scheduled_at = new Date(body.scheduled_at).toISOString();
      touch(d, "approved");
    },
    reject: async (id) => { await wait(); touch(find(id), "rejected"); },
    retry: async (id) => { await wait(); const d = find(id); d.error = null; touch(d, "approved"); },
    regenerate: async (id) => {
      await wait(500);
      const d = find(id); touch(d, "rejected");
      const fresh = clone(d);
      Object.assign(fresh, { id: nextId++, status: "pending", topic: `${d.topic} (new angle)`, created_at: new Date().toISOString(), updated_at: new Date().toISOString() });
      drafts.unshift(fresh);
    },
    generate: async (pageId, format) => {
      await wait(900);
      const tpl = drafts.find((d) => d.page_id === pageId && d.status === "pending" && d.kind === "post" && (!format || d.format === format))
        ?? drafts.find((d) => d.page_id === pageId && d.kind === "post" && d.content.caption)!;
      const fresh = clone(tpl);
      Object.assign(fresh, { id: nextId++, status: "pending", topic: `${tpl.topic} — variant`, created_at: new Date().toISOString(), updated_at: new Date().toISOString(), metrics: null });
      drafts.unshift(fresh);
    },
    runJob: async (job) => {
      await wait(600);
      if (job === "publish") {
        drafts.filter((d) => d.status === "approved" && d.scheduled_at && new Date(d.scheduled_at) <= new Date())
          .forEach((d) => touch(d, "published"));
      }
    },
  };
}
