"""End-to-end offline test: mock LLM + dry-run publishers, temp DB and media dir."""
import json
import os
import tempfile
from datetime import timedelta
from pathlib import Path

import pytest

TMP = Path(tempfile.mkdtemp())
os.environ.update(LLM_PROVIDER="mock", MODE="dry_run", DATABASE_URL=f"sqlite:///{TMP/'t.db'}",
                  MEDIA_DIR=str(TMP / "media"), DASHBOARD_PASSWORD="pw")

from app.agents.critic import rule_violations  # noqa: E402
from app.agents.graph import generate_post  # noqa: E402
from app.db import Draft, DraftStatus, Metric, select, session, utcnow  # noqa: E402
from app.pages import get_page  # noqa: E402


@pytest.mark.parametrize("page_id,fmt,ext", [
    ("insta_main", "carousel", ".png"), ("insta_main", "reel", ".mp4"), ("insta_main", "image", ".png"),
    ("linkedin_main", "document", ".pdf"), ("linkedin_main", "text", None), ("x_main", "thread", None),
])
def test_generate_each_format(page_id, fmt, ext):
    r = generate_post(page_id, fmt=fmt)
    assert r["draft_id"] and r["critic"]["verdict"] == "pass"
    with session() as db:
        d = db.get(Draft, r["draft_id"])
        assert d.status == DraftStatus.pending and d.scheduled_at > utcnow()
        if ext:
            assert d.media and d.media[0].endswith(ext) and all(Path(m).exists() for m in d.media)
        else:
            assert not d.media


def test_rules_catch_x_problems():
    page = get_page("x_main")
    v = rule_violations(page, "thread", {"thread": ["a" * 300, "see https://x.com", "ok"], "hashtags": ["#a", "#b"]})
    assert any(">280" in s for s in v) and any("URL" in s for s in v) and any("hashtags" in s for s in v)


def test_approve_publish_metrics_and_replies():
    from fastapi.testclient import TestClient

    from app.analytics import collect_metrics, performance_summary
    from app.engagement import scan_comments
    from app.publisher import publish_due
    from app.web.main import app

    with TestClient(app) as client:
        assert client.get("/classic", auth=("u", "pw")).status_code == 200
        assert client.get("/classic", auth=("u", "wrong")).status_code == 401
        with session() as db:
            draft_id = db.exec(select(Draft).where(Draft.status == DraftStatus.pending)).first().id
        r = client.post(f"/drafts/{draft_id}/approve", auth=("u", "pw"), data={"caption": "Edited caption"},
                        follow_redirects=False)
        assert r.status_code == 303
        ov = client.get("/api/overview", auth=("u", "pw")).json()
        assert ov["counts"]["approved"] == 1 and set(ov["pages"]) == {"insta_main", "linkedin_main", "x_main"}
        assert client.get("/api/drafts?status=pending", auth=("u", "pw")).json()[0]["trace"]

    with session() as db:  # make it due now
        d = db.get(Draft, draft_id)
        assert d.status == DraftStatus.approved and d.content["caption"] == "Edited caption"
        d.scheduled_at = utcnow() - timedelta(minutes=1)
        db.add(d)
        db.commit()
    assert publish_due() == 1
    with session() as db:
        d = db.get(Draft, draft_id)
        assert d.status == DraftStatus.published and d.published_id.startswith("dry_")

    collect_metrics()
    with session() as db:
        assert db.exec(select(Metric)).first() is not None
    assert performance_summary(get_page(d.page_id))["posts_analysed"] >= 1

    assert scan_comments() >= 1
    assert scan_comments() == 0  # never double-replies
    with session() as db:
        reply = db.exec(select(Draft).where(Draft.kind == "reply")).first()
        reply.status = DraftStatus.approved
        db.add(reply)
        db.commit()
    assert publish_due() == 1


