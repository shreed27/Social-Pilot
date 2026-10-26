"""Writer agent: turns the plan into platform-native, human-sounding copy built for one action."""
from app.agents.depth import facts_prompt
from app.agents.state import PostState
from app.humanize import HUMAN_VOICE_RULES
from app.llm import ask_json
from app.pages import get_page
from app.playbooks import ARCHETYPES, playbook_text

SLIDE_LAYOUTS = (
    "Each slide has a 'layout': "
    "'text' (title + 18–40 word body: the how/why plus a concrete example) · "
    "'list' (title + 'items': 3–5 short, specific bullets) · "
    "'steps' (title + 'items': 3–6 numbered actions with timings/quantities) · "
    "'stat' ('stat': the number, e.g. '2 min' or '68%', title = what it means, body = context, 'source') · "
    "'image' (title ≤ 8 words + 'image_prompt': a concrete photo/illustration scene that SHOWS the point; "
    "no text, logos, screens or real people) · "
    "'compare' (title + 'left' = common way, 'right' = better way, ≤ 12 words each). "
    "Use at least 3 different layouts, at most 2 'image' slides, never two 'stat' slides in a row."
)

FORMAT_RULES = {
    "carousel": "8–10 slides. Slide 1 = cover: the hook (≤ 10 words) + a subline that makes them swipe (layout 'text'). "
                "Every middle slide teaches ONE specific thing in enough depth to act on it today, and makes sense "
                "alone (Instagram re-shows unswiped slides). Second-to-last = the payoff or twist. Last = one CTA "
                "built for the goal action. " + SLIDE_LAYOUTS + " Caption: 400–1,200 characters, a mini-article that "
                "adds context NOT on the slides (the story behind it, one extra tip, who it's for) and the niche's "
                "search words in plain sentences.",
    "document": "9–12 pages. Page 1 = hook + promise. One idea per page, explained with an example. Final page = "
                "summary of takeaways + one question for the comments. " + SLIDE_LAYOUTS +
                " Post text: 700–1,300 characters that set up why this matters, with one concrete story.",
    "reel": "6–9 on-screen text beats, 12–25 s total. Beat 1 (≤ 1.5 s) IS the hook, readable muted. By second 3 "
            "the viewer must know the payoff. 1.2–2.5 s per beat; every beat adds something new and specific. The last "
            "beat loops back into the first. Plan 1–3 B-roll shots (5–8 s each) that will be AI-generated behind the "
            "text: concrete, filmable scenes with camera motion that SHOW the idea (e.g. 'close-up of a hand closing a "
            "notebook on a hostel desk at night, slow push-in, warm lamp light'). No text, screens, logos, brands or "
            "real people in shots. Caption: 300–900 characters with the full method written out, so people save it.",
    "image": "One image with a headline of ≤ 8 words that works as a standalone screenshot, plus a 'cover_prompt' "
             "for the picture. Caption: 500–1,500 characters that deliver the full value (steps, example, why).",
    "text": "LinkedIn: 1,100–1,800 characters: hook, one concrete story or example with real detail, 3–5 specific "
            "takeaways, a turn, a closing question. X: one post ≤ 270 characters with one sharp, specific idea.",
    "thread": "6–10 posts. Post 1 = standalone hook that promises the payoff. Each post carries one specific, usable "
              "point (a number, a named tool, an exact step, an example). Last post recaps or lands the twist.",
}

SLIDE_SPEC = ('{"layout": "text|list|steps|stat|image|compare", "title": str, "body": str, "items": [str], '
              '"stat": str, "source": str, "image_prompt": str, "left": str, "right": str, "highlight": str (1–2 words of the title to colour)}')

FORMAT_SPEC = {
    "text": '{"caption": str, "hashtags": [str], "cta": str, "sources": [{"title": str, "url": str}]}',
    "thread": '{"thread": [str], "caption": str (= first post), "hashtags": [str], "cta": str, "sources": [{"title": str, "url": str}]}',
    "image": '{"caption": str, "image_headline": str, "highlight": str (1–2 words of the headline to colour), "cover_prompt": str (photo scene behind the headline, no text), "hashtags": [str], "cta": str, "alt_text": str, "sources": [{"title": str, "url": str}]}',
    "carousel": '{"caption": str, "slides": [' + SLIDE_SPEC + '], "cover_prompt": str (optional photo scene behind the cover slide, no text), "hashtags": [str], "cta": str, "alt_text": str, "sources": [{"title": str, "url": str}]}',
    "document": '{"caption": str, "slides": [' + SLIDE_SPEC + '], "hashtags": [str], "cta": str, "sources": [{"title": str, "url": str}]}',
    "reel": '{"caption": str, "reel_script": [{"text": str, "seconds": float, "highlight": str}], "broll": [{"scene": str, "seconds": int}], "hashtags": [str], "cta": str, "sources": [{"title": str, "url": str}]}',
}

