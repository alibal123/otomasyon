"""Pillow ile 1080x1350 (4:5) gönderi görselleri. İtalik yazı tipi kullanılmaz."""
from __future__ import annotations

import io
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
M = 70  # kenar boşluğu

PALETTES = [
    dict(bg="#0B1D3A", fg="#F4F1EA", accent="#F2B84B", muted="#9FB1CE", card="#14305C"),  # gece mavisi
    dict(bg="#4A0E1C", fg="#FFF3E6", accent="#FF9F68", muted="#E2B8A8", card="#6B1A2D"),  # bordo
    dict(bg="#0E3B33", fg="#F2FAF6", accent="#C6F36B", muted="#9CCFC0", card="#17564B"),  # zümrüt
    dict(bg="#F3E9D8", fg="#241A12", accent="#B83A08", muted="#5E4C3B", card="#E6D6BC"),  # krem
    dict(bg="#2A1252", fg="#FBF3FF", accent="#FF6FB5", muted="#C5AEE8", card="#3F1D78"),  # mor
    dict(bg="#171717", fg="#F5F5F5", accent="#FF7A1A", muted="#A3A3A3", card="#262626"),  # kömür
    dict(bg="#0F4C5C", fg="#FDF6E3", accent="#FFB703", muted="#A8D5DD", card="#176478"),  # petrol
    dict(bg="#F7D9D0", fg="#3A1620", accent="#B5174B", muted="#6E414C", card="#F0C3B6"),  # pudra
]

_FONT_DIRS = {
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ],
    "reg": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ],
}
_cache: dict = {}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    kind = "bold" if bold else "reg"
    if kind not in _cache:
        path = next((p for p in _FONT_DIRS[kind] if os.path.exists(p)), None)
        if not path:
            raise RuntimeError("Uygun yazı tipi bulunamadı (DejaVu Sans veya Arial gerekli).")
        _cache[kind] = path
    return ImageFont.truetype(_cache[kind], size)


