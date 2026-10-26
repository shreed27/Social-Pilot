"""Builds frontend/src/demo-data.json: sample pages, drafts, media and 30 days of metrics.

Used only when the dashboard can't reach the API (the published preview). Every page, handle and
number here is SAMPLE data for illustration.
"""
import base64
import io
import json
import random
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image  # noqa: E402

from app.agents.visuals import _reel_frame, render_bold, render_post_card, render_slide  # noqa: E402
from app.agents.critic import quality_report, viral_score  # noqa: E402
from app import quality  # noqa: E402
from app.pages import Page  # noqa: E402
from app.pages import Brand  # noqa: E402

random.seed(7)
NOW = datetime.now(timezone.utc).replace(second=0, microsecond=0)
OUT = ROOT / "frontend" / "src" / "demo-data.json"

PAGES = [
    {"id": "insta_main", "platform": "instagram", "handle": "@studybyte.ai",
     "niche": "AI tools and study systems for Indian college students",
     "audience": "18–24, engineering and commerce students, preparing for exams and placements",
     "goal": "Grow followers in the niche via saves and shares",
     "voice": "Friendly, punchy, practical. Short lines. One idea per slide.",
     "pillars": [{"name": "how-to", "description": "Step-by-step tutorials people save"},
                 {"name": "tool-of-the-week", "description": "One tool, what it does, how to use it"},
                 {"name": "myth-vs-fact", "description": "Correct a common study myth"},
                 {"name": "relatable", "description": "Shareable student-life moments"}],
     "formats": ["carousel", "reel", "image"], "posts_per_week": 5, "preferred_slots": ["09:00", "13:00", "19:30"],
     "hashtags": {"core": ["#studytips", "#aitools"], "max_per_post": 8},
     "brand": {"bg": "#0F172A", "fg": "#F8FAFC", "accent": "#F59E0B"},
     "avoid": ["politics", "unverified claims"], "cta_options": ["Save this for exam week", "Follow for one tool a day"]},
    {"id": "linkedin_main", "platform": "linkedin", "handle": "Buildwise Labs",
     "niche": "Practical AI for startup founders and product teams in India",
     "audience": "Founders, PMs and engineering leads at seed to Series B startups",
     "goal": "Grow page followers with credible, insight-led posts",
     "voice": "Expert but human. Opinionated, backed by specifics. No buzzwords.",
     "pillars": [{"name": "framework", "description": "A reusable checklist, best as a document carousel"},
                 {"name": "insight", "description": "A non-obvious lesson with a concrete example"},
                 {"name": "industry-take", "description": "A clear opinion on a recent development"},
                 {"name": "behind-the-scenes", "description": "How the team builds and decides"}],
     "formats": ["document", "text", "image"], "posts_per_week": 4, "preferred_slots": ["08:30", "12:30"],
     "hashtags": {"core": ["#productmanagement"], "max_per_post": 3},
     "brand": {"bg": "#FFFFFF", "fg": "#111827", "accent": "#2563EB"},
     "avoid": ["politics", "engagement bait"], "cta_options": ["Follow Buildwise Labs for weekly frameworks"]},
    {"id": "x_main", "platform": "x", "handle": "@shipwithai",
     "niche": "Building with AI: dev tools, agents and shipping fast",
     "audience": "Indie hackers and developers who build with LLMs",
     "goal": "Grow followers via threads and timely takes",
     "voice": "Sharp, concise, a bit witty. Strong first line.",
     "pillars": [{"name": "thread", "description": "4–7 posts that teach one thing end to end"},
                 {"name": "hot-take", "description": "A crisp opinion on today's news"},
                 {"name": "list", "description": "A curated list of tools or examples"}],
     "formats": ["thread", "text", "image"], "posts_per_week": 10, "preferred_slots": ["10:00", "18:00", "21:30"],
     "hashtags": {"core": [], "max_per_post": 1},
     "brand": {"bg": "#000000", "fg": "#FFFFFF", "accent": "#1D9BF0"},
     "avoid": ["politics", "links in the main post"], "cta_options": ["Follow for more builder notes"]},
]
PAGE = {p["id"]: p for p in PAGES}


