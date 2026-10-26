"""Thin LLM layer. Every agent calls `ask_json(task, system, prompt)` and gets a dict back.

LLM_PROVIDER=mock returns deterministic canned output so the full pipeline can be
tested offline without API keys.
"""
import json
import logging
import re
from typing import Any

from app.settings import get_settings

log = logging.getLogger(__name__)


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)


def ask_json(task: str, system: str, prompt: str, *, web_search: bool = False, max_tokens: int = 4000) -> dict:
    s = get_settings()
    if s.llm_provider == "mock":
        return _mock(task, prompt)

    import anthropic

    client = anthropic.Anthropic(api_key=s.anthropic_api_key or None)
    kwargs: dict[str, Any] = dict(
        model=s.llm_model,
        max_tokens=max_tokens,
        system=system + "\n\nRespond with ONE valid JSON object only. No prose outside the JSON.",
        messages=[{"role": "user", "content": prompt}],
    )
    if web_search:
        kwargs["tools"] = [{"type": s.web_search_tool_type, "name": "web_search", "max_uses": 5}]

    last_err = None
    for attempt in range(3):
        resp = client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        try:
            return _extract_json(text)
        except json.JSONDecodeError as e:  # ask the model to repair once or twice
            last_err = e
            kwargs["messages"] = kwargs["messages"][:1] + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": "That was not valid JSON. Return only the corrected JSON object."},
            ]
            log.warning("LLM returned invalid JSON for %s (attempt %d)", task, attempt + 1)
    raise ValueError(f"LLM failed to return JSON for {task}: {last_err}")


# ── Offline mock ─────────────────────────────────────────────────────────────

