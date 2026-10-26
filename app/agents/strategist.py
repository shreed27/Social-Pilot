"""Strategist agent: picks pillar, format and archetype (bandits over past results), the idea, the
goal action (send / save / comment / reply), and the visual template."""
import json

from app.agents.state import PostState
from app.analytics import performance_summary, pick_archetype, pick_arm
from app.llm import ask_json
from app.pages import get_page
from app.playbooks import ARCHETYPES, PLATFORM_PLAYBOOK, TEMPLATES, archetypes_for, playbook_text


def strategist_node(state: PostState) -> PostState:
    page = get_page(state["page_id"])
    perf = performance_summary(page)
    pillar, fmt = state.get("pillar") or None, state.get("format") or None
    if not (pillar and fmt):
        bp, bf = pick_arm(page)
        pillar, fmt = pillar or bp, fmt or bf
    allowed = list(archetypes_for(page.platform))
    suggested = pick_archetype(page, allowed)
    visual = fmt in ("carousel", "document", "image")

    prompt = f"""You are the growth strategist. The only KPI is net new followers from the niche, which
comes from posts that reach NON-followers. Plan the next post.

PAGE BRIEF
{page.brief()}

{playbook_text(page.platform)}

ARCHETYPES ALLOWED ON THIS PLATFORM
{json.dumps({k: {'goal': ARCHETYPES[k]['goal'], 'structure': ARCHETYPES[k]['structure']} for k in allowed}, indent=1)}
The bandit suggests "{suggested}" (it has been working or needs testing). Use it unless an idea clearly fits another better.
{"VISUAL TEMPLATES: " + json.dumps(TEMPLATES) if visual else ""}

WHAT HAS WORKED SO FAR
{json.dumps(perf, indent=1)}

CANDIDATE IDEAS FROM THE TREND SCOUT
{json.dumps(state.get('ideas', []), indent=1)}

The post is fixed to PILLAR: {pillar} and FORMAT: {fmt}.
Pick the single idea most likely to be SENT to a friend or SAVED by this exact audience, and sharpen it:
- angle: the specific promise (concrete, a number or named thing where possible)
- goal: the one action this post is engineered for, from {PLATFORM_PLAYBOOK[page.platform]['best_actions']}
- why_viral: one sentence on the emotion or usefulness that makes someone act (be honest)
Return: {{"topic": str, "angle": str, "archetype": str, "goal": str, "why_viral": str{', "template": str' if visual else ''}}}"""
    out = ask_json("strategy", "You are a data-driven social media growth strategist.", prompt)
    arch = out.get("archetype") if out.get("archetype") in allowed else suggested
    template = out.get("template") if out.get("template") in TEMPLATES else ("split" if arch == "before_after" else "bold")
    return {
        "performance": perf, "pillar": pillar, "format": fmt,
        "topic": out["topic"], "angle": out["angle"], "archetype": arch, "goal": out.get("goal", ""),
        "why_viral": out.get("why_viral", ""), "template": template if visual else "", "revisions": 0,
        "log": state.get("log", []) + [f"strategy: {pillar}/{fmt}/{arch} → {out['topic']} (goal: {out.get('goal', '?')})"],
    }