def jpeg(im: Image.Image, w=540) -> str:
    im = im.convert("RGB").resize((w, int(im.height * w / im.width)))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def slides_media(page_id, slides, template="bold"):
    p = PAGE[page_id]
    br = Brand(**p["brand"])
    return [{"url": jpeg(render_slide(br, template, s, i=i, n=len(slides), handle=p["handle"])), "type": "jpg"}
            for i, s in enumerate(slides, 1)]


def card(page_id, title):
    p = PAGE[page_id]
    return render_bold(Brand(**p["brand"]), title, handle=p["handle"], cover=True)


def reel_media(page_id, beats):
    p = PAGE[page_id]
    br = Brand(**p["brand"])
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        lines = []
        for i, b in enumerate(beats):
            pg = Page(id=page_id, platform=p["platform"], handle=p["handle"], niche=p["niche"], audience="", goal="", voice="",
                      pillars=[], formats=[], brand=br)
            _reel_frame(pg, b["text"], b.get("highlight", ""), i, len(beats)).resize((540, 960)).save(td / f"{i}.png")
            lines += [f"file '{i}.png'", f"duration {b['seconds']}"]
        lines.append(f"file '{len(beats) - 1}.png'")
        (td / "l.txt").write_text("\n".join(lines))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "l.txt",
                        "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
                        "-movflags", "+faststart", "out.mp4"], cwd=td, check=True)
        return [{"url": "data:video/mp4;base64," + base64.b64encode((td / "out.mp4").read_bytes()).decode(), "type": "mp4"}]


def trace(pillar, fmt, topic, score, revisions=0):
    t = ["research: 8 ideas from 24 headlines + live trend scan", f"strategy: {pillar}/{fmt} → {topic}",
         "depth: fact pack with 14 specifics, 3 sources", "hooks: 7 tested, winner picked by judge", "write: draft v1"]
    for r in range(revisions):
        t += [f"critic: viral {score - 1.2:.1f} revise ['sounds AI-written: AI-sounding words: unlock']", f"write: draft v{r + 2}"]
    t += [f"critic: viral {score} pass", "visuals: rendered", "queued for approval"]
    return t


def critic(platform, hook, share, save, disc, human, fb, action, niche=9, fit=9, safety=10, depth=9):
    s = {"hook": hook, "shareability": share, "save_worthiness": save, "depth": depth, "discussion": disc, "human_voice": human,
         "niche_fit": niche, "platform_fit": fit, "brand_safety": safety}
    v = viral_score(platform, s)
    return {"scores": s, "overall": v, "viral_score": v, "predicted_action": action, "verdict": "pass", "feedback": fb, "violations": []}


def hooks(*pairs):
    return [{"type": t_, "text": x, "score": sc} for t_, x, sc in pairs]


drafts = []
_id = [100]


def add(page_id, fmt, pillar, topic, angle, content, *, status="pending", when=None, media=None, crit=None,
        kind="post", reply_context=None, metrics=None, error=None, created_ago_h=2, revisions=0):
    _id[0] += 1
    p = PAGE[page_id]
    c = crit or critic(p["platform"], 8, 8, 8, 7, 8, "Solid. The second line could be more specific.", "save")
    if kind == "post" and status in ("pending", "approved"):
        pg = Page(**{k: v for k, v in p.items() if k in Page.model_fields})
        c = {**c, "quality": quality_report(pg, fmt, content)[0], "artefacts_stripped": 0}
        for h in content.get("hook_options") or []:
            h["hookscore"] = quality.hook(h["text"])["score"]
    drafts.append({
        "id": _id[0], "page_id": page_id, "platform": p["platform"], "kind": kind, "format": fmt, "pillar": pillar,
        "topic": topic, "angle": angle, "content": content, "media": media or [],
        "critic": c if kind == "post" else {}, "trace": trace(pillar, fmt, topic, c["overall"], revisions) if kind == "post" else
        ["engagement: new comment detected", "reply: drafted", "queued for approval"],
        "reply_context": reply_context, "status": status, "scheduled_at": when.isoformat() if when else None,
        "published_id": f"sample_{_id[0]}" if status == "published" else None, "error": error,
        "created_at": (NOW - timedelta(hours=created_ago_h)).isoformat(),
        "updated_at": (NOW - timedelta(hours=max(created_ago_h - 1, 0))).isoformat(), "metrics": metrics,
    })


def slot(days, hhmm):  # IST slot → UTC
    h, m = map(int, hhmm.split(":"))
    ist = (NOW + timedelta(hours=5, minutes=30)).replace(hour=h, minute=m) + timedelta(days=days)
    return ist - timedelta(hours=5, minutes=30)