def test_ai_tells_and_viral_score():
    from app.agents.critic import viral_score
    from app.humanize import ai_tells

    bad = "In today's fast-paced world, let's dive in and unlock your potential. No fees. No stress. Just growth."
    tells = " ".join(ai_tells(bad))
    assert "unlock" in tells and "No X. No Y. Just Z." in tells
    assert ai_tells("I cancelled 4 subscriptions last night. Here's what I use now.") == []
    s = {"hook": 10, "shareability": 10, "save_worthiness": 6, "discussion": 2, "human_voice": 8, "niche_fit": 8, "platform_fit": 8}
    assert viral_score("instagram", s) > viral_score("x", s)  # IG weights sends, X weights replies


def test_hook_tournament_saved_on_draft():
    r = generate_post("insta_main", fmt="carousel")
    with session() as db:
        d = db.get(Draft, r["draft_id"])
    assert d.content["hook"] and len(d.content["hook_options"]) >= 3
    assert d.content["archetype"] and d.content["goal"] and d.critic["viral_score"] >= 8
    assert d.content["slides"][0]["title"] == d.content["hook"] or d.content["hook"]


def test_quality_gates_send_slop_back():
    from app.agents.critic import quality_report
    page = get_page("linkedin_main")
    slop = {"caption": "In today's fast-paced world, let's dive in. We leverage cutting-edge synergy to unlock value. "
                       "We empower teams to elevate outcomes. We streamline workflows seamlessly.",
            "hook": "Hey guys, today I want to talk about AI"}
    report, v = quality_report(page, "text", slop)
    assert report["human"]["verdict"] != "PASS" and any("human score" in x for x in v)
    assert any("hook" in x for x in v)
    from app.agents.critic import clean_content
    cleaned, n = clean_content("linkedin", {"caption": "It​s a game-changer — really."})
    assert n >= 2 and "​" not in cleaned["caption"] and "—" not in cleaned["caption"]


def test_xbird_scout_read_only_ranked_and_capped(tmp_path, monkeypatch):
    import sys
    from app.settings import get_settings
    from app.sources import xbird

    s = get_settings()
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("FAKE_XBIRD_LOG", str(log))
    monkeypatch.setattr(s, "xbird_enabled", True)
    monkeypatch.setattr(s, "xbird_command", f"{sys.executable} {Path(__file__).parent / 'fake_xbird.py'}")
    monkeypatch.setattr(s, "xbird_daily_budget_usd", 1.0)
    page = get_page("x_main")
    monkeypatch.setattr(page, "search_keywords", ["study tips"])
    monkeypatch.setattr(page, "reference_accounts", ["@topper"])
    xbird._ledger_path().unlink(missing_ok=True)

    posts = xbird.scout(page)
    assert posts and posts[0]["author"] == "smallacct"          # the outlier beats the big account
    assert posts[0]["multiple"] > 3 and "re-reading" in posts[0]["text"]
    assert "x its author" not in xbird.as_prompt(posts) and "× its author's usual" in xbird.as_prompt(posts)
    tools = [json.loads(l)["tool"] for l in log.read_text().splitlines()]
    assert set(tools) <= xbird.READ_TOOLS and "post_tweet" not in tools
    assert round(xbird.spent_today(), 3) == 0.1                   # 2 calls × 20 × $0.0025

    import asyncio
    with pytest.raises(PermissionError):
        asyncio.run(xbird._run([("post_tweet", {"text": "hi"})]))
    monkeypatch.setattr(s, "xbird_daily_budget_usd", 0.1)
    assert xbird.scout(page) == []                                # budget reached → no more calls


def test_research_uses_live_x_posts(monkeypatch):
    from app.agents import research
    from app.sources import xbird
    seen = {}
    monkeypatch.setattr(xbird, "scout", lambda page: [{"multiple": 9.0, "likes": 4200, "replies": 610, "bookmarks": 900,
                                                       "author": "smallacct", "text": "I failed DBMS twice."}])
    real = research.ask_json
    def spy(task, system, prompt, **kw):
        seen["prompt"] = prompt
        return real(task, system, prompt, **kw)
    monkeypatch.setattr(research, "ask_json", spy)
    out = research.research_node({"page_id": "x_main", "log": []})
    assert "LIVE ON X THIS WEEK" in seen["prompt"] and "I failed DBMS twice." in seen["prompt"]
    assert "live X posts via xbird" in out["log"][-1]


