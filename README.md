# SocialPilot

Agentic automation for your Instagram, LinkedIn and X pages: research → strategy → writing →
self-review → visuals → **your approval** → scheduled publishing → comment replies → analytics that
feed back into what gets posted next. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and
growth plan.

## Quick start (offline, no keys needed)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # MODE=dry_run, nothing gets posted
export LLM_PROVIDER=mock           # canned agent output for a first look
python cli.py generate insta_main --format carousel
python cli.py generate x_main --format thread
uvicorn app.web.main:app --reload  # http://localhost:8000  (any username, password from .env)
pytest -q                          # end-to-end test of every format
```

Then set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` to get real drafts (still in `dry_run`).

## The dashboard

A React app in `frontend/` (React 19 + TypeScript, shadcn/ui-style components on Radix primitives,
Tailwind CSS v4, Recharts 3, Motion, cmdk ⌘K palette, Sonner toasts). A prebuilt copy ships in
`frontend/dist`, so `uvicorn app.web.main:app` serves it at http://localhost:8000 with no Node needed.

- **Command center**: follower growth across pages, KPIs, live agent pipeline, best hours, activity, up next
- **Approval queue**: native Instagram / LinkedIn / X previews, editable copy and threads, critic radar, agent trace, schedule, approve / regenerate / reject
- **Calendar**: week view of every slot · **Analytics**: per-page pillars, formats, sortable post table · **Pages & agents**
- Press **⌘K / Ctrl+K** for search and commands; the sun/moon button switches themes.

To change the UI:

```bash
cd frontend && npm install
npm run dev            # http://localhost:5173, proxies /api to the backend on :8000
npm run build          # rebuilds frontend/dist
```

If the API isn't reachable, the dashboard runs on built-in sample data (`npm run build:artifact` makes a
single-file preview; `python scripts/build_demo_data.py` regenerates the sample set). The original
server-rendered page is still available at `/classic`.

## 1. Describe your pages

Everything the agents know comes from `config/pages.yaml`: niche, audience, goal, voice, content
pillars, allowed formats, cadence, preferred slots, hashtags, brand colours, trend feeds, topics to
avoid and CTAs. Replace every `<FILL ME>`. The more specific the audience and pillars, the better
the output.

To make posts spread, also:
- list 3–10 top accounts in each niche under `reference_accounts`,
- paste a few viral posts from your niche into `config/swipe/<page_id>.md` (see `config/swipe/README.md`),
- set `RESEARCH_WEB_SEARCH=true` so the trend scout checks what's spreading this week before every draft.

## Deep posts, posting on approve, Slack

**Depth.** Before writing, a depth agent builds a fact pack for the topic: exact steps with timings, numbers with
their sources, named tools, real examples from the audience's week, the common mistake and why it happens. The
writer must use at least four of them, and the critic scores *depth* and enforces floors (8–10 slide carousels with
real bodies, ≥ 3 slide layouts, 300+ character Instagram captions, 1,100+ character LinkedIn posts, 5+ post threads).
Numbers it couldn't verify are listed under "Check before posting" in the dashboard. Turn on
`RESEARCH_WEB_SEARCH=true` so the fact pack comes from live sources.

**Pictures.** Slides use the layout that fits the point: `text`, `list`, numbered `steps`, a big-number `stat`
with its source, an `image` slide (AI photo via kie.ai, max 2 per carousel), or a `compare` panel.