# ── pending: the approval queue ──────────────────────────────────────────────
ig_slides = [
    {"layout": "text", "title": "You're paying for 5 study apps you don't need", "body": "Free swaps, and the one setting in each that actually matters.", "highlight": "5 study apps"},
    {"layout": "text", "title": "1. NotebookLM replaces tuition notes", "body": "Upload one chapter PDF and ask it to quiz you on the parts you keep skipping. It only answers from your file, so it won't make things up about your syllabus.", "highlight": "NotebookLM"},
    {"layout": "steps", "title": "2. Anki, set up in 3 minutes", "items": ["One deck per subject, not one giant deck", "Cap new cards at 20 a day", "Review before breakfast, not after dinner"], "highlight": "Anki"},
    {"layout": "stat", "stat": "20 min", "title": "of Anki a day beats a 6-hour all-nighter", "body": "Spaced reviews show you a card right before you'd forget it, so each review counts.", "source": "example"},
    {"layout": "list", "title": "3. Perplexity, used properly", "items": ["Ask for sources first, answer second", "Open 2 of the links before you cite", "Use Focus: Academic for assignments"], "highlight": "Perplexity"},
    {"layout": "compare", "title": "4. Excalidraw vs drawing by hand", "left": "Redraw the ER diagram at midnight", "right": "Drag, export, paste into your lab record", "highlight": "Excalidraw"},
    {"layout": "text", "title": "5. Forest replaces your willpower", "body": "Phone down, tree grows. Open Instagram and the tree dies. Sounds silly. It's the only one I never cancelled.", "highlight": "Forest"},
    {"layout": "text", "title": "The real saving isn't ₹1,800", "body": "It's the forty minutes a week you stop losing switching between five apps that each do half the job.", "highlight": "forty minutes"},
    {"layout": "text", "title": "Send this to the friend who pays for everything", "body": "and still studies the night before", "highlight": "Send this"},
]
add("insta_main", "carousel", "tool-of-the-week", "5 free tools that replace paid study apps",
    "Five swaps that cover notes, revision, research, diagrams and focus",
    {"caption": "I was paying ₹1,800 a month for study apps.\n\nI only noticed in September, when my bank app showed four autopays I'd forgotten about, for tools I opened maybe twice a week before exams.\n\nCancelled all of them. These 5 free ones do the same job, and for notes and revision they're honestly better.\n\nSwipe for the one setting in each that matters. Slide 3 alone saved my DBMS marks.\n\nSave this before mid-sems.",
     "hashtags": ["#studytips", "#aitools", "#engineeringstudents", "#examprep"],
     "cta": "Send this to the friend who pays for everything", "slides": ig_slides, "alt_text": "Seven slides naming five free study tools",
     "archetype": "list", "goal": "send", "template": "bold", "hook": ig_slides[0]["title"],
     "sources": [{"title": "Anki manual: deck options", "url": "https://docs.ankiweb.net/deck-options.html"},
                 {"title": "NotebookLM help", "url": "https://support.google.com/notebooklm"}], "unverified": [],
     "why_viral": "Saving money is the easiest thing to forward. Broke-student humour makes people tag a friend.",
     "hook_options": hooks(("bold_claim", "You're paying for 5 study apps you don't need", 9.1),
                           ("micro_story", "I cancelled ₹1,800 of study apps last month", 8.7),
                           ("callout", "If you still pay for Notion AI, read this", 8.2),
                           ("contrast", "Paid study apps vs the free ones toppers use", 7.9),
                           ("question", "Why are you still paying for study apps?", 7.1))},
    when=slot(1, "19:30"), media=slides_media("insta_main", ig_slides, "bold"),
    crit=critic("instagram", 9.5, 9, 9, 6, 9, "Strong. Slide 3 could name a real exam ('20 minutes a day beats a 6-hour all-nighter before DBMS').", "send"),
    created_ago_h=1)

