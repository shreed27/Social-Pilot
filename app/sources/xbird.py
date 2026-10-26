"""Read-only X trend research through xbird (github.com/checkra1neth/xbird-skill).

xbird is an MCP server that talks to X with YOUR logged-in x.com browser session (no developer
account) and charges per call in USDC from a wallet it generates. This module:

- only ever calls tools in READ_TOOLS; anything else raises, so it can never post, like or follow
- caps calls per run and spend per day (XBIRD_MAX_CALLS_PER_RUN, XBIRD_DAILY_BUDGET_USD)
- ranks what it finds by how far each post beat its own author's median in the sample
  (raw likes favour big accounts; the multiple shows which ideas travelled)

Usage: XBIRD_ENABLED=true, then the research agent calls scout(page) before every draft, or run
`python cli.py xbird-scout <page_id>` to see the table.
"""
import asyncio
import json
import logging
import re
import shlex
import statistics
from datetime import date, datetime, timedelta, timezone

from app import quality
from app.pages import Page
from app.settings import get_settings

log = logging.getLogger(__name__)

READ_TOOLS = {"search_tweets", "get_user_tweets_by_handle", "get_news", "get_explore_page", "get_tweet"}
# Published xbird rates (resource × count). Used only to enforce the daily budget.
RATE = {"search_tweets": 0.0025, "get_user_tweets_by_handle": 0.0025, "get_news": 0.0025,
        "get_explore_page": 0.0025, "get_tweet": 0.0025}
COUNT = 20


class BudgetExceeded(RuntimeError):
    pass


# ── spend ledger ─────────────────────────────────────────────────────────────

def _ledger_path():
    return get_settings().media_dir.parent / "xbird_spend.json"


def spent_today() -> float:
    try:
        d = json.loads(_ledger_path().read_text())
        return float(d.get(date.today().isoformat(), 0))
    except (OSError, ValueError):
        return 0.0


def _record(cost: float) -> None:
    p = _ledger_path()
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        d = {}
    k = date.today().isoformat()
    d[k] = round(float(d.get(k, 0)) + cost, 4)
    p.write_text(json.dumps(d))


# ── result parsing (tolerant: xbird returns JSON text content) ────────────────

TEXT_KEYS = ("full_text", "text", "content")
NUM = {
    "likes": ("favorite_count", "likeCount", "like_count", "likes", "favoriteCount"),
    "reposts": ("retweet_count", "retweetCount", "repost_count", "retweets"),
    "replies": ("reply_count", "replyCount", "replies"),
    "quotes": ("quote_count", "quoteCount", "quotes"),
    "bookmarks": ("bookmark_count", "bookmarkCount", "bookmarks"),
    "views": ("view_count", "viewCount", "views", "impression_count", "impressions"),
}
AUTHOR_KEYS = ("screen_name", "username", "handle", "userName")


