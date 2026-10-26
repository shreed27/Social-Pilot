"""Slack updates for the team channel, via an Incoming Webhook.

- published(): ✅ every post that goes live, with a link to it
- failed():    ❌ any post that couldn't be published, with the reason
- drafts_ready(): 📝 one message per planning run listing drafts waiting for review
- digest():    📊 the daily report: followers, what went out, how it did, what's next, spend

All calls are best-effort: Slack being down never blocks posting.
"""
import logging
from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

import httpx

from app.db import Draft, DraftStatus, FollowerSnapshot, Metric, select, session, utcnow
from app.pages import Page, load_pages
from app.settings import get_settings

log = logging.getLogger(__name__)
ICON = {"instagram": "📸", "linkedin": "💼", "x": "𝕏"}


def enabled() -> bool:
    return bool(get_settings().slack_webhook_url)


def send(text: str, blocks: list | None = None) -> bool:
    s = get_settings()
    if not s.slack_webhook_url:
        return False
    try:
        r = httpx.post(s.slack_webhook_url, json={"text": text, **({"blocks": blocks} if blocks else {})}, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("slack send failed: %s", e)
        return False


def _esc(t: str) -> str:
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _dash(path: str = "") -> str | None:
    base = get_settings().dashboard_url.rstrip("/")
    return f"{base}/{path}" if base else None


def _button(text: str, url: str | None) -> list:
    return [{"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": text}, "url": url}]}] if url else []


def published(d: Draft, page: Page, link: str | None) -> None:
    mode = "" if get_settings().live else " _(dry run, not really posted)_"
    title = f"{ICON.get(page.platform, '')} Published on {page.platform} · {page.handle}{mode}"
    body = f"*{_esc(d.topic)}*\n{_esc((d.content.get('caption') or '')[:280])}"
    score = (d.critic or {}).get("viral_score")
    ctx = f"{d.format}" + (f" · viral score {score}" if score else "") + (f" · <{link}|open post>" if link else "")
    send(f"{title}: {d.topic}", [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{title}*\n{body}"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": ctx}]},
    ])


def failed(d: Draft, page: Page) -> None:
    text = f"❌ Couldn't publish {page.platform} {d.format} for {page.handle}: *{_esc(d.topic)}*\n> {_esc((d.error or '')[:400])}"
    send(text, [{"type": "section", "text": {"type": "mrkdwn", "text": text}}, *_button("Retry in dashboard", _dash("#queue"))])


def drafts_ready(drafts: list[Draft]) -> None:
    if not drafts or not get_settings().slack_notify_drafts:
        return
    pages = load_pages()
    lines = [f"{ICON.get(d.platform, '')} *{_esc(d.topic)}* · {d.format} · viral {(d.critic or {}).get('viral_score', '–')}"
             + (" · _auto-approved_" if d.status == DraftStatus.approved else "") + f" · {pages[d.page_id].handle}"
             for d in drafts]
    head = f"📝 {len(drafts)} new draft{'s' if len(drafts) != 1 else ''} from the agents"
    send(head, [{"type": "section", "text": {"type": "mrkdwn", "text": head + "\n" + "\n".join(lines[:15])}},
                *_button("Review and approve", _dash("#queue"))])


def _followers(page_id: str) -> tuple[int | None, int, int]:
    now = utcnow()
    with session() as db:
        snaps = db.exec(select(FollowerSnapshot).where(FollowerSnapshot.page_id == page_id,
                                                       FollowerSnapshot.captured_at >= now - timedelta(days=8))
                        .order_by(FollowerSnapshot.captured_at)).all()
    if not snaps:
        return None, 0, 0

    def at(delta: timedelta):
        cut = now - delta
        older = [s for s in snaps if s.captured_at <= cut]
        return (older[-1] if older else snaps[0]).followers
    cur = snaps[-1].followers
    return cur, cur - at(timedelta(days=1)), cur - at(timedelta(days=7))


