"""JSON API used by the React dashboard (frontend/)."""
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.analytics import collect_metrics, performance_summary
from app.db import Draft, DraftStatus, FollowerSnapshot, Metric, select, session, utcnow
from app.engagement import scan_comments
from app.pages import load_pages
from app.publisher import publish_due
from app.settings import get_settings

router = APIRouter(prefix="/api")
UTC = ZoneInfo("UTC")


def _media_url(path: str) -> str:
    s = get_settings()
    try:
        rel = Path(path).resolve().relative_to(s.media_dir.resolve()).as_posix()
    except ValueError:
        return path
    return f"/media/{rel}"


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).isoformat()


def serialize(d: Draft, metric: Metric | None = None) -> dict:
    return {
        "id": d.id, "page_id": d.page_id, "platform": d.platform, "kind": d.kind, "format": d.format,
        "pillar": d.pillar, "topic": d.topic, "angle": d.angle, "content": d.content,
        "media": [{"url": _media_url(m), "type": Path(m).suffix.lstrip(".")} for m in d.media],
        "critic": d.critic, "trace": d.trace or [], "reply_context": d.reply_context, "status": d.status.value,
        "scheduled_at": _iso(d.scheduled_at), "published_id": d.published_id, "error": d.error,
        "created_at": _iso(d.created_at), "updated_at": _iso(d.updated_at),
        "metrics": None if not metric else {
            "impressions": metric.impressions, "likes": metric.likes, "comments": metric.comments,
            "shares": metric.shares, "saves": metric.saves, "follows": metric.follows,
            "engagement": round(metric.engagement, 4)},
    }


def _latest_metric(db, draft_id: int) -> Metric | None:
    return db.exec(select(Metric).where(Metric.draft_id == draft_id).order_by(Metric.captured_at.desc())).first()


def _get(db, draft_id: int) -> Draft:
    d = db.get(Draft, draft_id)
    if not d:
        raise HTTPException(404, "Draft not found")
    return d


# ── pages ────────────────────────────────────────────────────────────────────

@router.get("/pages")
def pages():
    return [p.model_dump() for p in load_pages().values()]


# ── drafts ───────────────────────────────────────────────────────────────────

@router.get("/drafts")
def drafts(status: str | None = None, page_id: str | None = None):
    with session() as db:
        q = select(Draft)
        if status:
            q = q.where(Draft.status == DraftStatus(status))
        if page_id:
            q = q.where(Draft.page_id == page_id)
        rows = db.exec(q.order_by(Draft.created_at.desc())).all()
        return [serialize(d, _latest_metric(db, d.id)) for d in rows]


class ApproveBody(BaseModel):
    caption: str | None = None
    thread: list[str] | None = None
    scheduled_at: str | None = None  # ISO 8601 with offset; ignored when publish_now
    publish_now: bool = True         # Approve = post it now. False = keep it for its scheduled slot.


@router.post("/drafts/{draft_id}/approve")
def approve(draft_id: int, body: ApproveBody, bg: BackgroundTasks):
    with session() as db:
        d = _get(db, draft_id)
        content = dict(d.content)
        if body.thread:
            content["thread"] = [p for p in body.thread if p.strip()]
            content["caption"] = content["thread"][0]
        elif body.caption is not None:
            content["caption"] = body.caption
        d.content = content
        if body.publish_now and d.kind == "post":
            d.scheduled_at = utcnow()
        elif body.scheduled_at:
            d.scheduled_at = datetime.fromisoformat(body.scheduled_at.replace("Z", "+00:00")).astimezone(UTC)
        d.status, d.updated_at = DraftStatus.approved, utcnow()
        db.add(d)
        db.commit()
        out = serialize(d)
    if body.publish_now or d.kind == "reply":
        from app.publisher import publish_now
        bg.add_task(publish_now, draft_id)   # runs right after the response; the dashboard polls for the result
        out["status"] = "publishing"
    return out


@router.post("/drafts/{draft_id}/reject")
def reject(draft_id: int):
    return _status(draft_id, DraftStatus.rejected)


@router.post("/drafts/{draft_id}/retry")
def retry(draft_id: int):
    return _status(draft_id, DraftStatus.approved)


@router.post("/drafts/{draft_id}/regenerate")
def regenerate(draft_id: int, bg: BackgroundTasks):
    from app.agents.graph import generate_post
    with session() as db:
        d = _get(db, draft_id)
        page_id, pillar, fmt = d.page_id, d.pillar, d.format
    _status(draft_id, DraftStatus.rejected)
    bg.add_task(generate_post, page_id, pillar=pillar, fmt=fmt)
    return {"queued": True}


def _status(draft_id: int, status: DraftStatus):
    with session() as db:
        d = _get(db, draft_id)
        d.status, d.updated_at = status, utcnow()
        db.add(d)
        db.commit()
        return serialize(d)


