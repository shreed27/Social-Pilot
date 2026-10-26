"""Quality gates built on Jake Schincariol's open-source scorers (app/vendor/jake, MIT).

- clean()       strips machine artefacts: invisible watermark characters, em dashes, curly quotes,
                and 150+ stock AI phrases (platform-specific lexicon). Safe to auto-apply.
- human()       five-check human score (burstiness, specificity, slop density, fingerprint, voice).
- hook()        five-property hook score (length, specificity, stakes, frontload, address) + dealbreakers.
- reel_beats()  beat-sheet timing: hook over 3 s, beats over 4 s, no loop back to the hook.
- ig_caption()  Instagram caption lint: the 125-char window, hashtag cap, one ask, links.

The README of those tools is candid that the hook scorer catches weak hooks well but cannot pick
winners between two decent ones, so SocialPilot uses it as a floor, and lets the LLM judge and
real engagement data decide among the hooks that clear it.
"""
import json
from functools import lru_cache
from pathlib import Path

from app.vendor.jake import beats as _beats
from app.vendor.jake import caption as _caption
from app.vendor.jake import detect as _detect
from app.vendor.jake import hookscore as _hookscore
from app.vendor.jake import humanize as _humanize

VENDOR = Path(__file__).parent / "vendor" / "jake"
HUMAN_PASS = 70.0     # detect.py's own PASS line
HOOK_FLOOR = 50.0     # hookscore.py: "if the top one is under 50, none of these are the hook"


@lru_cache
def _lex(platform: str) -> dict:
    name = "slop_linkedin.json" if platform == "linkedin" else "slop_instagram.json"
    return json.loads((VENDOR / name).read_text(encoding="utf-8"))


def clean(text: str, platform: str) -> tuple[str, int]:
    """Returns (cleaned_text, number_of_changes)."""
    if not text or not text.strip():
        return text, 0
    out, report = _humanize.humanize(text, _lex(platform))
    changes = sum(len(report.get(k) or []) for k in ("invisible", "typographic", "lexical"))
    # humanize() appends a trailing newline; keep the caller's shape
    return (out.rstrip("\n") if not text.endswith("\n") else out), changes


def human(text: str, platform: str) -> dict:
    results, overall, verdict = _detect.run(text, _lex(platform))
    weakest = min(results, key=lambda k: results[k][0])
    return {"score": round(overall, 1), "verdict": verdict, "weakest": weakest,
            "checks": {k: round(v[0], 1) for k, v in results.items()}}


def hook(text: str) -> dict:
    results, overall, verdict, flags = _hookscore.run(text)
    weakest = min(results, key=lambda k: results[k][0])
    return {"score": round(overall, 1), "verdict": verdict, "weakest": weakest, "dealbreakers": flags}


def reel_beats(beats: list[dict]) -> dict:
    """On-screen beats are read, not spoken, but word count still sets how long a beat takes to land."""
    script = "\n".join(b.get("text", "") for b in beats if b.get("text"))
    a = _beats.analyse(script) or {"notes": [], "total_seconds": 0, "beats": []}
    problems = [n.split(". ")[0] + "." for n in a["notes"]
                if n.startswith(("Beat 1 takes", "Beat(s)", "No loop")) or "nothing concrete" in n]
    return {"seconds": a.get("total_seconds", 0), "problems": problems, "notes": a["notes"]}


def ig_caption(text: str, keywords: list[str] | None = None) -> dict:
    a = _caption.analyse(text, keywords=keywords or None)
    return {"verdict": a["verdict"], "visible": a["visible"],
            "fails": [f"{c['check']}: {c['detail']}" for c in a["checks"] if c["status"] == "FAIL"],
            "warns": [f"{c['check']}: {c['detail']}" for c in a["checks"] if c["status"] == "WARN"]}
