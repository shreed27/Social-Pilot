"""Detects the tells that make a post read as AI-written. LinkedIn in particular down-ranks generic
AI-sounding posts, and on every platform readers scroll past them. The critic sends any draft with
tells back to the writer."""
import re

BANNED_WORDS = [
    "delve", "leverage", "empower", "elevate", "unlock", "unleash", "harness", "foster", "ignite", "embark",
    "navigate the", "seamless", "seamlessly", "robust", "cutting-edge", "game-changer", "game changer",
    "revolutionary", "transformative", "paradigm", "synergy", "tapestry", "testament", "beacon", "realm",
    "symphony", "landscape", "myriad", "plethora", "multifaceted", "pivotal", "unwavering", "holistic",
    "furthermore", "moreover", "additionally", "in conclusion", "it is important to note", "it's important to note",
    "in today's fast-paced", "in today's digital", "in the ever-evolving", "ever-changing world",
    "let's dive in", "dive into", "deep dive", "picture this", "imagine a world", "buckle up",
    "here's the kicker", "but here's the thing", "here's the thing", "real talk", "the secret sauce",
    "at the end of the day", "look no further", "take it to the next level", "supercharge", "skyrocket",
    "journey", "unlocking", "streamline", "optimize your", "crucial", "vital role", "embrace",
]

PATTERNS = [
    (re.compile(r"\bno \w+\.\s+no \w+\.\s+just\b", re.I), "'No X. No Y. Just Z.' formula"),
    (re.compile(r"\bnot (?:just|only) [^.]{1,60}?,? but (?:also )?", re.I), "'not just X, but Y' construction"),
    (re.compile(r"—"), None),  # counted below
    (re.compile(r"\b(?:I think|I believe|kind of|sort of|arguably)\b", re.I), "hedging phrase"),
    (re.compile(r"^(?:🚀|✨|💡|🔥|✅|👉)", re.M), "emoji bullet list"),
]


def ai_tells(text: str) -> list[str]:
    """Returns human-readable problems; empty list means the copy reads human."""
    if not text:
        return []
    low = text.lower()
    found = []
    words = sorted({w for w in BANNED_WORDS if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", low)})
    if words:
        found.append("AI-sounding words: " + ", ".join(words[:8]))
    for rx, label in PATTERNS:
        if label and rx.search(text):
            found.append(label)
    if text.count("—") > 2:
        found.append(f"{text.count('—')} em dashes (reads machine-written; use full stops)")
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 3]
    if len(sentences) >= 5:
        lens = [len(s.split()) for s in sentences]
        avg = sum(lens) / len(lens)
        spread = max(lens) - min(lens)
        if spread < 6 and 10 <= avg <= 22:
            found.append("every sentence is the same length (vary rhythm: some very short)")
    return found


HUMAN_VOICE_RULES = """WRITE LIKE A REAL PERSON, NOT A BRAND OR AN AI:
- Sound like one specific, opinionated person from this niche talking to a friend. Use "I"/"we" and "you".
- Concrete beats clever: real numbers, named tools, named places, exact steps, an actual moment.
- Vary rhythm hard (a detector scores this): mix 2–5 word lines with at least one sentence of 20+
  words that explains something. Fragments are fine. Never five sentences of the same length.
- Something checkable in the first line and in every few lines: a number, a named tool, a place, a price.
- Take a side. No hedging (I think, maybe, kind of), no "on the other hand" balancing.
- Contractions always (it's, don't, you'll). Everyday words a 19-year-old or a busy founder would use.
- Never use: delve, leverage, unlock, elevate, seamless, game-changer, journey, landscape, realm, tapestry,
  testament, "let's dive in", "here's the thing", "in today's fast-paced world", "picture this",
  "No X. No Y. Just Z.", "not just X but Y", "in conclusion". At most one em dash per post.
- No fake stories or invented statistics. If you use a number, it must be real or clearly an example.
- No emoji bullet lists. At most 1–2 emojis per post, only where a person would naturally use one."""
