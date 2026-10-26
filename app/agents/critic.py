"""Critic agent: hard rules + AI-tell detection + a viral-potential score weighted by what each
platform's ranking system actually rewards. Drafts below the bar loop back to the writer."""
import json
import re

from app import quality
from app.agents.state import PostState
from app.humanize import ai_tells
from app.platforms.base import PlatformClient
from app.llm import ask_json
from app.pages import Page, get_page
from app.playbooks import playbook_text
from app.settings import get_settings

URL_RE = re.compile(r"https?://|www\.|\.com/|\.in/", re.I)

DIMENSIONS = {
    "hook": "Would this audience stop scrolling in under a second?",
    "shareability": "Would someone SEND this to a specific friend or story it?",
    "save_worthiness": "Would they save it to come back to?",
    "depth": "Does it teach something specific and usable (exact steps, sourced numbers, named tools, real examples) that a generic post wouldn't?",
    "discussion": "Would people comment or reply with their own experience/opinion?",
    "human_voice": "Does it sound like a real, opinionated person (not AI, not a brand)?",
    "niche_fit": "Is it squarely for this page's niche and audience?",
    "platform_fit": "Is it native to the platform (length, structure, format conventions)?",
    "brand_safety": "No false claims, invented stats, avoid-list topics, spam or rage-bait?",
}

# How much each dimension drives distribution on each platform (from the playbook research).
WEIGHTS = {
    "instagram": {"hook": .22, "shareability": .22, "save_worthiness": .16, "depth": .12, "discussion": .05,
                  "human_voice": .1, "niche_fit": .05, "platform_fit": .08},
    "linkedin": {"hook": .18, "shareability": .08, "save_worthiness": .17, "depth": .15, "discussion": .22,
                 "human_voice": .12, "niche_fit": .04, "platform_fit": .04},
    "x": {"hook": .28, "shareability": .1, "save_worthiness": .1, "depth": .1, "discussion": .27,
          "human_voice": .08, "niche_fit": .04, "platform_fit": .03},
}


def all_text(c: dict) -> str:
    parts = [c.get("caption", ""), c.get("image_headline", ""), c.get("cta", "")]
    parts += c.get("thread") or []
    for s in c.get("slides") or []:
        parts.append(" ".join(x for x in (s.get("stat", ""), s.get("title", "")) if x).strip() + ".")
        if s.get("body"):
            parts.append(s["body"])
        parts += [i for i in s.get("items") or [] if i]
        parts += [x for x in (s.get("left"), s.get("right")) if x]
    parts += [b.get("text", "") for b in c.get("reel_script") or []]
    return "\n".join(p for p in parts if p)


def rule_violations(page: Page, fmt: str, c: dict) -> list[str]:
    v: list[str] = []
    caption = c.get("caption", "")
    tags = c.get("hashtags", []) or []
    if len(tags) > page.hashtags.max_per_post:
        v.append(f"{len(tags)} hashtags > max {page.hashtags.max_per_post}")
    if page.platform == "instagram":
        if len(caption) > 2200:
            v.append("Instagram caption over 2,200 chars")
        if fmt == "carousel" and not (2 <= len(c.get("slides", [])) <= 20):
            v.append("Instagram carousel must have 2–20 slides")
    if page.platform == "linkedin":
        if len(caption) > 3000:
            v.append("LinkedIn post over 3,000 chars")
        if URL_RE.search(caption):
            v.append("LinkedIn post contains a link (cuts reach sharply)")
    if page.platform == "x":
        posts = c.get("thread") or [caption]
        for i, p in enumerate(posts, 1):
            if len(p) > 280:
                v.append(f"X post {i} is {len(p)} chars (>280)")
            if URL_RE.search(p):
                v.append(f"X post {i} contains a URL")
    if fmt in ("carousel", "document") and not c.get("slides"):
        v.append("missing slides")
    if fmt == "reel":
        beats = c.get("reel_script") or []
        if not beats:
            v.append("missing reel_script")
        elif float(beats[0].get("seconds", 2)) > 2.5:
            v.append("first reel beat longer than 2.5 s (hook must land immediately)")
    if fmt == "thread" and len(c.get("thread", [])) < 3:
        v.append("thread needs at least 3 posts")
    v += depth_violations(page, fmt, c)
    for word in page.avoid:
        w = word.split("(")[0].strip().lower()
        if w and len(w) > 3 and w in json.dumps(c).lower():
            v.append(f"mentions avoided topic: {w}")
    v += [f"sounds AI-written: {t}" for t in ai_tells(all_text(c))]
    return v