pc_slides = [
    {"title": "Things nobody tells you in 1st year:", "highlight": "nobody"},
    {"title": "Your CGPA matters less than one real project.", "highlight": "one real project"},
    {"title": "The 3 seniors in my batch with the best offers weren't toppers. They shipped stuff.", "highlight": "shipped stuff"},
    {"title": "75% attendance is the rule that actually gets people detained, so track it from week 1 instead of panicking in week 12 like I did.", "highlight": "75% attendance"},
    {"title": "Be nice in group projects. Those 4 people are your first network.", "highlight": "first network"},
    {"title": "Send this to a 1st year who needs it.", "highlight": "Send this"},
]
add("insta_main", "carousel", "relatable", "Things nobody tells you in 1st year",
    "Earned lessons from 4th year, written like texts from a senior",
    {"caption": "Things I wish a senior had told me in my first week of B.Tech.\n\nNumber 3 cost me a semester, because I found out about the 75% rule in November, two weeks before the shortage list went up on the notice board.\n\nNone of this is in the orientation slides. All of it is stuff seniors tell you in the canteen, if you ask.\n\nSend it to a junior.",
     "hashtags": ["#collegelife", "#engineeringstudents", "#studytips"], "cta": "Send this to a 1st year who needs it",
     "slides": pc_slides, "archetype": "advice_i_needed", "goal": "send", "template": "post_card", "hook": pc_slides[0]["title"],
     "why_viral": "Seniors send it to juniors, juniors send it to their batch group. Each slide is a standalone screenshot.",
     "hook_options": hooks(("callout", "Things nobody tells you in 1st year:", 9.0),
                           ("bold_claim", "Your CGPA matters less than you think", 8.4),
                           ("micro_story", "I lost a semester to something nobody warned me about", 8.3),
                           ("question", "What do you wish you knew in 1st year?", 7.2))},
    when=slot(2, "21:00"), media=slides_media("insta_main", pc_slides, "post_card"),
    crit=critic("instagram", 9, 9.5, 8, 8, 9.5, "Very shareable. Keep slide 4; it's the one people will argue about.", "send"),
    created_ago_h=2)

reel = [{"text": "Stop re-reading notes. Try this 2-minute test.", "seconds": 1.6, "highlight": "2-minute"},
        {"text": "Feels like studying. Isn't.", "seconds": 1.4},
        {"text": "Close your DBMS notes", "seconds": 1.3, "highlight": "Close"}, {"text": "Write what you remember. 2 minutes.", "seconds": 1.6},
        {"text": "Check. Fill the gaps.", "seconds": 1.5}, {"text": "That's active recall. 15 minutes.", "seconds": 1.8, "highlight": "active recall"},
        {"text": "Still re-reading notes?", "seconds": 1.6}]
add("insta_main", "reel", "myth-vs-fact", "Re-reading notes doesn't work: active recall in 12 seconds",
    "Bust the re-reading myth and show the 3-step recall loop",
    {"caption": "Re-reading feels productive. It isn't.\n\nTry it on one DBMS chapter tonight: 2 minutes writing down everything you remember with the book shut, then 5 minutes checking what you missed against your notes.\n\nThe gaps are your syllabus. Re-test only those tomorrow at 8am, before you look at anything new. Day 3, test again. By day 7 you'll know Unit 2 cold.\n\nIt feels worse than re-reading for 3 hours. That's the point: the struggle is what makes it stick.\n\nSave this for revision week.",
     "hashtags": ["#studytips", "#activerecall", "#examprep"], "cta": "Save this for revision week", "reel_script": reel,
     "archetype": "contrarian", "goal": "watch_time", "hook": reel[0]["text"],
     "why_viral": "Calls out something everyone does. Last line loops back into the first.",
     "hook_options": hooks(("specific_number", "Stop re-reading notes. Try this 2-minute test.", 9.2),
                           ("bold_claim", "Re-reading your notes is lying to you", 8.6),
                           ("question", "Why do you forget everything in the exam hall?", 8.5),
                           ("contrast", "How toppers revise vs how we revise", 8.1))},
    when=slot(2, "13:00"), media=reel_media("insta_main", reel),
    crit=critic("instagram", 9.5, 8.5, 8.5, 7, 9, "Payoff lands by second 3 and it loops. Good.", "watch_time"), revisions=1, created_ago_h=3)

