import * as React from "react";
import { Command } from "cmdk";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Activity, Layers, MessageSquareReply, Moon, Plus, RefreshCcw, Search, Send, Sun } from "lucide-react";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Button, Dialog, DialogContent, Select, Tooltip } from "./ui/primitives";
import { FORMAT_LABEL, PlatformMark } from "./common";

export type View = "overview" | "queue" | "calendar" | "analytics" | "pages";
export const VIEWS: { id: View; label: string }[] = [
  { id: "overview", label: "Today" },
  { id: "queue", label: "Review" },
  { id: "calendar", label: "Calendar" },
  { id: "analytics", label: "Results" },
  { id: "pages", label: "Pages" },
];

function useTheme() {
  const [theme, setTheme] = React.useState<"dark" | "light">(() => {
    const t = document.documentElement.getAttribute("data-theme");
    if (t === "light" || t === "dark") return t;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("sp-theme", next); } catch { /* storage unavailable */ }
    setTheme(next);
  };
  React.useEffect(() => {
    try { const t = localStorage.getItem("sp-theme"); if (t) { document.documentElement.setAttribute("data-theme", t); setTheme(t as "dark" | "light"); } } catch { /* ignore */ }
  }, []);
  return { theme, toggle };
}

export function Shell({ view, setView, children, onGenerate, onCommand }: {
  view: View; setView: (v: View) => void; children: React.ReactNode; onGenerate: () => void; onCommand: () => void;
}) {
  const { overview, backend } = useStore();
  const { theme, toggle } = useTheme();
  const pending = overview?.counts.pending ?? 0;
  const mode = backend?.demo ? "Sample data" : overview?.mode === "live" ? "Posting live" : "Dry run";

  const link = (v: { id: View; label: string }, small?: boolean) => (
    <button key={v.id} type="button" onClick={() => setView(v.id)} aria-current={view === v.id ? "page" : undefined}
      className={cn("hit flex shrink-0 items-center gap-2 rounded-input px-3 font-medium cursor-pointer whitespace-nowrap",
        small ? "h-8 text-[14px]" : "h-9 text-[14.5px]",
        view === v.id ? "bg-paper-3 text-ink" : "text-ink-2 hover:bg-paper-2 hover:text-ink")}>
      {v.label}
      {v.id === "queue" && pending > 0 && <span className="num text-[12.5px] text-muted" aria-label={`${pending} waiting`}>{pending}</span>}
    </button>
  );

  return (
    <div className="desk flex min-h-full flex-col">
      <header className="sticky top-0 z-[300] shrink-0 border-b border-rule bg-desk px-4 sm:px-6">
        <div className="mx-auto flex h-16 max-w-[1360px] items-center gap-6">
          <button type="button" onClick={() => setView("overview")} className="flex items-center gap-2 cursor-pointer" aria-label="SocialPilot, go to Today">
            <Send className="size-[18px] -rotate-12 text-ink" aria-hidden="true" />
            <span className="text-[19px] font-semibold tracking-[-0.02em]">SocialPilot</span>
          </button>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main">{VIEWS.map((v) => link(v))}</nav>
          <div className="ml-auto flex items-center gap-1.5">
            <span className="hidden whitespace-nowrap px-2 text-[13px] text-muted lg:inline">{mode}</span>
            <Tooltip content={<span>Search or run a command <kbd className="ml-1">⌘ K</kbd></span>}>
              <Button variant="ghost" size="icon" onClick={onCommand} aria-label="Search or run a command"><Search /></Button>
            </Tooltip>
            <Tooltip content={theme === "dark" ? "Light desk" : "Dark desk"}>
              <Button variant="ghost" size="icon" onClick={toggle} aria-label="Switch between light and dark">{theme === "dark" ? <Sun /> : <Moon />}</Button>
            </Tooltip>
            <Button onClick={onGenerate} aria-label="New post"><Plus /><span className="hidden sm:inline">New post</span></Button>
          </div>
        </div>
        <nav className="-mx-1 flex gap-1 overflow-x-auto pb-2 scrollbar-thin md:hidden" aria-label="Main">{VIEWS.map((v) => link(v, true))}</nav>
      </header>
      <main className="flex-1 px-4 sm:px-6">
        <div className="mx-auto w-full max-w-[1360px] pb-24 pt-8">{children}</div>
      </main>
    </div>
  );
}

