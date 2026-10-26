"""Instagram via the Instagram Graph API (professional account linked to a Facebook Page).

Publishing is two-step: create a media container, wait until it is FINISHED, then publish it.
Media must be on a public URL Instagram can fetch (see PUBLIC_MEDIA_BASE_URL).
"""
import time

import httpx

from app.db import Draft
from app.platforms.base import PlatformClient


class InstagramClient(PlatformClient):
    @property
    def base(self) -> str:
        return f"{self.s.ig_graph_host}/{self.s.ig_api_version}"

    def _post(self, path: str, **params) -> dict:
        r = httpx.post(f"{self.base}/{path}", params={**params, "access_token": self.s.ig_access_token}, timeout=60)
        r.raise_for_status()
        return r.json()

    def _get(self, path: str, **params) -> dict:
        r = httpx.get(f"{self.base}/{path}", params={**params, "access_token": self.s.ig_access_token}, timeout=60)
        r.raise_for_status()
        return r.json()

    def _wait(self, container_id: str, timeout_s: int = 600) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            status = self._get(container_id, fields="status_code").get("status_code")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"Instagram container {container_id} {status}")
            time.sleep(5)
        raise TimeoutError(f"Instagram container {container_id} not ready")

    def publish(self, draft: Draft) -> str:
        ig = self.s.ig_user_id
        caption = self.compose_caption(draft)
        if draft.format == "carousel":
            children = [self._post(f"{ig}/media", image_url=self.public_url(p), is_carousel_item="true")["id"]
                        for p in draft.media[:10]]
            for c in children:
                self._wait(c)
            container = self._post(f"{ig}/media", media_type="CAROUSEL", children=",".join(children),
                                   caption=caption)["id"]
        elif draft.format == "reel":
            container = self._post(f"{ig}/media", media_type="REELS", video_url=self.public_url(draft.media[0]),
                                   caption=caption, share_to_feed="true")["id"]
        elif draft.format == "image":
            container = self._post(f"{ig}/media", image_url=self.public_url(draft.media[0]), caption=caption,
                                   alt_text=draft.content.get("alt_text", ""))["id"]
        else:
            raise ValueError(f"Instagram does not support format {draft.format}")
        self._wait(container)
        return self._post(f"{ig}/media_publish", creation_id=container)["id"]

    def permalink(self, post_id: str) -> str | None:
        return self._get(post_id, fields="permalink").get("permalink")

    def reply(self, post_id: str, comment_id: str, text: str) -> str:
        return self._post(f"{comment_id}/replies", message=text)["id"]

    def follower_count(self) -> int | None:
        return self._get(self.s.ig_user_id, fields="followers_count").get("followers_count")

    def post_metrics(self, post_id: str) -> dict | None:
        data = self._get(f"{post_id}/insights", metric="reach,likes,comments,shares,saved,follows").get("data", [])
        v = {d["name"]: (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value", 0))
             for d in data}
        return {"impressions": v.get("reach", 0), "likes": v.get("likes", 0), "comments": v.get("comments", 0),
                "shares": v.get("shares", 0), "saves": v.get("saved", 0), "follows": v.get("follows", 0)}

    def new_comments(self, post_id: str) -> list[dict]:
        data = self._get(f"{post_id}/comments", fields="id,text,username").get("data", [])
        return [{"id": c["id"], "text": c.get("text", ""), "author": c.get("username", "")} for c in data]
