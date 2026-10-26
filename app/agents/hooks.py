"""Hook tournament: most posts live or die in the first line / slide / 2 seconds.

1. Generate 7 hooks, one per hook type.
2. A separate judge (fresh context, no authorship bias) scores each as a scroll-stopper for this audience.
3. The winner goes to the writer; the rest are kept so you can swap hooks in the dashboard.
"""
import json

from app import quality
from app.agents.state import PostState
from app.humanize import ai_tells
from app.llm import ask_json
from app.pages import get_page
from app.playbooks import HOOK_TYPES


def hooks_node(state: PostState) -> PostState:
    page = get_page(state["page_id"])
    where = {"instagram": "the first frame / cover slide (shown muted, as on-screen text)",
             "linkedin": "the first 2 lines before 'see more' (~210 characters)",
             "x": "the first 8 words of the post"}[page.platform]
    gen = ask_json("hooks", "You write scroll-stopping hooks for top creators.", f"""
Write hooks for {where}.
PAGE: {page.handle} · niche: {page.niche} · audience: {page.audience} · voice: {page.voice}
TOPIC: {state['topic']}
ANGLE: {state['angle']}
ARCHETYPE: {state.get('archetype')} · GOAL ACTION: {state.get('goal')}
SPECIFICS YOU CAN USE (a number or name from here makes a hook stronger): {json.dumps({k: (state.get('facts') or {}).get(k) for k in ("numbers", "counterintuitive", "mistakes")}, ensure_ascii=False)[:1500]}

Write exactly one hook per type: {json.dumps(HOOK_TYPES)}
Rules: under 12 words where possible; specific, not generic; sounds like a person, not an ad;
no clickbait the post can't pay off; no emojis; no question marks unless the type is "question".
Return: {{"hooks": [{{"type": str, "text": str}}]}}""")
    hooks = [h for h in gen.get("hooks", []) if h.get("text")]

    judged = ask_json("hook_judge", "You are a ruthless judge of social media hooks.", f"""
You're a {page.audience} scrolling {page.platform} fast. Score each hook 0–10 on:
stop: would you stop scrolling?  clarity: do you instantly know what you get?
specific: concrete, not generic?  human: sounds like a real person, not AI or an ad?
Then pick the winner (best overall for reaching people who don't follow {page.handle} yet).

HOOKS
{json.dumps([{"i": i, **h} for i, h in enumerate(hooks)], indent=1)}

Return: {{"scores": [{{"i": int, "stop": n, "clarity": n, "specific": n, "human": n, "total": n}}], "winner": int, "why": str}}""")
    scores = {s["i"]: s for s in judged.get("scores", [])}
    for i, h in enumerate(hooks):
        sc = scores.get(i, {})
        total = sc.get("total") or round(sum(sc.get(k, 0) for k in ("stop", "clarity", "specific", "human")) / 4, 1)
        hs = quality.hook(h["text"])                     # open-source hook scorer: a floor, not a picker
        h["hookscore"], h["verdict"] = hs["score"], hs["verdict"]
        score = 0.6 * float(total) + 0.4 * hs["score"] / 10
        if hs["dealbreakers"]:
            score -= 3
        elif hs["score"] < quality.HOOK_FLOOR:
            score -= 2
        if ai_tells(h["text"]):
            score -= 1.5
        h["score"] = round(score, 1)
    hooks.sort(key=lambda h: h.get("score", 0), reverse=True)
    winner = hooks[0]["text"] if hooks else state.get("topic", "")
    return {"hook": winner, "hook_options": hooks[:5],
            "log": state.get("log", []) + [f"hooks: {len(hooks)} tested, winner {hooks[0]['score'] if hooks else '-'} → {winner}"]}