def wrap(d: ImageDraw.ImageDraw, text: str, f, maxw: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(d, text, maxw, maxh, start, minsize=26, bold=True, gap=1.2):
    size = start
    while True:
        f = font(size, bold)
        lines = wrap(d, text, f, maxw)
        ok = len(lines) * size * gap <= maxh and all(d.textlength(l, font=f) <= maxw for l in lines)
        if ok or size <= minsize:
            return f, lines
        size -= 2


def block(d, x, y, lines, f, fill, gap=1.2, center_w: int | None = None) -> int:
    for l in lines:
        tx = x + ((center_w - d.textlength(l, font=f)) / 2 if center_w else 0)
        d.text((tx, y), l, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def poster(data: bytes | None, w: int, h: int, radius: int = 22, label: str = "") -> Image.Image:
    if data:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    else:
        im = Image.new("RGB", (w, h), "#555555")
        ImageDraw.Draw(im).text((20, 20), label[:30], font=font(28, True), fill="#FFFFFF")
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    im = im.crop((l, t, l + w, t + h))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius, fill=255)
    im = im.convert("RGBA")
    im.putalpha(mask)
    return im


def put(canvas: Image.Image, im: Image.Image, xy):
    canvas.paste(im, (int(xy[0]), int(xy[1])), im)


def base(p: dict, variant: int):
    img = Image.new("RGB", (W, H), p["bg"])
    d = ImageDraw.Draw(img)
    v = variant % 4
    if v == 0:
        d.ellipse((W - 380, -260, W + 280, 400), fill=p["card"])
    elif v == 1:
        d.rectangle((0, H - 230, W, H), fill=p["card"])
    elif v == 2:
        d.rectangle((0, 0, 26, H), fill=p["accent"])
    else:
        d.polygon([(0, 0), (520, 0), (0, 380)], fill=p["card"])
    return img, d


def footer(d, p, idx, total):
    d.text((M, H - 78), "@derecefilm", font=font(30, True), fill=p["muted"])
    if total > 1:
        t = f"{idx}/{total}"
        d.text((W - M - d.textlength(t, font=font(30, True)), H - 78), t, font=font(30, True), fill=p["muted"])


def pill(d, p, x, y, text):
    f = font(30, True)
    w = d.textlength(text, font=f)
    d.rounded_rectangle((x, y, x + w + 44, y + 58), 29, fill=p["accent"])
    d.text((x + 22, y + 11), text, font=f, fill=p["bg"])


# ---------------------------------------------------------------- kapak (liste / radar)
def cover(p, variant, kicker, title, posters, sub, idx, total):
    img, d = base(p, variant)
    top = variant % 2 == 0
    ty = 150 if top else 700
    pill(d, p, M, ty - 90 if top else ty - 90, kicker)
    f, lines = fit(d, title, W - 2 * M, 420, 100)
    y = block(d, M, ty, lines, f, p["fg"])
    d.text((M, y + 10), sub, font=font(34), fill=p["muted"])
    py = 640 if top else 110
    n = min(3, len(posters))
    pw = (W - 2 * M - 30 * (n - 1)) // n
    for i in range(n):
        put(img, poster(posters[i], pw, int(pw * 1.5)), (M + i * (pw + 30), py))
    footer(d, p, idx, total)
    return img


# ---------------------------------------------------------------- liste öğesi
def list_item(p, variant, n, item, idx, total):
    img, d = base(p, variant)
    left = variant % 2 == 0
    pw, ph = 450, 675
    px = M if left else W - M - pw
    tx = M + pw + 50 if left else M
    tw = W - 2 * M - pw - 50
    put(img, poster(item.get("poster"), pw, ph), (px, 190))
    d.text((tx, 170), f"{n:02d}", font=font(130, True), fill=p["accent"])
    f, lines = fit(d, item["title"], tw, 230, 58)
    y = block(d, tx, 330, lines, f, p["fg"])
    d.text((tx, y + 8), str(item.get("year", "")), font=font(34, True), fill=p["muted"])
    f2, l2 = fit(d, item["blurb"], tw, 520, 36, bold=False, gap=1.3)
    block(d, tx, y + 70, l2, f2, p["fg"], gap=1.3)
    footer(d, p, idx, total)
    return img


# ---------------------------------------------------------------- tek film / belgesel
def single_cover(p, variant, kicker, title, tagline, poster_data, idx, total):
    img, d = base(p, variant)
    if variant % 2 == 0:
        put(img, poster(poster_data, 600, 900), ((W - 600) // 2, 90))
        pill(d, p, M, 1015, kicker)
        f, lines = fit(d, title, W - 2 * M, 130, 72)
        y = block(d, M, 1090, lines, f, p["fg"])
        f2, l2 = fit(d, tagline, W - 2 * M, 90, 34, bold=False)
        block(d, M, y + 4, l2, f2, p["muted"])
    else:
        put(img, poster(poster_data, 470, 705), (W - M - 470, 120))
        pill(d, p, M, 120, kicker)
        f, lines = fit(d, title, 430, 520, 74)
        y = block(d, M, 215, lines, f, p["fg"])
        f2, l2 = fit(d, tagline, 430, 420, 34, bold=False, gap=1.3)
        block(d, M, y + 20, l2, f2, p["muted"], gap=1.3)
    footer(d, p, idx, total)
    return img


def single_detail(p, variant, heading, why, facts, idx, total):
    img, d = base(p, variant + 1)
    d.text((M, 150), heading, font=font(64, True), fill=p["accent"])
    f, lines = fit(d, why, W - 2 * M, 560, 44, bold=False, gap=1.35)
    y = block(d, M, 270, lines, f, p["fg"], gap=1.35)
    y = max(y + 40, 900)
    d.rounded_rectangle((M, y - 20, W - M, y + 40 + 52 * len(facts)), 24, fill=p["card"])
    for i, fact in enumerate(facts):
        d.text((M + 36, y + i * 52), f"•  {fact}", font=font(34, True), fill=p["fg"])
    footer(d, p, idx, total)
    return img


# ---------------------------------------------------------------- quiz
def quiz_question(p, variant, question, options, idx, total):
    img, d = base(p, variant)
    d.text((W - 330, 40), "?", font=font(520, True), fill=p["card"])
    pill(d, p, M, 130, "QUIZ")
    f, lines = fit(d, question, W - 2 * M, 430, 62)
    y = block(d, M, 230, lines, f, p["fg"])
    y = max(y + 40, 700)
    for i, o in enumerate(options):
        d.rounded_rectangle((M, y, W - M, y + 130), 28, fill=p["card"])
        d.ellipse((M + 24, y + 29, M + 96, y + 101), fill=p["accent"])
        d.text((M + 60 - d.textlength("ABC"[i], font=font(40, True)) / 2, y + 40), "ABC"[i], font=font(40, True), fill=p["bg"])
        fo, lo = fit(d, o, W - 2 * M - 150, 110, 38, minsize=24)
        block(d, M + 124, y + 65 - int(len(lo) * fo.size * 1.1 / 2), lo, fo, p["fg"], gap=1.1)
        y += 160
    d.text((M, y + 10), "Cevabı kaydırınca gör →", font=font(32), fill=p["muted"])
    footer(d, p, idx, total)
    return img


def quiz_answer(p, variant, letter, answer, explanation, poster_data, idx, total):
    img, d = base(p, variant + 2)
    pill(d, p, M, 130, "CEVAP")
    f, lines = fit(d, f"{letter}) {answer}", W - 2 * M, 220, 72)
    y = block(d, M, 230, lines, f, p["accent"])
    f2, l2 = fit(d, explanation, W - 2 * M - 360, 520, 38, bold=False, gap=1.35)
    block(d, M, y + 40, l2, f2, p["fg"], gap=1.35)
    put(img, poster(poster_data, 300, 450), (W - M - 300, y + 40))
    footer(d, p, idx, total)
    return img


# ---------------------------------------------------------------- radar detay
def radar_detail(p, variant, title, items, idx, total):
    img, d = base(p, variant)
    f, lines = fit(d, title, W - 2 * M, 130, 56)
    block(d, M, 110, lines, f, p["fg"])
    y = 260
    for it in items[:4]:
        put(img, poster(it.get("poster"), 150, 225, radius=16), (M, y))
        d.text((M + 190, y + 4), it["date"], font=font(30, True), fill=p["accent"])
        fo, lo = fit(d, it["title"], W - 2 * M - 190, 80, 42)
        yy = block(d, M + 190, y + 46, lo, fo, p["fg"])
        fb, lb = fit(d, it["blurb"], W - 2 * M - 190, 110, 28, bold=False, gap=1.25)
        block(d, M + 190, yy + 4, lb, fb, p["muted"], gap=1.25)
        y += 255
    footer(d, p, idx, total)
    return img
