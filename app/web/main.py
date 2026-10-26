"""Approval dashboard + API. Run: uvicorn app.web.main:app --reload"""
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.analytics import collect_metrics, performance_summary
from app.db import Draft, DraftStatus, select, session, utcnow
from app.engagement import scan_comments
from app.pages import load_pages
from app.publisher import publish_due
from app.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
s = get_settings()
TZ, UTC = ZoneInfo(s.timezone), ZoneInfo("UTC")


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app import scheduler
    sched = scheduler.start()
    yield
    sched.shutdown(wait=False)


app = FastAPI(title="SocialPilot", lifespan=lifespan)
app.mount("/media", StaticFiles(directory=s.media_dir), name="media")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
security = HTTPBasic()


def auth(creds: HTTPBasicCredentials = Depends(security)):
    if not secrets.compare_digest(creds.password.encode(), s.dashboard_password.encode()):
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})


def to_local(dt: datetime | None) -> str:
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).astimezone(TZ).strftime("%Y-%m-%dT%H:%M") if dt else ""


def media_url(path: str) -> str:
    rel = Path(path).resolve().relative_to(s.media_dir.resolve()).as_posix()
    return f"/media/{rel}"


templates.env.filters["local"] = to_local
templates.env.filters["media_url"] = media_url


@app.get("/classic", dependencies=[Depends(auth)])
def queue(request: Request, status: str = "pending", page: str = ""):
    with session() as db:
        q = select(Draft).where(Draft.status == DraftStatus(status))
        if page:
            q = q.where(Draft.page_id == page)
        drafts = db.exec(q.order_by(Draft.kind.desc(), Draft.scheduled_at)).all()
        counts = {st.value: len(db.exec(select(Draft).where(Draft.status == st)).all()) for st in DraftStatus}
    return templates.TemplateResponse(request, "index.html", {
        "drafts": drafts, "status": status, "page_filter": page, "pages": load_pages(),
        "counts": counts, "mode": s.mode})


@app.post("/drafts/{draft_id}/approve", dependencies=[Depends(auth)])
def approve(draft_id: int, bg: BackgroundTasks, caption: str = Form(""), thread: str = Form(""),
            scheduled_at: str = Form(""), action: str = Form("schedule")):
    with session() as db:
        d = db.get(Draft, draft_id) or _404()
        content = dict(d.content)
        if caption:
            content["caption"] = caption
        if thread.strip():
            content["thread"] = [p.strip() for p in thread.split("\n---\n") if p.strip()]
            content["caption"] = content["thread"][0]
        d.content = content
        if action == "now":
            d.scheduled_at = utcnow()
        elif scheduled_at:
            d.scheduled_at = datetime.fromisoformat(scheduled_at).replace(tzinfo=TZ).astimezone(UTC)
        d.status, d.updated_at = DraftStatus.approved, utcnow()
        db.add(d)
        db.commit()
    if action == "now":
        from app.publisher import publish_now
        bg.add_task(publish_now, draft_id)
    return RedirectResponse("/classic", status_code=303)


@app.post("/drafts/{draft_id}/reject", dependencies=[Depends(auth)])
def reject(draft_id: int):
    _set_status(draft_id, DraftStatus.rejected)
    return RedirectResponse("/classic", status_code=303)


@app.post("/drafts/{draft_id}/retry", dependencies=[Depends(auth)])
def retry(draft_id: int):
    _set_status(draft_id, DraftStatus.approved)
    return RedirectResponse("/classic?status=failed", status_code=303)


@app.post("/drafts/{draft_id}/regenerate", dependencies=[Depends(auth)])
def regenerate(draft_id: int, bg: BackgroundTasks):
    from app.agents.graph import generate_post
    with session() as db:
        d = db.get(Draft, draft_id) or _404()
        page_id, pillar, fmt = d.page_id, d.pillar, d.format
    _set_status(draft_id, DraftStatus.rejected)
    bg.add_task(generate_post, page_id, pillar=pillar, fmt=fmt)
    return RedirectResponse("/classic", status_code=303)


@app.post("/generate", dependencies=[Depends(auth)])
def generate(bg: BackgroundTasks, page_id: str = Form(...), fmt: str = Form("")):
    from app.agents.graph import generate_post
    bg.add_task(generate_post, page_id, fmt=fmt or None)
    return RedirectResponse("/classic", status_code=303)


@app.post("/run/{job}", dependencies=[Depends(auth)])
def run_job(job: str, bg: BackgroundTasks):
    from app.scheduler import keep_queue_full
    jobs = {"plan": keep_queue_full, "publish": publish_due, "engage": scan_comments, "metrics": collect_metrics}
    if job not in jobs:
        _404()
    bg.add_task(jobs[job])
    return RedirectResponse("/classic", status_code=303)


@app.get("/analytics", dependencies=[Depends(auth)])
def analytics():
    return {pid: performance_summary(p) for pid, p in load_pages().items()}


@app.get("/health")
def health():
    return {"ok": True, "mode": s.mode}


def _set_status(draft_id: int, status: DraftStatus):
    with session() as db:
        d = db.get(Draft, draft_id) or _404()
        d.status, d.updated_at = status, utcnow()
        db.add(d)
        db.commit()


def _404():
    raise HTTPException(404)


# ── JSON API + React dashboard (frontend/dist) ──
from app.web.api import router as api_router  # noqa: E402

app.include_router(api_router, dependencies=[Depends(auth)])
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/", dependencies=[Depends(auth)])
def dashboard():
    if (DIST / "index.html").exists():
        from fastapi.responses import FileResponse
        return FileResponse(DIST / "index.html")
    return RedirectResponse("/classic")


if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")
