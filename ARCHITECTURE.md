# SocialPilot — Architecture & Growth Plan

An agentic system that runs three social pages (Instagram, LinkedIn, X) end to end: it researches
what the niche cares about, decides what to post, writes and designs it, checks its own work,
queues it for one-click human approval, publishes on schedule, replies to comments, and learns from
the numbers which content actually grows followers.

## 1. The loop

```
           ┌────────────────────────── learning loop ───────────────────────────┐
           ▼                                                                     │
 ┌──────────┐   ┌────────────┐   ┌────────┐   ┌────────┐   ┌─────────┐   ┌──────┴─────┐
 │ Research │ → │ Strategist │ → │ Writer │ → │ Critic │ → │ Visuals │ → │  Approval  │
 │  agent   │   │   agent    │   │ agent  │   │ agent  │   │  agent  │   │   queue    │
 └──────────┘   └────────────┘   └────────┘   └───┬────┘   └─────────┘   └──────┬─────┘
  RSS / web      bandit over        platform-      │ score < 7.5 or              │ you approve /
  search, dedup  pillar×format +    native copy    │ rule broken → rewrite       │ edit / reject
  vs last 30d    LLM angle + hook   per format     └──→ Writer (max 2x)          ▼
                                                                         ┌────────────┐
 ┌────────────┐      ┌────────────┐      new comments  ┌────────────┐    │ Scheduler  │
 │ Analytics  │ ←─── │ Published  │ ─────────────────→ │ Engagement │    │ + Publisher│
 │   agent    │      │   posts    │                    │   agent    │ →  └────────────┘
 └────────────┘      └────────────┘                    └────────────┘  reply drafts → queue
  metrics + follower count every 6 h
```

The content pipeline is a LangGraph state machine (`app/agents/graph.py`). The critic → writer edge
is conditional, so a weak draft gets rewritten with specific editor feedback before any human sees it.

## 2. Agents

| Agent | File | What it decides |
|---|---|---|
| Research | `agents/research.py` | 6 candidate ideas from niche RSS feeds (optional: Claude web search), never repeating a topic from the last 30 days |
| Strategist | `agents/strategist.py` | Which **pillar × format** to post next (Thompson sampling over past engagement), then the exact angle and hook |
| Writer | `agents/writer.py` | Platform-native copy per format: caption, thread, carousel slides, reel script, alt text |
| Critic | `agents/critic.py` | Hard rules (length, slide count, hashtags, no URLs on X, avoid-list) + an LLM editor scoring hook, value, niche fit, platform fit, brand safety |
| Visuals | `agents/visuals.py` | Renders on-brand media: IG carousel PNGs, LinkedIn PDF document, single image card (optional AI background), 1080×1920 reel MP4 |
| Engagement | `engagement.py` | Reads new comments on recent posts, drafts short human replies, skips spam/trolls |
| Analytics | `analytics.py` | Pulls per-post metrics and follower counts; scores posts weighted toward saves, shares and follows |

## 2b. Viral playbook (researched Oct 2026)

`app/playbooks.py` encodes what each ranking system rewards; every agent reads it.

| | Optimise for | Hard rules baked in |
|---|---|---|
| Instagram | **Sends per reach** (reaching non-followers), watch time incl. replays, saves | Original only; hook on screen in frame 1 (half watch muted); carousels 7–10 slides that stand alone; reels loop; 3–5 hashtags |
| LinkedIn | **Comments** (heaviest), saves (~5× a like), dwell time; first 30–60 min decide reach | Stay on niche (topic-matched ranker); 2-line hook before "see more"; 8–12 page documents; no links; no generic AI copy; no engagement bait |
| X | **Replies the author answers** (heaviest), profile clicks, bookmarks | No links; claim clear in 8 words; take a side; < ~100 chars for single posts; never rage-bait (mutes/blocks are heavily negative) |

Pipeline additions:
- **Trend scout** (research agent): niche news + optional live web search of what's spreading this week and what your
  `reference_accounts` post + your `config/swipe/<page>.md` file of saved viral posts (studied, never copied).
