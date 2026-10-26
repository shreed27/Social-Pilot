"""Visual agent: renders on-brand media in templates modelled on formats that spread in 2026.

Templates (chosen by the strategist, tracked by analytics):
- bold       big type, one idea per slide, highlighted keyword, progress dots, "swipe" cue on the cover
- post_card  looks like a text-post screenshot (avatar, name, big text): the most-sent format for takes
- minimal    plain high-contrast storytelling slide, one sentence
- split      two-column contrast ("common way" vs "better way") for before/after posts

Formats: carousel → PNG slides (1080×1350) · document → PDF + PNG previews · image → one card
reel → 1080×1920 MP4: hook on screen from frame 1, 1–2.5 s beats, slow push-in, progress bar.
"""
import base64
import io
import logging
import subprocess
import uuid
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.agents.state import PostState
from app.pages import Brand, Page, get_page
from app.settings import get_settings

log = logging.getLogger(__name__)
FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "C:/Windows/Fonts", "."]
W, H = 1080, 1350


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for d in FONT_DIRS:
        p = Path(d) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default(size)


def _rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _is_dark(hex_: str) -> bool:
    r, g, b = _rgb(hex_)
    return (0.299 * r + 0.587 * g + 0.114 * b) < 140


def _mix(a: str, b: str, t: float) -> tuple[int, int, int]:
    ra, rb = _rgb(a), _rgb(b)
    return tuple(int(x + (y - x) * t) for x, y in zip(ra, rb))  # type: ignore[return-value]


def _wrap_words(draw, text: str, font, max_w: int) -> list[list[str]]:
    lines: list[list[str]] = []
    for para in (text or "").split("\n"):
        line: list[str] = []
        for w in para.split():
            test = " ".join(line + [w])
            if draw.textlength(test, font=font) <= max_w or not line:
                line.append(w)
            else:
                lines.append(line)
                line = [w]
        lines.append(line)
    return [ln for ln in lines if ln] or [[]]


def _draw_rich(draw, x: int, y: int, lines: list[list[str]], font, fill, accent, highlight: str, gap: int) -> int:
    hl = {w.strip(".,!?:;'\"").lower() for w in (highlight or "").split()}
    space = draw.textlength(" ", font=font)
    for line in lines:
        cx = x
        for w in line:
            colour = accent if w.strip(".,!?:;'\"").lower() in hl else fill
            draw.text((cx, y), w, font=font, fill=colour)
            cx += draw.textlength(w, font=font) + space
        y += font.size + gap
    return y


def _dots(draw, n: int, i: int, y: int, fg, accent):
    if n <= 1:
        return
    size, gap = 12, 14
    total = n * size + (n - 1) * gap
    x = (W - total) // 2
    total += 22  # the active dot is a wider pill
    x = (W - total) // 2
    for k in range(n):
        w = 34 if k == i else size
        draw.rounded_rectangle([x, y, x + w, y + size], radius=6, fill=accent if k == i else fg)
        x += w + gap


def _base(brand: Brand, size=(W, H), background: Image.Image | None = None):
    img = background.copy() if background else Image.new("RGB", size, brand.bg)
    d = ImageDraw.Draw(img, "RGBA")
    if background:
        d.rectangle([0, 0, *size], fill=(0, 0, 0, 150))
    return img, d


