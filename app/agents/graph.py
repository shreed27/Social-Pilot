"""The content pipeline as a LangGraph state machine.

research → strategist → depth → hooks → writer → critic ─┬─(revise, ≤ MAX_REVISIONS)→ writer
                                          └─(pass)→ visuals → queue_for_approval → END
"""
import logging

from langgraph.graph import END, StateGraph

from app.agents.critic import critic_node, route_after_critic
from app.agents.depth import depth_node
from app.agents.hooks import hooks_node
from app.agents.research import research_node
from app.agents.state import PostState
from app.agents.strategist import strategist_node
from app.agents.visuals import visuals_node
from app.agents.writer import writer_node
from app.analytics import next_slot
from app.db import Draft, DraftStatus, session
from app.settings import get_settings
from app.notify import notify
from app.pages import get_page

log = logging.getLogger(__name__)


def queue_node(state: PostState) -> PostState:
    page = get_page(state["page_id"])
    draft = Draft(page_id=page.id, platform=page.platform, format=state["format"], pillar=state["pillar"],
                  topic=state["topic"], angle=state["angle"], content=state["content"],
                  media=state.get("media", []), critic=state.get("critic", {}), trace=state.get("log", []),
                  scheduled_at=next_slot(page))
    s = get_settings()
    crit = draft.critic or {}
    auto = (s.auto_approve_min_score > 0 and crit.get("verdict") == "pass" and not crit.get("violations")
            and float(crit.get("viral_score") or 0) >= s.auto_approve_min_score)
    if auto:  # opt-in autopilot: only drafts that cleared every gate AND scored at or above the bar
        draft.status = DraftStatus.approved
        draft.trace = list(draft.trace) + [f"auto-approved (viral {crit.get('viral_score')} ≥ {s.auto_approve_min_score})"]
    with session() as db:
        db.add(draft)
        db.commit()
        db.refresh(draft)
    if auto:
        notify(f"🚀 Auto-approved {page.platform} {draft.format} for {page.handle}: “{draft.topic}” "
               f"(viral {crit.get('viral_score')}). Posts at its slot unless you reject it.")
        return {"draft_id": draft.id, "log": state.get("log", []) + [f"queued + auto-approved draft #{draft.id}"]}
    notify(f"📝 New {page.platform} {draft.format} draft for {page.handle}: “{draft.topic}” "
           f"(score {draft.critic.get('overall')}). Review it in the dashboard.")
    return {"draft_id": draft.id, "log": state.get("log", []) + [f"queued draft #{draft.id}"]}


def build_graph():
    g = StateGraph(PostState)
    g.add_node("research", research_node)
    g.add_node("strategist", strategist_node)
    g.add_node("depth", depth_node)
    g.add_node("hooks", hooks_node)
    g.add_node("writer", writer_node)
    g.add_node("critic", critic_node)
    g.add_node("visuals", visuals_node)
    g.add_node("queue", queue_node)
    g.set_entry_point("research")
    g.add_edge("research", "strategist")
    g.add_edge("strategist", "depth")
    g.add_edge("depth", "hooks")
    g.add_edge("hooks", "writer")
    g.add_edge("writer", "critic")
    g.add_conditional_edges("critic", route_after_critic, {"writer": "writer", "visuals": "visuals"})
    g.add_edge("visuals", "queue")
    g.add_edge("queue", END)
    return g.compile()


_graph = None


def generate_post(page_id: str, *, pillar: str | None = None, fmt: str | None = None) -> PostState:
    global _graph
    _graph = _graph or build_graph()
    init: PostState = {"page_id": page_id, "log": []}
    if pillar:
        init["pillar"] = pillar
    if fmt:
        init["format"] = fmt
    result = _graph.invoke(init)
    for line in result.get("log", []):
        log.info("[%s] %s", page_id, line)
    return result