/* ── New post dialog ── */
export function GenerateDialog({ open, onOpenChange, initialPage }: { open: boolean; onOpenChange: (o: boolean) => void; initialPage?: string }) {
  const { pages, generate, busy } = useStore();
  const [pageId, setPageId] = React.useState(initialPage || pages[0]?.id || "");
  const [format, setFormat] = React.useState("auto");
  React.useEffect(() => { if (open) { setPageId(initialPage || pages[0]?.id || ""); setFormat("auto"); } }, [open, initialPage, pages]);
  const page = pages.find((p) => p.id === pageId);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title="Write a new post" className="p-6">
        <h2 className="text-[22px]">Write a new post</h2>
        <p className="mt-1 max-w-[52ch] text-[14.5px] text-muted">The agents research the topic, write it, check it and design it. It lands in Review in about a minute.</p>
        <div className="mt-6 grid gap-5">
          <div className="grid gap-2">
            <span className="text-[14px] font-medium">For which page?</span>
            <div className="grid gap-2 sm:grid-cols-3">
              {pages.map((p) => (
                <button key={p.id} type="button" onClick={() => { setPageId(p.id); setFormat("auto"); }} aria-pressed={pageId === p.id}
                  className={cn("flex items-center gap-2.5 rounded-input border p-3 text-left cursor-pointer",
                    pageId === p.id ? "border-ink bg-paper-2" : "border-rule hover:border-rule-2")}>
                  <PlatformMark platform={p.platform} size="sm" /><span className="truncate text-[14px] font-medium">{p.handle}</span>
                </button>
              ))}
            </div>
            {page && <p className="text-[13.5px] text-muted">{page.niche}</p>}
          </div>
          <div className="grid gap-2">
            <span className="text-[14px] font-medium">Format</span>
            <Select ariaLabel="Format" value={format} onValueChange={setFormat} className="w-full"
              options={[{ value: "auto", label: "Let the strategist pick what’s working" },
                ...(page?.formats || []).map((f) => ({ value: f, label: FORMAT_LABEL[f] || f }))]} />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button disabled={!pageId || busy[`gen${pageId}`]} onClick={async () => { await generate(pageId, format === "auto" ? undefined : format); onOpenChange(false); }}>
            {busy[`gen${pageId}`] ? "Writing…" : "Write it"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ── ⌘K command palette ── */
export function CommandPalette({ open, onOpenChange, setView, openDraft, onGenerate }: {
  open: boolean; onOpenChange: (o: boolean) => void; setView: (v: View) => void; openDraft: (id: number) => void; onGenerate: (pageId?: string) => void;
}) {
  const { drafts, pages, runJob } = useStore();
  const run = (fn: () => void) => { onOpenChange(false); fn(); };
  const item = "flex items-center gap-3 rounded-input px-3 py-2.5 text-[14px] cursor-pointer data-[selected=true]:bg-paper-2";
  const group = "[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:text-[12.5px] [&_[cmdk-group-heading]]:text-muted";
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-[400] bg-board/40" />
        <DialogPrimitive.Content className="stock fixed left-1/2 top-[12%] z-[400] w-[calc(100%-32px)] max-w-xl -translate-x-1/2 overflow-hidden rounded-card outline-none">
          <DialogPrimitive.Title className="sr-only">Search or run a command</DialogPrimitive.Title>
          <Command label="Search or run a command" className="flex flex-col">
            <div className="flex items-center gap-3 border-b border-rule px-5">
              <Search className="size-[18px] text-muted" />
              <Command.Input autoFocus placeholder="Find a draft, write a post, run a job…" className="h-14 flex-1 bg-transparent text-[16px] outline-none placeholder:text-muted" />
            </div>
            <Command.List className="max-h-[400px] overflow-y-auto p-2 scrollbar-thin">
              <Command.Empty className="py-10 text-center text-[14px] text-muted">Nothing matches that.</Command.Empty>
              <Command.Group heading="Write" className={group}>
                {pages.map((p) => (
                  <Command.Item key={p.id} value={`write new post ${p.handle} ${p.platform}`} className={item} onSelect={() => run(() => onGenerate(p.id))}>
                    <PlatformMark platform={p.platform} size="sm" /> New post for {p.handle}
                  </Command.Item>
                ))}
                <Command.Item value="fill queue plan days" className={item} onSelect={() => run(() => runJob("plan"))}><Layers className="size-4" /> Fill the next two days for every page</Command.Item>
              </Command.Group>
              <Command.Group heading="Run" className={group}>
                <Command.Item value="reply comments engage" className={item} onSelect={() => run(() => runJob("engage"))}><MessageSquareReply className="size-4" /> Draft replies to new comments</Command.Item>
                <Command.Item value="metrics results refresh" className={item} onSelect={() => run(() => runJob("metrics"))}><Activity className="size-4" /> Refresh results and follower counts</Command.Item>
                <Command.Item value="publish due posts" className={item} onSelect={() => run(() => runJob("publish"))}><RefreshCcw className="size-4" /> Post anything that’s due</Command.Item>
                <Command.Item value="slack daily report digest" className={item} onSelect={() => run(() => runJob("digest"))}><Send className="size-4" /> Send today’s report to Slack</Command.Item>
              </Command.Group>
              <Command.Group heading="Go to" className={group}>
                {VIEWS.map((v) => <Command.Item key={v.id} value={`go ${v.label}`} className={item} onSelect={() => run(() => setView(v.id))}>{v.label}</Command.Item>)}
              </Command.Group>
              <Command.Group heading="Drafts" className={group}>
                {drafts.filter((d) => d.status !== "published").slice(0, 30).map((d) => (
                  <Command.Item key={d.id} value={`${d.topic} ${d.format} ${d.status} ${d.id}`} className={item} onSelect={() => run(() => openDraft(d.id))}>
                    <PlatformMark platform={d.platform} size="sm" /><span className="flex-1 truncate">{d.kind === "reply" ? "Reply: " : ""}{d.topic}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            </Command.List>
          </Command>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
