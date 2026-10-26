"""Viral playbooks: what each platform's ranking system rewards (researched Oct 2026), and the
content archetypes and hook patterns that reliably earn those signals.

Every agent reads from here: the strategist picks an archetype + goal, the writer follows its
structure, the critic scores against the platform's signals, the visual agent picks a template.
Sources are listed in ARCHITECTURE.md ("Viral playbook").
"""

PLATFORM_PLAYBOOK = {
    "instagram": {
        "optimize_for": "sends per reach (DM shares, biggest lever for reaching NON-followers), watch time "
                        "(incl. replays) and saves. Likes per reach matters mostly for existing followers.",
        "rules": [
            "Original content only. Pages that mostly repost lose recommendations to non-followers.",
            "About half of viewers watch muted: the hook must be ON SCREEN as text in the first frame.",
            "The first 24 hours decide reach. Post when the audience is awake; reply to every comment fast.",
            "Carousels: up to 20 slides; unswiped slides get re-shown later, so every slide must stand alone. "
            "They earn far more saves than single images. 7–10 slides is the sweet spot.",
            "Reels: payoff promised by second 3, first word on screen immediately, end on a loop back to the start.",
            "Hashtags don't drive reach anymore: 3–5 descriptive ones for classification, never a wall.",
            "Put niche keywords in the caption and on-screen text (Instagram search reads them).",
            "No third-party watermarks.",
        ],
        "caption": "First 125 characters must re-state the hook or add tension. Then 2–5 short lines of context "
                   "or the 'why'. End with a SEND-oriented CTA ('Send this to the friend who…') or a save CTA.",
        "best_actions": ["send", "save", "watch_time"],
    },
    "linkedin": {
        "optimize_for": "comments (most heavily weighted, thoughtful threaded ones most), saves (≈5× a like), "
                        "and dwell time. The first 30–60 minutes decide whether a post expands.",
        "rules": [
            "The 360Brew ranker matches posts to readers by topic: stay tightly on the page's niche every time.",
            "Only ~210 characters show before 'see more': lines 1–2 must create an information gap.",
            "Document (PDF) carousels earn the most dwell time: 8–12 pages, one idea per page, large text.",
            "External links cut reach sharply (even in the first comment). Never include links.",
            "Generic AI-sounding posts with no original insight get a fraction of the reach. Every post needs "
            "a specific example, number, decision or opinion that only this page would write.",
            "No engagement bait ('comment YES', 'like if you agree'). Ask a real question people can answer "
            "from their own experience.",
            "Short paragraphs (1–3 lines) with white space. 1–3 hashtags at most.",
            "Company pages get little organic reach: write posts employees will want to reshare.",
        ],
        "caption": "Hook in ≤ 2 lines. Then the story / argument with concrete detail. Close with a specific "
                   "question that invites experience-based comments.",
        "best_actions": ["comment", "save", "dwell"],
    },
    "x": {
        "optimize_for": "replies (and especially replies the author answers back: the heaviest positive "
                        "signal), profile clicks, bookmarks, conversation dwell. Likes are nearly worthless; "
                        "mutes/blocks/reports are heavily negative.",
        "rules": [
            "No links in the post (non-Premium link posts get close to zero engagement).",
            "Make the argument clear in the first 8 words. Cut hedges (I think, maybe, kind of).",
            "Take a side. A confident, defensible position beats a neutral one.",
            "Single posts under ~100 characters tend to do best; use a thread only for 3+ distinct points.",
            "Text tends to beat images and video on X; use an image only when it IS the content.",
            "Screenshot-able: one sharp idea people want to quote.",
            "Never rage-bait or punch down: negative feedback is weighted heavily against you.",
            "Max 1 hashtag, usually none. No ALL CAPS.",
        ],
        "caption": "One tight post, or a thread whose first post works as a standalone banger.",
        "best_actions": ["reply", "bookmark", "profile_click"],
    },
}

