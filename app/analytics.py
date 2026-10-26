"""Analytics + learning loop.

- `collect_metrics()` pulls fresh numbers for recently published posts and follower counts.
- `performance_summary()` turns them into something the strategist can reason over.
- `pick_arm()` chooses the next (pillar, format) with Thompson sampling, so the system
  keeps exploiting what grows the page while still testing new combinations.
"""
import logging
import random
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.db import Draft, DraftStatus, FollowerSnapshot, Metric, select, session, utcnow
from app.pages import Page, load_pages
from app.settings import get_settings

log = logging.getLogger(__name__)


def _latest_metrics(page_id: str, days: int = 60) -> list[tuple[Draft, Metric]]:
    since = utcnow() - timedelta(days=days)
    with session() as db:
        drafts = db.exec(select(Draft).where(Draft.page_id == page_id, Draft.kind == "post",
                                             Draft.status == DraftStatus.published,
                                             Draft.created_at >= since)).all()
        out = []
        for d in drafts:
            m = db.exec(select(Metric).where(Metric.draft_id == d.id).order_by(Metric.captured_at.desc())).first()
            if m:
                out.append((d, m))
        return out


def performance_summary(page: Page) -> dict:
    rows = _latest_metrics(page.id)
    by_pillar, by_format, by_hour = defaultdict(list), defaultdict(list), defaultdict(list)
    by_archetype, by_template = defaultdict(list), defaultdict(list)
    tz = ZoneInfo(get_settings().timezone)
    for d, m in rows:
        by_pillar[d.pillar].append(m.engagement)
        by_format[d.format].append(m.engagement)
        if d.content.get("archetype"):
            by_archetype[d.content["archetype"]].append(m.engagement)
        if d.content.get("template"):
            by_template[d.content["template"]].append(m.engagement)
        if d.scheduled_at:
            sa = d.scheduled_at if d.scheduled_at.tzinfo else d.scheduled_at.replace(tzinfo=ZoneInfo("UTC"))
            local = sa.astimezone(tz)
            by_hour[local.strftime("%H:00")].append(m.engagement)

    def agg(groups):
        return {k: {"posts": len(v), "avg_engagement": round(sum(v) / len(v), 4)} for k, v in groups.items()}

    top = sorted(rows, key=lambda r: r[1].engagement, reverse=True)[:3]
    with session() as db:
        snaps = db.exec(select(FollowerSnapshot).where(FollowerSnapshot.page_id == page.id)
                        .order_by(FollowerSnapshot.captured_at)).all()
    growth = None
    if len(snaps) >= 2:
        growth = {"start": snaps[0].followers, "now": snaps[-1].followers,
                  "delta": snaps[-1].followers - snaps[0].followers}
    return {
        "posts_analysed": len(rows),
        "by_pillar": agg(by_pillar),
        "by_format": agg(by_format),
        "by_hour": agg(by_hour),
        "by_archetype": agg(by_archetype),
        "by_template": agg(by_template),
        "top_posts": [{"topic": d.topic, "angle": d.angle, "format": d.format, "engagement": round(m.engagement, 4)}
                      for d, m in top],
        "followers": growth,
    }


def pick_arm(page: Page) -> tuple[str, str]:
    """Thompson sampling over (pillar, format) using engagement as a soft success signal."""
    rows = _latest_metrics(page.id)
    stats: dict[tuple[str, str], list[float]] = defaultdict(list)
    for d, m in rows:
        stats[(d.pillar, d.format)].append(min(m.engagement * 10, 1.0))  # squash to [0,1]
    best, best_draw = None, -1.0
    for p in page.pillars:
        for f in page.formats:
            obs = stats.get((p.name, f), [])
            a = 1 + sum(obs)
            b = 1 + len(obs) - sum(obs)
            draw = random.betavariate(a, b)
            if draw > best_draw:
                best, best_draw = (p.name, f), draw
    return best


def pick_archetype(page: Page, allowed: list[str]) -> str:
    """Thompson sampling over content archetypes, so proven ones get used more often."""
    rows = _latest_metrics(page.id)
    obs: dict[str, list[float]] = defaultdict(list)
    for d, m in rows:
        if d.content.get("archetype"):
            obs[d.content["archetype"]].append(min(m.engagement * 10, 1.0))
    def draw(a: str) -> float:
        o = obs.get(a, [])
        return random.betavariate(1 + sum(o), 1 + len(o) - sum(o))
    return max(allowed, key=draw)


def next_slot(page: Page) -> datetime:
    """Next free posting slot (UTC, tz-aware). Prefers the best-performing hours once data exists."""
    s = get_settings()
    tz = ZoneInfo(s.timezone)
    summary = performance_summary(page)["by_hour"]
    slots = list(page.preferred_slots)
    if summary:
        ranked = sorted(summary.items(), key=lambda kv: kv[1]["avg_engagement"], reverse=True)
        learned = [h for h, v in ranked if v["posts"] >= 3][:2]
        slots = sorted(set(learned + slots))

    with session() as db:
        taken = {d.scheduled_at for d in db.exec(select(Draft).where(
            Draft.page_id == page.id, Draft.kind == "post",
            Draft.status.in_([DraftStatus.pending, DraftStatus.approved]))).all() if d.scheduled_at}

    min_gap_h = max(1, int(168 / max(page.posts_per_week, 1) * 0.6))
    now = datetime.now(tz)
    for day in range(0, 21):
        date = (now + timedelta(days=day)).date()
        for hm in slots:
            h, mnt = map(int, hm.split(":"))
            cand = datetime(date.year, date.month, date.day, h, mnt, tzinfo=tz)
            if cand <= now + timedelta(minutes=30):
                continue
            cand_utc = cand.astimezone(ZoneInfo("UTC"))
            if all(abs((cand_utc - t).total_seconds()) >= min_gap_h * 3600 for t in taken):
                return cand_utc
    return (now + timedelta(days=1)).astimezone(ZoneInfo("UTC"))


def collect_metrics() -> None:
    from app.platforms.registry import client_for

    since = utcnow() - timedelta(days=14)
    for page in load_pages().values():
        client = client_for(page)
        try:
            followers = client.follower_count()
            if followers is not None:
                with session() as db:
                    db.add(FollowerSnapshot(page_id=page.id, followers=followers))
                    db.commit()
        except Exception as e:  # noqa: BLE001
            log.warning("follower count failed for %s: %s", page.id, e)

        with session() as db:
            posts = db.exec(select(Draft).where(Draft.page_id == page.id, Draft.kind == "post",
                                                Draft.status == DraftStatus.published,
                                                Draft.updated_at >= since)).all()
            for d in posts:
                try:
                    m = client.post_metrics(d.published_id)
                    if m:
                        db.add(Metric(draft_id=d.id, page_id=page.id, **m))
                except Exception as e:  # noqa: BLE001
                    log.warning("metrics failed for draft %s: %s", d.id, e)
            db.commit()