def _mock(task: str, prompt: str) -> dict:
    fmt = re.search(r"FORMAT: (\w+)", prompt)
    fmt = fmt.group(1) if fmt else "text"
    if task == "research":
        return {"ideas": [
            {"topic": "Free AI tools that replace paid apps", "pillar": "tool-of-the-week", "archetype": "list",
             "why_it_spreads": "People send money-saving lists to friends", "timely": False, "source": "mock"},
            {"topic": "The note-taking mistake toppers never make", "pillar": "myth-vs-fact", "archetype": "contrarian",
             "why_it_spreads": "Mild outrage + save", "timely": False, "source": "mock"},
        ]}
    if task == "strategy":
        return {"topic": "Free AI tools that replace paid apps", "angle": "5 swaps that save ₹2,000/month",
                "archetype": "list", "goal": "send", "template": "bold",
                "why_viral": "Saves money; easy to send to a broke friend"}
    if task == "hooks":
        return {"hooks": [
            {"type": "bold_claim", "text": "You're paying for 5 apps you don't need"},
            {"type": "specific_number", "text": "These 5 free tools saved me ₹2,000 a month"},
            {"type": "callout", "text": "If you still pay for Notion AI, read this"},
            {"type": "curiosity_gap", "text": "The free app I use instead of ChatGPT Plus"},
            {"type": "question", "text": "Why are you still paying for study apps?"},
            {"type": "micro_story", "text": "I cancelled 4 subscriptions last night"},
            {"type": "contrast", "text": "Paid apps vs the free ones I actually use"},
        ]}
    if task == "hook_judge":
        return {"scores": [{"i": i, "stop": 8 - (i % 3), "clarity": 8, "specific": 8, "human": 9,
                            "total": 8.5 - (i % 3) * 0.5} for i in range(7)], "winner": 0, "why": "mock"}
    if task == "depth":
        return {"key_points": [{"point": "Re-reading builds familiarity, not recall", "detail": "Recognising a page feels like knowing it",
                                "example": "You can follow a DBMS solution but can't start one blank"}],
                "steps": ["Close the notes", "Write everything you remember for 2 minutes", "Check and mark gaps in red", "Re-test only the gaps tomorrow"],
                "numbers": [{"stat": "2 minutes", "context": "one recall round per topic", "source": "example", "url": "", "verify": False}],
                "names": ["NotebookLM", "Anki", "Forest"], "mistakes": [{"mistake": "Highlighting everything", "why": "It feels productive", "fix": "Turn highlights into questions"}],
                "counterintuitive": "Getting answers wrong while practising helps you remember them",
                "sources": [{"title": "Retrieval practice overview", "url": "https://www.retrievalpractice.org/"}]}
    if task == "write":
        cap = ("You're paying for 5 apps you don't need.\n\nI found that out in September, when my bank app showed ₹1,800 a month "
               "going to study tools I opened maybe twice a week, and most of that was autopay I'd forgotten about.\n\n"
               "So I cancelled them. All of them.\n\nHere's what I use now, and the one setting in each that matters. "
               "NotebookLM if you have PDFs. Anki if you forget things by Friday. Forest if your phone wins every evening.\n\n"
               "Save it for the next billing cycle.")
        base = {"caption": cap, "hashtags": ["#aitools", "#productivity"], "cta": "Send this to the friend who still pays for everything",
                "alt_text": "Slides listing five free tools", "sources": [{"title": "Retrieval practice overview", "url": "https://www.retrievalpractice.org/"}]}
        if fmt in ("carousel", "document"):
            base["slides"] = [
                {"layout": "text", "title": "You're paying for 5 apps you don't need", "body": "Free swaps inside, with the one setting that matters in each.", "highlight": "5 apps"},
                {"layout": "text", "title": "1. NotebookLM", "body": "Upload a chapter, then ask it to quiz you on the parts you keep skipping before every test. It only answers from your PDF.", "highlight": "NotebookLM"},
                {"layout": "steps", "title": "2. Anki, set up in 3 minutes", "items": ["Make one deck per subject", "Cap new cards at 20 a day", "Review before breakfast"], "highlight": "Anki"},
                {"layout": "stat", "stat": "20 min", "title": "of Anki a day beats a 6-hour all-nighter", "body": "Spaced reviews catch things right before you'd forget them.", "source": "example"},
                {"layout": "image", "title": "3. Perplexity for research", "image_prompt": "A student at a library desk with stacked books and a laptop, warm window light, shallow depth of field"},
                {"layout": "list", "title": "4. Excalidraw for diagrams", "items": ["ER diagrams in 2 minutes", "Paste straight into your lab record", "Free, nothing to install"], "highlight": "Excalidraw"},
                {"layout": "compare", "title": "5. Forest vs willpower", "left": "Phone face-down and hope", "right": "Tree dies if you open Instagram", "highlight": "Forest"},
                {"layout": "text", "title": "The real saving isn't the money", "body": "It's the forty minutes a week you stop spending switching between apps that all do half the job.", "highlight": "forty minutes"},
                {"layout": "text", "title": "Send this to a friend", "body": "the one who still pays for everything and studies the night before", "highlight": "Send"}]
        if fmt == "reel":
            base["reel_script"] = [{"text": t, "seconds": s} for t, s in [
                ("You're paying for 5 apps you don't need", 1.6), ("Notes? NotebookLM. Free.", 1.4),
                ("Flashcards? Anki. 10 min a day.", 1.6), ("Research? Perplexity. Free.", 1.4),
                ("Focus? Forest. Free.", 1.3), ("Diagrams? Excalidraw. Free.", 1.4), ("So why pay for 5 apps?", 1.6)]]
            base["broll"] = [{"scene": "Close-up of a student's hand cancelling subscriptions on a crumpled bill on a hostel desk, warm lamp light, slow push-in", "seconds": 5},
                             {"scene": "Over-the-shoulder shot of a student writing notes from memory in a quiet library, handheld, soft daylight", "seconds": 5}]
        if fmt == "thread":
            base["thread"] = ["You're paying for 5 apps you don't need. Free swaps that work:",
                              "1/ NotebookLM instead of paid note tools. Upload the PDF, ask it to quiz you, and watch how fast you find what you don't know.",
                              "2/ Anki. Ten minutes a day.", "3/ Perplexity, for answers with sources.", "4/ Excalidraw. Free. Fast.",
                              "5/ Forest, because your phone is the real problem and no study app has ever fixed that for anyone I know.",
                              "Bookmark it. Cancel one subscription tonight."]
        if fmt == "image":
            base["image_headline"] = "5 free swaps for paid apps"
            base["highlight"] = "free"
            base["cover_prompt"] = "Moody photo of a cluttered student desk at night with an open notebook and a mug, dark empty space at the top"
        if fmt == "text":
            base["caption"] = cap + ("\n\nThe bigger lesson wasn't about apps.\n\nEvery tool we add promises to save time, and each one quietly "
                                     "takes ten minutes a week to open, sync and remember. Five tools is close to an hour a week, which is "
                                     "an hour we could spend on the actual work. For a team of eight, that's a full working day every week, gone to tabs and logins.\n\nThree rules I use now:\n1. Cancel anything you "
                                     "haven't opened in 14 days.\n2. One tool per job, never two.\n3. Put what you save somewhere you'll "
                                     "notice it.\n\nWhich one would you cancel first?")
        return base
    if task == "critic":
        return {"scores": {"hook": 9, "shareability": 8.5, "save_worthiness": 8.5, "depth": 9, "discussion": 8, "human_voice": 9,
                           "niche_fit": 9, "platform_fit": 9, "brand_safety": 10},
                "predicted_action": "send", "feedback": "Strong. Name one of the paid apps on slide 1 to make it sharper."}
    if task == "reply":
        return {"should_reply": True, "reply": "Thanks! Which one are you trying first?", "reason": "genuine question"}
    if task == "insights":
        return {"summary": "Carousels on how-to pillar outperform; evening slots best.", "recommendations": []}
    return {}
