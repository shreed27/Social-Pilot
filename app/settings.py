from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    mode: str = "dry_run"
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5-5"
    timezone: str = "Asia/Kolkata"
    database_url: str = f"sqlite:///{ROOT / 'data' / 'socialpilot.db'}"
    dashboard_password: str = "change-me"
    public_media_base_url: str = "http://localhost:8000/media"
    media_dir: Path = ROOT / "data" / "media"
    pages_file: Path = ROOT / "config" / "pages.yaml"

    openai_api_key: str = ""
    image_model: str = "gpt-image-1"

    research_web_search: bool = False
    web_search_tool_type: str = "web_search_20250305"

    # kie.ai: AI video + images (same API the Open-Higgsfield-AI studio uses). Paid per generation.
    kie_api_key: str = ""
    kie_video_model: str = "veo3_fast"        # veo3_fast | veo3 | kling-3.0/video | bytedance/seedance-2-fast | ...
    kie_image_model: str = "nano-banana-2"
    kie_clips_per_reel: int = 2
    kie_keep_audio: bool = False              # AI clips' own audio; usually you add trending audio in-app instead
    kie_daily_budget_usd: float = 3.0
    kie_ai_covers: bool = True                # AI photo background on image posts and bold carousel covers

    # Scheduling / autonomy
    plan_days_ahead: int = 2
    auto_approve_min_score: float = 0.0       # 0 = off. e.g. 9.0 auto-approves drafts that clear every gate and score ≥ 9

    # xbird (read-only X research through your own x.com session; paid per call in USDC)
    xbird_enabled: bool = False
    xbird_command: str = "npx -y @checkra1n/xbird"
    xbird_max_calls_per_run: int = 4
    xbird_daily_budget_usd: float = 1.0
    xbird_min_likes: int = 200
    xbird_lookback_days: int = 7

    critic_min_score: float = 8.0
    max_revisions: int = 2

    # Slack: incoming webhook for a channel (api.slack.com/apps → Incoming Webhooks)
    slack_webhook_url: str = ""
    slack_digest_time: str = "21:00"          # local time for the daily report
    slack_notify_drafts: bool = True          # ping when drafts need review (batched per planning run)
    dashboard_url: str = ""                   # e.g. https://social.yourco.in, used for buttons in Slack

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    ig_user_id: str = ""
    ig_access_token: str = ""
    ig_graph_host: str = "https://graph.facebook.com"
    ig_api_version: str = "v26.0"

    linkedin_access_token: str = ""
    linkedin_version: str = "202610"

    x_access_token: str = ""
    x_user_id: str = ""

    @property
    def live(self) -> bool:
        return self.mode == "live"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.media_dir.mkdir(parents=True, exist_ok=True)
    return s
