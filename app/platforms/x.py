"""X via the v2 API (pay-per-use credits, OAuth 2.0 user token with tweet.read tweet.write
users.read media.write offline.access).

Cost notes (Oct 2026, check docs.x.com before going live): a plain post is billed per request and a
post containing a URL is billed far higher, so the writer + critic keep URLs out of X posts. Follows
and likes via API are not available on pay-per-use, which is fine: this system never auto-follows.
"""
from pathlib import Path

import httpx

from app.db import Draft
from app.platforms.base import PlatformClient

API = "https://api.x.com/2"


class XClient(PlatformClient):
    @property
    def auth(self) -> dict:
        return {"Authorization": f"Bearer {self.s.x_access_token}"}

    def _tweet(self, text: str, reply_to: str | None = None, media_ids: list[str] | None = None) -> str:
        body: dict = {"text": text}
        if reply_to:
            body["reply"] = {"in_reply_to_tweet_id": reply_to}
        if media_ids:
            body["media"] = {"media_ids": media_ids}
        r = httpx.post(f"{API}/tweets", headers=self.auth, json=body, timeout=60)
        r.raise_for_status()
        return r.json()["data"]["id"]

    def _upload_image(self, path: str) -> str:
        r = httpx.post(f"{API}/media/upload", headers=self.auth, timeout=120,
                       files={"media": (Path(path).name, Path(path).read_bytes(), "image/png")},
                       data={"media_category": "tweet_image"})
        r.raise_for_status()
        return r.json()["data"]["id"]

    def publish(self, draft: Draft) -> str:
        c = draft.content
        posts = c.get("thread") or [self.compose_caption(draft)]
        media_ids = [self._upload_image(p) for p in draft.media[:4] if p.endswith(".png")] or None
        first = self._tweet(posts[0], media_ids=media_ids)
        prev = first
        for p in posts[1:]:
            prev = self._tweet(p, reply_to=prev)
        return first

    def permalink(self, post_id: str) -> str | None:
        return f"https://x.com/i/web/status/{post_id}" if post_id else None

    def reply(self, post_id: str, comment_id: str, text: str) -> str:
        return self._tweet(text, reply_to=comment_id)

    def follower_count(self) -> int | None:
        r = httpx.get(f"{API}/users/me", headers=self.auth, params={"user.fields": "public_metrics"}, timeout=30)
        r.raise_for_status()
        return r.json()["data"]["public_metrics"]["followers_count"]

    def post_metrics(self, post_id: str) -> dict | None:
        r = httpx.get(f"{API}/tweets", headers=self.auth, timeout=30,
                      params={"ids": post_id, "tweet.fields": "public_metrics"})
        r.raise_for_status()
        m = (r.json().get("data") or [{}])[0].get("public_metrics", {})
        return {"impressions": m.get("impression_count", 0), "likes": m.get("like_count", 0),
                "comments": m.get("reply_count", 0), "shares": m.get("retweet_count", 0) + m.get("quote_count", 0),
                "saves": m.get("bookmark_count", 0), "follows": 0}

    def new_comments(self, post_id: str) -> list[dict]:
        r = httpx.get(f"{API}/tweets/search/recent", headers=self.auth, timeout=30,
                      params={"query": f"conversation_id:{post_id} -from:{self.s.x_user_id} is:reply",
                              "tweet.fields": "author_id", "max_results": 20})
        r.raise_for_status()
        return [{"id": t["id"], "text": t["text"], "author": t.get("author_id", "")}
                for t in r.json().get("data", []) or []]
