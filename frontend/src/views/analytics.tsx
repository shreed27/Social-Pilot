import * as React from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { useStore } from "@/lib/store";
import { platformColor, useThemeColors } from "@/lib/theme";
import type { Analytics } from "@/lib/types";
import { cn, fmtInt, fmtPct, fmtWhen } from "@/lib/utils";
import { Groove } from "@/components/ui/primitives";
import { FORMAT_LABEL, PlatformMark } from "@/components/common";
import { ChartTooltip } from "./overview";

type SortKey = "engagement" | "impressions" | "saves" | "follows";
const SORTS: { k: SortKey; l: string }[] = [{ k: "engagement", l: "Engagement" }, { k: "impressions", l: "Reach" }, { k: "saves", l: "Saves" }, { k: "follows", l: "Follows" }];
const nice = (k: string) => (FORMAT_LABEL[k] || k.replaceAll("_", " ").replaceAll("-", " "));

export function AnalyticsView({ openDraft }: { openDraft: (id: number) => void }) {
  const { pages, backend, drafts, overview } = useStore();
  const c = useThemeColors();
  const [pageId, setPageId] = React.useState(pages[0]?.id);
  const [data, setData] = React.useState<Analytics | null>(null);
  const [sort, setSort] = React.useState<SortKey>("engagement");
  const page = pages.find((p) => p.id === pageId);
  React.useEffect(() => { if (backend && pageId) backend.analytics(pageId).then(setData).catch(() => setData(null)); }, [backend, pageId, drafts.length]);
  if (!page) return null;
  void platformColor;
  const color = c.ink;
  const rows = (o?: Record<string, { posts: number; avg_engagement: number }>) =>
    Object.entries(o || {}).map(([k, v]) => ({ name: nice(k), ...v })).sort((a, b) => b.avg_engagement - a.avg_engagement);
  const pillar = rows(data?.by_pillar), format = rows(data?.by_format), arche = rows(data?.by_archetype);
  const posts = drafts.filter((d) => d.page_id === pageId && d.metrics).sort((a, b) => (b.metrics![sort] as number) - (a.metrics![sort] as number));
  const s = overview?.pages[page.id];
  const bestFormat = format[0], bestPillar = pillar[0];

  const bars = (list: { name: string; avg_engagement: number }[], h = 220) => (
    <div style={{ height: h }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={list} layout="vertical" margin={{ left: 0, right: 40, top: 0, bottom: 0 }}>
          <CartesianGrid stroke={c.rule} horizontal={false} />
          <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: c.muted, fontSize: 12 }} tickFormatter={(v) => fmtPct(v, 0)} />
          <YAxis type="category" dataKey="name" tickLine={false} axisLine={false} tick={{ fill: c.ink, fontSize: 13.5 }} width={130} />
          <RTooltip content={<ChartTooltip valueFmt={(v: number) => fmtPct(v)} />} cursor={{ fill: c["paper-2"] }} />
          <Bar dataKey="avg_engagement" name="Engagement" fill={color} radius={[0, 2, 2, 0]} barSize={16} isAnimationActive={false}
            label={{ position: "right", fill: c.ink, fontSize: 12.5, formatter: (v: unknown) => fmtPct(Number(v)) }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div className="grid gap-12">
      <div className="overflow-x-auto scrollbar-thin">
        <Groove label="Choose a page" value={pageId || ""} onChange={setPageId}
          options={pages.map((p) => ({ value: p.id, label: <><PlatformMark platform={p.platform} size="sm" />{p.handle}</> }))} />
      </div>

      <section className="grid gap-3">
        <h1 className="max-w-[32ch] text-[clamp(26px,3.2vw,38px)] leading-[1.1]">
          {page.handle} {s?.growth_30d ? <>gained {fmtInt(s.growth_30d)} followers this month</> : "is just getting started"}
          {bestFormat ? <>, and {bestFormat.name.toLowerCase()}s are earning the most.</> : "."}
        </h1>
        <p className="max-w-[68ch] text-[16px] text-ink-2">
          {fmtInt(s?.followers)} followers now, {s?.growth_7d ? `${s.growth_7d > 0 ? "+" : ""}${fmtInt(s.growth_7d)} in the last 7 days` : "no change this week"}.
          {" "}{data?.posts_analysed ?? 0} posts tracked, averaging {fmtPct(s?.avg_engagement)} weighted engagement
          {bestPillar ? <>. The {bestPillar.name} pillar leads at {fmtPct(bestPillar.avg_engagement)}.</> : "."}
        </p>
      </section>

      <section className="grid gap-10 lg:grid-cols-2">
        <div className="grid content-start gap-3">
          <h2 className="text-[20px]">By format</h2>
          <div className="border-t border-ink pt-4">{bars(format, Math.max(140, format.length * 46))}</div>
        </div>
        <div className="grid content-start gap-3">
          <h2 className="text-[20px]">By content pillar</h2>
          <div className="border-t border-ink pt-4">{bars(pillar, Math.max(140, pillar.length * 46))}</div>
        </div>
        {arche.length > 0 && (
          <div className="grid content-start gap-3 lg:col-span-2">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-[20px]">By post structure</h2>
              <p className="text-[14px] text-muted">The strategist picks winning structures more often, and keeps testing the rest.</p>
            </div>
            <div className="border-t border-ink pt-4">{bars(arche, Math.max(140, arche.length * 46))}</div>
          </div>
        )}
      </section>

      <section className="grid gap-4">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="text-[20px]">Every post</h2>
          <Groove label="Sort posts by" value={sort} onChange={setSort} options={SORTS.map(({ k, l }) => ({ value: k, label: l }))} />
        </div>
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full min-w-[760px] text-[14px]">
            <thead>
              <tr className="border-b border-ink text-left text-[13px] text-muted">
                {["Post", "Format", "Went live", "Reach", "Likes", "Saves", "Shares", "Follows", "Engagement"].map((h, i) => (
                  <th key={h} className={cn("py-2.5 pr-5 font-medium whitespace-nowrap", i > 2 && "text-right", i === 0 && "sticky left-0 z-[1] bg-desk")}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {posts.map((d, i) => (
                <tr key={d.id} onClick={() => openDraft(d.id)} className="border-b border-rule cursor-pointer hover:bg-paper-2">
                  <td className="sticky left-0 z-[1] bg-desk py-3 pr-5"><button type="button" onClick={(e) => { e.stopPropagation(); openDraft(d.id); }} className="block max-w-[min(44ch,50vw)] truncate whitespace-nowrap text-left font-medium hover:underline underline-offset-4 cursor-pointer">{i === 0 && <span className="mr-2 text-[13px] font-semibold text-ink">Best:</span>}{d.topic}</button></td>
                  <td className="pr-5 text-ink-2">{FORMAT_LABEL[d.format]}</td>
                  <td className="whitespace-nowrap pr-5 text-ink-2">{fmtWhen(d.scheduled_at)}</td>
                  {(["impressions", "likes", "saves", "shares", "follows"] as const).map((k) => <td key={k} className="num pr-5 text-right">{fmtInt(d.metrics![k])}</td>)}
                  <td className="num text-right text-ink">{fmtPct(d.metrics!.engagement)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
