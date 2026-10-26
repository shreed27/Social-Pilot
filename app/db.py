"""Persistence: drafts (approval queue), published posts, metrics, comments."""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.settings import get_settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DraftStatus(str, Enum):
    pending = "pending"        # waiting for human approval
    approved = "approved"      # approved + scheduled
    publishing = "publishing"  # claimed by a publisher right now (prevents double posting)
    rejected = "rejected"
    published = "published"
    failed = "failed"


class Draft(SQLModel, table=True):
    """A post (or a reply) the agents prepared. Nothing is published unless approved."""
    id: Optional[int] = Field(default=None, primary_key=True)
    page_id: str = Field(index=True)
    platform: str
    kind: str = "post"                 # post | reply
    format: str                        # text | thread | image | carousel | reel | document | reply
    pillar: str = ""
    topic: str = ""
    angle: str = ""
    content: dict = Field(default_factory=dict, sa_column=Column(JSON))   # caption, thread, slides, script...
    media: list = Field(default_factory=list, sa_column=Column(JSON))     # local file paths
    critic: dict = Field(default_factory=dict, sa_column=Column(JSON))    # scores + notes
    trace: list = Field(default_factory=list, sa_column=Column(JSON))     # agent steps that produced it
    reply_to: Optional[str] = None     # platform comment id (for replies)
    reply_context: Optional[str] = None
    status: DraftStatus = DraftStatus.pending
    scheduled_at: Optional[datetime] = None   # UTC
    published_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Metric(SQLModel, table=True):
    """Snapshot of one published post's performance."""
    id: Optional[int] = Field(default=None, primary_key=True)
    draft_id: int = Field(index=True)
    page_id: str = Field(index=True)
    impressions: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    follows: int = 0
    captured_at: datetime = Field(default_factory=utcnow)

    @property
    def engagement(self) -> float:
        # Weight actions by how strongly they drive reach + follows.
        score = self.likes + 2 * self.comments + 3 * self.shares + 3 * self.saves + 10 * self.follows
        return score / max(self.impressions, 1)


class FollowerSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    page_id: str = Field(index=True)
    followers: int
    captured_at: datetime = Field(default_factory=utcnow)


class SeenComment(SQLModel, table=True):
    """Comments the engagement agent already handled, so it never double-replies."""
    id: str = Field(primary_key=True)  # "<page_id>:<comment_id>"
    page_id: str
    created_at: datetime = Field(default_factory=utcnow)


_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(_engine)
    return _engine


def session() -> Session:
    return Session(engine(), expire_on_commit=False)


__all__ = ["Draft", "DraftStatus", "Metric", "FollowerSnapshot", "SeenComment", "session", "select", "utcnow"]