li_slides = [
    {"layout": "text", "title": "Before you add AI to a feature, ask these 4 questions", "body": "We run this on every roadmap item now. It takes ten minutes.", "highlight": "4 questions"},
    {"layout": "text", "title": "1. Can the user tell when it's wrong?", "body": "If they can't, every bad answer quietly burns trust you won't get back. A support bot that's confidently wrong is worse than no bot.", "highlight": "wrong"},
    {"layout": "stat", "stat": "1 in 20", "title": "wrong answers is enough to lose a user's trust", "body": "Pick the error rate you can live with before you build, not after launch.", "source": "example"},
    {"layout": "compare", "title": "2. What does one wrong answer cost?", "left": "Bad summary: they re-read the doc", "right": "Bad refund call: ticket, churn, a tweet", "highlight": "cost"},
    {"layout": "list", "title": "3. Is there a boring version?", "items": ["Rules for the top 10 cases", "Search instead of generation", "A better form with good defaults"], "highlight": "boring"},
    {"layout": "steps", "title": "4. Who owns the eval?", "items": ["Name one owner", "Collect 50 real examples", "Review them every Friday", "Set a line for rolling back"], "highlight": "owns"},
    {"layout": "text", "title": "We killed 3 of 7 AI features with this.", "body": "All three failed question one. The four we kept are the ones customers mention without being asked.", "highlight": "killed 3 of 7"},
    {"layout": "text", "title": "Which question would have saved your last AI launch?", "body": "Tell me in the comments. I read every one.", "highlight": ""},
]
add("linkedin_main", "document", "framework", "The 4-question test before you add AI to a feature",
    "A filter we use to kill weak AI ideas before they reach the roadmap",
    {"caption": "We killed 3 of our 7 planned AI features last quarter.\n\nNot because the model was bad.\n\nBecause when we finally sat down and asked what happens when it's wrong, nobody in the room had an answer for three of them, and that's a bad sign two weeks before a launch.\n\nSo now every AI idea gets this 4-question filter first. Ten minutes.",
     "hashtags": ["#productmanagement", "#ai"], "cta": "Which question would have saved your last AI launch?",
     "slides": li_slides, "archetype": "framework", "goal": "save", "template": "bold",
     "sources": [{"title": "Google PAIR Guidebook: errors and failure", "url": "https://pair.withgoogle.com/guidebook"}], "unverified": [], "hook": "We killed 3 of our 7 planned AI features last quarter.",
     "why_viral": "Founders save frameworks they can use in Monday's planning. The 'we killed 3 of 7' detail makes it credible.",
     "hook_options": hooks(("specific_number", "We killed 3 of our 7 planned AI features last quarter.", 9.0),
                           ("bold_claim", "Most AI features fail before a line of code.", 8.3),
                           ("question", "What happens when your AI feature is wrong?", 7.8))},
    when=slot(1, "08:30"), media=slides_media("linkedin_main", li_slides, "bold"),
    crit=critic("linkedin", 9, 8, 9.5, 8.5, 9, "Credible and specific. The closing question will pull real comments.", "save"),
    created_ago_h=2)

add("x_main", "thread", "thread", "What actually matters when picking an AI coding agent",
    "Six criteria from running agents on real repos, ranked",
    {"thread": ["I've used 6 AI coding agents this year. Benchmarks predicted none of the winners.\n\nWhat actually decides if it saves you time:",
                "1/ Repo context. Can it read the whole codebase or just the open file? This matters more than which model it runs.",
                "2/ It runs your tests. An agent that can't check its own work is handing you homework.",
                "3/ Small diffs.",
                "4/ It asks when it's unsure, instead of silently guessing what you meant on a vague task and burning an afternoon of your review time on the wrong thing.",
                "5/ Cost per merged PR.",
                "Which one did I miss? I'll add the best reply to the list."],
     "caption": "I've used 6 AI coding agents this year. Benchmarks predicted none of the winners.", "hashtags": [],
     "cta": "Which one did I miss?", "archetype": "contrarian", "goal": "reply", "hook": "I've used 6 AI coding agents this year. Benchmarks predicted none of the winners.",
     "why_viral": "Takes a side against benchmark culture; the last post invites replies the author can answer (heaviest X signal).",
     "hook_options": hooks(("specific_number", "I've used 6 AI coding agents this year. Benchmarks predicted none of the winners.", 9.1),
                           ("bold_claim", "Benchmarks are the worst way to pick an AI coding agent.", 8.7),
                           ("specific_number", "I ran 6 coding agents on the same bug. The winner wasn't the smartest.", 8.9),
                           ("question", "Picking an AI coding agent? Ignore the benchmarks.", 7.6))},
    when=slot(1, "18:00"), crit=critic("x", 9, 7.5, 8.5, 9, 9, "Strong take, no links, ends with a real question.", "reply"), created_ago_h=1)