def _fake_clip(path, color="0x224466"):
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc2=size=720x1280:rate=24",
                    "-t", "3", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def test_ai_broll_reel_end_to_end(tmp_path, monkeypatch):
    import shutil
    import subprocess
    from app.settings import get_settings
    from app.sources import kie

    s = get_settings()
    monkeypatch.setattr(s, "kie_api_key", "test-key")
    monkeypatch.setattr(s, "kie_video_model", "veo3_fast")
    monkeypatch.setattr(s, "kie_daily_budget_usd", 1.0)
    kie._ledger().unlink(missing_ok=True)
    clip = _fake_clip(tmp_path / "src.mp4")
    calls = []

    class R:
        def __init__(self, j): self._j = j
        def raise_for_status(self): pass
        def json(self): return self._j

    def fake_post(url, headers, json, timeout):
        calls.append(("POST", url, json))
        assert headers["Authorization"] == "Bearer test-key" and json["aspect_ratio"] == "9:16"
        assert "NO text" in json["prompt"]                       # scene rules are always appended
        return R({"code": 200, "data": {"taskId": f"t{len(calls)}"}})

    def fake_get(url, headers, timeout):
        calls.append(("GET", url, None))
        return R({"code": 200, "data": {"successFlag": 1, "response": {"resultUrls": ["https://cdn.example/clip.mp4"]}}})

    monkeypatch.setattr(kie.httpx, "post", fake_post)
    monkeypatch.setattr(kie.httpx, "get", fake_get)
    monkeypatch.setattr(kie.time, "sleep", lambda s: None)
    monkeypatch.setattr(kie, "download", lambda url, dest: shutil.copy(clip, dest) and dest)

    r = generate_post("insta_main", fmt="reel")
    with session() as db:
        d = db.get(Draft, r["draft_id"])
    out = d.media[0]
    assert out.endswith(".mp4") and Path(out).exists()
    assert sum(1 for c in calls if c[0] == "POST" and c[1].endswith("/api/v1/veo/generate")) == 2
    assert round(kie.spent_today(), 2) == 0.80                    # 2 clips × $0.40
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                            "-of", "json", out], capture_output=True, text=True).stdout
    info = json.loads(probe)
    v = next(x for x in info["streams"] if x["codec_type"] == "video")
    assert (v["width"], v["height"]) == (1080, 1920) and any(x["codec_type"] == "audio" for x in info["streams"])
    total = sum(b["seconds"] for b in d.content["reel_script"])
    assert abs(float(info["format"]["duration"]) - total) < 0.6

    # budget: $0.20 left can't cover another 2-clip reel → falls back to the text reel, no new charge
    r2 = generate_post("insta_main", fmt="reel")
    assert round(kie.spent_today(), 2) == 0.80
    with session() as db:
        assert Path(db.get(Draft, r2["draft_id"]).media[0]).exists()


def test_kie_parses_job_results():
    from app.sources.kie import KieClient
    assert KieClient._urls({"resultJson": '{"resultUrls": ["https://x/a.mp4"]}'}) == ["https://x/a.mp4"]
    assert KieClient._urls({"response": {"resultUrls": ["https://x/b.mp4"]}}) == ["https://x/b.mp4"]
    from app.sources.kie import video_cost
    assert video_cost("veo3_fast") == 0.40 and abs(video_cost("kling-3.0/video", 5) - 0.35) < 1e-9


