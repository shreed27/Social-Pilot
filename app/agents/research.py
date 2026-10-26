"""Research agent / trend scout: finds what's earning attention in the niche right now.

Inputs: RSS headlines, optional live web search (RESEARCH_WEB_SEARCH=true) that studies what is
going viral on the platform this week and what the page's reference accounts are posting, the
page's own top performers, and the swipe file of saved viral posts.
"""
import json
import logging
import xml.etree.ElementTree as ET
from datetime import timedelta

import httpx

from app.agents.state import PostState
from app.analytics import performance_summary
from app.db import Draft, select, session, utcnow
from app.llm import ask_json
from app.pages import get_page
from app.playbooks import archetypes_for
from app.settings import get_settings
from app.sources import xbird

log = logging.getLogger(__name__)


def fetch_headlines(urls: list[str], limit: int = 25) -> list[str]:
    out: list[str] = []
    for url in urls:
        if "FILL" in url.upper():
            continue
        try:
            r = httpx.get(url, timeout=15, follow_redirects=True, headers={"User-Agent": "socialpilot/1.0"})
            root = ET.fromstring(r.content)
            for item in root.iter():
                if item.tag.endswith("item") or item.tag.endswith("entry"):
                    title = next((c.text for c in item if c.tag.endswith("title")), None)
                    if title:
                        out.append(title.strip())
        except Exception as e:  # noqa: BLE001
            log.warning("feed failed %s: %s", url, e)
    return out[:limit]


def recent_topics(page_id: str, days: int = 30) -> list[str]:
    with session() as db:
        rows = db.exec(select(Draft.topic).where(Draft.page_id == page_id,
                                                 Draft.created_at >= utcnow() - timedelta(days=days))).all()
    return [t for t in rows if t]


def research_node(state: PostState) -> PostState:
    s = get_settings()
    page = get_page(state["page_id"])
    headlines = fetch_headlines(page.sources)
    already = recent_topics(page.id)
    top = performance_summary(page).get("top_posts", [])
    swipe = page.swipe_file()
    x_live = xbird.scout(page)          # [] unless XBIRD_ENABLED
    scout = ""
    if s.research_web_search:
        refs = ", ".join(page.reference_accounts) or "the biggest accounts in this niche"
        scout = f"""
LIVE TREND SCOUTING (use web search, max 5 searches):
1. What is getting unusually high shares/saves/comments on {page.platform} in "{page.niche}" in the last 7–14 days?
2. What formats and hooks are {refs} using in their best recent posts?
3. Any news, launch, exam date, policy change or meme this audience is talking about right now?
Use findings to shape ideas. Do not copy anyone's post; find the underlying angle."""

    prompt = f"""You find post ideas that can break out of the page's follower base.

PAGE BRIEF
{page.brief()}

CONTENT ARCHETYPES THAT SPREAD ON {page.platform.upper()}
{json.dumps({k: v['structure'] for k, v in archetypes_for(page.platform).items()}, indent=1)}

TODAY'S HEADLINES IN THE NICHE
{chr(10).join('- ' + h for h in headlines) or '(none)'}

THIS PAGE'S BEST PERFORMERS SO FAR (make more of what worked, from a new angle)
{json.dumps(top, indent=1) or '(no data yet)'}

{"LIVE ON X THIS WEEK (via xbird, ranked by how far each post beat its author's usual engagement). "
 "Find the underlying angle and why it travelled; never copy wording:" + chr(10) + xbird.as_prompt(x_live) + chr(10) if x_live else ""}
SAVED VIRAL POSTS FROM THE NICHE (study why they worked; never copy)
{swipe or '(none saved)'}

TOPICS ALREADY COVERED IN THE LAST 30 DAYS (do not repeat)
{chr(10).join('- ' + t for t in already) or '(none)'}
{scout}

Propose 8 ideas. For each, the test is: would someone in this audience SEND it to a friend, SAVE
it, or feel compelled to REPLY? Ideas must be specific (a named tool, a real situation, an exact
mistake), never generic ("tips for productivity"). Mix 3 timely ideas with 5 evergreen ones.
Return: {{"ideas": [{{"topic": str, "pillar": str, "archetype": str, "why_it_spreads": str, "timely": bool, "source": str}}]}}"""
    out = ask_json("research", "You are a trend scout who studies what goes viral.", prompt,
                   web_search=s.research_web_search)
    ideas = out.get("ideas", [])
    return {"ideas": ideas, "log": state.get("log", []) + [f"research: {len(ideas)} ideas from {len(headlines)} headlines"
                                                           + (" + live trend scan" if scout else "")
                                                           + (f" + {len(x_live)} live X posts via xbird" if x_live else "")]}