add("insta_main", "reply", "", "Reply on: 5 free tools that replace paid study apps", "",
    {"caption": "NotebookLM, no question. Upload one chapter tonight and ask it to quiz you. Which subject is it for?"},
    kind="reply", reply_context="priya.codes: which one if I only have time to learn ONE??", created_ago_h=0)

add("linkedin_main", "text", "industry-take", "Why AI pilots stall after the demo",
    "The gap is ownership of quality after launch, not the model",
    {"caption": "Our first 3 AI pilots looked great in the demo. All 3 stalled by week two.\n\nOne was a support-reply drafter for a 40-person SaaS team in Bengaluru. Day 1, the founders loved it. Day 9, two agents quietly stopped using it because it kept quoting a refund policy that had changed in March.\n\nI've since watched it happen at a dozen startups we work with, and the ones that stall have one thing in common: by week two, nobody owns quality.\n\nNo eval set. Nobody reading real outputs. No line for when to roll back.\n\nThe fix is boring.\n\nOne owner, by name. 50 real examples pulled from actual usage, not the ones from the demo. A 30-minute review every Friday where you read outputs, not dashboards. And a written line for when you roll back, agreed before launch, so nobody has to argue about it at 11pm. Ours is simple: if more than 2 of the Friday 50 are wrong in a way a customer would screenshot, it goes back behind a flag.\n\nWe started doing this after pilot number three died. The next two shipped, and one of them is now the feature customers mention first in renewal calls.\n\nNone of it needs a better model. It needs someone who cares whether the answers are right.\n\nWhat's the most common reason you've seen a pilot stall?",
     "hashtags": ["#productmanagement", "#ai"], "cta": "", "archetype": "contrarian", "goal": "comment",
     "hook": "Our first 3 AI pilots looked great in the demo. All 3 stalled by week two.", "why_viral": "Everyone in the audience has lived this. The question asks for their own story.",
     "hook_options": hooks(("specific_number", "Our first 3 AI pilots looked great in the demo. All 3 stalled by week two.", 8.8),
                           ("bold_claim", "Every AI pilot looks great in the demo.", 8.1),
                           ("micro_story", "Our AI pilot died in week two. Not because of the model.", 8.5))},
    when=slot(3, "12:30"), crit=critic("linkedin", 8.5, 7.5, 7.5, 9, 9, "Good. A real example in line 2 would make it hit harder.", "comment"), created_ago_h=4)

# ── approved / scheduled ─────────────────────────────────────────────────────
img = render_bold(Brand(**PAGE["insta_main"]["brand"]), "Your 7-day placement prep plan", "Day 1: Resume. Day 2: DSA patterns. Day 3: Mock interview…", highlight="7-day", handle="@studybyte.ai", cover=True)
add("insta_main", "image", "how-to", "7-day placement prep plan", "A day-by-day plan for the week before campus placements",
    {"caption": "Placements in 7 days? Here's the plan I'd follow.\n\nDay 1 is your resume, because a recruiter at a campus drive spends about as long on it as you spend deciding whether to skip this post.\n\nDays 2 to 5: DSA patterns, not random problems.\n\nDay 6, one mock interview with a friend who's already placed, out loud, timed. Day 7, rest, because walking in exhausted costs you more than one extra day of practice ever gives you.\n\nSave this and send it to whoever in your group is panicking.", "hashtags": ["#placements", "#studytips"], "cta": "Save this", "hook": "Placements in 7 days? Here's the plan I'd follow."},
    status="approved", when=NOW + timedelta(hours=5), media=[{"url": jpeg(img), "type": "jpg"}], created_ago_h=20)
add("x_main", "text", "hot-take", "Agents need fewer tools, not more", "",
    {"caption": "Most AI agents fail because you gave them 40 tools, not 4.\n\nI've watched it happen. Every extra tool is another way for the model to pick the wrong one at step 3 and spend the next 20 steps confidently fixing a problem it created.\n\nYou don't need a bigger model. Cut to 4 and watch it get smarter.", "hashtags": [], "hook": "Most AI agents fail because you gave them 40 tools, not 4."},
    status="approved", when=NOW + timedelta(hours=9), created_ago_h=18)