**Approve = post.** In the dashboard, *Approve & post now* publishes immediately through the platform's API
(the dashboard refreshes when it's live, and Slack confirms with a link). *Schedule* keeps it for its slot.
Drafts are claimed atomically, so a post can never go out twice. In `MODE=dry_run` posting is simulated; set
`MODE=live` once your platform tokens are in `.env`.

**Slack.** Create a Slack app at api.slack.com/apps → *Incoming Webhooks* → *Add New Webhook to Workspace*, pick
your channel, and put the URL in `SLACK_WEBHOOK_URL`. Then `python cli.py slack-test`. You'll get:
- ✅ every post that goes live, with a link · ❌ any failure, with the reason and a retry button
- 📝 one message per planning run with the drafts waiting for review (`SLACK_NOTIFY_DRAFTS`)
- 📊 a daily report at `SLACK_DIGEST_TIME` (default 21:00): followers and growth per page, what went out,
  the best post of the week with reach/saves/shares/follows, what's scheduled next, failures, and spend.
  `python cli.py slack-digest` sends it now. Set `DASHBOARD_URL` so the buttons open your dashboard.

## AI video and the all-day schedule

**AI B-roll reels via kie.ai** (the same API the [Open-Higgsfield-AI](https://github.com/Autom8AI/Open-Higgsfield-AI)
studio uses; SocialPilot calls it directly so nobody has to click through a studio). Get a key at kie.ai, set
`KIE_API_KEY`, and every reel gets 1–3 AI shots planned by the writer, generated in 9:16, stitched, with the hook and
beats burned in inside Instagram's safe zone. Image posts and carousel covers get an AI photo background too.

| | Default | Approx. cost |
|---|---|---|
| Reel clips | `veo3_fast`, 2 clips per reel | ~$0.40 per clip → ~$0.80 per reel |
| Images / covers | `nano-banana-2` | ~$0.04 each |
| Daily cap | `KIE_DAILY_BUDGET_USD=3.00` | hard stop; reels fall back to text-motion |

AI video models can't render text reliably, so shots never contain text, logos, screens or real people; all text is
added by SocialPilot. Clips are silent by default: add a trending sound in the Instagram app (the API can't attach
licensed music), which also helps reach. Set `KIE_KEEP_AUDIO=true` to keep the model's own audio instead.

**Posting all day** (`config/pages.yaml`): Instagram ~2/day (12/week, spaced 8 h+ apart), LinkedIn 1/day, X ~4/day.
The planner runs at 06:07 and 14:07 so timely ideas keep arriving, and keeps `PLAN_DAYS_AHEAD` days queued.

**Autopilot (opt-in)**: `AUTO_APPROVE_MIN_SCORE=9.0` auto-approves only drafts that pass every quality gate *and*
score ≥ 9.0 on viral potential; everything else still waits for you, and you get a Telegram ping either way.
Start at 0 (off) for the first couple of weeks, until the drafts you approve and the ones the critic passes agree.

Rough daily spend at this cadence with video on: ~$1–2 kie.ai + ~$0.10–0.30 xbird (if enabled) + LLM usage.

## Quality gates and X research

**Quality gates** (always on): every draft is cleaned and scored by Jake Schincariol's open-source
scorers, vendored in `app/vendor/jake` (MIT):
- invisible watermark characters, em dashes, curly quotes and 150+ stock AI phrases are stripped automatically
- human score must PASS (≥ 70 with every check ≥ 55: burstiness, specificity, slop, fingerprint, voice)
- hook score must be ≥ 50 with no dealbreakers (greetings, "stop scrolling"…)
- reels: hook lands within ~3 s, no beat over 4 s, last beat loops back to the hook
- Instagram: the caption must survive the 125-character "… more" cut

Anything that fails goes back to the writer with the exact reason. The dashboard shows the scores per draft.

**X research via xbird** (optional, read-only): set `XBIRD_ENABLED=true`, fill `search_keywords` (and
`reference_accounts`) in `pages.yaml`, then on the machine where you're logged in to x.com:

```bash
npx @checkra1n/xbird login          # once; or install Bun and it reads your browser session itself
# fund the wallet xbird creates (USDC on Base). A 20-post search costs about $0.05
python cli.py xbird-scout x_main    # see what's working this week, ranked by outlier multiple
```

The trend scout then feeds those posts into every draft. SocialPilot only calls xbird's search/read
tools, caps calls per run (`XBIRD_MAX_CALLS_PER_RUN`) and spend per day (`XBIRD_DAILY_BUDGET_USD`), and
starts it with a minimal environment so it never sees your other keys. It's unofficial: X's terms
don't allow cookie-based automation, so use it on an account you're prepared to risk, and keep
posting through the official API (below).

**Claude Code skills**: for writing by hand in Claude Code, install the same author's skills:
`/plugin marketplace add Jakeschincariol/instagram-agent-skill` then `/plugin install instagram-agent`
(gives `/ig-reel`, `/ig-caption`, `/ig-viral`…), and the same for `linkedin-agent-skill` (`/li-post`…).

## 2. Connect the platforms

**Instagram** — convert to a Professional account and link it to a Facebook Page. In a Meta developer
app add the Instagram product, grant `instagram_basic`, `instagram_content_publish`,
`instagram_manage_comments`, `instagram_manage_insights`, generate a long-lived token, and set
`IG_USER_ID`, `IG_ACCESS_TOKEN`. Instagram fetches media by URL, so expose `/media` publicly
(Cloudflare Tunnel / ngrok) or sync `data/media` to S3/R2, and set `PUBLIC_MEDIA_BASE_URL`.

**LinkedIn** — create an app tied to your company Page, have a Page super admin verify it, and apply
for the **Community Management API** (requires a registered legal organization). With
`w_organization_social`, `r_organization_social` and `rw_organization_admin`, run the OAuth flow as a
Page admin and set `LINKEDIN_ACCESS_TOKEN` (expires in 60 days) and `organization_urn` in pages.yaml.

**X** — create a project + app at developer.x.com, load pay-per-use credits, enable OAuth 2.0 with
`tweet.read tweet.write users.read media.write offline.access`, and set `X_ACCESS_TOKEN`, `X_USER_ID`.
Plain posts are cheap; posts containing URLs cost much more, which is why the agents never put links in X posts.

Set `MODE=live` only after a few days of reviewing drafts in `dry_run`.

## 3. Daily use

Open the dashboard → **Pending**. Each card shows the copy (editable), media preview, editor scores and
any rule warnings. *Approve & schedule* (time is pre-filled with the best free slot), *Reject*, or
*Regenerate* (same pillar/format, new idea). Approved posts go out at their time; approved replies go
out within 5 minutes. Optional: set `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` to get pinged when drafts are waiting.

## Project layout

```
config/pages.yaml        page scopes (the agents' brief)
app/agents/              research, strategist, writer, critic, visuals, LangGraph wiring
app/platforms/           Instagram, LinkedIn, X clients + dry-run client
app/engagement.py        comment → reply drafts
app/analytics.py         metrics, follower tracking, bandit, best-slot scheduling
app/publisher.py         publishes approved drafts
app/scheduler.py         background jobs
app/web/                 FastAPI approval dashboard
cli.py                   run any step by hand
tests/test_pipeline.py   offline end-to-end tests
```

## CLI

```
python cli.py pages                         # list configured pages
python cli.py generate <page_id> [--format carousel|reel|image|document|text|thread] [--pillar how-to]
python cli.py fill | publish | engage | metrics
```