def render_bold(brand: Brand, title: str, body: str = "", *, highlight: str = "", index: int = 0, total: int = 1,
                handle: str = "", size=(W, H), background: Image.Image | None = None, cover: bool = False) -> Image.Image:
    w_, h_ = size
    img, d = _base(brand, size, background)
    pad = 96
    muted = _mix(brand.fg, brand.bg, 0.45)
    tsize = (104 if len(title) < 34 else 88 if len(title) < 60 else 72) if cover else (84 if len(title) < 40 else 68)
    tf, bf = _font(brand.font, tsize), _font(brand.font.replace("-Bold", ""), 44)
    t_lines = _wrap_words(d, title, tf, w_ - 2 * pad)
    b_lines = _wrap_words(d, body, bf, w_ - 2 * pad) if body else []
    block = len(t_lines) * (tf.size + 16) + (40 + len(b_lines) * (bf.size + 14) if b_lines else 0)
    y = max(pad + 60, int((h_ - block) * (0.40 if cover else 0.42)))
    if not cover and total > 1:
        num = _font(brand.font, 40)
        d.text((pad, y - 90), f"{index:02d}", font=num, fill=brand.accent)
    y = _draw_rich(d, pad, y, t_lines, tf, brand.fg, brand.accent, highlight, 16)
    if b_lines:
        _draw_rich(d, pad, y + 40, b_lines, bf, _mix(brand.fg, brand.bg, 0.15), brand.accent, "", 14)
    small = _font(brand.font, 32)
    if handle:
        d.text((pad, h_ - pad - 32), handle, font=small, fill=muted)
    if cover and total > 1:
        label = "Swipe  →"
        tw = d.textlength(label, font=small)
        x1 = w_ - pad
        d.rounded_rectangle([x1 - tw - 48, h_ - pad - 46, x1, h_ - pad + 12], radius=29, fill=brand.accent)
        d.text((x1 - tw - 24, h_ - pad - 32), label, font=small, fill=brand.bg)
    elif total > 1:
        _dots(d, total, index - 1, h_ - pad - 22, _mix(brand.fg, brand.bg, 0.7), brand.accent)
    return img


def render_post_card(brand: Brand, text: str, *, handle: str, highlight: str = "", index: int = 0, total: int = 1) -> Image.Image:
    img, d = _base(brand)
    light_card = _is_dark(brand.bg)
    card_bg = "#FFFFFF" if light_card else "#111111"
    ink = (15, 20, 25) if light_card else (240, 240, 240)
    sub = (100, 110, 120) if light_card else (150, 155, 160)
    pad, cw = 80, W - 160
    tf = _font(brand.font.replace("-Bold", ""), 58 if len(text) < 120 else 48)
    lines = _wrap_words(d, text, tf, cw - 2 * 56)
    ch = 56 + 96 + 40 + len(lines) * (tf.size + 18) + 56
    top = (H - ch) // 2
    d.rounded_rectangle([pad, top, pad + cw, top + ch], radius=36, fill=card_bg)
    ax, ay = pad + 56, top + 56
    d.ellipse([ax, ay, ax + 96, ay + 96], fill=brand.accent)
    ini = handle.lstrip("@")[:2].upper()
    f_ini = _font(brand.font, 38)
    d.text((ax + 48 - d.textlength(ini, font=f_ini) / 2, ay + 26), ini, font=f_ini, fill=brand.bg)
    name = handle.lstrip("@").replace(".", " ").replace("_", " ").title()
    d.text((ax + 120, ay + 10), name, font=_font(brand.font, 40), fill=ink)
    d.text((ax + 120, ay + 56), handle if handle.startswith("@") else f"@{handle.replace(' ', '').lower()}",
           font=_font(brand.font.replace("-Bold", ""), 34), fill=sub)
    _draw_rich(d, ax, ay + 96 + 40, lines, tf, ink, brand.accent, highlight, 18)
    if total > 1:
        _dots(d, total, index - 1, H - 110, _mix(brand.fg, brand.bg, 0.6), brand.accent)
    return img