def test_auto_approve_is_opt_in(monkeypatch):
    from app.settings import get_settings
    s = get_settings()
    r = generate_post("x_main", fmt="thread")
    with session() as db:
        assert db.get(Draft, r["draft_id"]).status == DraftStatus.pending      # default: waits for you
    monkeypatch.setattr(s, "auto_approve_min_score", 8.0)
    r = generate_post("x_main", fmt="thread")
    with session() as db:
        d = db.get(Draft, r["draft_id"])
    assert d.status == DraftStatus.approved and "auto-approved" in d.trace[-1]
    monkeypatch.setattr(s, "auto_approve_min_score", 9.9)                     # bar too high → still waits
    r = generate_post("x_main", fmt="thread")
    with session() as db:
        assert db.get(Draft, r["draft_id"]).status == DraftStatus.pending


def test_approve_posts_immediately_and_notifies_slack(monkeypatch):
    from fastapi.testclient import TestClient

    from app import publisher, slack
    from app.settings import get_settings
    from app.web.main import app

    sent = []
    monkeypatch.setattr(get_settings(), "slack_webhook_url", "https://hooks.slack.test/T/B/X")
    monkeypatch.setattr(get_settings(), "dashboard_url", "https://social.example.in")

    class R:
        def raise_for_status(self): pass
    monkeypatch.setattr(slack.httpx, "post", lambda url, json, timeout: sent.append(json) or R())

    r = generate_post("linkedin_main", fmt="document")
    with TestClient(app) as client:
        res = client.post(f"/api/drafts/{r['draft_id']}/approve", auth=("u", "pw"), json={})
        assert res.status_code == 200 and res.json()["status"] == "publishing"
    with session() as db:
        d = db.get(Draft, r["draft_id"])
    assert d.status == DraftStatus.published and d.published_id.startswith("dry_")   # posted, not just scheduled
    assert any("Published on linkedin" in m["text"] for m in sent)
    assert publisher.publish_now(d.id) is False                                     # can't go out twice

    # scheduled path still works: publish_now=false keeps it for its slot
    r2 = generate_post("x_main", fmt="thread")
    with TestClient(app) as client:
        res = client.post(f"/api/drafts/{r2['draft_id']}/approve", auth=("u", "pw"), json={"publish_now": False})
        assert res.json()["status"] == "approved"

    text, blocks = slack.build_digest()
    flat = json.dumps(blocks)
    assert "SocialPilot daily report" in flat and "waiting for your review" in flat and "Open dashboard" in flat
    assert "posts published" in text
    assert slack.digest() is True and sent[-1]["blocks"][0]["type"] == "header"


def test_failed_publish_alerts_slack(monkeypatch):
    from app import publisher, slack
    from app.platforms.base import DryRunClient
    from app.settings import get_settings

    sent = []
    monkeypatch.setattr(get_settings(), "slack_webhook_url", "https://hooks.slack.test/x")
    class R:
        def raise_for_status(self): pass
    monkeypatch.setattr(slack.httpx, "post", lambda url, json, timeout: sent.append(json) or R())
    monkeypatch.setattr(DryRunClient, "publish", lambda self, d: (_ for _ in ()).throw(RuntimeError("token expired")))
    r = generate_post("insta_main", fmt="image")
    with session() as db:
        d = db.get(Draft, r["draft_id"]); d.status = DraftStatus.approved; db.add(d); db.commit()
    assert publisher.publish_now(r["draft_id"]) is True
    with session() as db:
        assert db.get(Draft, r["draft_id"]).status == DraftStatus.failed
    assert any("Couldn't publish" in m["text"] and "token expired" in m["text"] for m in sent)


def test_deep_layouts_render(monkeypatch):
    r = generate_post("insta_main", fmt="carousel")
    with session() as db:
        d = db.get(Draft, r["draft_id"])
    layouts = {s.get("layout") for s in d.content["slides"]}
    assert {"steps", "stat", "list", "compare"} <= layouts and len(d.media) == len(d.content["slides"])
    assert d.content.get("sources") and len(d.content["caption"]) >= 300
    assert "depth: fact pack" in " ".join(d.trace)
