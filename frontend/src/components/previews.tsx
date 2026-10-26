/* Platform-native previews: what the post will look like in each app. */
import * as React from "react";
import { Bookmark, ChevronLeft, ChevronRight, Globe2, Heart, MessageCircle, MoreHorizontal, Repeat2, Send, Share, ThumbsUp } from "lucide-react";
import type { Draft, Page } from "@/lib/types";
import { cn } from "@/lib/utils";

function Avatar({ page, size = 32 }: { page: Page; size?: number }) {
  const initials = page.handle.replace(/^@/, "").slice(0, 2).toUpperCase();
  return (
    <span className="grid shrink-0 place-items-center rounded-full font-semibold text-[11px]"
      style={{ width: size, height: size, background: page.brand.bg, color: page.brand.accent, boxShadow: `0 0 0 1px ${page.brand.accent}55` }}>
      {initials}
    </span>
  );
}

function Rich({ text, accent }: { text: string; accent: string }) {
  const parts = text.split(/(#\w+|@\w[\w.]*)/g);
  return <>{parts.map((p, i) => (/^[#@]\w/.test(p) ? <span key={i} style={{ color: accent }}>{p}</span> : <React.Fragment key={i}>{p}</React.Fragment>))}</>;
}

function Slider({ media, aspect }: { media: Draft["media"]; aspect: string }) {
  const [i, setI] = React.useState(0);
  React.useEffect(() => setI(0), [media]);
  if (!media.length) return null;
  const m = media[i];
  return (
    <div className="relative bg-black" style={{ aspectRatio: aspect }}>
      {m.type === "mp4" ? (
        <video key={m.url} src={m.url} poster={media.find((x) => x.type !== "mp4" && x.type !== "pdf")?.url} preload="metadata" className="size-full object-cover" controls muted playsInline loop />
      ) : m.type === "pdf" ? (
        <a href={m.url} target="_blank" rel="noreferrer" className="grid size-full place-items-center text-sm text-white/80 underline">Open the PDF document</a>
      ) : (
        <img src={m.url} alt={`Slide ${i + 1}`} className="size-full object-cover" />
      )}
      {media.length > 1 && (
        <>
          <span className="absolute right-2 top-2 rounded-full bg-black/60 px-2 py-0.5 num text-[11px] text-white">{i + 1}/{media.length}</span>
          {i > 0 && <button type="button" aria-label="Previous slide" onClick={() => setI(i - 1)} className="absolute left-2 top-1/2 -translate-y-1/2 grid size-7 place-items-center rounded-full bg-white/85 text-black cursor-pointer"><ChevronLeft className="size-4" /></button>}
          {i < media.length - 1 && <button type="button" aria-label="Next slide" onClick={() => setI(i + 1)} className="absolute right-2 top-1/2 -translate-y-1/2 grid size-7 place-items-center rounded-full bg-white/85 text-black cursor-pointer"><ChevronRight className="size-4" /></button>}
        </>
      )}
    </div>
  );
}

const shell = "stock mx-auto w-full overflow-hidden rounded-card";

export function InstagramPreview({ d, page, caption }: { d: Draft; page: Page; caption: string }) {
  const [more, setMore] = React.useState(false);
  const tags = (d.content.hashtags || []).join(" ");
  const full = `${caption}${d.content.cta && !caption.includes(d.content.cta) ? `\n\n${d.content.cta}` : ""}${tags ? `\n\n${tags}` : ""}`;
  const aspect = d.format === "reel" ? "9 / 16" : "4 / 5";
  return (
    <div className={cn(shell, d.format === "reel" ? "max-w-[300px]" : "max-w-[380px]")}>
      <div className="flex items-center gap-2.5 px-3 py-2.5">
        <Avatar page={page} size={30} />
        <div className="flex-1 leading-tight"><div className="text-[13px] font-semibold">{page.handle.replace(/^@/, "")}</div><div className="text-[11px] text-muted">{d.format === "reel" ? "Original audio" : "Draft preview"}</div></div>
        <MoreHorizontal className="size-4 text-muted" />
      </div>
      <Slider media={d.media} aspect={aspect} />
      {d.format === "carousel" && d.media.length > 1 && (
        <div className="flex justify-center gap-1 pt-2">{d.media.map((_, i) => <span key={i} className={cn("size-1.5 rounded-full", i === 0 ? "bg-ink" : "bg-rule-2")} />)}</div>
      )}
      <div className="flex items-center gap-3.5 px-3 pt-2.5"><Heart className="size-5" /><MessageCircle className="size-5" /><Send className="size-5" /><Bookmark className="ml-auto size-5" /></div>
      <div className="px-3 pb-3 pt-2 text-[13px] leading-snug whitespace-pre-line">
        <span className="font-semibold">{page.handle.replace(/^@/, "")} </span>
        <Rich text={more ? full : full.slice(0, 125)} accent="var(--color-li)" />
        {!more && full.length > 125 && <button type="button" className="text-muted cursor-pointer" onClick={() => setMore(true)}>… more</button>}
      </div>
    </div>
  );
}

export function LinkedInPreview({ d, page, caption }: { d: Draft; page: Page; caption: string }) {
  const [more, setMore] = React.useState(false);
  const tags = (d.content.hashtags || []).join(" ");
  const full = `${caption}${tags ? `\n\n${tags}` : ""}`;
  const lines = full.split("\n");
  const short = lines.slice(0, 3).join("\n");
  const pdf = d.media.find((m) => m.type === "pdf");
  const visual = d.media.filter((m) => m.type !== "pdf").length ? d.media.filter((m) => m.type !== "pdf") : d.media;
  return (
    <div className={cn(shell, "max-w-[520px]")}>
      <div className="flex items-start gap-2.5 px-4 pt-3">
        <Avatar page={page} size={44} />
        <div className="flex-1 leading-tight">
          <div className="text-[14px] font-semibold">{page.handle}</div>
          <div className="text-[12px] text-muted">Company page · Follow</div>
          <div className="flex items-center gap-1 text-[12px] text-muted">now · <Globe2 className="size-3" /></div>
        </div>
        <MoreHorizontal className="size-4 text-muted" />
      </div>
      <div className="px-4 py-3 text-[14px] leading-relaxed whitespace-pre-line">
        <Rich text={more ? full : short} accent="var(--color-li)" />
        {!more && full.length > short.length && <button type="button" className="text-muted cursor-pointer" onClick={() => setMore(true)}>…see more</button>}
      </div>
      {visual.length > 0 && (
        <div className="border-y border-rule">
          {d.format === "document" && (
            <div className="flex items-center justify-between gap-3 px-4 py-2 text-[12px]">
              <span className="font-medium truncate">{d.content.slides?.[0]?.title || d.topic}</span>
              <span className="flex shrink-0 items-center gap-2 num text-muted">{visual.length} pages
                {pdf && <a href={pdf.url} target="_blank" rel="noreferrer" className="text-li underline">PDF</a>}</span>
            </div>
          )}
          <Slider media={visual} aspect="4 / 5" />
        </div>
      )}
      <div className="flex items-center justify-around px-2 py-1.5 text-[13px] text-muted">
        {[[ThumbsUp, "Like"], [MessageCircle, "Comment"], [Repeat2, "Repost"], [Send, "Send"]].map(([I, l]) => {
          const Icon = I as React.ElementType;
          return <span key={l as string} className="flex items-center gap-1.5 px-2 py-1.5"><Icon className="size-4" />{l as string}</span>;
        })}
      </div>
    </div>
  );
}

export function XPreview({ d, page, posts }: { d: Draft; page: Page; posts: string[] }) {
  return (
    <div className={cn(shell, "max-w-[540px] py-2")}>
      {posts.map((p, i) => {
        const len = [...p].length;
        return (
          <div key={i} className="relative flex gap-3 px-4 py-2.5">
            {i < posts.length - 1 && <span aria-hidden="true" className="absolute left-[35px] top-12 bottom-0 w-0.5 bg-rule-2" />}
            <Avatar page={page} size={40} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5 text-[14px]">
                <span className="font-semibold">{page.handle.replace(/^@/, "")}</span><span className="text-muted">{page.handle}</span>
                <span className={cn("ml-auto num text-[11px]", len > 280 ? "text-bad" : len > 250 ? "text-ink" : "text-muted")}>{len}/280</span>
              </div>
              <p className="mt-0.5 text-[14.5px] leading-snug whitespace-pre-line"><Rich text={p} accent="var(--color-li)" /></p>
              {i === 0 && d.media[0] && <img src={d.media[0].url} alt="" width={500} height={500} className="mt-2 w-full rounded-input border border-rule" />}
              <div className="mt-2 flex max-w-xs justify-between text-muted"><MessageCircle className="size-4" /><Repeat2 className="size-4" /><Heart className="size-4" /><Share className="size-4" /></div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ReplyPreview({ d, page, reply }: { d: Draft; page: Page; reply: string }) {
  const [author, ...rest] = (d.reply_context || "").split(": ");
  return (
    <div className={cn(shell, "max-w-[460px] p-4 grid gap-3")}>
      <div className="flex gap-2.5">
        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-paper-2 text-[11px] font-semibold">{(author || "?").slice(0, 2).toUpperCase()}</span>
        <div className="rounded-card rounded-tl-[2px] bg-paper-2 px-3 py-2 text-[13.5px]"><div className="text-[12px] font-semibold">{author}</div>{rest.join(": ")}</div>
      </div>
      <div className="flex gap-2.5 pl-8">
        <Avatar page={page} size={28} />
        <div className="rounded-card rounded-tl-[2px] border border-ink px-3 py-2 text-[13.5px]"><div className="text-[12px] font-semibold">{page.handle}, draft reply</div>{reply}</div>
      </div>
    </div>
  );
}