def build_digest() -> tuple[str, list]:
    from app.sources import kie, xbird

    s = get_settings()
    tz = ZoneInfo(s.timezone)
    now = utcnow()
    since = now - timedelta(days=1)
    pages = load_pages()
    with session() as db:
        all_d = db.exec(select(Draft)).all()
        latest = {}
        for m in db.exec(select(Metric).order_by(Metric.captured_at)).all():
            latest[m.draft_id] = m

    def ts(d):  # tz-aware UTC
        x = d.updated_at
        return x if x.tzinfo else x.replace(tzinfo=ZoneInfo("UTC"))

    posted = [d for d in all_d if d.status == DraftStatus.published and d.kind == "post" and ts(d) >= since]
    replies = [d for d in all_d if d.status == DraftStatus.published and d.kind == "reply" and ts(d) >= since]
    failed_ = [d for d in all_d if d.status == DraftStatus.failed and ts(d) >= since]
    pending = [d for d in all_d if d.status == DraftStatus.pending]
    upcoming = sorted([d for d in all_d if d.status == DraftStatus.approved and d.scheduled_at
                       and (d.scheduled_at if d.scheduled_at.tzinfo else d.scheduled_at.replace(tzinfo=ZoneInfo("UTC")))
                       <= now + timedelta(days=1)], key=lambda d: d.scheduled_at)

    day = now.astimezone(tz).strftime("%a %d %b")
    blocks: list = [{"type": "header", "text": {"type": "plain_text", "text": f"📊 SocialPilot daily report · {day}"}}]
    total_growth = 0
    by_page = defaultdict(list)
    for d in posted:
        by_page[d.page_id].append(d)
    for pid, p in pages.items():
        cur, d1, d7 = _followers(pid)
        total_growth += d1
        mine = by_page.get(pid, [])
        week = [d for d in all_d if d.page_id == pid and d.status == DraftStatus.published and d.kind == "post"
                and ts(d) >= now - timedelta(days=7) and d.id in latest]
        top = max(week, key=lambda d: latest[d.id].engagement, default=None)
        line = (f"*{ICON.get(p.platform, '')} {p.handle}*  ·  "
                + (f"{cur:,} followers ({d1:+,} today, {d7:+,} this week)" if cur is not None else "followers not tracked yet")
                + f"\n{len(mine)} post{'s' if len(mine) != 1 else ''} published today")
        if mine:
            line += ": " + "; ".join(f"“{_esc(d.topic[:60])}”" for d in mine[:3])
        if top:
            m = latest[top.id]
            link = (top.content or {}).get("permalink")
            name = f"<{link}|{_esc(top.topic[:60])}>" if link else f"“{_esc(top.topic[:60])}”"
            line += f"\n🏆 Best this week: {name} · {m.impressions:,} reach, {m.saves:,} saves, {m.shares:,} shares, {m.follows:,} follows"
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": line}})

    blocks.append({"type": "divider"})
    summary = (f"*Today:* {len(posted)} posts and {len(replies)} replies published · {len(failed_)} failed · "
               f"*{len(pending)} waiting for your review*")
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": summary}})
    if upcoming:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Next 24 hours:*\n" + "\n".join(
            f"{(d.scheduled_at if d.scheduled_at.tzinfo else d.scheduled_at.replace(tzinfo=ZoneInfo('UTC'))).astimezone(tz).strftime('%a %H:%M')}"
            f"  {ICON.get(d.platform, '')} {_esc(d.topic[:70])}" for d in upcoming[:8])}})
    if failed_:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*Failed:*\n" + "\n".join(
            f"❌ {_esc(d.topic[:60])}: {_esc((d.error or '')[:120])}" for d in failed_[:5])}})
    spend = f"AI video/images ${kie.spent_today():.2f} of ${s.kie_daily_budget_usd:.2f}"
    if s.xbird_enabled:
        spend += f" · X research ${xbird.spent_today():.2f} of ${s.xbird_daily_budget_usd:.2f}"
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f"Spend today: {spend} · mode: {s.mode}"}]})
    blocks += _button("Open dashboard", _dash(""))
    text = f"SocialPilot {day}: {len(posted)} posts published, {total_growth:+,} followers, {len(pending)} waiting for review"
    return text, blocks


def digest() -> bool:
    text, blocks = build_digest()
    ok = send(text, blocks)
    log.info("slack digest %s", "sent" if ok else "skipped (no webhook)" if not enabled() else "failed")
    return ok
