"""Depth agent: builds a fact pack for the chosen topic so posts teach something specific.

Generic posts ("5 tips to study better") don't get saved or sent. Posts that hand people an exact
method, a surprising number with a source, a named tool, or the mistake everyone makes do.
With RESEARCH_WEB_SEARCH=true this agent looks things up; otherwise it works from model knowledge
and marks anything checkable as "verify", which the dashboard shows next to the draft.
"""
import json

from app.agents.state import PostState
from app.llm import ask_json
from app.pages import get_page
from app.settings import get_settings


def depth_node(state: PostState) -> PostState:
    s = get_settings()
    page = get_page(state["page_id"])
    search = s.research_web_search
    out = ask_json("depth", "You are a meticulous researcher for a top creator. You never invent facts.", f"""
Build a FACT PACK for one {page.platform} post.

AUDIENCE: {page.audience}
NICHE: {page.niche}
TOPIC: {state['topic']}
ANGLE: {state['angle']}
ARCHETYPE: {state.get('archetype')}

{"Use web search (max 5 searches) to find current, checkable specifics. Prefer primary sources." if search else
 "You can't browse. Use well-established knowledge only, and mark every number or claim a reader could check as verify=true."}

Collect what makes a post worth saving: the exact steps (with timings/quantities), 2–4 numbers that
surprise this audience (each with where it comes from), named tools/places/people's roles (no private
individuals), real examples or scenarios from this audience's daily life, the most common mistake and
why it happens, and one counterintuitive point. Skip anything generic. Never make up a statistic.

Return: {{"key_points": [{{"point": str, "detail": str, "example": str}}],
"steps": [str], "numbers": [{{"stat": str, "context": str, "source": str, "url": str, "verify": bool}}],
"names": [str], "mistakes": [{{"mistake": str, "why": str, "fix": str}}], "counterintuitive": str,
"sources": [{{"title": str, "url": str}}]}}""", web_search=search, max_tokens=5000)
    n = sum(len(out.get(k) or []) for k in ("key_points", "steps", "numbers", "mistakes"))
    return {"facts": out, "log": state.get("log", []) + [f"depth: fact pack with {n} specifics"
                                                        + (f", {len(out.get('sources') or [])} sources" if out.get("sources") else "")]}


def facts_prompt(facts: dict | None) -> str:
    if not facts:
        return ""
    return ("FACT PACK (your raw material: use at least 4 specifics from it; numbers ONLY from here, "
            "and keep any marked verify=true out of the post unless it's framed as an example):\n"
            + json.dumps(facts, indent=1, ensure_ascii=False))