- **Archetypes**: framework, relatable, contrarian, before/after, proof, red flags, advice-I-needed, explainer, story,
  hot take, list, news. A bandit learns which ones grow each page.
- **Hook tournament**: 7 hooks of different types; a separate judge scores stop-power, clarity, specificity and human
  voice; the winner opens the post and the rest stay swappable in the dashboard.
- **Human voice**: writer rules + `app/humanize.py` detector (AI vocabulary, "No X. No Y. Just Z.", "not just X but Y",
  em-dash overuse, hedging, uniform sentence rhythm). Any tell sends the draft back.
- **Viral score**: 8 dimensions weighted per platform (e.g. shareability counts most on Instagram, discussion on
  LinkedIn and X). Drafts must reach 8.0 (`CRITIC_MIN_SCORE`).
- **Templates**: bold (highlighted keyword), post_card (text-post screenshot style, the most-sent format for takes),
  minimal (storytelling), split (before/after). Reels: text from frame 1, 1–2.5 s beats, push-in motion, progress bar.

Nothing can make every post go viral; distribution has a large luck component. This raises the hit rate and learns
from every post. Add trending audio to reels in the Instagram app before or after publishing (the API can't attach
licensed music), and use Trial Reels to test hooks on non-followers.

Sources: [Buffer: Instagram algorithm](https://buffer.com/resources/instagram-algorithms/) ·
[Blackalpaca: Instagram 2026](https://blckalpaca.at/en/knowledge-base/social-media/social-media-algorithms-distribution/instagram-algorithm-2026) ·
[SocialPilot: LinkedIn algorithm](https://www.socialpilot.co/blog/linkedin-algorithm) ·
[PostEverywhere: viral on LinkedIn](https://posteverywhere.ai/blog/how-to-go-viral-on-linkedin) ·
[PostEverywhere: X algorithm](https://posteverywhere.ai/blog/how-the-x-twitter-algorithm-works) ·
[Postory: what goes viral on X](https://postory.io/blog/what-goes-viral-on-twitter) ·
[whaaat.ai: carousel trends](https://www.whaaat.ai/blog/instagram-carousel-trends-2026-12-formats-blowing-up-right-now) ·
[InstantDM: viral carousel types](https://instantdm.com/blog/create-viral-instagram-carousel-types-that-get-millions-of-views-in-2026) ·
[Virvid: first 3 seconds](https://virvid.ai/blog/first-3-seconds-hook-faceless-shorts-2026) ·
[AI writing tells](https://www.oliviacal.com/post/ai-writing-tells)

## 2c. Quality gates and live X research

- `app/quality.py` wraps the vendored scorers (`app/vendor/jake`, MIT, from
  [instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill) and
  [linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill)). The critic auto-cleans artefacts,
  then hard-fails on human score, hook score, reel timing and the Instagram caption window. Their author measured
  that the hook scorer catches weak hooks well (AUC 0.83) but can't pick between two decent ones (AUC 0.56), so it
  is a floor; the LLM judge and real engagement data decide above it.
- `app/sources/xbird.py` is an MCP stdio client for [xbird](https://github.com/checkra1neth/xbird-skill). It only
  calls allowlisted read tools (checked before the process starts), enforces per-run and per-day spend caps,
  passes a minimal environment, and ranks posts by multiple over each author's median, the same evidence standard
  as `/ig-viral`. Results go into the trend scout's prompt as "live on X this week".

## 2d. AI video (kie.ai)

`app/sources/kie.py` mirrors the request/poll flow of Open-Higgsfield-AI's `src/lib/kie.js` (Veo via
`/api/v1/veo/generate` + `record-info`; Kling, Seedance, Wan, Sora and Nano Banana via `/api/v1/jobs/createTask` +
`recordInfo`) with a daily dollar ledger. `visuals._render_broll_reel` downloads the clips, normalises them to
1080×1920@30, loops/trims to the beat-sheet length, and overlays one transparent PNG per beat (text box + progress bar)
inside the safe zone (y 230–1440, right 230 px clear). Any failure or budget shortfall falls back to the text-motion reel.

## 3. Why human-approval-first

Every post and every reply lands in the dashboard as a draft. You edit the caption or time, then
approve, reject or regenerate. This keeps brand risk near zero while the agents learn your voice.
Once the critic scores track your own approve/reject decisions, you can raise the autonomy (e.g.
auto-approve replies, or posts scoring ≥ 9) by adding a rule in `publisher.py`.

## 4. How the system grows followers

Follower growth on all three platforms comes from reach (the algorithm showing posts to non-followers)
converted into a follow. The system works both levers:

**Reach**
- *Saves and shares are weighted 3×* in the engagement score because they're the strongest distribution
  signals, so the bandit drifts toward formats that earn them (usually IG carousels/reels, LinkedIn
  documents, X threads).
- *Hooks are judged separately* by the critic; the first line/slide/2 seconds decides most reach.
- *Timely posts* come from the research feed; evergreen how-tos keep earning saves for weeks.
- *Consistency*: the scheduler keeps a 3-day buffer per page so cadence never breaks.
- *Fast replies* to comments in the first hours extend a post's life; the engagement agent drafts them every 30 min.

**Conversion to follows**
- Every post ends with a follow-oriented CTA from the page's `cta_options`.
- Pillars force a recognisable series ("tool of the week", numbered threads), which gives people a reason to follow rather than just like.
- Follows per post are weighted 10× in the score.

**What it will never do** — buy followers, run follow/unfollow or mass-like bots, comment-spam other
accounts, or post engagement bait. All three platforms detect this and throttle or ban accounts, and it
fills the page with followers who never engage, which lowers reach for every future post. On X, API
follows and likes aren't available on pay-per-use anyway.

## 5. Platform access (verified Oct 2026)

| | Instagram | LinkedIn (company page) | X |
|---|---|---|---|
| API | Instagram Graph API (container → publish) | Versioned REST Posts API | v2 API |
| Account | Professional account linked to a FB Page | Page admin + **Community Management API** approval | Developer app, pay-per-use credits |
| Formats here | image, carousel (≤10), reel | text, image, document (PDF carousel) | text, thread, image |
| Gotchas | Media must be on a public URL; check `content_publishing_limit` | Review needs a registered legal organization; tokens last 60 days | URL posts are billed much higher than plain posts → system keeps URLs out |

Platform rules and prices change often; re-check the official docs before going live.

## 6. Data model (SQLite → swap for Postgres via `DATABASE_URL`)

- `Draft` — every post/reply: content JSON, media paths, critic scores, status
  (`pending → approved → published | failed`, or `rejected`), scheduled time, platform ID
- `Metric` — snapshots of impressions, likes, comments, shares, saves, follows per post
- `FollowerSnapshot` — follower count per page over time
- `SeenComment` — guarantees the engagement agent never replies twice

## 7. Jobs

| Job | When | What |
|---|---|---|
| plan | daily 06:07 | top up each page's queue to 3 days of posts |
| publish | every 5 min | publish approved posts that are due; approved replies immediately |
| engage | every 30 min | new comments → reply drafts |
| metrics | every 6 h | metrics + follower counts → learning loop |

## 8. Roadmap

1. **Now:** fill `config/pages.yaml` with the real page scopes; run in `dry_run`; review a week of drafts.
2. **Week 1–2:** connect APIs, go `live` with approval on; keep rejecting weak drafts — the reasons you
   reject are the best signal for tightening voice and pillars.
3. **Week 3+:** add a few top creators per niche as reference accounts the research agent studies;
   cross-post winners (a strong X thread → LinkedIn post → IG carousel).
4. **Later:** auto-approve high-scoring replies; voiceover + B-roll for reels; Postgres + a worker queue
   if volume grows.
