"""kie.ai client: AI video and image generation for posts.

This is the same API the Open-Higgsfield-AI studio (github.com/Autom8AI/Open-Higgsfield-AI) calls;
SocialPilot talks to it directly so reels get footage without anyone clicking through a studio.
The request/poll shapes mirror that repo's src/lib/kie.js.

Paid per generation (1 credit = $0.005). Approximate prices used for the daily budget, Oct 2026:
  veo3_fast ≈ $0.40 / 8 s clip with audio · veo3 ≈ $2.00 · kling-3.0 std ≈ $0.07/s · seedance-2-fast ≈ $0.06/s
  nano-banana-2 image ≈ $0.04 (1K)
Failed generations aren't charged by kie.ai; this ledger counts them anyway to stay conservative.
"""
import json
import logging
import time
from datetime import date
from pathlib import Path

import httpx

from app.settings import get_settings

log = logging.getLogger(__name__)
BASE = "https://api.kie.ai"

VIDEO_PRICE = {"veo3_fast": 0.40, "veo3_lite": 0.30, "veo3": 2.00}   # per clip
PER_SECOND = {"kling": 0.07, "seedance": 0.06, "wan": 0.08, "sora": 0.10}
IMAGE_PRICE = {"nano-banana-2": 0.04, "nano-banana": 0.04, "nano-banana-pro": 0.12}


class BudgetExceeded(RuntimeError):
    pass


def video_cost(model: str, seconds: int = 8) -> float:
    if model in VIDEO_PRICE:
        return VIDEO_PRICE[model]
    for k, v in PER_SECOND.items():
        if k in model:
            return v * seconds
    return 1.0  # unknown model: assume expensive


# ── ledger ──────────────────────────────────────────────────────────────────

def _ledger() -> Path:
    return get_settings().media_dir.parent / "kie_spend.json"


def spent_today() -> float:
    try:
        return float(json.loads(_ledger().read_text()).get(date.today().isoformat(), 0))
    except (OSError, ValueError):
        return 0.0


def _charge(cost: float) -> None:
    s = get_settings()
    if spent_today() + cost > s.kie_daily_budget_usd + 1e-9:
        raise BudgetExceeded(f"kie.ai daily budget ${s.kie_daily_budget_usd:.2f} reached "
                             f"(spent ${spent_today():.2f}, this needs ${cost:.2f})")
    p = _ledger()
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        d = {}
    k = date.today().isoformat()
    d[k] = round(float(d.get(k, 0)) + cost, 4)
    p.write_text(json.dumps(d))


def can_afford(cost: float) -> bool:
    return spent_today() + cost <= get_settings().kie_daily_budget_usd + 1e-9


def enabled() -> bool:
    return bool(get_settings().kie_api_key)


# ── client ──────────────────────────────────────────────────────────────────

class KieClient:
    def __init__(self, key: str | None = None):
        self.key = key or get_settings().kie_api_key
        if not self.key:
            raise RuntimeError("KIE_API_KEY is not set")
        self.h = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}

    def _post(self, path: str, body: dict) -> dict:
        r = httpx.post(f"{BASE}{path}", headers=self.h, json=body, timeout=60)
        r.raise_for_status()
        j = r.json()
        if j.get("code") not in (None, 200):
            raise RuntimeError(f"kie.ai error {j.get('code')}: {j.get('msg')}")
        return j.get("data") or {}

    def _get(self, path: str) -> dict:
        r = httpx.get(f"{BASE}{path}", headers=self.h, timeout=60)
        r.raise_for_status()
        j = r.json()
        if j.get("code") not in (None, 200):
            raise RuntimeError(f"kie.ai error {j.get('code')}: {j.get('msg')}")
        return j.get("data") or {}

    @staticmethod
    def _urls(data: dict) -> list[str]:
        for src in (data, data.get("response") or {}):
            if src.get("resultUrls"):
                return list(src["resultUrls"])
        rj = data.get("resultJson")
        if isinstance(rj, str) and rj:
            try:
                rj = json.loads(rj)
            except ValueError:
                rj = {}
        if isinstance(rj, dict) and rj.get("resultUrls"):
            return list(rj["resultUrls"])
        return []

    def _poll_jobs(self, task_id: str, timeout_s: int = 900) -> list[str]:
        end = time.time() + timeout_s
        while time.time() < end:
            time.sleep(4)
            d = self._get(f"/api/v1/jobs/recordInfo?taskId={task_id}")
            state = str(d.get("state", "")).lower()
            if state == "success":
                return self._urls(d)
            if state in ("fail", "error"):
                raise RuntimeError(f"kie.ai generation failed: {d.get('failMsg') or 'unknown'}")
        raise TimeoutError("kie.ai generation timed out")

    def _poll_veo(self, task_id: str, timeout_s: int = 1200) -> list[str]:
        end = time.time() + timeout_s
        while time.time() < end:
            time.sleep(5)
            d = self._get(f"/api/v1/veo/record-info?taskId={task_id}")
            flag = d.get("successFlag")
            if flag == 1:
                return self._urls(d)
            if flag in (2, 3):
                raise RuntimeError(f"kie.ai Veo failed: {d.get('errorMessage') or 'unknown'}")
        raise TimeoutError("kie.ai Veo generation timed out")

    def video(self, prompt: str, *, aspect: str = "9:16", seconds: int = 8, image_url: str | None = None) -> str:
        model = get_settings().kie_video_model
        _charge(video_cost(model, seconds))
        if model.startswith("veo3"):
            body = {"prompt": prompt, "model": model, "aspect_ratio": aspect, "enableFallback": False,
                    "generationType": "FIRST_AND_LAST_FRAMES_2_VIDEO" if image_url else "TEXT_2_VIDEO"}
            if image_url:
                body["imageUrls"] = [image_url]
            task = self._post("/api/v1/veo/generate", body)["taskId"]
            urls = self._poll_veo(task)
        else:
            inp = {"prompt": prompt, "aspect_ratio": aspect, "duration": str(seconds)}
            if image_url:
                inp["image_urls"] = [image_url]
            task = self._post("/api/v1/jobs/createTask", {"model": model, "input": inp})["taskId"]
            urls = self._poll_jobs(task)
        if not urls:
            raise RuntimeError("kie.ai returned no video URL")
        return urls[0]

    def image(self, prompt: str, *, aspect: str = "4:5") -> str:
        model = get_settings().kie_image_model
        _charge(IMAGE_PRICE.get(model, 0.1))
        task = self._post("/api/v1/jobs/createTask", {"model": model, "input": {
            "prompt": prompt, "aspect_ratio": aspect, "resolution": "1K", "output_format": "jpg"}})["taskId"]
        urls = self._poll_jobs(task, timeout_s=300)
        if not urls:
            raise RuntimeError("kie.ai returned no image URL")
        return urls[0]


def download(url: str, dest: Path) -> Path:
    with httpx.stream("GET", url, timeout=300, follow_redirects=True) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
    return dest


SCENE_RULES = ("Vertical 9:16, cinematic, real camera motion (slow push-in, handheld, orbit), shallow depth of field, "
               "natural light. NO text, letters, captions, logos, brand names, UI screens, or recognisable real people "
               "or celebrities. No watermarks.")