class GenerateBody(BaseModel):
    page_id: str
    format: str | None = None
    pillar: str | None = None


@router.post("/generate")
def generate(body: GenerateBody, bg: BackgroundTasks):
    from app.scheduler import generate_and_notify
    if body.page_id not in load_pages():
        raise HTTPException(404, "Unknown page")
    bg.add_task(generate_and_notify, body.page_id, pillar=body.pillar, fmt=body.format)
    return {"queued": True}


@router.post("/jobs/{job}")
def run_job(job: str, bg: BackgroundTasks):
    from app.scheduler import keep_queue_full
    from app import slack
    jobs = {"plan": keep_queue_full, "publish": publish_due, "engage": scan_comments, "metrics": collect_metrics,
            "digest": slack.digest}
    if job not in jobs:
        raise HTTPException(404, "Unknown job")
    bg.add_task(jobs[job])
    return {"queued": job}


# ── overview + analytics ─────────────────────────────────────────────────────

@router.get("/overview")
def overview():
    pages_ = load_pages()
    since = utcnow() - timedelta(days=30)
    with session() as db:
        all_drafts = db.exec(select(Draft)).all()
        snaps = db.exec(select(FollowerSnapshot).where(FollowerSnapshot.captured_at >= since)
                        .order_by(FollowerSnapshot.captured_at)).all()
        metrics = {d.id: _latest_metric(db, d.id) for d in all_drafts if d.status == DraftStatus.published}

    # follower series: one point per day per page (last value of the day)
    daily: dict[str, dict[str, int]] = defaultdict(dict)
    for s in snaps:
        daily[s.captured_at.strftime("%Y-%m-%d")][s.page_id] = s.followers
    series = [{"date": day, **vals} for day, vals in sorted(daily.items())]

    per_page = {}
    for pid, p in pages_.items():
        pts = [s.followers for s in snaps if s.page_id == pid]
        week = [s for s in snaps if s.page_id == pid and s.captured_at >= utcnow() - timedelta(days=7)]
        pub = [d for d in all_drafts if d.page_id == pid and d.status == DraftStatus.published and d.kind == "post"]
        eng = [metrics[d.id].engagement for d in pub if metrics.get(d.id)]
        per_page[pid] = {
            "platform": p.platform, "handle": p.handle, "niche": p.niche,
            "followers": pts[-1] if pts else None,
            "growth_7d": (week[-1].followers - week[0].followers) if len(week) >= 2 else 0,
            "growth_30d": (pts[-1] - pts[0]) if len(pts) >= 2 else 0,
            "published": len(pub),
            "pending": sum(1 for d in all_drafts if d.page_id == pid and d.status == DraftStatus.pending),
            "avg_engagement": round(sum(eng) / len(eng), 4) if eng else 0,
            "posts_per_week": p.posts_per_week,
        }

    by_format: dict[str, list[float]] = defaultdict(list)
    by_hour: dict[int, list[float]] = defaultdict(list)
    tz = ZoneInfo(get_settings().timezone)
    for d in all_drafts:
        m = metrics.get(d.id)
        if not m:
            continue
        by_format[f"{d.platform}:{d.format}"].append(m.engagement)
        if d.scheduled_at:
            sa = d.scheduled_at if d.scheduled_at.tzinfo else d.scheduled_at.replace(tzinfo=UTC)
            by_hour[sa.astimezone(tz).hour].append(m.engagement)

    activity = sorted(all_drafts, key=lambda d: d.updated_at or d.created_at, reverse=True)[:12]
    counts = {st.value: sum(1 for d in all_drafts if d.status == st) for st in DraftStatus}
    upcoming = sorted([d for d in all_drafts if d.status == DraftStatus.approved and d.scheduled_at],
                      key=lambda d: d.scheduled_at)[:6]
    return {
        "mode": get_settings().mode,
        "counts": counts,
        "pages": per_page,
        "followers_series": series,
        "by_format": [{"key": k, "platform": k.split(":")[0], "format": k.split(":")[1], "posts": len(v),
                       "avg_engagement": round(sum(v) / len(v), 4)} for k, v in sorted(by_format.items())],
        "by_hour": [{"hour": h, "posts": len(v), "avg_engagement": round(sum(v) / len(v), 4)}
                    for h, v in sorted(by_hour.items())],
        "activity": [{"id": d.id, "page_id": d.page_id, "platform": d.platform, "kind": d.kind, "format": d.format,
                      "topic": d.topic, "status": d.status.value, "at": _iso(d.updated_at or d.created_at)}
                     for d in activity],
        "upcoming": [serialize(d) for d in upcoming],
    }


@router.get("/analytics/{page_id}")
def page_analytics(page_id: str):
    pages_ = load_pages()
    if page_id not in pages_:
        raise HTTPException(404, "Unknown page")
    return performance_summary(pages_[page_id])