def render_minimal(brand: Brand, text: str, *, handle: str, highlight: str = "", index: int = 0, total: int = 1) -> Image.Image:
    img, d = _base(brand)
    pad = 110
    tf = _font(brand.font, 76 if len(text) < 70 else 60)
    lines = _wrap_words(d, text, tf, W - 2 * pad)
    block = len(lines) * (tf.size + 22)
    _draw_rich(d, pad, (H - block) // 2, lines, tf, brand.fg, brand.accent, highlight, 22)
    small = _font(brand.font, 30)
    d.text((pad, H - pad - 30), handle, font=small, fill=_mix(brand.fg, brand.bg, 0.5))
    if total > 1:
        lbl = f"{index}/{total}"
        d.text((W - pad - d.textlength(lbl, font=small), H - pad - 30), lbl, font=small, fill=_mix(brand.fg, brand.bg, 0.5))
    return img


def render_split(brand: Brand, title: str, left: str, right: str, *, handle: str, index: int = 0, total: int = 1,
                 left_label: str = "Most people", right_label: str = "Do this instead") -> Image.Image:
    img, d = _base(brand)
    pad, gap = 80, 32
    tf = _font(brand.font, 64)
    y = _draw_rich(d, pad, 150, _wrap_words(d, title, tf, W - 2 * pad), tf, brand.fg, brand.accent, "", 12) + 50
    colw = (W - 2 * pad - gap) // 2
    bad, good = (214, 69, 65), (34, 160, 96)
    lf, bf = _font(brand.font, 34), _font(brand.font.replace("-Bold", ""), 46)
    wrapped = [_wrap_words(d, txt, bf, colw - 72) for txt in (left, right)]
    ph = 120 + max(len(w) for w in wrapped) * (bf.size + 14) + 60
    y = max(y, (H - ph) // 2 + 40)
    for i, (lab, txt, col) in enumerate(((left_label, left, bad), (right_label, right, good))):
        x = pad + i * (colw + gap)
        panel = _mix(brand.bg, brand.fg, 0.08)
        d.rounded_rectangle([x, y, x + colw, y + ph], radius=28, fill=panel, outline=col, width=4)
        mark = "✗" if i == 0 else "✓"
        d.text((x + 36, y + 36), f"{mark}  {lab}", font=lf, fill=col)
        _draw_rich(d, x + 36, y + 120, _wrap_words(d, txt, bf, colw - 72), bf, brand.fg, brand.accent, "", 14)
    small = _font(brand.font, 30)
    d.text((pad, H - 130), handle, font=small, fill=_mix(brand.fg, brand.bg, 0.5))
    if total > 1:
        _dots(d, total, index - 1, H - 118, _mix(brand.fg, brand.bg, 0.7), brand.accent)
    return img


def _footer(d, brand: Brand, handle: str, i: int, n: int, h_: int = H):
    pad = 96
    d.text((pad, h_ - pad - 32), handle, font=_font(brand.font, 32), fill=_mix(brand.fg, brand.bg, 0.45))
    if n > 1:
        _dots(d, n, i - 1, h_ - pad - 22, _mix(brand.fg, brand.bg, 0.7), brand.accent)


def _title_block(d, brand: Brand, title: str, highlight: str, y: int, size: int = 66, pad: int = 96) -> int:
    tf = _font(brand.font, size)
    return _draw_rich(d, pad, y, _wrap_words(d, title, tf, W - 2 * pad), tf, brand.fg, brand.accent, highlight, 14)


def render_list(brand: Brand, title: str, items: list[str], *, numbered: bool, highlight: str = "", handle: str = "",
                i: int = 0, n: int = 1) -> Image.Image:
    img, d = _base(brand)
    pad = 96
    items = [x for x in items if x][:6]
    f = _font(brand.font.replace("-Bold", ""), 46 if len(items) <= 4 else 40)
    wrapped = [_wrap_words(d, x, f, W - 2 * pad - 110) for x in items]
    body_h = sum(len(w) * (f.size + 12) + 44 for w in wrapped)
    tf_size = 66 if len(title) < 40 else 56
    title_h = len(_wrap_words(d, title, _font(brand.font, tf_size), W - 2 * pad)) * (tf_size + 14)
    y = max(150, (H - (title_h + 60 + body_h)) // 2 - 20)
    y = _title_block(d, brand, title, highlight, y, tf_size) + 50
    for k, lines in enumerate(wrapped, 1):
        if numbered:
            d.ellipse([pad, y - 2, pad + 64, y + 62], fill=brand.accent)
            num = str(k)
            nf = _font(brand.font, 36)
            d.text((pad + 32 - d.textlength(num, font=nf) / 2, y + 10), num, font=nf, fill=brand.bg)
        else:
            d.rounded_rectangle([pad + 18, y + 18, pad + 42, y + 42], radius=6, fill=brand.accent)
        y = _draw_rich(d, pad + 100, y, lines, f, brand.fg, brand.accent, "", 12) + 32
    _footer(d, brand, handle, i, n)
    return img


def render_stat(brand: Brand, stat: str, title: str, body: str = "", source: str = "", *, handle: str = "",
                i: int = 0, n: int = 1) -> Image.Image:
    img, d = _base(brand)
    pad = 96
    sf = _font(brand.font, 260 if len(stat) <= 4 else 200 if len(stat) <= 7 else 150)
    tf, bf = _font(brand.font, 60), _font(brand.font.replace("-Bold", ""), 42)
    t_lines = _wrap_words(d, title, tf, W - 2 * pad)
    b_lines = _wrap_words(d, body, bf, W - 2 * pad) if body else []
    block = sf.size + 30 + len(t_lines) * (tf.size + 12) + (30 + len(b_lines) * (bf.size + 12) if b_lines else 0)
    y = max(140, (H - block) // 2 - 40)
    d.text((pad - 8, y), stat, font=sf, fill=brand.accent)
    y += sf.size + 30
    y = _draw_rich(d, pad, y, t_lines, tf, brand.fg, brand.accent, "", 12)
    if b_lines:
        _draw_rich(d, pad, y + 30, b_lines, bf, _mix(brand.fg, brand.bg, 0.2), brand.accent, "", 12)
    if source and source.lower() not in ("example", "n/a", ""):
        sf2 = _font(brand.font.replace("-Bold", ""), 28)
        d.text((pad, H - 200), f"Source: {source}"[:70], font=sf2, fill=_mix(brand.fg, brand.bg, 0.5))
    _footer(d, brand, handle, i, n)
    return img


def render_image_slide(brand: Brand, picture: Image.Image, title: str, body: str = "", *, highlight: str = "",
                       handle: str = "", i: int = 0, n: int = 1) -> Image.Image:
    img, d = _base(brand)
    pad = 64
    ph = int(H * 0.56)
    pic = _cover_crop(picture.convert("RGB"), (W - 2 * pad, ph))
    mask = Image.new("L", pic.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, *pic.size], radius=36, fill=255)
    img.paste(pic, (pad, pad + 20), mask)
    y = pad + 20 + ph + 50
    tf = _font(brand.font, 62 if len(title) < 36 else 52)
    y = _draw_rich(d, 96, y, _wrap_words(d, title, tf, W - 192), tf, brand.fg, brand.accent, highlight, 12)
    if body:
        bf = _font(brand.font.replace("-Bold", ""), 38)
        _draw_rich(d, 96, y + 18, _wrap_words(d, body, bf, W - 192)[:3], bf, _mix(brand.fg, brand.bg, 0.2), brand.accent, "", 10)
    _footer(d, brand, handle, i, n)
    return img


def render_slide(brand: Brand, template: str, slide: dict, *, i: int, n: int, handle: str,
                 picture: Image.Image | None = None) -> Image.Image:
    title, body, hl = slide.get("title", ""), slide.get("body", ""), slide.get("highlight", "")
    layout = (slide.get("layout") or "text").lower()
    cover = i == 1
    if not cover:
        if layout in ("list", "steps") and slide.get("items"):
            return render_list(brand, title, slide["items"], numbered=layout == "steps", highlight=hl, handle=handle, i=i, n=n)
        if layout == "stat" and slide.get("stat"):
            return render_stat(brand, slide["stat"], title, body, slide.get("source", ""), handle=handle, i=i, n=n)
        if layout == "image" and picture is not None:
            return render_image_slide(brand, picture, title, body, highlight=hl, handle=handle, i=i, n=n)
        if layout == "compare" and slide.get("left") and slide.get("right"):
            return render_split(brand, title, slide["left"], slide["right"], handle=handle, index=i, total=n)
    if template == "post_card":
        return render_post_card(brand, f"{title}\n{body}".strip() if body and not cover else title, handle=handle,
                                highlight=hl, index=i, total=n)
    if template == "minimal":
        return render_minimal(brand, f"{title} {body}".strip(), handle=handle, highlight=hl, index=i, total=n)
    if template == "split" and not cover and slide.get("left") and slide.get("right"):
        return render_split(brand, title, slide["left"], slide["right"], handle=handle, index=i, total=n)
    return render_bold(brand, title, body, highlight=hl, index=i, total=n, handle=handle, cover=cover)


# kept for callers/tests that use the old name
def render_card(brand: Brand, title: str, body: str = "", *, size=(W, H), index: str = "", handle: str = "",
                background: Image.Image | None = None) -> Image.Image:
    i, n = (int(index.split("/")[0]), int(index.split("/")[1])) if index else (1, 1)
    return render_bold(brand, title, body, index=i, total=n, handle=handle, size=size, background=background, cover=(i == 1 and n == 1))


def _ai_background(prompt: str, size: tuple[int, int]) -> Image.Image | None:
    """AI photo background: kie.ai (Nano Banana, ~$0.04) if configured, else OpenAI, else None (flat brand colour)."""
    s = get_settings()
    from app.sources import kie
    if kie.enabled() and s.kie_ai_covers and kie.can_afford(kie.IMAGE_PRICE.get(s.kie_image_model, 0.1)):
        try:
            url = kie.KieClient().image(f"{prompt} {kie.SCENE_RULES}", aspect="3:4")
            tmp = s.media_dir / f"bg_{uuid.uuid4().hex[:8]}.jpg"
            kie.download(url, tmp)
            img = Image.open(tmp).convert("RGB")
            tmp.unlink(missing_ok=True)
            return _cover_crop(img, size)
        except Exception as e:  # noqa: BLE001
            log.warning("kie.ai background failed, falling back: %s", e)
    if not s.openai_api_key:
        return None
    try:
        r = httpx.post("https://api.openai.com/v1/images/generations", timeout=120,
                       headers={"Authorization": f"Bearer {s.openai_api_key}"},
                       json={"model": s.image_model, "prompt": prompt, "size": "1024x1536"})
        r.raise_for_status()
        img = Image.open(io.BytesIO(base64.b64decode(r.json()["data"][0]["b64_json"]))).convert("RGB")
        return _cover_crop(img, size)
    except Exception as e:  # noqa: BLE001
        log.warning("AI background failed, using flat brand colour: %s", e)
        return None


def _cover_crop(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    w, h = size
    scale = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def _out(page: Page, ext: str) -> Path:
    d = get_settings().media_dir / page.id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{uuid.uuid4().hex[:10]}.{ext}"


def _reel_frame(page: Page, text: str, highlight: str, i: int, n: int) -> Image.Image:
    b = page.brand
    img = Image.new("RGB", (1080, 1920), b.bg)
    d = ImageDraw.Draw(img)
    pad = 90
    tf = _font(b.font, 110 if len(text) < 26 else 92 if len(text) < 48 else 76)
    lines = _wrap_words(d, text, tf, 1080 - 2 * pad)
    block = len(lines) * (tf.size + 20)
    _draw_rich(d, pad, (1920 - block) // 2 - 60, lines, tf, b.fg, b.accent, highlight, 20)
    # progress bar (watchers see it's short → they stay)
    d.rounded_rectangle([pad, 150, 1080 - pad, 162], radius=6, fill=_mix(b.fg, b.bg, 0.8))
    d.rounded_rectangle([pad, 150, pad + int((1080 - 2 * pad) * (i + 1) / n), 162], radius=6, fill=b.accent)
    small = _font(b.font, 40)
    d.text((pad, 1920 - 260), page.handle, font=small, fill=_mix(b.fg, b.bg, 0.4))
    return img


def render_reel(page: Page, beats: list[dict], broll: list[dict] | None = None) -> Path:
    """AI B-roll reel when kie.ai is configured and in budget; otherwise the text-motion reel."""
    from app.sources import kie
    s = get_settings()
    scenes = [b for b in (broll or []) if b.get("scene")][: max(1, s.kie_clips_per_reel)]
    if scenes and kie.enabled():
        cost = sum(kie.video_cost(s.kie_video_model, int(b.get("seconds", 8))) for b in scenes)
        if kie.can_afford(cost):
            try:
                return _render_broll_reel(page, beats, scenes)
            except Exception as e:  # noqa: BLE001
                log.warning("AI b-roll reel failed, falling back to text reel: %s", e)
        else:
            log.info("kie.ai budget left can't cover %.2f; using text reel", cost)
    return _render_text_reel(page, beats)


def _render_text_reel(page: Page, beats: list[dict]) -> Path:
    tmp = get_settings().media_dir / page.id / f"reel_{uuid.uuid4().hex[:6]}"
    tmp.mkdir(parents=True, exist_ok=True)
    segs = []
    for i, b in enumerate(beats):
        fp = tmp / f"{i:02d}.png"
        _reel_frame(page, b["text"], b.get("highlight", ""), i, len(beats)).save(fp)
        secs = max(0.8, float(b.get("seconds", 1.8)))
        frames = int(secs * 30)
        seg = tmp / f"{i:02d}.mp4"
        # slow push-in keeps the frame alive; text is on screen from frame 0 (muted viewers)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", fp.name, "-frames:v", str(frames),
            "-vf", f"scale=1188:2112,zoompan=z='1+0.06*on/{frames}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-r", "30", seg.name,
        ], cwd=tmp, check=True)
        segs.append(f"file '{seg.name}'")
    (tmp / "list.txt").write_text("\n".join(segs))
    out = _out(page, "mp4")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
        "-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart", str(out.resolve()),
    ], cwd=tmp, check=True)
    return out


# Instagram's UI covers the top ~230 px, the bottom ~480 px and the right ~230 px of a 1080×1920 reel.
SAFE = {"x0": 80, "x1": 1080 - 230, "y0": 260, "y1": 1440}


def _overlay_png(page: Page, text: str, highlight: str, i: int, n: int, path: Path) -> None:
    b = page.brand
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    maxw = SAFE["x1"] - SAFE["x0"] - 64
    tf = _font(b.font, 92 if len(text) < 28 else 78 if len(text) < 50 else 64)
    lines = _wrap_words(d, text, tf, maxw)
    lh = tf.size + 18
    block_h = len(lines) * lh
    widest = max(d.textlength(" ".join(ln), font=tf) for ln in lines)
    y = SAFE["y0"] + int((SAFE["y1"] - SAFE["y0"] - block_h) * 0.38)   # upper-middle of the safe zone
    x = SAFE["x0"] + (SAFE["x1"] - SAFE["x0"] - int(widest)) // 2
    d.rounded_rectangle([x - 32, y - 26, x + widest + 32, y + block_h + 10], radius=28, fill=(0, 0, 0, 165))
    _draw_rich(d, x, y, lines, tf, (255, 255, 255), b.accent, highlight, 18)
    # progress bar just inside the safe top edge
    d.rounded_rectangle([SAFE["x0"], SAFE["y0"] - 40, SAFE["x1"], SAFE["y0"] - 30], radius=5, fill=(255, 255, 255, 90))
    d.rounded_rectangle([SAFE["x0"], SAFE["y0"] - 40, SAFE["x0"] + int((SAFE["x1"] - SAFE["x0"]) * (i + 1) / n),
                         SAFE["y0"] - 30], radius=5, fill=b.accent)
    img.save(path)


def _render_broll_reel(page: Page, beats: list[dict], scenes: list[dict]) -> Path:
    from app.sources import kie
    s = get_settings()
    tmp = s.media_dir / page.id / f"broll_{uuid.uuid4().hex[:6]}"
    tmp.mkdir(parents=True, exist_ok=True)
    client = kie.KieClient()
    clips = []
    for k, sc in enumerate(scenes):
        url = client.video(f"{sc['scene']} {kie.SCENE_RULES}", aspect="9:16", seconds=int(sc.get("seconds", 8)))
        raw = kie.download(url, tmp / f"raw{k}.mp4")
        norm = tmp / f"clip{k}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw.name,
                        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p",
                        *([] if s.kie_keep_audio else ["-an"]), "-c:v", "libx264", "-preset", "veryfast", norm.name],
                       cwd=tmp, check=True)
        clips.append(norm.name)
    total = sum(max(0.8, float(b.get("seconds", 1.8))) for b in beats)
    (tmp / "clips.txt").write_text("\n".join(f"file '{c}'" for c in clips))
    base = tmp / "base.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-f", "concat", "-safe", "0",
                    "-i", "clips.txt", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast",
                    *(["-c:a", "aac"] if s.kie_keep_audio else ["-an"]), base.name], cwd=tmp, check=True)
    # one transparent overlay per beat, shown only during its time window
    inputs, filters, t0, last = ["-i", base.name], [], 0.0, "[0:v]"
    for i, b in enumerate(beats):
        png = tmp / f"ov{i:02d}.png"
        _overlay_png(page, b["text"], b.get("highlight", ""), i, len(beats), png)
        t1 = t0 + max(0.8, float(b.get("seconds", 1.8)))
        inputs += ["-i", png.name]
        tag = f"[v{i}]"
        filters.append(f"{last}[{i + 1}:v]overlay=0:0:enable='between(t,{t0:.2f},{t1:.2f})'{tag}")
        last, t0 = tag, t1
    out = _out(page, "mp4")
    if s.kie_keep_audio:
        audio_in, audio_map = [], ["-map", "0:a?"]
    else:  # silent track: Instagram ranks muted-safe reels fine, and you add trending audio in the app
        audio_in = ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
        audio_map = ["-map", f"{len(beats) + 1}:a"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, *audio_in,
           "-filter_complex", ";".join(filters), "-map", last, *audio_map,
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
           "-movflags", "+faststart", str(out.resolve())]
    subprocess.run(cmd, cwd=tmp, check=True)
    return out


