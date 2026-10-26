"""Engagement agent: reads new comments on our recent posts and drafts replies into the approval queue.
Replying fast and genuinely is one of the strongest organic growth levers on every platform."""
import logging
from datetime import timedelta

from app.db import Draft, DraftStatus, SeenComment, select, session, utcnow
from app.llm import ask_json
from app.pages import load_pages
from app.platforms.registry import client_for

log = logging.getLogger(__name__)


def scan_comments(days: int = 7) -> int:
    created = 0
    for page in load_pages().values():
        client = client_for(page)
        with session() as db:
            posts = db.exec(select(Draft).where(Draft.page_id == page.id, Draft.kind == "post",
                                                Draft.status == DraftStatus.published,
                                                Draft.updated_at >= utcnow() - timedelta(days=days))).all()
            for post in posts:
                try:
                    comments = client.new_comments(post.published_id)
                except Exception as e:  # noqa: BLE001
                    log.warning("comments failed for %s: %s", post.published_id, e)
                    continue
                for c in comments:
                    key = f"{page.id}:{c['id']}"
                    if db.get(SeenComment, key):
                        continue
                    db.add(SeenComment(id=key, page_id=page.id))
                    out = ask_json("reply", "You manage community replies for a creator page.", f"""
PAGE: {page.handle} — niche: {page.niche}. Voice: {page.voice}
OUR POST: {post.content.get('caption', '')[:600]}
COMMENT by {c['author']}: {c['text']}

Decide if a reply helps (questions, genuine feedback, praise worth acknowledging). Skip spam,
trolls, bots and anything political. A good reply is short, human, adds value or asks a follow-up
question to keep the conversation going. Never promise things, never share links.
Return: {{"should_reply": bool, "reply": str, "reason": str}}""")
                    if out.get("should_reply") and out.get("reply"):
                        db.add(Draft(page_id=page.id, platform=page.platform, kind="reply", format="reply",
                                     topic=f"Reply on: {post.topic}", content={"caption": out["reply"]},
                                     reply_to=c["id"], reply_context=f"{c['author']}: {c['text']}",
                                     angle=post.published_id or ""))
                        created += 1
            db.commit()
    if created:
        from app.notify import notify
        notify(f"💬 {created} new reply draft(s) waiting for approval.")
    return created
