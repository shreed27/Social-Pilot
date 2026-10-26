"""LinkedIn company page via the versioned REST Posts API (needs Community Management API access
and w_organization_social; the token's member must be a Page admin)."""
import re
from pathlib import Path
from urllib.parse import quote

import httpx

from app.db import Draft
from app.platforms.base import PlatformClient

API = "https://api.linkedin.com/rest"
_RESERVED = re.compile(r"([\\|{}@\[\]()<>*_~])")


def little_text(text: str) -> str:
    """Escape LinkedIn 'little text' reserved chars; keep #hashtags as real hashtags."""
    text = _RESERVED.sub(r"\\\1", text)
    return re.sub(r"#(\w+)", r"{hashtag|\\#|\1}", text)


class LinkedInClient(PlatformClient):
    @property
    def org(self) -> str:
        return self.page.organization_urn or ""

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.s.linkedin_access_token}", "LinkedIn-Version": self.s.linkedin_version,
                "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"}

    def _upload(self, kind: str, path: str) -> str:
        """kind = images | documents. Returns the asset URN."""
        r = httpx.post(f"{API}/{kind}?action=initializeUpload", headers=self.headers, timeout=60,
                       json={"initializeUploadRequest": {"owner": self.org}})
        r.raise_for_status()
        v = r.json()["value"]
        up = httpx.put(v["uploadUrl"], content=Path(path).read_bytes(), timeout=300,
                       headers={"Authorization": self.headers["Authorization"]})
        up.raise_for_status()
        return v["image"] if kind == "images" else v["document"]

    def publish(self, draft: Draft) -> str:
        body = {
            "author": self.org,
            "commentary": little_text(self.compose_caption(draft)),
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if draft.format == "image":
            body["content"] = {"media": {"id": self._upload("images", draft.media[0]),
                                         "altText": draft.content.get("alt_text", "")}}
        elif draft.format == "document":
            title = (draft.content.get("slides") or [{}])[0].get("title", draft.topic)[:100]
            body["content"] = {"media": {"id": self._upload("documents", draft.media[0]), "title": title}}
        r = httpx.post(f"{API}/posts", headers=self.headers, json=body, timeout=60)
        r.raise_for_status()
        return r.headers.get("x-restli-id", "")

    def permalink(self, post_id: str) -> str | None:
        return f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else None

    def reply(self, post_id: str, comment_id: str, text: str) -> str:
        r = httpx.post(f"{API}/socialActions/{quote(post_id, safe='')}/comments", headers=self.headers, timeout=60,
                       json={"actor": self.org, "object": post_id, "parentComment": comment_id,
                             "message": {"text": text}})
        r.raise_for_status()
        return r.headers.get("x-restli-id", "")

    def follower_count(self) -> int | None:
        r = httpx.get(f"{API}/networkSizes/{quote(self.org, safe='')}", headers=self.headers,
                      params={"edgeType": "COMPANY_FOLLOWED_BY_MEMBER"}, timeout=60)
        r.raise_for_status()
        return r.json().get("firstDegreeSize")

    def post_metrics(self, post_id: str) -> dict | None:
        key = "ugcPosts" if "ugcPost" in post_id else "shares"
        url = (f"{API}/organizationalEntityShareStatistics?q=organizationalEntity"
               f"&organizationalEntity={quote(self.org, safe='')}&{key}=List({quote(post_id, safe='')})")
        r = httpx.get(url, headers=self.headers, timeout=60)
        r.raise_for_status()
        els = r.json().get("elements", [])
        if not els:
            return None
        t = els[0].get("totalShareStatistics", {})
        return {"impressions": t.get("impressionCount", 0), "likes": t.get("likeCount", 0),
                "comments": t.get("commentCount", 0), "shares": t.get("shareCount", 0), "saves": 0, "follows": 0}

    def new_comments(self, post_id: str) -> list[dict]:
        r = httpx.get(f"{API}/socialActions/{quote(post_id, safe='')}/comments", headers=self.headers, timeout=60)
        r.raise_for_status()
        out = []
        for c in r.json().get("elements", []):
            if c.get("actor") == self.org:
                continue
            out.append({"id": c.get("$URN") or c.get("commentUrn") or str(c.get("id")),
                        "text": c.get("message", {}).get("text", ""), "author": c.get("actor", "")})
        return out