def _num(v) -> int:
    if isinstance(v, dict):
        v = v.get("count", 0)
    try:
        return int(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return 0


def _pick(d: dict, keys) -> object:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    for sub in ("legacy", "public_metrics", "metrics", "stats"):
        if isinstance(d.get(sub), dict):
            for k in keys:
                if k in d[sub]:
                    return d[sub][k]
    return None


def _author(d: dict) -> str:
    a = _pick(d, AUTHOR_KEYS)
    if a:
        return str(a)
    for k in ("user", "author", "core"):
        if isinstance(d.get(k), dict):
            got = _author(d[k])
            if got:
                return got
    return ""


def extract_posts(payload) -> list[dict]:
    out, seen = [], set()

    def walk(x):
        if isinstance(x, dict):
            text = _pick(x, TEXT_KEYS)
            likes = _pick(x, NUM["likes"])
            if isinstance(text, str) and likes is not None:
                key = " ".join(text.split()).lower()
                if key not in seen:      # nested copies (e.g. "legacy") describe the same post
                    seen.add(key)
                    out.append({"id": str(x.get("id") or x.get("rest_id") or x.get("id_str") or ""),
                                "text": text.strip(), "author": _author(x),
                                **{k: _num(_pick(x, keys)) for k, keys in NUM.items()}})
                return
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(payload)
    return out


def rank(posts: list[dict], top: int = 10) -> list[dict]:
    for p in posts:
        # X's ranker weighs replies and bookmarks far above likes (see app/playbooks.py)
        p["engagement"] = p["likes"] + 2 * p["reposts"] + 3 * p["replies"] + 2 * p["quotes"] + 3 * p["bookmarks"]
    by_author: dict[str, list[int]] = {}
    for p in posts:
        by_author.setdefault(p["author"] or "?", []).append(p["engagement"])
    overall = statistics.median([p["engagement"] for p in posts]) if posts else 1
    for p in posts:
        base = statistics.median(by_author[p["author"] or "?"]) if len(by_author[p["author"] or "?"]) >= 3 else overall
        p["multiple"] = round(p["engagement"] / max(base, 1), 1)
        first = re.split(r"\n|(?<=[.!?])\s", p["text"], maxsplit=1)[0][:200]
        h = quality.hook(first)
        p["hook"], p["hook_score"] = first, h["score"]
    posts.sort(key=lambda p: (p["multiple"], p["engagement"]), reverse=True)
    return posts[:top]


# ── MCP client ───────────────────────────────────────────────────────────────

def _preflight(calls: list[tuple[str, dict]]) -> list[tuple[str, dict, float]]:
    """Refuse anything that isn't a read tool, and drop calls that would exceed today's budget,
    before xbird is even started."""
    s = get_settings()
    planned, budget_left = [], s.xbird_daily_budget_usd - spent_today()
    for name, args in calls:
        if name not in READ_TOOLS:
            raise PermissionError(f"xbird tool '{name}' is not read-only; refusing to call it")
        cost = RATE[name] * int(args.get("count", COUNT))
        if cost > budget_left + 1e-9:
            if not planned:
                raise BudgetExceeded(f"xbird daily budget ${s.xbird_daily_budget_usd:.2f} reached")
            break
        budget_left -= cost
        planned.append((name, args, cost))
    return planned


async def _run(calls: list[tuple[str, dict]]) -> list:
    import os

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import get_default_environment, stdio_client

    s = get_settings()
    argv = shlex.split(s.xbird_command)
    # Minimal environment (HOME, PATH...) so a third-party process never sees your other API keys.
    env = {**get_default_environment(), **{k: v for k, v in os.environ.items() if k.startswith(("XBIRD_", "FAKE_XBIRD_"))}}
    params = StdioServerParameters(command=argv[0], args=argv[1:], env=env)
    planned = _preflight(calls)
    results = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for name, args, cost in planned:
                res = await session.call_tool(name, args)
                _record(cost)
                for c in res.content or []:
                    txt = getattr(c, "text", None)
                    if txt:
                        try:
                            results.append(json.loads(txt))
                        except ValueError:
                            results.append({"text_blob": txt})
                if getattr(res, "structuredContent", None):
                    results.append(res.structuredContent)
    return results


def plan_calls(page: Page) -> list[tuple[str, dict]]:
    s = get_settings()
    since = (datetime.now(timezone.utc) - timedelta(days=s.xbird_lookback_days)).strftime("%Y-%m-%d")
    terms = page.search_keywords or [" ".join(page.niche.split()[:4])]
    calls = [("search_tweets", {"query": f'{t} min_faves:{s.xbird_min_likes} -is:retweet -filter:replies lang:en since:{since}',
                                "count": COUNT}) for t in terms if "FILL" not in t.upper()]
    calls += [("get_user_tweets_by_handle", {"handle": h.lstrip("@"), "count": COUNT})
              for h in page.reference_accounts if "FILL" not in h.upper()]
    return calls[: s.xbird_max_calls_per_run]


def scout(page: Page, top: int = 10) -> list[dict]:
    """Returns the top posts in the niche this week, or [] if disabled / nothing to search / failed."""
    s = get_settings()
    if not s.xbird_enabled:
        return []
    calls = plan_calls(page)
    if not calls:
        log.info("xbird: no search_keywords or reference_accounts for %s", page.id)
        return []
    try:
        payloads = asyncio.run(_run(calls))
    except BudgetExceeded as e:
        log.warning("%s", e)
        return []
    except Exception as e:  # noqa: BLE001  (xbird not installed, not logged in, wallet empty...)
        log.warning("xbird scout failed for %s: %s", page.id, e)
        return []
    posts = extract_posts(payloads)
    return rank(posts, top)


def as_prompt(posts: list[dict]) -> str:
    lines = []
    for p in posts:
        lines.append(f"- {p['multiple']}× its author's usual · {p['likes']} likes, {p['replies']} replies, "
                     f"{p['bookmarks']} bookmarks · @{p['author'] or '?'}: \"{p['text'][:280]}\"")
    return "\n".join(lines)
