import { cn } from "@/lib/utils";
import type { Platform, Status } from "@/lib/types";
import { Badge } from "./ui/primitives";

export const PLATFORM: Record<Platform, { label: string; short: string; color: string }> = {
  instagram: { label: "Instagram", short: "IG", color: "var(--color-ig)" },
  linkedin: { label: "LinkedIn", short: "in", color: "var(--color-li)" },
  x: { label: "X", short: "X", color: "var(--color-x)" },
};

/* platform marks are the one place a brand colour appears */
export function PlatformMark({ platform, size = "md", className }: { platform: Platform; size?: "sm" | "md" | "lg"; className?: string }) {
  const p = PLATFORM[platform];
  const s = { sm: "size-5 text-[10px]", md: "size-7 text-[11px]", lg: "size-9 text-[13px]" }[size];
  return (
    <span className={cn("inline-grid shrink-0 place-items-center rounded-full font-semibold text-on-mark", s, className)}
      style={{ background: p.color }} role="img" aria-label={p.label} title={p.label}>
      {p.short}
    </span>
  );
}

/* "Live" is the one settled state, so it is pressed into the stock in coral. Everything else is an ink outline. */
export function LiveStamp({ className }: { className?: string }) {
  return <span className={cn("pressed text-[15px]", className)}>Live</span>;
}

const STATUS_STYLE: Record<Exclude<Status, "published">, { v: "strong" | "default" | "bad"; label: string }> = {
  pending: { v: "strong", label: "Needs you" },
  approved: { v: "default", label: "Scheduled" },
  publishing: { v: "default", label: "Posting now" },
  failed: { v: "bad", label: "Failed" },
  rejected: { v: "default", label: "Rejected" },
};
export function StatusBadge({ status }: { status: Status }) {
  if (status === "published") return <LiveStamp />;
  const s = STATUS_STYLE[status];
  return <Badge variant={s.v}>{s.label}</Badge>;
}

export const FORMAT_LABEL: Record<string, string> = {
  carousel: "Carousel", reel: "Reel", image: "Image", document: "Document", text: "Text post", thread: "Thread", reply: "Reply",
};

export function Delta({ value, suffix = "" }: { value: number; suffix?: string }) {
  if (!value) return <span className="num text-muted">0{suffix}</span>;
  return <span className={cn("num", value > 0 ? "text-good" : "text-bad")}>{value > 0 ? "+" : "−"}{Math.abs(value).toLocaleString("en-IN")}{suffix}</span>;
}

export function Empty({ title, hint, action }: { title: string; hint?: string; action?: React.ReactNode }) {
  return (
    <div className="grid justify-items-start gap-2 rounded-card bg-paper-2 px-6 py-10">
      <p className="text-[18px] font-semibold">{title}</p>
      {hint && <p className="max-w-[48ch] text-[14px] text-muted">{hint}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

/* The ink filter behind the pressed stamp: a shade wall offset into the letters and an uneven noise mask. */
export function PressFilter() {
  return (
    <svg width="0" height="0" aria-hidden="true" className="absolute">
      <filter id="press-ink" x="-10%" y="-20%" width="120%" height="140%">
        <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="2" seed="7" result="noise" />
        <feColorMatrix in="noise" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -0.7 1.12" result="mask" />
        <feComposite in="SourceGraphic" in2="mask" operator="in" result="inked" />
        <feOffset in="SourceAlpha" dx="0.5" dy="0.7" result="wall" />
        <feComposite in="SourceAlpha" in2="wall" operator="out" result="lip" />
        <feFlood floodOpacity="0.22" result="tint" />
        <feComposite in="tint" in2="lip" operator="in" result="shade" />
        <feMerge><feMergeNode in="inked" /><feMergeNode in="shade" /></feMerge>
      </filter>
    </svg>
  );
}
