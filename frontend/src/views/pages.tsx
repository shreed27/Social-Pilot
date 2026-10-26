import { useStore } from "@/lib/store";
import { Button } from "@/components/ui/primitives";
import { FORMAT_LABEL, PlatformMark } from "@/components/common";

/* The content pipeline is a real sequence, so it's numbered. Background jobs aren't, so they're a plain list. */
const PIPELINE = [
  { name: "Trend scout", job: "Reads niche news, what's spreading this week, your reference accounts and saved viral posts, and proposes 8 ideas people would send, save or argue with." },
  { name: "Strategist", job: "Picks the pillar, format and post structure that have been growing this page, and the one action the post is built for." },
  { name: "Depth research", job: "Builds a fact pack: exact steps, sourced numbers, named tools, real examples, the common mistake. Unverified numbers get flagged for you." },
  { name: "Hook tournament", job: "Writes 7 opening lines of different kinds; a separate judge picks the one most likely to stop the scroll." },
  { name: "Writer", job: "Writes in a human voice to each platform's rules, using at least four specifics from the fact pack." },
  { name: "Critic and quality checks", job: "Strips AI-sounding phrasing, then scores viral potential and depth. Anything under 8, or failing a check, goes back for a rewrite." },
  { name: "Visuals", job: "Designs the slides (lists, steps, big numbers, comparisons, AI photos) and makes reels from AI footage with the text burned in." },
  { name: "You", job: "Nothing posts until you approve it. Post now, or schedule it." },
  { name: "Publisher", job: "Posts through each platform's official API the moment you approve, or at the scheduled time. Never twice." },
];
const ALSO = [
  { name: "Comment replies", when: "every 30 minutes", job: "drafts short, human replies to new comments for you to approve" },
  { name: "Results", when: "every 6 hours", job: "pulls reach, saves, shares, follows and follower counts, and teaches the strategist what works" },
  { name: "Slack", when: "live, plus 9pm daily", job: "posts every published or failed post, pings when drafts need you, and sends the daily report" },
  { name: "Planner", when: "6am and 2pm", job: "keeps two days of posts ready for every page" },
];

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 border-t border-rule py-3 sm:grid-cols-[120px_1fr] sm:gap-4">
      <dt className="text-[13.5px] text-muted">{k}</dt>
      <dd className="min-w-0 text-[14.5px] leading-relaxed">{children}</dd>
    </div>
  );
}

export function PagesView({ onGenerate }: { onGenerate: (pageId: string) => void }) {
  const { pages } = useStore();
  return (
    <div className="grid gap-16">
      <section className="grid gap-6">
        <div className="grid gap-1">
          <h1 className="text-[clamp(26px,3vw,36px)]">Your pages</h1>
          <p className="text-[15px] text-ink-2">Everything the agents know about each page. Change it in <code className="num rounded-input bg-paper-2 px-1.5 py-0.5 text-[13.5px]">config/pages.yaml</code>.</p>
        </div>
        <div className="grid gap-6 xl:grid-cols-3">
          {pages.map((p) => (
            <article key={p.id} className="stock grid content-start gap-4 rounded-card p-6">
              <div className="flex items-center gap-3">
                <PlatformMark platform={p.platform} size="lg" />
                <div className="min-w-0">
                  <h2 className="truncate text-[20px]">{p.handle}</h2>
                  <p className="text-[13.5px] text-muted">{p.posts_per_week} posts a week</p>
                </div>
                <div className="ml-auto flex gap-1" aria-label="Brand colours">
                  {[p.brand.bg, p.brand.fg, p.brand.accent].map((col) => <span key={col} className="size-5 rounded-full ring-1 ring-rule-2" style={{ background: col }} title={col} />)}
                </div>
              </div>
              <p className="text-[15.5px] font-medium leading-snug">{p.niche}</p>
              <dl>
                <Row k="Audience">{p.audience}</Row>
                <Row k="Voice">{p.voice}</Row>
                <Row k="Pillars">{p.pillars.map((x) => x.name).join(", ")}</Row>
                <Row k="Formats">{p.formats.map((f) => FORMAT_LABEL[f] || f).join(", ")}</Row>
                <Row k="Posts at">{p.preferred_slots.join(", ")}, adjusted to what performs</Row>
                <Row k="Stays away from">{p.avoid.join(", ")}</Row>
              </dl>
              <Button variant="card" className="justify-self-start" onClick={() => onGenerate(p.id)}>Write a post for {p.handle}</Button>
            </article>
          ))}
        </div>
      </section>

      <section className="grid gap-10 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <div className="grid content-start gap-5">
          <div className="grid gap-1">
            <h2 className="text-[24px]">How a post gets made</h2>
            <p className="text-[15px] text-ink-2">Every draft goes through these steps, in this order.</p>
          </div>
          <ol className="grid">
            {PIPELINE.map((s, i) => (
              <li key={s.name} className="grid grid-cols-[44px_1fr] gap-3 border-t border-rule py-4">
                <span className={`num grid size-8 place-items-center rounded-full text-[14px] ${s.name === "You" ? "bg-board text-board-type" : "border border-rule-2"}`}>{i + 1}</span>
                <div className="grid gap-0.5">
                  <h3 className="text-[17px]">{s.name}</h3>
                  <p className="max-w-[62ch] text-[14.5px] leading-relaxed text-ink-2">{s.job}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
        <div className="grid content-start gap-5">
          <h2 className="text-[24px]">Also running</h2>
          <ul className="grid">
            {ALSO.map((a) => (
              <li key={a.name} className="grid gap-0.5 border-t border-rule py-4">
                <h3 className="text-[17px]">{a.name}</h3>
                <p className="text-[13.5px] text-muted">{a.when}</p>
                <p className="text-[14.5px] leading-relaxed text-ink-2">It {a.job}.</p>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
