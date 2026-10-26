/* Review: one draft at a time on the table, with the editor's notes beside it and the decision
   in a fixed bar underneath. Keyboard: J/K move, P post now, S schedule, R reject, E edit. */
import * as React from "react";
import { AlertTriangle, ArrowUpRight, CalendarClock, Plus, RotateCcw, Send, Sparkles, Trash2, X } from "lucide-react";
import { useStore } from "@/lib/store";
import type { Draft, Status } from "@/lib/types";
import { cn, fmtInt, fmtPct, fmtWhen, timeAgo, toLocalInput } from "@/lib/utils";
import { Badge, Button, Groove, Input, Meter, Textarea } from "@/components/ui/primitives";
import { Empty, FORMAT_LABEL, PlatformMark, StatusBadge } from "@/components/common";
import { InstagramPreview, LinkedInPreview, ReplyPreview, XPreview } from "@/components/previews";

const FILTERS: { id: Status; label: string }[] = [
  { id: "pending", label: "Needs you" }, { id: "approved", label: "Scheduled" }, { id: "published", label: "Live" },
  { id: "failed", label: "Failed" }, { id: "rejected", label: "Rejected" },
];
const label = (k: string) => k.replaceAll("_", " ");
const SCORE_LABEL: Record<string, string> = {
  hook: "Opening", shareability: "Shareable", save_worthiness: "Worth saving", depth: "Depth", discussion: "Sparks replies",
  human_voice: "Human voice", niche_fit: "On niche", platform_fit: "Fits the platform",
};
const ACTION: Record<string, string> = {
  send: "get sent to friends", save: "get saved", comment: "start a comment thread", reply: "pull replies",
  bookmark: "get bookmarked", watch_time: "get watched twice", dwell: "keep people reading", profile_click: "send people to the profile",
};
const VERDICT_OK = new Set(["PASS", "STRONG", "READY"]);

function Note({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("grid gap-2.5 border-t border-rule pt-5", className)}>
      <h3 className="font-sans text-[13.5px] font-semibold tracking-normal text-muted">{title}</h3>
      {children}
    </section>
  );
}