add("linkedin_main", "text", "behind-the-scenes", "How we review AI output every Friday", "",
    {"caption": "We read our AI's 50 worst answers every Friday. You should too.\n\n30 minutes. No slides.\n\nWe sort each one into good, wrong or embarrassing, and anything embarrassing becomes a test case before Monday, which is how our eval set grew from 12 examples to over 400 without anyone being assigned to it.\n\nThree things made it stick:\n1. Same time every week. Friday 4pm, calendar block, no exceptions.\n2. Real outputs only. No cherry-picked examples, no screenshots from the demo.\n3. The person who built the feature isn't the one grading it.\n\nWeek one, we found a reply telling a customer in Pune their plan included a feature it didn't. Nobody had noticed for 11 days, because every dashboard we had said the bot was 'performing well'. One person reading 50 answers caught it in four minutes.\n\nThe first month was painful. We found answers we'd have been embarrassed to see in a customer's screenshot. That's exactly why it works.\n\nWe now run the same review for 6 clients. Average time: 34 minutes a week.\n\nWhat does your review look like?", "hashtags": ["#ai"], "hook": "We read our AI's 50 worst answers every Friday. You should too."},
    status="approved", when=NOW + timedelta(days=1, hours=3), created_ago_h=26)

# ── failed / rejected ────────────────────────────────────────────────────────
add("x_main", "text", "list", "5 open-source eval tools worth knowing", "",
    {"caption": "5 open-source eval tools worth knowing in 2026 👇", "hashtags": []}, status="failed",
    when=NOW - timedelta(hours=2), error="402 Payment Required: API credits exhausted. Top up credits in the X developer console, then retry.",
    created_ago_h=30)
add("insta_main", "image", "relatable", "When the PPT is due at 9 and it's 8:55", "",
    {"caption": "Every group project ever.", "hashtags": ["#collegelife"]}, status="rejected", created_ago_h=40)

# ── published history with metrics ───────────────────────────────────────────
history = [
    ("insta_main", "carousel", "how-to", "How to make notes that actually stick", 13, 0.071),
    ("insta_main", "reel", "myth-vs-fact", "Pulling all-nighters lowers your score", 11, 0.094),
    ("insta_main", "carousel", "tool-of-the-week", "Notion templates for semester planning", 8, 0.063),
    ("insta_main", "image", "relatable", "Group project roles, explained", 6, 0.038),
    ("insta_main", "reel", "how-to", "Pomodoro, but for coding practice", 4, 0.088),
    ("insta_main", "carousel", "how-to", "Your first DSA roadmap", 2, 0.079),
    ("linkedin_main", "document", "framework", "The RICE score is broken for AI features", 12, 0.052),
    ("linkedin_main", "text", "insight", "We shipped a worse model and users were happier", 9, 0.047),
    ("linkedin_main", "document", "framework", "A one-page AI launch checklist", 5, 0.061),
    ("linkedin_main", "text", "industry-take", "Open models changed our build-vs-buy math", 3, 0.039),
    ("x_main", "thread", "thread", "How I cut my LLM bill by caching prompts", 12, 0.058),
    ("x_main", "text", "hot-take", "Evals are the new unit tests", 10, 0.034),
    ("x_main", "thread", "thread", "Agent loops that don't spiral", 7, 0.066),
    ("x_main", "text", "list", "Six tiny tools I use every day", 5, 0.029),
    ("x_main", "thread", "thread", "Structured outputs, the boring superpower", 1, 0.071),
]
for page_id, fmt, pillar, topic, days_ago, eng in history:
    p = PAGE[page_id]
    hh = random.choice(p["preferred_slots"])
    when = slot(-days_ago, hh)
    imp = random.randint(1400, 6200) if p["platform"] == "instagram" else random.randint(900, 4800)
    m = {"impressions": imp, "likes": int(imp * eng * 0.55), "comments": int(imp * eng * 0.06),
         "shares": int(imp * eng * 0.08), "saves": int(imp * eng * (0.12 if p["platform"] != "x" else 0.05)),
         "follows": max(1, int(imp * eng * 0.03))}
    m["engagement"] = round((m["likes"] + 2 * m["comments"] + 3 * m["shares"] + 3 * m["saves"] + 10 * m["follows"]) / imp, 4)
    cover = None
    if fmt in ("carousel", "document", "image", "reel"):
        cover = [{"url": jpeg(card(page_id, topic), 360), "type": "jpg"}]
    arch = {"how-to": "framework", "myth-vs-fact": "contrarian", "tool-of-the-week": "list", "relatable": "relatable",
            "framework": "framework", "insight": "story", "industry-take": "contrarian", "thread": "explainer",
            "hot-take": "hot_take", "list": "list"}[pillar]
    add(page_id, fmt, pillar, topic, "", {"caption": topic, "hashtags": p["hashtags"]["core"], "archetype": arch}, status="published",
        when=when, media=cover, metrics=m, created_ago_h=days_ago * 24 + 20)

