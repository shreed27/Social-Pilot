import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { useStore } from "@/lib/store";
import { platformColor, useThemeColors } from "@/lib/theme";
import type { Draft, Platform } from "@/lib/types";
import { cn, fmtCompact, fmtInt, fmtPct, timeAgo } from "@/lib/utils";
import { Button } from "@/components/ui/primitives";
import { Delta, FORMAT_LABEL, LiveStamp, PLATFORM, PlatformMark } from "@/components/common";
import type { View } from "@/components/shell";

export function ChartTooltip({ active, payload, label, valueFmt = fmtInt, labelFmt }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-input bg-board px-3 py-2 text-[12.5px] text-board-type">
      <div className="mb-1">{labelFmt ? labelFmt(label) : label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="size-2 rounded-full" style={{ background: p.color || p.fill }} />
          <span className="flex-1">{p.name}</span><span className="num">{valueFmt(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

const isToday = (iso?: string | null) => !!iso && new Date(iso).toDateString() === new Date().toDateString();
const clock = (iso: string) => new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });

/* A proof: the draft as it will look, on cotton stock. */
export function Proof({ d, onOpen, className }: { d: Draft; onOpen: () => void; className?: string }) {
  const img = d.media.find((m) => m.type !== "mp4" && m.type !== "pdf");
  const isReel = d.media.some((m) => m.type === "mp4");
  const text = d.kind === "reply" ? d.content.caption : (d.content.thread?.[0] || d.content.caption || d.topic);
  return (
    <button type="button" onClick={onOpen} className={cn("stock flex w-[220px] shrink-0 flex-col overflow-hidden rounded-card text-left cursor-pointer", className)}>
      <div className="relative aspect-[4/5] w-full overflow-hidden border-b border-rule">
        {img ? <img src={img.url} alt="" width={220} height={275} className="size-full object-cover" />
          : isReel ? <div className="grid size-full place-items-center bg-board px-5 text-center text-[18px] font-semibold leading-tight text-board-type">{d.content.reel_script?.[0]?.text}</div>
          : <p className="h-full overflow-hidden px-4 pb-4 pt-12 text-[14px] leading-snug whitespace-pre-line [mask-image:linear-gradient(to_bottom,black_80%,transparent)]">{d.kind === "reply" && <span className="mb-2 block text-muted">{d.reply_context}</span>}{text}</p>}
        <PlatformMark platform={d.platform} size="sm" className="absolute left-3 top-3" />
      </div>
      <div className="grid flex-1 content-start gap-1 p-3">
        <span className="text-[14px] font-medium leading-snug">{d.kind === "reply" ? "Reply to a comment" : d.topic}</span>
        <span className="text-[13px] text-muted">{d.kind === "reply" ? "Ready to send" : FORMAT_LABEL[d.format]}{d.critic?.viral_score ? `, scores ${d.critic.viral_score}` : ""}</span>
      </div>
    </button>
  );
}

function Spark({ data, color, label }: { data: number[]; color: string; label: string }) {
  return (
    <div className="h-8 w-28" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data.map((v, i) => ({ i, v }))} margin={{ top: 3, right: 2, bottom: 3, left: 2 }}>
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.75} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function OverviewView({ setView, openDraft }: { setView: (v: View) => void; openDraft: (id: number) => void }) {
  const { overview, drafts, pages } = useStore();
  const c = useThemeColors();
  if (!overview) return null;
  const series = overview.followers_series;
  const last = series[series.length - 1], prev = series[series.length - 2];
  const gainedToday = pages.reduce((s, p) => s + (Number(last?.[p.id] || 0) - Number(prev?.[p.id] || 0)), 0);
  const liveToday = drafts.filter((d) => d.status === "published" && isToday(d.updated_at));
  const pending = drafts.filter((d) => d.status === "pending");
  const posts = pending.filter((d) => d.kind === "post").length, replies = pending.length - posts;
  const now = new Date();
  const hour = now.getHours();
  const greet = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const waiting = `${posts ? `${posts} draft${posts === 1 ? "" : "s"}` : ""}${posts && replies ? " and " : ""}${replies ? `${replies} repl${replies === 1 ? "y" : "ies"}` : ""}`;

  const show = drafts.filter((d) => d.kind === "post" && d.scheduled_at && ["approved", "published", "pending", "failed", "publishing"].includes(d.status))
    .filter((d) => { const t = new Date(d.scheduled_at!).getTime(); return t > Date.now() - 12 * 3600e3 && t < Date.now() + 24 * 3600e3; })
    .sort((a, b) => a.scheduled_at!.localeCompare(b.scheduled_at!));

  const working = [...overview.by_format].sort((a, b) => b.avg_engagement - a.avg_engagement).slice(0, 3);
  const th = "pb-2 pr-6 text-left text-[13px] font-medium text-muted whitespace-nowrap";

  return (
    <div className="grid gap-16">
      <section className="grid gap-4">
        <p className="text-[14px] text-muted"><time dateTime={now.toISOString().slice(0, 10)}>{greet}. {now.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}.</time></p>
        <h1 className="max-w-[30ch] text-[clamp(28px,3.4vw,40px)] leading-[1.08]">
          {liveToday.length ? `${liveToday.length} post${liveToday.length === 1 ? "" : "s"} went live today` : "Nothing has gone live yet today"}
          {gainedToday > 0 ? `, and your pages picked up ${fmtInt(gainedToday)} followers.` : "."}
        </h1>
        <p className="text-[17px] text-ink-2">{pending.length ? `${waiting} ${pending.length === 1 ? "is" : "are"} waiting for your approval.` : "Nothing is waiting on you."}</p>
        <div className="mt-2 flex flex-wrap gap-3">
          {pending.length > 0 && <Button onClick={() => setView("queue")}>Review {pending.length} waiting</Button>}
          <Button variant="card" onClick={() => setView("calendar")}>See the week</Button>
        </div>
      </section>

      {pending.length > 0 && (
        <section className="grid gap-5" aria-labelledby="waiting-h">
          <div className="flex items-baseline justify-between gap-4">
            <h2 id="waiting-h" className="text-[22px]">On your desk</h2>
            <button type="button" onClick={() => setView("queue")} className="hit text-[14px] font-medium text-ink underline decoration-rule-2 underline-offset-4 hover:decoration-accent-2 cursor-pointer">Review all {pending.length}</button>
          </div>
          <div className="-mx-4 flex gap-6 overflow-x-auto px-4 pb-6 pt-1 sm:-mx-6 sm:px-6 scrollbar-thin">
            {pending.slice(0, 8).map((d) => <Proof key={d.id} d={d} onOpen={() => openDraft(d.id)} />)}
          </div>
        </section>
      )}

      <section className="grid gap-4" aria-labelledby="pages-h">
        <h2 id="pages-h" className="text-[22px]">Your pages</h2>
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full min-w-[760px] border-collapse">
            <thead><tr className="border-b border-ink">
              <th className={cn(th, "sticky left-0 z-[1] bg-desk")}>Page</th><th className={cn(th, "text-right")}>Followers</th><th className={cn(th, "text-right")}>This week</th>
              <th className={cn(th, "text-right")}>This month</th><th className={th}>30 days</th><th className={th}>Next post</th>
            </tr></thead>
            <tbody>
              {pages.map((p) => {
                const s = overview.pages[p.id];
                const nextUp = drafts.filter((d) => d.page_id === p.id && d.status === "approved" && d.scheduled_at)
                  .sort((a, b) => a.scheduled_at!.localeCompare(b.scheduled_at!))[0];
                return (
                  <tr key={p.id} className="border-b border-rule align-middle">
                    <td className="sticky left-0 z-[1] bg-desk py-3.5 pr-6"><span className="flex items-center gap-2.5"><PlatformMark platform={p.platform} /><span className="font-medium">{p.handle}</span></span></td>
                    <td className="num py-3.5 pr-6 text-right text-[20px]">{fmtInt(s?.followers)}</td>
                    <td className="py-3.5 pr-6 text-right"><Delta value={s?.growth_7d ?? 0} /></td>
                    <td className="py-3.5 pr-6 text-right"><Delta value={s?.growth_30d ?? 0} /></td>
                    <td className="py-3.5 pr-6"><Spark data={series.map((r) => Number(r[p.id] || 0))} color={c.ink} label={`${p.handle} followers over 30 days`} /></td>
                    <td className="max-w-[34ch] py-3.5 text-[14px] text-ink-2">
                      {nextUp ? <><span className="text-ink">{FORMAT_LABEL[nextUp.format]}, {timeAgo(nextUp.scheduled_at)}</span><span className="block truncate text-muted">{nextUp.topic}</span></> : <span className="text-muted">Nothing scheduled</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="grid content-start gap-4">
          <h2 className="text-[22px]">Run of show</h2>
          {show.length === 0 ? <p className="text-[15px] text-muted">Nothing posted or scheduled in the last 12 hours or the next 24.</p> : (
            <ol className="grid border-t border-ink">
              {show.map((d) => {
                const done = d.status === "published";
                return (
                  <li key={d.id} className="grid grid-cols-[84px_minmax(0,1fr)_auto] items-start gap-3 border-b border-rule py-3">
                    <span className={cn("num pt-0.5 text-[14px]", !done && "text-muted")}>{clock(d.scheduled_at!)}</span>
                    <button type="button" onClick={() => openDraft(d.id)} className="grid min-w-0 gap-0.5 text-left cursor-pointer group">
                      <span className="flex min-w-0 items-center gap-2 text-[15px] font-medium group-hover:underline underline-offset-4">
                        <PlatformMark platform={d.platform} size="sm" /><span className="truncate">{d.topic}</span>
                      </span>
                      <span className="text-[13px] text-muted">
                        {FORMAT_LABEL[d.format]}{done && d.metrics ? `, ${fmtCompact(d.metrics.impressions)} reached so far` : ""}
                      </span>
                    </button>
                    <span className="pt-0.5 text-[13px]">
                      {done ? <LiveStamp /> : d.status === "pending" ? <span className="font-medium text-ink">Needs you</span> : d.status === "failed" ? <span className="text-bad">Failed</span> : <span className="text-muted">Scheduled</span>}
                    </span>
                  </li>
                );
              })}
            </ol>
          )}
        </div>

        <div className="grid content-start gap-4">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="text-[22px]">Followers, last 30 days</h2>
            <div className="flex gap-4 text-[13.5px] text-muted">
              {pages.map((p) => <span key={p.id} className="flex items-center gap-1.5"><span aria-hidden="true" className="h-0.5 w-4" style={{ background: platformColor(c, p.platform) }} />{PLATFORM[p.platform].label}</span>)}
            </div>
          </div>
          <div className="h-[280px] border-t border-ink pt-4" role="img" aria-label="Followers for each page over the last 30 days">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series} margin={{ left: 0, right: 12, top: 10, bottom: 0 }}>
                <CartesianGrid stroke={c.rule} vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fill: c.muted, fontSize: 12 }} minTickGap={40}
                  tickFormatter={(d) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" })} />
                <YAxis tickLine={false} axisLine={false} tick={{ fill: c.muted, fontSize: 12 }} width={44} tickFormatter={fmtCompact} />
                <RTooltip content={<ChartTooltip labelFmt={(d: string) => new Date(d).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" })} />} cursor={{ stroke: c["rule-2"] }} />
                {pages.map((p) => <Line key={p.id} type="monotone" dataKey={p.id} name={p.handle} stroke={platformColor(c, p.platform)} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 0 }} isAnimationActive={false} />)}
              </LineChart>
            </ResponsiveContainer>
          </div>
          {working.length > 0 && (
            <div className="grid gap-2 pt-4">
              <h3 className="text-[17px]">What’s earning follows</h3>
              <table className="w-full border-collapse text-[15px]">
                <thead><tr className="border-b border-ink text-[13px] text-muted"><th className="pb-2 text-left font-medium">Format</th><th className="pb-2 text-right font-medium">Engagement</th><th className="pb-2 text-right font-medium">Posts</th></tr></thead>
                <tbody>
                  {working.map((w) => (
                    <tr key={w.key} className="border-b border-rule">
                      <td className="py-2">{PLATFORM[w.platform as Platform].label} {(FORMAT_LABEL[w.format] || w.format).toLowerCase()}s</td>
                      <td className="num py-2 text-right">{fmtPct(w.avg_engagement)}</td>
                      <td className="w-24 py-2 text-right text-[13px] text-muted">{w.posts} posts</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
