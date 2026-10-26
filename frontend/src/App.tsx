import * as React from "react";
import { Toaster } from "sonner";
import { Send } from "lucide-react";
import { StoreProvider, useStore } from "@/lib/store";
import { TooltipProvider } from "@/components/ui/primitives";
import { PressFilter } from "@/components/common";
import { CommandPalette, GenerateDialog, Shell, VIEWS, type View } from "@/components/shell";
import { OverviewView } from "@/views/overview";
import { QueueView } from "@/views/queue";
import { CalendarView } from "@/views/calendar";
import { AnalyticsView } from "@/views/analytics";
import { PagesView } from "@/views/pages";

const fromHash = (): View => {
  const h = location.hash.replace("#", "") as View;
  return VIEWS.some((v) => v.id === h) ? h : "overview";
};

function Boot() {
  const { error } = useStore();
  return (
    <div className="desk grid min-h-dvh place-items-center px-4">
      <div className="stock grid w-full max-w-sm gap-2 rounded-card p-6" role={error ? "alert" : "status"}>
        <Send className="size-5 -rotate-12 text-ink" aria-hidden="true" />
        <p className="text-[17px] font-semibold">{error ? "The dashboard couldn’t reach the agents" : "Connecting to the agents…"}</p>
        <p className="text-[14px] text-muted">{error ? `${error}. Check the server is running with uvicorn app.web.main:app, then reload this page.` : "Loading your pages and drafts."}</p>
      </div>
    </div>
  );
}

function Dashboard() {
  const { ready } = useStore();
  const [view, setViewState] = React.useState<View>(fromHash);
  const [selected, setSelected] = React.useState<number | null>(null);
  const [cmdOpen, setCmdOpen] = React.useState(false);
  const [gen, setGen] = React.useState<{ open: boolean; page?: string }>({ open: false });

  const setView = React.useCallback((v: View) => {
    setViewState(v);
    try { history.replaceState(null, "", `#${v}`); } catch { /* sandboxed */ }
  }, []);
  const openDraft = (id: number) => { setSelected(id); setView("queue"); };

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setCmdOpen((o) => !o); }
    };
    const onHash = () => setViewState(fromHash());
    window.addEventListener("keydown", onKey);
    window.addEventListener("hashchange", onHash);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("hashchange", onHash); };
  }, []);

  if (!ready) return <Boot />;
  return (
    <>
      <Shell view={view} setView={setView} onGenerate={() => setGen({ open: true })} onCommand={() => setCmdOpen(true)}>
        {view === "overview" && <OverviewView setView={setView} openDraft={openDraft} />}
        {view === "queue" && <QueueView selected={selected} setSelected={setSelected} />}
        {view === "calendar" && <CalendarView openDraft={openDraft} />}
        {view === "analytics" && <AnalyticsView openDraft={openDraft} />}
        {view === "pages" && <PagesView onGenerate={(p) => setGen({ open: true, page: p })} />}
      </Shell>
      <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} setView={setView} openDraft={openDraft} onGenerate={(p) => setGen({ open: true, page: p })} />
      <GenerateDialog open={gen.open} initialPage={gen.page} onOpenChange={(o) => setGen((g) => ({ ...g, open: o }))} />
    </>
  );
}

export default function App() {
  return (
    <StoreProvider>
      <TooltipProvider>
        <PressFilter />
        <Dashboard />
        <Toaster position="bottom-right" theme="system" toastOptions={{
          style: { background: "var(--color-cotton)", color: "var(--color-print)", border: "1px solid var(--color-rule-2)", borderRadius: "var(--radius-card)", fontFamily: "var(--font-body)" },
        }} />
      </TooltipProvider>
    </StoreProvider>
  );
}