def clean_content(platform: str, c: dict) -> tuple[dict, int]:
    """Auto-strip machine artefacts (invisible characters, em dashes, stock AI phrases) everywhere."""
    c = json.loads(json.dumps(c))
    n = 0

    def fix(s):
        nonlocal n
        out, k = quality.clean(s, platform) if isinstance(s, str) else (s, 0)
        n += k
        return out
    for key in ("caption", "image_headline", "cta", "alt_text"):
        if c.get(key):
            c[key] = fix(c[key])
    if c.get("thread"):
        c["thread"] = [fix(x) for x in c["thread"]]
    for s in c.get("slides") or []:
        for key in ("title", "body", "left", "right", "stat"):
            if s.get(key):
                s[key] = fix(s[key])
        if s.get("items"):
            s["items"] = [fix(i) for i in s["items"]]
    for b in c.get("reel_script") or []:
        if b.get("text"):
            b["text"] = fix(b["text"])
    return c, n


def quality_report(page: Page, fmt: str, c: dict) -> tuple[dict, list[str]]:
    """Runs the open-source scorers; returns (report, hard violations)."""
    v: list[str] = []
    # Reel beats are deliberately short on-screen fragments (timed by the beat check below), so the
    # human check reads the caption there; everywhere else it reads every word that gets published.
    text = "\n".join(x for x in (c.get("caption", ""), c.get("cta", "")) if x) if fmt == "reel" else all_text(c)
    hum = quality.human(text, page.platform)
    if hum["verdict"] != "PASS":
        v.append(f"human score {hum['score']} ({hum['verdict']}; weakest: {hum['weakest'].lower()} "
                 f"{hum['checks'][hum['weakest']]}). Needs ≥ {quality.HUMAN_PASS:.0f} with every check ≥ 55")
    opening = c.get("hook") or (c.get("thread") or [c.get("caption", "")])[0].split("\n")[0]
    hk = quality.hook(opening)
    if hk["score"] < quality.HOOK_FLOOR:
        v.append(f"hook score {hk['score']} < {quality.HOOK_FLOOR:.0f} (weakest: {hk['weakest'].lower()})")
    v += [f"hook dealbreaker: {d}" for d in hk["dealbreakers"]]
    report = {"human": hum, "hook": hk}
    if fmt == "reel" and c.get("reel_script"):
        rb = quality.reel_beats(c["reel_script"])
        report["beats"] = rb
        v += [f"reel timing: {p}" for p in rb["problems"]]
    if page.platform == "instagram" and fmt != "reply":
        class _D:  # compose exactly what will be posted
            content = c
        cap = quality.ig_caption(PlatformClient.compose_caption(_D()))  # type: ignore[arg-type]
        report["caption"] = cap
        v += [f"caption: {f}" for f in cap["fails"]]
    return report, v


def _slide_words(s: dict, one_liners: bool = False) -> int:
    parts = [s.get("body", "")] + list(s.get("items") or []) + [s.get("left", ""), s.get("right", "")]
    if one_liners:  # post_card / minimal templates carry the idea in the title line itself
        parts.append(s.get("title", ""))
    return len(" ".join(parts).split())