def visuals_node(state: PostState) -> PostState:
    page = get_page(state["page_id"])
    fmt, c = state["format"], state["content"]
    template = c.get("template") or state.get("template") or "bold"
    media: list[str] = []
    if fmt in ("carousel", "document"):
        slides = c.get("slides", [])[: (20 if fmt == "carousel" else 15)]
        pictures = {}
        for i, sl in enumerate(slides, 1):
            if i > 1 and (sl.get("layout") or "") == "image" and sl.get("image_prompt") and len(pictures) < 2:
                pic = _ai_background(sl["image_prompt"], (W - 128, int(H * 0.56)))
                if pic is not None:
                    pictures[i] = pic
        imgs = [render_slide(page.brand, template, sl, i=i, n=len(slides), handle=page.handle, picture=pictures.get(i))
                for i, sl in enumerate(slides, 1)]
        if template == "bold" and c.get("cover_prompt") and slides:
            bg = _ai_background(c["cover_prompt"], (W, H))
            if bg is not None:
                sl = slides[0]
                imgs[0] = render_bold(page.brand, sl["title"], sl.get("body", ""), highlight=sl.get("highlight", ""),
                                      index=1, total=len(slides), handle=page.handle, background=bg, cover=True)
        if fmt == "document":
            pdf = _out(page, "pdf")
            imgs[0].save(pdf, save_all=True, append_images=imgs[1:], resolution=150)
            media.append(str(pdf))  # uploaded to LinkedIn; PNGs below are dashboard previews
        for im in imgs:
            p = _out(page, "png")
            im.save(p)
            media.append(str(p))
    elif fmt == "image":
        headline = c.get("image_headline") or state.get("hook", "")
        p = _out(page, "png")
        if template == "post_card":
            img = render_post_card(page.brand, headline, handle=page.handle, highlight=c.get("highlight", ""))
        else:
            bg = _ai_background(c.get("cover_prompt") or f"Editorial photo for a post about {state['topic']} ({page.niche}), "
                                f"dark negative space at the top for a headline.", (W, H))
            img = render_bold(page.brand, headline, highlight=c.get("highlight", ""), handle=page.handle, background=bg, cover=True)
        img.save(p)
        media.append(str(p))
    elif fmt == "reel":
        media.append(str(render_reel(page, c.get("reel_script", []), c.get("broll"))))
    layouts = sorted({(s.get("layout") or "text") for s in c.get("slides") or []})
    return {"media": media, "log": state.get("log", []) + [f"visuals: {len(media)} file(s), template {template}"
                                                           + (f", layouts {'/'.join(layouts)}" if layouts else "")]}
