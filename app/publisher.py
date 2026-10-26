"""Publishes approved drafts. Only APPROVED drafts are ever published.

Two paths, both safe to run at the same time:
- publish_now(id): right after you click "Approve & post now" in the dashboard
- publish_due():   every 5 minutes for scheduled posts and approved replies
Each draft is claimed atomically (approved → publishing) before posting, so it can't go out twice.
"""
import logging

from sqlalchemy import update

from app.db import Draft, DraftStatus, select, session, utcnow
from app.pages import get_page
from app.platforms.registry import client_for

log = logging.getLogger(__name__)


def _claim(draft_id: int) -> bool:
    with session() as db:
        res = db.exec(update(Draft).where(Draft.id == draft_id, Draft.status == DraftStatus.approved)
                      .values(status=DraftStatus.publishing, updated_at=utcnow()))
        db.commit()
        return res.rowcount == 1


def publish_draft(draft: Draft) -> None:
    from app import slack

    page = get_page(draft.page_id)
    client = client_for(page)
    try:
        if draft.kind == "reply":
            draft.published_id = client.reply(draft.angle, draft.reply_to, draft.content["caption"])
        else:
            draft.published_id = client.publish(draft)
        draft.status = DraftStatus.published
        draft.error = None
        try:
            link = client.permalink(draft.published_id)
        except Exception:  # noqa: BLE001
            link = None
        if link:
            draft.content = {**draft.content, "permalink": link}
        log.info("published draft #%s → %s", draft.id, draft.published_id)
        slack.published(draft, page, link)
    except Exception as e:  # noqa: BLE001
        draft.status = DraftStatus.failed
        body = getattr(getattr(e, "response", None), "text", "")
        draft.error = f"{e} {body}"[:2000]
        log.exception("publish failed for draft #%s", draft.id)
        slack.failed(draft, page)
    draft.updated_at = utcnow()


def _publish_claimed(draft_id: int) -> None:
    with session() as db:
        d = db.get(Draft, draft_id)
        publish_draft(d)
        db.add(d)
        db.commit()


def publish_now(draft_id: int) -> bool:
    """Publish one approved draft immediately. Returns False if someone else already claimed it."""
    if not _claim(draft_id):
        return False
    _publish_claimed(draft_id)
    return True


def publish_due() -> int:
    with session() as db:
        due = [d.id for d in db.exec(select(Draft).where(Draft.status == DraftStatus.approved)).all()
               if d.kind == "reply" or (d.scheduled_at and d.scheduled_at <= utcnow())]
    n = 0
    for draft_id in due:
        if _claim(draft_id):
            _publish_claimed(draft_id)
            n += 1
    return n
