"""Loads page definitions from config/pages.yaml."""
from functools import lru_cache
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.settings import get_settings


class Pillar(BaseModel):
    name: str
    description: str


class Hashtags(BaseModel):
    core: list[str] = Field(default_factory=list)
    max_per_post: int = 5


class Brand(BaseModel):
    bg: str = "#111111"
    fg: str = "#FFFFFF"
    accent: str = "#F59E0B"
    font: str = "DejaVuSans-Bold.ttf"


class Page(BaseModel):
    id: str
    platform: str  # instagram | linkedin | x
    handle: str
    niche: str
    audience: str
    goal: str
    voice: str
    language: str = "English"
    pillars: list[Pillar]
    formats: list[str]
    posts_per_week: int = 4
    preferred_slots: list[str] = Field(default_factory=lambda: ["10:00"])
    hashtags: Hashtags = Field(default_factory=Hashtags)
    brand: Brand = Field(default_factory=Brand)
    sources: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    cta_options: list[str] = Field(default_factory=list)
    organization_urn: str | None = None
    reference_accounts: list[str] = Field(default_factory=list)   # top accounts in the niche to learn from
    search_keywords: list[str] = Field(default_factory=list)      # what the X trend search looks for
    extra: dict[str, Any] = Field(default_factory=dict)

    def swipe_file(self, max_chars: int = 6000) -> str:
        """Viral posts you saved as style references: config/swipe/<page_id>.md (optional)."""
        f = get_settings().pages_file.parent / "swipe" / f"{self.id}.md"
        return f.read_text()[:max_chars] if f.exists() else ""

    def brief(self) -> str:
        pillars = "\n".join(f"  - {p.name}: {p.description}" for p in self.pillars)
        return (
            f"Platform: {self.platform}\nHandle: {self.handle}\nNiche: {self.niche}\n"
            f"Audience: {self.audience}\nGoal: {self.goal}\nVoice: {self.voice}\n"
            f"Language: {self.language}\nPillars:\n{pillars}\n"
            f"Allowed formats: {', '.join(self.formats)}\n"
            f"Avoid: {', '.join(self.avoid) or 'n/a'}\n"
            f"CTA options: {' | '.join(self.cta_options) or 'n/a'}"
        )


@lru_cache
def load_pages() -> dict[str, Page]:
    data = yaml.safe_load(get_settings().pages_file.read_text())
    return {p["id"]: Page(**p) for p in data["pages"]}


def get_page(page_id: str) -> Page:
    return load_pages()[page_id]