GOAL_CTA = {
    "send": "End with a send prompt that names the person ('Send this to the friend who still…').",
    "save": "End with a save prompt tied to a moment they'll need it ('Save this for exam week').",
    "comment": "End with a specific question people can answer from their own experience.",
    "reply": "End on a statement people will want to argue with or add to. No 'thoughts?'.",
    "bookmark": "Make it a reference worth coming back to.",
    "watch_time": "Make the last beat loop back to the first.",
    "dwell": "Reward reading to the end with the best insight last.",
    "profile_click": "Make the reader curious who wrote this.",
}


def writer_node(state: PostState) -> PostState:
    page = get_page(state["page_id"])
    fmt = state["format"]
    arch = ARCHETYPES.get(state.get("archetype", ""), {})
    feedback = ""
    if state.get("critic") and state["critic"].get("verdict") != "pass":
        feedback = (f"\n\nTHE EDITOR SENT YOUR LAST DRAFT BACK.\nDraft: {state.get('content')}\n"
                    f"Feedback: {state['critic'].get('feedback')}\nMust fix: {state['critic'].get('violations', [])}\n"
                    "Rewrite it properly; don't just patch words.")
    swipe = page.swipe_file(3000)
    template_note = ""
    if state.get("template") == "split":
        template_note = "\nTEMPLATE 'split': every middle slide is a contrast. Fill 'left' (the bad/common way) and 'right' (the better way), ≤ 10 words each; 'title' labels the comparison."
    elif state.get("template") == "post_card":
        template_note = "\nTEMPLATE 'post_card': each slide reads like a standalone text post. Put the full line in 'title'; keep 'body' empty or ≤ 12 words."
    elif state.get("template") == "minimal":
        template_note = "\nTEMPLATE 'minimal': one sentence per slide, story-like, in 'title'. 'body' empty."

    prompt = f"""Write one {page.platform} {fmt} post.

PAGE BRIEF
{page.brief()}

{playbook_text(page.platform)}

FORMAT RULES: {FORMAT_RULES[fmt]}{template_note}

THE PLAN
FORMAT: {fmt}
Pillar: {state['pillar']} · Archetype: {state.get('archetype')} → {arch.get('structure', '')}
Topic: {state['topic']}
Angle: {state['angle']}
Winning hook (use it verbatim as the opening line / cover / first beat): {state['hook']}
Goal action: {state.get('goal')} → {GOAL_CTA.get(state.get('goal', ''), '')}
Why it should spread: {state.get('why_viral', '')}
Core hashtags: {page.hashtags.core} (max {page.hashtags.max_per_post} total; put them only in "hashtags")

{facts_prompt(state.get("facts"))}

DEPTH: a reader should finish this knowing exactly what to do and why. Prefer one idea explained properly
over five ideas listed. Every claim gets a specific: a number, a named tool, a timing, an example from
this audience's real week. If it could appear on any generic page, rewrite it.

{HUMAN_VOICE_RULES}
{f"STYLE REFERENCES FROM THE NICHE (match the energy and structure, never copy wording):{chr(10)}{swipe}" if swipe else ""}

Before writing, decide the ONE emotion this post triggers (relief, "that's so me", surprise, ambition,
mild outrage, FOMO) and make every line serve it. Cut anything a reader would skim.{feedback}

Return exactly this JSON shape: {FORMAT_SPEC[fmt]}"""
    content = ask_json("write", "You are a top creator in this niche who writes like a human.", prompt)
    content.update({"archetype": state.get("archetype"), "goal": state.get("goal"), "template": state.get("template"),
                    "hook": state.get("hook"), "hook_options": state.get("hook_options", []),
                    "why_viral": state.get("why_viral", "")})
    facts = state.get("facts") or {}
    if not content.get("sources") and facts.get("sources"):
        content["sources"] = facts["sources"]
    content["unverified"] = [n.get("stat") for n in facts.get("numbers") or [] if n.get("verify")]
    return {"content": content, "log": state.get("log", []) + [f"write: draft v{state.get('revisions', 0) + 1}"]}
