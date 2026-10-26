"""Common interface every platform client implements."""
import logging
import random
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.db import Draft
from app.pages import Page
from app.settings import get_settings

log = logging.getLogger(__name__)


class PlatformClient(ABC):
    def __init__(self, page: Page):
        self.page = page
        self.s = get_settings()

    # ── publishing ──
    @abstractmethod
    def publish(self, draft: Draft) -> str: ...

    @abstractmethod
    def reply(self, post_id: str, comment_id: str, text: str) -> str: ...

    # ── reading ──
    @abstractmethod
    def follower_count(self) -> int | None: ...

    @abstractmethod
    def post_metrics(self, post_id: str) -> dict | None: ...

    @abstractmethod
    def new_comments(self, post_id: str) -> list[dict]:
        """[{id, text, author}] for comments on one of our posts."""

    def permalink(self, post_id: str) -> str | None:
        return None

    # ── helpers ──
    def public_url(self, local_path: str) -> str:
        rel = Path(local_path).resolve().relative_to(self.s.media_dir.resolve())
        return f"{self.s.public_media_base_url.rstrip('/')}/{rel.as_posix()}"

    @staticmethod
    def compose_caption(draft: Draft, hashtags_inline: bool = True) -> str:
        c = draft.content
        text = c.get("caption", "").strip()
        cta = (c.get("cta") or "").strip()
        if cta and cta.lower() not in text.lower():
            text += f"\n\n{cta}"
        tags = " ".join(t if t.startswith("#") else f"#{t}" for t in c.get("hashtags", []) or [])
        if tags and hashtags_inline:
            text += f"\n\n{tags}"
        return text


class DryRunClient(PlatformClient):
    """Used when MODE=dry_run. Logs what would happen; returns fake IDs and synthetic metrics
    so the dashboard, scheduler and learning loop can be exercised end to end."""

    def publish(self, draft: Draft) -> str:
        log.info("[DRY RUN] would publish %s %s for %s: %s | media=%s", self.page.platform, draft.format,
                 self.page.handle, (draft.content.get("caption") or "")[:80], draft.media)
        return f"dry_{uuid.uuid4().hex[:12]}"

    def reply(self, post_id: str, comment_id: str, text: str) -> str:
        log.info("[DRY RUN] would reply to %s: %s", comment_id, text)
        return f"dry_reply_{uuid.uuid4().hex[:8]}"

    def follower_count(self) -> int | None:
        return random.randint(100, 120)

    def post_metrics(self, post_id: str) -> dict | None:
        imp = random.randint(300, 3000)
        return {"impressions": imp, "likes": int(imp * random.uniform(.02, .08)),
                "comments": random.randint(0, 15), "shares": random.randint(0, 20),
                "saves": random.randint(0, 40), "follows": random.randint(0, 8)}

    def permalink(self, post_id: str) -> str | None:
        return None  # dry run: nothing was really posted

    def new_comments(self, post_id: str) -> list[dict]:
        return [{"id": f"c_{post_id[-6:]}", "text": "This is super useful, which one is best for beginners?",
                 "author": "demo_user"}]
