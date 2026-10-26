"""Background jobs (APScheduler, runs inside the FastAPI process).

- 06:07 and 14:07: top up each page's queue for the next PLAN_DAYS_AHEAD days
- every 5 min:  publish approved drafts that are due (replies go out right after approval)
- every 30 min: scan comments → reply drafts
- every 6 h:    collect metrics + follower counts → feeds the strategist's learning loop
- SLACK_DIGEST_TIME (default 21:00): daily report to Slack
"""
import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.analytics import collect_metrics
from app.db import Draft, DraftStatus, select, session, utcnow
from app.engagement import scan_comments
from app.pages import load_pages
from app.publisher import publish_due
from app.settings import get_settings

log = logging.getLogger(__name__)


def keep_queue_full(days_ahead: int | None = None) -> int:
    """Make sure each page has enough pending/approved posts for the next few days."""
    from app.agents.graph import generate_post

    from app import slack

    days_ahead = days_ahead or get_settings().plan_days_ahead
    made = 0
    new_ids: list[int] = []
    for page in load_pages().values():
        needed = round(page.posts_per_week * days_ahead / 7 + 0.49)
        with session() as db:
            have = len(db.exec(select(Draft).where(
                Draft.page_id == page.id, Draft.kind == "post",
                Draft.status.in_([DraftStatus.pending, DraftStatus.approved]),
                Draft.scheduled_at <= utcnow() + timedelta(days=days_ahead + 1))).all())
        for _ in range(max(0, needed - have)):
            try:
                r = generate_post(page.id)
                made += 1
                if r.get("draft_id"):
                    new_ids.append(r["draft_id"])
            except Exception:  # noqa: BLE001
                log.exception("generation failed for %s", page.id)
    if new_ids:
        with session() as db:
            slack.drafts_ready([db.get(Draft, i) for i in new_ids])
    return made


def generate_and_notify(page_id: str, **kw) -> None:
    """Manual 'Generate' from the dashboard: same as a planning run for one draft."""
    from app import slack
    from app.agents.graph import generate_post

    r = generate_post(page_id, **kw)
    if r.get("draft_id"):
        with session() as db:
            slack.drafts_ready([db.get(Draft, r["draft_id"])])


def start() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone=get_settings().timezone)
    # twice a day so fresh, timely ideas keep arriving (morning run catches overnight news)
    sched.add_job(keep_queue_full, "cron", hour="6,14", minute=7, id="plan")
    sched.add_job(publish_due, "interval", minutes=5, id="publish")
    sched.add_job(scan_comments, "interval", minutes=30, id="engage")
    sched.add_job(collect_metrics, "interval", hours=6, id="metrics")
    from app import slack
    hh, mm = (int(x) for x in get_settings().slack_digest_time.split(":"))
    # pull fresh numbers 10 minutes before the report, then send it
    sched.add_job(collect_metrics, "cron", hour=(hh if mm >= 10 else (hh - 1) % 24), minute=(mm - 10) % 60, id="metrics_pre_digest")
    sched.add_job(slack.digest, "cron", hour=hh, minute=mm, id="slack_digest")
    sched.start()
    log.info("scheduler started")
    return sched