# Content archetypes proven to spread, with the signal each one is best at earning.
ARCHETYPES = {
    "framework": {"goal": "save", "platforms": ["instagram", "linkedin", "x"],
                  "structure": "Name the system → one step per slide/post with a concrete action → recap slide.",
                  "hook_example": "The 4-step system I use to never miss a deadline"},
    "relatable": {"goal": "send", "platforms": ["instagram", "x"],
                  "structure": "Set up a situation the audience lives every week → escalating, painfully true "
                               "details → punchline. Funny because it's true.",
                  "hook_example": "Every engineering student the night before a viva"},
    "contrarian": {"goal": "comment", "platforms": ["instagram", "linkedin", "x"],
                   "structure": "A defensible take most of the niche disagrees with → why people believe the "
                                "opposite → your evidence → what to do instead.",
                   "hook_example": "Making notes is the slowest way to study"},
    "before_after": {"goal": "send", "platforms": ["instagram", "linkedin"],
                     "structure": "'X vs Y' cover → side-by-side comparisons, one per slide → verdict.",
                     "hook_example": "How toppers study vs how we study"},
    "proof": {"goal": "save", "platforms": ["instagram", "linkedin", "x"],
              "structure": "Specific result with a real number → what was done, step by step → the one lesson.",
              "hook_example": "We cut our onboarding from 9 steps to 3. Signups doubled."},
    "red_flags": {"goal": "send", "platforms": ["instagram", "linkedin"],
                  "structure": "'N red flags in <niche thing>' → one concrete warning sign per slide with why it "
                               "matters → what green looks like.",
                  "hook_example": "7 red flags in an internship offer"},
    "advice_i_needed": {"goal": "save", "platforms": ["instagram", "linkedin"],
                        "structure": "'Advice I needed at <stage>' → specific, earned lessons → ask readers for theirs.",
                        "hook_example": "Placement advice I needed in 2nd year, not 4th"},
    "explainer": {"goal": "save", "platforms": ["instagram", "linkedin", "x"],
                  "structure": "'What is <trending term>, actually?' → what it means → why everyone's talking "
                               "→ how it works → real example → why it matters to YOU.",
                  "hook_example": "What is an AI agent, actually? (in 6 slides)"},
    "story": {"goal": "comment", "platforms": ["linkedin", "x", "instagram"],
              "structure": "Start mid-moment with no setup → tension → turning point → the lesson, stated plainly.",
              "hook_example": "I got rejected from 31 internships. The 32nd one changed how I apply."},
    "hot_take": {"goal": "reply", "platforms": ["x", "linkedin"],
                 "structure": "One confident sentence. Optionally one line of reasoning. No hedging.",
                 "hook_example": "Most 'AI startups' are a prompt and a Stripe account."},
    "list": {"goal": "save", "platforms": ["x", "instagram", "linkedin"],
             "structure": "Curated, specific list where every item is named and useful on its own.",
             "hook_example": "6 free tools I'd pay for"},
    "news": {"goal": "send", "platforms": ["instagram", "linkedin", "x"],
             "structure": "What just changed (with date/source) → what it means for this audience → what to do now.",
             "hook_example": "Instagram just changed how Reels get ranked. Here's what it means for you."},
}

HOOK_TYPES = {
    "bold_claim": "A counterintuitive statement that challenges what the audience believes.",
    "curiosity_gap": "Hint at a specific payoff without revealing it.",
    "micro_story": "Start mid-story with no setup ('I deleted 3 months of notes last night.').",
    "specific_number": "A concrete, surprising number or result.",
    "callout": "Name exactly who this is for ('If you're in 3rd year and have zero projects…').",
    "question": "A question the viewer can't answer immediately but wants to.",
    "contrast": "X vs Y, before vs after, them vs you.",
}

# Visual templates the renderer supports, and what each suits.
TEMPLATES = {
    "bold": "Big type, one idea per slide, a highlighted keyword in the accent colour. Default for frameworks, lists.",
    "post_card": "Looks like a social text-post screenshot (avatar, name, big text). Great for hot takes, "
                 "relatable lines and quotes people screenshot and send.",
    "minimal": "Plain high-contrast storytelling slide, one sentence per slide. Great for stories and contrarian takes.",
    "split": "Two-column contrast (e.g. 'Them' vs 'You', 'Before' vs 'After'). For before_after archetype.",
}


def archetypes_for(platform: str) -> dict:
    return {k: v for k, v in ARCHETYPES.items() if platform in v["platforms"]}


def playbook_text(platform: str) -> str:
    pb = PLATFORM_PLAYBOOK[platform]
    rules = "\n".join(f"- {r}" for r in pb["rules"])
    return f"WHAT THE {platform.upper()} ALGORITHM REWARDS: {pb['optimize_for']}\nRULES:\n{rules}\nCAPTION: {pb['caption']}"