# ── overview ─────────────────────────────────────────────────────────────────
start = {"insta_main": 1240, "linkedin_main": 612, "x_main": 834}
end = {"insta_main": 1986, "linkedin_main": 903, "x_main": 1312}
series = []
for d in range(30, -1, -1):
    day = (NOW - timedelta(days=d)).strftime("%Y-%m-%d")
    t = (30 - d) / 30
    row = {"date": day}
    for pid in start:
        curve = t ** 1.35
        row[pid] = int(start[pid] + (end[pid] - start[pid]) * curve + random.randint(-6, 6) * (0 if d in (0, 30) else 1))
    series.append(row)

pub = [d for d in drafts if d["status"] == "published"]
by_format = {}
for d in pub:
    by_format.setdefault(f"{d['platform']}:{d['format']}", []).append(d["metrics"]["engagement"])
hours = {}
for d in pub:
    h = (datetime.fromisoformat(d["scheduled_at"]) + timedelta(hours=5, minutes=30)).hour
    hours.setdefault(h, []).append(d["metrics"]["engagement"])


def stats(pid):
    p = PAGE[pid]
    pp = [d for d in pub if d["page_id"] == pid]
    return {"platform": p["platform"], "handle": p["handle"], "niche": p["niche"], "followers": series[-1][pid],
            "growth_7d": series[-1][pid] - series[-8][pid], "growth_30d": series[-1][pid] - series[0][pid],
            "published": len(pp), "pending": sum(1 for d in drafts if d["page_id"] == pid and d["status"] == "pending"),
            "avg_engagement": round(sum(d["metrics"]["engagement"] for d in pp) / len(pp), 4),
            "posts_per_week": p["posts_per_week"]}


overview = {
    "mode": "demo",
    "counts": {s: sum(1 for d in drafts if d["status"] == s) for s in ["pending", "approved", "published", "failed", "rejected"]},
    "pages": {pid: stats(pid) for pid in PAGE},
    "followers_series": series,
    "by_format": [{"key": k, "platform": k.split(":")[0], "format": k.split(":")[1], "posts": len(v),
                   "avg_engagement": round(sum(v) / len(v), 4)} for k, v in sorted(by_format.items())],
    "by_hour": [{"hour": h, "posts": len(v), "avg_engagement": round(sum(v) / len(v), 4)} for h, v in sorted(hours.items())],
    "activity": [],
    "upcoming": [],
}


def analytics(pid):
    pp = [d for d in pub if d["page_id"] == pid]
    agg = lambda key: {k: {"posts": len(v), "avg_engagement": round(sum(v) / len(v), 4)} for k, v in
                       _group(pp, key).items()}
    top = sorted(pp, key=lambda d: d["metrics"]["engagement"], reverse=True)[:3]
    arch = {}
    for d in pp:
        arch.setdefault(d["content"]["archetype"], []).append(d["metrics"]["engagement"])
    return {"posts_analysed": len(pp), "by_pillar": agg("pillar"), "by_format": agg("format"), "by_hour": {},
            "by_archetype": {k: {"posts": len(v), "avg_engagement": round(sum(v) / len(v), 4)} for k, v in arch.items()},
            "top_posts": [{"topic": d["topic"], "angle": "", "format": d["format"], "engagement": d["metrics"]["engagement"]} for d in top],
            "followers": {"start": series[0][pid], "now": series[-1][pid], "delta": series[-1][pid] - series[0][pid]}}


def _group(rows, key):
    g = {}
    for d in rows:
        g.setdefault(d[key], []).append(d["metrics"]["engagement"])
    return g


OUT.write_text(json.dumps({"pages": PAGES, "drafts": drafts, "overview": overview,
                           "analytics": {pid: analytics(pid) for pid in PAGE}}))
print(OUT, round(OUT.stat().st_size / 1e6, 2), "MB,", len(drafts), "drafts")