def depth_violations(page: Page, fmt: str, c: dict) -> list[str]:
    """Hard floors so posts can't be thin. The LLM 'depth' score handles quality above the floor."""
    v: list[str] = []
    cap = len(c.get("caption", ""))
    slides = c.get("slides") or []
    one_liners = c.get("template") in ("post_card", "minimal")
    if fmt in ("carousel", "document") and len(slides) >= 4:
        middle = slides[1:-1]
        thin = [i + 2 for i, s in enumerate(middle) if s.get("layout") != "image" and _slide_words(s, one_liners) < 10]
        if len(thin) > max(1, len(middle) // 4):
            v.append(f"slides {thin} are too thin: explain the how/why with an example, or use a list/steps layout")
        layouts = {s.get("layout") or "text" for s in slides}
        if not one_liners and len(layouts) < 3:
            v.append(f"only {len(layouts)} slide layout(s); use at least 3 (text, list, steps, stat, image, compare)")
        if fmt == "carousel" and len(slides) < (6 if one_liners else 7):
            v.append(f"carousel has {len(slides)} slides; deep carousels need 8–10")
    if page.platform == "instagram" and fmt in ("carousel", "reel", "image") and cap < 300:
        v.append(f"caption is {cap} chars; write a 300+ char mini-article that adds context the visuals don't")
    if page.platform == "linkedin" and fmt == "text" and cap < 900:
        v.append(f"LinkedIn post is {cap} chars; deep posts run 1,100–1,800 with one concrete example")
    if fmt == "thread" and len(c.get("thread", [])) < 5:
        v.append("thread under 5 posts; each post should carry one specific, usable point")
    return v


def viral_score(platform: str, scores: dict) -> float:
    w = WEIGHTS[platform]
    return round(sum(float(scores.get(k, 0)) * wt for k, wt in w.items()) / sum(w.values()), 1)


def critic_node(state: PostState) -> PostState:
    s = get_settings()
    page = get_page(state["page_id"])
    content = dict(state["content"])
    tags = list(dict.fromkeys(content.get("hashtags") or []))
    core_first = [t for t in page.hashtags.core if t in tags] + [t for t in tags if t not in page.hashtags.core]
    content["hashtags"] = core_first[: page.hashtags.max_per_post]
    content, cleaned = clean_content(page.platform, content)
    violations = rule_violations(page, state["format"], content)
    qreport, qviol = quality_report(page, state["format"], content)
    violations += qviol

    visible = {k: v for k, v in content.items() if k not in ("hook_options", "why_viral")}
    prompt = f"""You are the editor of a page that grows fast. Score this {page.platform} {state['format']} 0–10
on each dimension, as the TARGET AUDIENCE would react, not as a marketer. Be strict: 6 = the
average post in the niche, 8 = clearly better than most, 9+ = the kind that breaks out.
{json.dumps(DIMENSIONS, indent=1)}

PAGE BRIEF
{page.brief()}

{playbook_text(page.platform)}

INTENDED GOAL ACTION: {state.get('goal')} · ARCHETYPE: {state.get('archetype')}

DRAFT
{json.dumps(visible, indent=1, ensure_ascii=False)}

Then say what single change would most increase its chance of being shared, in one or two
concrete edits (quote the line to change and give the replacement).
Return: {{"scores": {{{", ".join(f'"{k}": n' for k in DIMENSIONS)}}}, "predicted_action": str, "feedback": str}}"""
    out = ask_json("critic", "You are a demanding social media editor.", prompt)
    scores = {k: float(out.get("scores", {}).get(k, 0)) for k in DIMENSIONS}
    overall = viral_score(page.platform, scores)
    brand_safe = scores["brand_safety"] >= 8
    passed = overall >= s.critic_min_score and brand_safe and not violations
    critic = {"scores": scores, "overall": overall, "viral_score": overall, "predicted_action": out.get("predicted_action", ""),
              "feedback": out.get("feedback", ""), "violations": violations, "verdict": "pass" if passed else "revise",
              "quality": qreport, "artefacts_stripped": cleaned}
    return {
        "content": content, "critic": critic,
        "revisions": state.get("revisions", 0) + (0 if passed else 1),
        "log": state.get("log", []) + [f"critic: viral {overall} · human {qreport['human']['score']} · hook {qreport['hook']['score']}"
                                       f" · {cleaned} artefacts stripped · {'pass' if passed else 'revise'} {violations[:2] or ''}"],
    }


def route_after_critic(state: PostState) -> str:
    if state["critic"]["verdict"] == "pass":
        return "visuals"
    if state.get("revisions", 0) > get_settings().max_revisions:
        return "visuals"  # out of retries: still queued, the human sees the critic notes and decides
    return "writer"
