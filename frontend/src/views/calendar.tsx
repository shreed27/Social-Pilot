import * as React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useStore } from "@/lib/store";
import type { Draft } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/primitives";
import { FORMAT_LABEL, LiveStamp, PlatformMark } from "@/components/common";

const DAY = 864e5;
const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

function Slot({ d, onOpen }: { d: Draft; onOpen: () => void }) {
  const img = d.media.find((m) => m.type !== "mp4" && m.type !== "pdf");
  const t = new Date(d.scheduled_at!).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
  return (
    <button type="button" onClick={onOpen}
      className={cn("stock grid gap-2 rounded-card p-2.5 text-left cursor-pointer", d.status === "failed" && "outline outline-1 outline-bad")}>
      <div className="flex items-center gap-1.5">
        <PlatformMark platform={d.platform} size="sm" />
        <span className="num text-[13px]">{t}</span>
        {d.status === "published" && <LiveStamp className="ml-auto text-[14px]" />}
        {d.status === "pending" && <span className="ml-auto text-[12.5px] font-semibold text-ink">Needs you</span>}
        {d.status === "failed" && <span className="ml-auto text-[12.5px] font-medium text-bad">Failed</span>}
      </div>
      {img && <img src={img.url} alt="" width={160} height={200} className="aspect-[4/5] w-full rounded-input object-cover" />}
      <span className="text-[13px] font-medium leading-snug line-clamp-3">{d.topic}</span>
      <span className="text-[12px] text-muted">{FORMAT_LABEL[d.format]}</span>
    </button>
  );
}

export function CalendarView({ openDraft }: { openDraft: (id: number) => void }) {
  const { drafts } = useStore();
  const [offset, setOffset] = React.useState(0);
  const today = startOfDay(new Date());
  const start = new Date(today.getTime() + offset * 7 * DAY - 2 * DAY);
  const days = Array.from({ length: 7 }, (_, i) => new Date(start.getTime() + i * DAY));
  const items = drafts.filter((d) => d.kind === "post" && d.scheduled_at && ["pending", "approved", "published", "failed", "publishing"].includes(d.status));
  const inWeek = items.filter((d) => { const t = new Date(d.scheduled_at!).getTime(); return t >= days[0].getTime() && t < days[6].getTime() + DAY; });
  const live = inWeek.filter((d) => d.status === "published").length;
  const waiting = inWeek.filter((d) => d.status === "pending").length;

  return (
    <div className="grid gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="grid gap-1">
          <h1 className="text-[clamp(26px,3vw,36px)] leading-[1.1]">
            {days[0].toLocaleDateString("en-IN", { day: "numeric", month: "short" })} to {days[6].toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
          </h1>
          <p className="text-[15px] text-ink-2">{inWeek.length} posts this week. {live} live, {inWeek.length - live - waiting} scheduled{waiting ? <>, <span className="font-semibold text-ink">{waiting} waiting for you</span></> : ""}.</p>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" aria-label="Previous week" onClick={() => setOffset(offset - 1)}><ChevronLeft /></Button>
          <Button variant={offset === 0 ? "card" : "ghost"} size="sm" onClick={() => setOffset(0)}>This week</Button>
          <Button variant="ghost" size="icon" aria-label="Next week" onClick={() => setOffset(offset + 1)}><ChevronRight /></Button>
        </div>
      </div>
      <div className="-mx-4 overflow-x-auto px-4 pb-4 sm:-mx-6 sm:px-6 scrollbar-thin">
        <div className="grid min-w-[980px] grid-cols-7 gap-4">
          {days.map((day) => {
            const isToday = day.getTime() === today.getTime();
            const list = items.filter((d) => startOfDay(new Date(d.scheduled_at!)).getTime() === day.getTime())
              .sort((a, b) => a.scheduled_at!.localeCompare(b.scheduled_at!));
            return (
              <div key={day.toISOString()} className="grid content-start gap-3">
                <div className={cn("flex items-baseline gap-2 border-b-2 pb-2", isToday ? "border-ink" : "border-rule")}>
                  <span className="text-[28px] font-semibold leading-none tracking-[-0.03em]">{day.getDate()}</span>
                  <span className={cn("text-[14px]", isToday ? "font-semibold" : "text-muted")}>{isToday ? "Today" : day.toLocaleDateString("en-IN", { weekday: "short" })}</span>
                </div>
                {list.length === 0 ? <p className="py-6 text-center text-[13px] text-muted">Free</p>
                  : list.map((d) => <Slot key={d.id} d={d} onOpen={() => openDraft(d.id)} />)}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