function Notes({ d, editable, onUseHook }: { d: Draft; editable: boolean; onUseHook: (t: string) => void }) {
  const crit = d.critic || {};
  const q = crit.quality;
  const scores = Object.entries(crit.scores || {}).filter(([k]) => k !== "brand_safety").sort((a, b) => b[1] - a[1]);
  const hooks = d.content.hook_options || [];
  const checks = [
    q?.human && { name: "Sounds human", ok: q.human.verdict === "PASS", detail: `${q.human.score.toFixed(0)}/100, weakest on ${q.human.weakest.toLowerCase()}` },
    q?.hook && { name: "Opening line", ok: VERDICT_OK.has(q.hook.verdict), detail: `${q.hook.score.toFixed(0)}/100${q.hook.dealbreakers?.[0] ? `, ${q.hook.dealbreakers[0]}` : ""}` },
    q?.beats && { name: "Reel timing", ok: !q.beats.problems.length, detail: q.beats.problems[0] || `${q.beats.seconds.toFixed(0)}s, loops back to the start` },
    q?.caption && { name: "Caption before “more”", ok: VERDICT_OK.has(q.caption.verdict), detail: q.caption.fails[0] || q.caption.warns[0] || "lands whole" },
  ].filter(Boolean) as { name: string; ok: boolean; detail: string }[];

  return (
    <div className="grid content-start gap-5">
      {crit.viral_score != null && (
        <div className="grid gap-1">
          <div className="flex items-baseline gap-2">
            <span className="text-[48px] font-semibold leading-none tracking-[-0.04em]">{crit.viral_score}</span>
            <span className="text-[15px] text-muted">/ 10 viral potential</span>
          </div>
          {d.content.goal && <p className="text-[15px] leading-snug">Built to {ACTION[d.content.goal] || d.content.goal}{d.content.archetype ? `, as a ${label(d.content.archetype)} post` : ""}.</p>}
          {d.content.why_viral && <p className="text-[14px] leading-relaxed text-ink-2">{d.content.why_viral}</p>}
        </div>
      )}

      {checks.length > 0 && (
        <Note title="Checks before it can post">
          <ul className="grid gap-2">
            {checks.map((c) => (
              <li key={c.name} className="flex gap-2.5 text-[14px]">
                <span className={cn("mt-[3px] grid size-4 shrink-0 place-items-center rounded-full text-[10px] font-semibold", c.ok ? "bg-good text-on-mark" : "border border-ink text-ink")}>{c.ok ? "✓" : "!"}</span>
                <span><span className="font-medium">{c.name}</span><span className="text-muted">, {c.detail}</span></span>
              </li>
            ))}
          </ul>
          {!!crit.artefacts_stripped && <p className="text-[13px] text-muted">{crit.artefacts_stripped} AI-sounding bits were cleaned out automatically.</p>}
        </Note>
      )}

      {scores.length > 0 && (
        <Note title="How the editor scored it">
          <ul className="grid gap-2">
            {scores.map(([k, v]) => (
              <li key={k} className="grid grid-cols-[128px_1fr_26px] items-center gap-3 text-[13.5px]">
                <span className="text-ink-2">{SCORE_LABEL[k] || label(k)}</span>
                <Meter value={v} weak={v < 7} />
                <span className="num text-right">{v}</span>
              </li>
            ))}
          </ul>
          {crit.feedback && <p className="text-[14px] leading-relaxed text-ink-2">“{crit.feedback}”</p>}
          {crit.violations?.map((v) => <p key={v} className="flex gap-2 text-[13.5px]"><AlertTriangle className="mt-0.5 size-4 shrink-0 text-ink" aria-hidden="true" />{v}</p>)}
        </Note>
      )}

      {hooks.length > 0 && (
        <Note title={`Opening lines tried (${hooks.length})`}>
          <ol className="grid gap-3">
            {hooks.map((h, i) => (
              <li key={i} className="grid gap-1">
                <p className={cn("text-[14.5px] leading-snug", i === 0 && "font-semibold")}>{i === 0 && <Badge variant="strong" className="mr-2 align-[2px]">Using</Badge>}{h.text}</p>
                <div className="flex items-center gap-3 text-[12.5px] text-muted">
                  <span className="capitalize">{label(h.type)}</span>
                  <span className="num">{h.score?.toFixed(1)}</span>
                  {editable && i > 0 && <button type="button" onClick={() => onUseHook(h.text)} className="hit font-medium text-ink underline underline-offset-4 decoration-rule-2 hover:decoration-accent-2 cursor-pointer">Use this one</button>}
                </div>
              </li>
            ))}
          </ol>
        </Note>
      )}

      {(!!d.content.sources?.length || !!d.content.unverified?.length) && (
        <Note title="Where the facts come from">
          {d.content.sources?.slice(0, 5).map((s) => (
            <a key={s.url} href={s.url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-[14px] text-ink underline underline-offset-4 decoration-rule-2 hover:decoration-accent-2">
              <span className="truncate">{s.title || s.url}</span><ArrowUpRight className="size-3.5 shrink-0" />
            </a>
          ))}
          {!!d.content.unverified?.length && <p className="text-[14px]"><span className="font-semibold">Check first:</span> {d.content.unverified.join(", ")}</p>}
        </Note>
      )}

      {d.metrics && (
        <Note title="Results so far">
          <dl className="grid grid-cols-3 gap-y-3">
            {([["Reached", d.metrics.impressions], ["Saves", d.metrics.saves], ["Shares", d.metrics.shares], ["Likes", d.metrics.likes], ["Follows", d.metrics.follows]] as const).map(([k, v]) => (
              <div key={k}><dt className="text-[12.5px] text-muted">{k}</dt><dd className="num text-[20px]">{fmtInt(v)}</dd></div>
            ))}
            <div><dt className="text-[12.5px] text-muted">Engagement</dt><dd className="num text-[20px]">{fmtPct(d.metrics.engagement)}</dd></div>
          </dl>
        </Note>
      )}

      {d.trace.length > 0 && (
        <details className="group border-t border-rule pt-5">
          <summary className="cursor-pointer list-none text-[13.5px] font-semibold text-muted hover:text-ink">How the agents made it <span className="font-normal">({d.trace.length} steps)</span></summary>
          <ol className="mt-3 grid gap-1.5 text-[13px] text-ink-2">
            {d.trace.map((t, i) => <li key={i} className="grid grid-cols-[20px_1fr] gap-2"><span className="num text-muted">{i + 1}</span><span className="min-w-0 break-words">{t}</span></li>)}
          </ol>
        </details>
      )}
    </div>
  );
}

function Editor({ d, caption, setCaption, thread, setThread }: {
  d: Draft; caption: string; setCaption: (v: string) => void; thread: string[]; setThread: (v: string[]) => void;
}) {
  if (d.content.thread?.length) {
    return (
      <div className="grid gap-4">
        {thread.map((t, i) => {
          const len = [...t].length;
          return (
            <div key={i} className="grid gap-1.5">
              <div className="flex items-center justify-between text-[13px]">
                <label htmlFor={`post-${d.id}-${i}`} className="font-medium">Post {i + 1}</label>
                <span className={cn("num", len > 280 ? "text-bad" : "text-muted")}>{len} / 280</span>
              </div>
              <div className="flex gap-2">
                <Textarea id={`post-${d.id}-${i}`} value={t} className="min-h-20" onChange={(e) => setThread(thread.map((x, j) => (j === i ? e.target.value : x)))} />
                {thread.length > 1 && <Button variant="ghost" size="icon" aria-label={`Remove post ${i + 1}`} onClick={() => setThread(thread.filter((_, j) => j !== i))}><Trash2 /></Button>}
              </div>
            </div>
          );
        })}
        <Button variant="card" size="sm" className="justify-self-start" onClick={() => setThread([...thread, ""])}><Plus /> Add a post</Button>
      </div>
    );
  }
  return (
    <div className="grid gap-1.5">
      <div className="flex justify-between text-[13px]"><label htmlFor={`cap-${d.id}`} className="font-medium">{d.kind === "reply" ? "Reply" : "Caption"}</label><span className="num text-muted">{caption.length} characters</span></div>
      <Textarea id={`cap-${d.id}`} value={caption} onChange={(e) => setCaption(e.target.value)} className="min-h-[320px]" />
    </div>
  );
}

function Detail({ d }: { d: Draft }) {
  const { pageById, approve, reject, regenerate, retry, busy, overview, backend } = useStore();
  const page = pageById[d.page_id];
  const isThread = !!d.content.thread?.length;
  const [caption, setCaption] = React.useState(d.content.caption || "");
  const [thread, setThread] = React.useState<string[]>(d.content.thread || []);
  const [when, setWhen] = React.useState(toLocalInput(d.scheduled_at));
  const [editing, setEditing] = React.useState(false);
  React.useEffect(() => { setCaption(d.content.caption || ""); setThread(d.content.thread || []); setWhen(toLocalInput(d.scheduled_at)); setEditing(false); }, [d]);
  if (!page) return null;
  const working = busy[`d${d.id}`];
  const editable = d.status === "pending";
  const body = { caption: isThread ? undefined : caption, thread: isThread ? thread : undefined };
  const postNow = () => approve(d, { ...body, publish_now: true });
  const schedule = () => approve(d, { ...body, publish_now: false, scheduled_at: when ? new Date(when).toISOString() : undefined });
  const useHook = (text: string) => {
    if (isThread) setThread([text, ...thread.slice(1)]);
    else setCaption((c) => { const l = c.split("\n"); l[0] = text; return l.join("\n"); });
  };
  const modeNote = backend?.demo ? "Sample data: nothing really goes out." : overview?.mode !== "live" ? "Dry run: posting is simulated until MODE=live." : "";

  React.useEffect(() => {
    if (!editable) return;
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (el.closest("input, textarea, [contenteditable=true]") || e.metaKey || e.ctrlKey || e.altKey) return;
      const k = e.key.toLowerCase();
      if (k === "p") { e.preventDefault(); postNow(); }
      else if (k === "s" && d.kind === "post") { e.preventDefault(); schedule(); }
      else if (k === "r") { e.preventDefault(); reject(d); }
      else if (k === "e") { e.preventDefault(); setEditing((v) => !v); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const preview = d.kind === "reply" ? <ReplyPreview d={d} page={page} reply={caption} />
    : d.platform === "instagram" ? <InstagramPreview d={d} page={page} caption={caption} />
    : d.platform === "linkedin" ? <LinkedInPreview d={d} page={page} caption={caption} />
    : <XPreview d={d} page={page} posts={isThread ? thread : [caption]} />;

  return (
    <div className="grid gap-10 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="grid min-w-0 content-start gap-6">
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center gap-2 text-[14px] text-muted">
            <PlatformMark platform={d.platform} size="sm" /><span className="font-medium text-ink">{page.handle}</span>
            <span>{d.kind === "reply" ? "reply" : FORMAT_LABEL[d.format].toLowerCase()}</span>
            {d.pillar && <span>in {d.pillar}</span>}
            <StatusBadge status={d.status} />
          </div>
          <h1 className="max-w-[32ch] text-[clamp(24px,2.6vw,32px)] leading-[1.1]">{d.kind === "reply" ? "Reply to a comment" : d.topic}</h1>
          {d.angle && d.kind === "post" && <p className="max-w-[60ch] text-[16px] text-ink-2">{d.angle}</p>}
          {editable && modeNote && <p className="text-[13px] text-muted">{modeNote}</p>}
        </div>

        {d.error && <div className="flex gap-2.5 rounded-card border border-bad p-4 text-[14px] text-bad"><AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />{d.error}</div>}

        <div className="flex items-center gap-5 border-b border-rule">
          {[["preview", "How it will look"], ["edit", editable ? "Edit the words" : "The words"]].map(([k, l]) => (
            <button key={k} type="button" onClick={() => setEditing(k === "edit")} aria-pressed={editing === (k === "edit")}
              className={cn("-mb-px h-10 border-b-2 text-[14px] font-medium cursor-pointer", editing === (k === "edit") ? "border-ink text-ink" : "border-transparent text-muted hover:text-ink")}>{l}</button>
          ))}
          {editable && <span className="ml-auto hidden text-[12.5px] text-muted sm:inline"><kbd>E</kbd> to switch</span>}
        </div>

        <div className="min-h-[200px]">
          {editing ? (
            <div className="grid max-w-[720px] gap-5">
              {editable ? <Editor d={d} caption={caption} setCaption={setCaption} thread={thread} setThread={setThread} />
                : <p className="whitespace-pre-line text-[15.5px] leading-relaxed">{isThread ? thread.join("\n\n") : caption}</p>}
              {!!d.content.hashtags?.length && <p className="text-[14px] text-ink-2">{d.content.hashtags.join("  ")}</p>}
              {!!d.content.slides?.length && (
                <ol className="grid gap-2.5">
                  {d.content.slides.map((s, i) => (
                    <li key={i} className="grid grid-cols-[28px_1fr] gap-2 text-[14.5px]">
                      <span className="num text-muted">{i + 1}</span>
                      <span><span className="font-semibold">{s.stat ? `${s.stat} ` : ""}{s.title}</span>{" "}
                        <span className="text-ink-2">{s.body}{s.items?.length ? ` ${s.items.join("; ")}.` : ""}{s.left ? ` ${s.left} vs ${s.right}.` : ""}</span>
                        <span className="ml-1.5 text-[12.5px] text-muted">({s.layout || "text"})</span></span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          ) : <div className="py-2">{preview}</div>}
        </div>

        {/* the decision */}
        <div className="sticky bottom-4 z-10">
          <div className="stock flex flex-wrap items-center gap-2 rounded-card p-2">
            {editable ? (
              <>
                <Button disabled={working} onClick={postNow} className="pr-3">
                  <Send /> {d.kind === "reply" ? "Send reply now" : "Post now"} <kbd className="!border-board-type/40 !bg-transparent !text-board-type">P</kbd>
                </Button>
                {d.kind === "post" && (
                  <div className="flex items-center gap-1 rounded-stock bg-paper-2 p-0.5">
                    <Button variant="ghost" disabled={working} onClick={schedule} className="pr-2"><CalendarClock /> Schedule <kbd>S</kbd></Button>
                    <Input type="datetime-local" aria-label="Post at" value={when} onChange={(e) => setWhen(e.target.value)} className="h-8 w-[186px] px-2.5 text-[13px]" />
                  </div>
                )}
                <span className="ml-auto flex items-center gap-1">
                  {d.kind === "post" && <Button variant="ghost" size="icon" disabled={working} onClick={() => regenerate(d)} aria-label="Rewrite with a new angle" title="Rewrite with a new angle"><Sparkles /></Button>}
                  <Button variant="destructive" disabled={working} onClick={() => reject(d)} aria-label="Reject" title="Reject (R)"><X /> <span className="hidden 2xl:inline">Reject</span></Button>
                </span>
              </>
            ) : d.status === "failed" ? (
              <><Button disabled={working} onClick={() => retry(d)}><RotateCcw /> Try posting again</Button><span className="text-[13.5px] text-muted">Fix the cause above first, usually an expired token.</span></>
            ) : d.status === "published" ? (
              <>{d.content.permalink && <Button asChild><a href={d.content.permalink} target="_blank" rel="noreferrer"><ArrowUpRight /> Open the live post</a></Button>}
                <span className="px-2 text-[14px] text-muted">Went live {fmtWhen(d.scheduled_at)}</span></>
            ) : d.status === "approved" ? (
              <span className="px-2 py-2 text-[14px]">Scheduled for <span className="font-semibold">{fmtWhen(d.scheduled_at)}</span> ({timeAgo(d.scheduled_at)}). It posts automatically.</span>
            ) : d.status === "publishing" ? <span className="px-2 py-2 text-[14px]">Posting to {d.platform} now…</span>
              : <span className="px-2 py-2 text-[14px] text-muted">Rejected.</span>}
          </div>
        </div>
      </div>

      <aside className="min-w-0"><Notes d={d} editable={editable} onUseHook={useHook} /></aside>
    </div>
  );
}

export function QueueView({ selected, setSelected }: { selected: number | null; setSelected: (id: number | null) => void }) {
  const { drafts, pages, overview } = useStore();
  const [status, setStatus] = React.useState<Status>("pending");
  const [pageFilter, setPageFilter] = React.useState("all");

  React.useEffect(() => {
    if (selected) { const d = drafts.find((x) => x.id === selected); if (d && d.status !== status && d.status !== "publishing") setStatus(d.status); }
  }, [selected]); // eslint-disable-line react-hooks/exhaustive-deps

  const list = drafts.filter((d) => d.status === status && (pageFilter === "all" || d.page_id === pageFilter))
    .sort((a, b) => (a.kind === b.kind ? (a.scheduled_at || a.created_at).localeCompare(b.scheduled_at || b.created_at) : a.kind === "reply" ? 1 : -1));
  const current = drafts.find((d) => d.id === selected) || null;

  React.useEffect(() => {
    const keep = current && (current.status === status || current.status === "publishing" || current.status === "published");
    if (window.matchMedia("(min-width: 1024px)").matches && !keep && list[0]) setSelected(list[0].id);
  }, [status, pageFilter, drafts.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // after acting on a draft, move to the next one automatically
  const prevStatus = React.useRef(current?.status);
  React.useEffect(() => {
    if (current && prevStatus.current === "pending" && current.status !== "pending" && status === "pending") {
      const next = list.find((d) => d.id !== current.id);
      if (next) setSelected(next.id);
    }
    prevStatus.current = current?.status;
  }, [current?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest("input, textarea") || e.metaKey || e.ctrlKey) return;
      const k = e.key.toLowerCase();
      if (k !== "j" && k !== "k") return;
      const i = list.findIndex((d) => d.id === selected);
      const n = list[Math.min(list.length - 1, Math.max(0, i + (k === "j" ? 1 : -1)))];
      if (n) { e.preventDefault(); setSelected(n.id); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="grid gap-8 pt-6">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-rule">
        <div className="-mb-px flex items-center gap-6 overflow-x-auto scrollbar-thin" role="tablist" aria-label="Drafts by status">
          {FILTERS.map((f) => {
            const n = overview?.counts[f.id] ?? 0;
            return (
              <button key={f.id} type="button" role="tab" onClick={() => { setStatus(f.id); setSelected(null); }} aria-selected={status === f.id}
                className={cn("flex h-11 shrink-0 items-center gap-2 border-b-2 text-[15px] font-medium cursor-pointer whitespace-nowrap",
                  status === f.id ? "border-ink text-ink" : "border-transparent text-muted hover:text-ink")}>
                {f.label}<span className={cn("num text-[13px]", f.id === "pending" && n ? "text-ink" : "text-muted")}>{n}</span>
              </button>
            );
          })}
        </div>
        <div className="pb-2">
          <Groove label="Filter by page" value={pageFilter} onChange={setPageFilter}
            options={[{ value: "all", label: "All pages" }, ...pages.map((p) => ({ value: p.id, aria: p.handle, label: <PlatformMark platform={p.platform} size="sm" /> }))]} />
        </div>
      </div>

      <div className="grid gap-10 lg:grid-cols-[260px_minmax(0,1fr)]">
        <div className={cn("grid content-start gap-1", current && "hidden lg:grid")}>
          {list.length === 0 && <Empty title={status === "pending" ? "You’re all caught up" : `Nothing ${FILTERS.find((f) => f.id === status)?.label.toLowerCase()}`}
            hint={status === "pending" ? "New drafts arrive at 6am and 2pm, or write one with New post." : undefined} />}
          {list.map((d) => (
            <button key={d.id} type="button" onClick={() => setSelected(d.id)} aria-current={selected === d.id}
              className={cn("grid grid-cols-[auto_1fr] gap-3 rounded-card p-3 text-left cursor-pointer",
                selected === d.id ? "stock" : "hover:bg-paper-2")}>
              <PlatformMark platform={d.platform} size="sm" className="mt-0.5" />
              <span className="grid min-w-0 gap-0.5">
                <span className="text-[14.5px] font-medium leading-snug">{d.kind === "reply" ? d.reply_context : d.topic}</span>
                <span className="text-[12.5px] text-muted">
                  {d.kind === "reply" ? "Reply" : FORMAT_LABEL[d.format]}
                  {d.critic?.viral_score ? `, ${d.critic.viral_score}` : ""}
                  {d.scheduled_at && status !== "pending" ? `, ${fmtWhen(d.scheduled_at)}` : ""}
                </span>
              </span>
            </button>
          ))}
          {list.length > 1 && <p className="hidden px-3 pt-3 text-[13px] text-muted lg:block"><kbd>J</kbd> <kbd>K</kbd> to move through the list</p>}
        </div>
        <div className={cn("min-w-0", !current && "hidden lg:block")}>
          {current ? (
            <>
              <button type="button" onClick={() => setSelected(null)} className="hit mb-4 text-[14px] font-medium text-ink underline underline-offset-4 decoration-rule-2 lg:hidden cursor-pointer">Back to the list</button>
              <Detail d={current} />
            </>
          ) : <Empty title="Pick a draft" hint="Choose one on the left to see exactly how it will look." />}
        </div>
      </div>
    </div>
  );
}

