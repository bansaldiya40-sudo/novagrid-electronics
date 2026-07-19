"""
NovaGrid Electronics - Demo Data Seeder
Populates the SQLite database with 20+ realistic (fictional-brand)
electronics products, multi-image galleries, customer reviews,
advertisements, video ad records, discount rules, today's deals,
coupons, dealers and customer enquiries. Also generates a set of unique
premium studio-style product renders (PIL) and short Ken-Burns MP4
video previews (ffmpeg) for every product, so the app has no external
image or stock-footage dependencies whatsoever.
"""

import os
import math
import random
import subprocess
import datetime as dt
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps, ImageEnhance, ImageFont

from database.db_setup import (
    Base, engine, get_session, init_db,
    Product, Advertisement, VideoAd, DiscountRule, TodaysDeal,
    Dealer, Enquiry, AdminUser, Review, Coupon
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE_DIR, "assets", "images", "products")
AD_DIR = os.path.join(BASE_DIR, "assets", "images", "ads")
BANNER_DIR = os.path.join(BASE_DIR, "assets", "images", "banners")
CUSTOM_IMG_DIR = os.path.join(BASE_DIR, "assets", "images", "products_custom")
VIDEO_DIR = os.path.join(BASE_DIR, "assets", "videos")
CUSTOM_VIDEO_DIR = os.path.join(BASE_DIR, "assets", "videos", "custom")

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(AD_DIR, exist_ok=True)
os.makedirs(BANNER_DIR, exist_ok=True)
os.makedirs(CUSTOM_IMG_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)
os.makedirs(CUSTOM_VIDEO_DIR, exist_ok=True)


def _custom_photos_for_sku(sku):
    """Looks for user-supplied real product photos at
    assets/images/products_custom/<SKU>/ (1.jpg, 2.jpg, 3.jpg, 4.jpg, or
    any .jpg/.jpeg/.png/.webp files, sorted by filename). If present,
    these real photos are used instead of the procedural render — drop
    your own (properly licensed) product photography in there and
    reseed to pick them up. Returns a list of relative paths, or None."""
    folder = os.path.join(CUSTOM_IMG_DIR, sku)
    if not os.path.isdir(folder):
        return None
    exts = (".jpg", ".jpeg", ".png", ".webp")
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(exts))
    if not files:
        return None
    return [os.path.relpath(os.path.join(folder, f), BASE_DIR) for f in files]


def _custom_video_for_sku(sku):
    """Looks for a user-supplied real product video at
    assets/videos/custom/<SKU>.mp4 (or .mov/.webm). If present, it is
    used instead of the generated Ken-Burns preview."""
    for ext in (".mp4", ".mov", ".webm", ".m4v"):
        p = os.path.join(CUSTOM_VIDEO_DIR, f"{sku}{ext}")
        if os.path.isfile(p):
            return os.path.relpath(p, BASE_DIR)
    return None


# NovaGrid premium palette per category (deep plum/lavender studio background,
# accent finish drawn from purple / coral pink / emerald / soft gold)
CATEGORY_COLORS = {
    "Smartphones": ("#2A1B4D", "#7C4DFF"),
    "Laptops": ("#241B3D", "#D4AF6A"),
    "Audio": ("#2A1B4D", "#FF6F91"),
    "Televisions": ("#231942", "#12B886"),
    "Wearables": ("#2A1B4D", "#FF6F91"),
    "Home Appliances": ("#241B3D", "#12B886"),
    "Gaming": ("#1B1030", "#9D6BFF"),
    "Cameras": ("#241B3D", "#D4AF6A"),
}

GALLERY_LABELS = ["Front View", "Angle View", "Lifestyle Shot", "Detail Close-Up"]


def _get_font(size, bold=True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _hex(c):
    return tuple(int(c.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


def _lerp(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _rrect(draw, box, radius, **kw):
    draw.rounded_rectangle(box, radius=radius, **kw)


# --------------------------------------------------------------------------- #
# CATEGORY SILHOUETTES — flat gray/white shapes; colour + lighting is applied
# afterwards from the alpha mask (see _apply_material_light), so every
# category benefits from the same studio-lighting pipeline for free.
# --------------------------------------------------------------------------- #
def _draw_smartphone(draw, cx, cy, s, variant):
    bw, bh = s * 0.34, s * 0.70
    if variant == 3:
        bw, bh = s * 0.62, s * 1.3
    box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    _rrect(draw, box, radius=bw * 0.17, fill=(255, 255, 255, 255))
    screen = (box[0] + bw * 0.045, box[1] + bh * 0.03, box[2] - bw * 0.045, box[3] - bh * 0.03)
    _rrect(draw, screen, radius=bw * 0.12, fill=(60, 60, 65, 255))
    notch_w = bw * 0.30
    draw.rounded_rectangle((cx - notch_w / 2, box[1] + bh * 0.018, cx + notch_w / 2, box[1] + bh * 0.045),
                            radius=6, fill=(20, 20, 20, 255))
    cam_r = bw * 0.16
    camx, camy = box[0] + bw * 0.22, box[1] + bh * 0.10
    draw.ellipse((camx - cam_r, camy - cam_r, camx + cam_r, camy + cam_r), fill=(210, 210, 212, 255))
    draw.ellipse((camx - cam_r * 0.55, camy - cam_r * 0.55, camx + cam_r * 0.55, camy + cam_r * 0.55),
                  fill=(30, 30, 30, 255))
    for i, yfrac in enumerate([0.30, 0.40, 0.52]):
        yy = screen[1] + (screen[3] - screen[1]) * yfrac
        draw.line((screen[0] + bw * 0.10, yy, screen[2] - bw * 0.10, yy), fill=(150, 150, 155, 255), width=3)


def _draw_laptop(draw, cx, cy, s, variant):
    sw, sh = s * 0.64, s * 0.42
    screen_box = (cx - sw / 2, cy - sh / 2 - s * 0.07, cx + sw / 2, cy + sh / 2 - s * 0.07)
    _rrect(draw, screen_box, radius=10, fill=(240, 240, 242, 255))
    inner = (screen_box[0] + 8, screen_box[1] + 8, screen_box[2] - 8, screen_box[3] - 8)
    _rrect(draw, inner, radius=6, fill=(55, 58, 66, 255))
    base_y0 = screen_box[3]
    base_y1 = base_y0 + s * 0.05
    draw.polygon([
        (cx - sw / 2 - s * 0.055, base_y0), (cx + sw / 2 + s * 0.055, base_y0),
        (cx + sw / 2 + s * 0.11, base_y1), (cx - sw / 2 - s * 0.11, base_y1),
    ], fill=(225, 225, 228, 255))
    if variant != 3:
        kb = (cx - sw * 0.42, base_y0 + s * 0.012, cx + sw * 0.42, base_y0 + s * 0.032)
        draw.rounded_rectangle(kb, radius=4, fill=(170, 170, 175, 255))
    draw.rounded_rectangle((cx - s * 0.05, base_y1 - s * 0.012, cx + s * 0.05, base_y1 + s * 0.004),
                            radius=4, fill=(200, 200, 204, 255))


def _draw_headphones(draw, cx, cy, s, variant):
    r = s * 0.32
    band_box = (cx - r, cy - r * 1.18, cx + r, cy + r * 0.55)
    draw.arc(band_box, start=195, end=345, fill=(235, 235, 238, 255), width=int(s * 0.05))
    for side in (-1, 1):
        ex = cx + side * r * 0.98
        ey = cy + r * 0.32
        ew, eh = s * 0.16, s * 0.26
        cup = (ex - ew / 2, ey - eh / 2, ex + ew / 2, ey + eh / 2)
        _rrect(draw, cup, radius=ew * 0.4, fill=(225, 225, 228, 255))
        pad = (ex - ew * 0.28, ey - eh * 0.28, ex + ew * 0.28, ey + eh * 0.28)
        _rrect(draw, pad, radius=ew * 0.3, fill=(60, 60, 65, 255))


def _draw_television(draw, cx, cy, s, variant):
    sw, sh = s * 0.70, s * 0.42
    box = (cx - sw / 2, cy - sh / 2 - s * 0.05, cx + sw / 2, cy + sh / 2 - s * 0.05)
    _rrect(draw, box, radius=8, fill=(235, 235, 238, 255))
    inner = (box[0] + 6, box[1] + 6, box[2] - 6, box[3] - 6)
    _rrect(draw, inner, radius=4, fill=(45, 48, 56, 255))
    if variant != 3:
        gx0, gy0 = inner[0] + (inner[2] - inner[0]) * 0.08, inner[1] + (inner[3] - inner[1]) * 0.18
        cell = (inner[2] - inner[0]) * 0.09
        for i in range(6):
            x = gx0 + i * cell * 1.35
            draw.rounded_rectangle((x, gy0, x + cell, gy0 + cell), radius=6, fill=(120, 122, 132, 255))
    neck_y = box[3]
    draw.rectangle((cx - s * 0.017, neck_y, cx + s * 0.017, neck_y + s * 0.055), fill=(210, 210, 214, 255))
    draw.rounded_rectangle((cx - s * 0.12, neck_y + s * 0.055, cx + s * 0.12, neck_y + s * 0.072),
                            radius=6, fill=(195, 195, 200, 255))


def _draw_watch(draw, cx, cy, s, variant):
    r = s * 0.22
    draw.rounded_rectangle((cx - s * 0.095, cy - r - s * 0.22, cx + s * 0.095, cy - r + s * 0.02),
                            radius=16, fill=(70, 70, 75, 255))
    draw.rounded_rectangle((cx - s * 0.095, cy + r - s * 0.02, cx + s * 0.095, cy + r + s * 0.22),
                            radius=16, fill=(70, 70, 75, 255))
    face = (cx - r, cy - r, cx + r, cy + r)
    draw.ellipse(face, fill=(235, 235, 238, 255))
    inner = (cx - r * 0.74, cy - r * 0.74, cx + r * 0.74, cy + r * 0.74)
    draw.ellipse(inner, fill=(55, 58, 66, 255))
    draw.ellipse((cx + r * 0.94, cy - r * 0.11, cx + r * 1.16, cy + r * 0.11), fill=(200, 200, 204, 255))


def _draw_appliance(draw, cx, cy, s, variant):
    bw, bh = s * 0.46, s * 0.66
    box = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    _rrect(draw, box, radius=bw * 0.09, fill=(245, 245, 248, 255))
    mid_y = box[1] + bh * 0.42
    draw.line((box[0] + 6, mid_y, box[2] - 6, mid_y), fill=(180, 180, 185, 255), width=3)
    draw.rounded_rectangle((cx - bw * 0.045, box[1] + bh * 0.12, cx + bw * 0.045, box[1] + bh * 0.22),
                            radius=6, fill=(140, 140, 145, 255))
    draw.rounded_rectangle((cx - bw * 0.045, mid_y + bh * 0.10, cx + bw * 0.045, mid_y + bh * 0.20),
                            radius=6, fill=(140, 140, 145, 255))


def _draw_controller(draw, cx, cy, s, variant):
    bw, bh = s * 0.64, s * 0.30
    body = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    _rrect(draw, body, radius=bh * 0.55, fill=(235, 235, 238, 255))
    grip_r = bh * 0.64
    draw.ellipse((cx - bw / 2 - grip_r * 0.25, cy + bh * 0.05, cx - bw / 2 + grip_r, cy + bh * 0.9),
                  fill=(235, 235, 238, 255))
    draw.ellipse((cx + bw / 2 - grip_r, cy + bh * 0.05, cx + bw / 2 + grip_r * 0.25, cy + bh * 0.9),
                  fill=(235, 235, 238, 255))
    dpad_cx, dpad_cy = cx - bw * 0.27, cy
    draw.rectangle((dpad_cx - 15, dpad_cy - 5, dpad_cx + 15, dpad_cy + 5), fill=(70, 70, 75, 255))
    draw.rectangle((dpad_cx - 5, dpad_cy - 15, dpad_cx + 5, dpad_cy + 15), fill=(70, 70, 75, 255))
    bx, by = cx + bw * 0.27, cy
    for dx, dy, col in [(0, -15, 150), (0, 15, 90), (-15, 0, 90), (15, 0, 150)]:
        draw.ellipse((bx + dx - 7, by + dy - 7, bx + dx + 7, by + dy + 7), fill=(col, col, col, 255))


def _draw_camera(draw, cx, cy, s, variant):
    bw, bh = s * 0.54, s * 0.36
    body = (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)
    _rrect(draw, body, radius=12, fill=(230, 230, 233, 255))
    draw.rounded_rectangle((cx - bw * 0.22, body[1] - s * 0.055, cx - bw * 0.02, body[1]), radius=6,
                            fill=(230, 230, 233, 255))
    r = bh * 0.66 if variant != 3 else bh * 1.05
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(40, 40, 42, 255))
    r2 = r * 0.56
    draw.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), fill=(90, 92, 98, 255))
    r3 = r2 * 0.45
    draw.ellipse((cx - r3, cy - r3, cx + r3, cy + r3), fill=(18, 18, 20, 255))
    hr = 16 * (r / (bh * 0.66))
    hx = cx - bw * 0.40 * (r / (bh * 0.66))
    hy = cy - bh * 0.30 * (r / (bh * 0.66))
    draw.ellipse((hx, hy, hx + hr, hy + hr), fill=(225, 225, 230, 255))


def _draw_bolt(draw, cx, cy, s, variant):
    r = s * 0.34
    bolt = [
        (cx + r * 0.15, cy - r), (cx - r * 0.55, cy + r * 0.15), (cx - r * 0.05, cy + r * 0.15),
        (cx - r * 0.15, cy + r), (cx + r * 0.55, cy - r * 0.15), (cx + r * 0.05, cy - r * 0.15),
    ]
    draw.polygon(bolt, fill=(235, 235, 238, 255))


_SILHOUETTES = {
    "Smartphones": _draw_smartphone,
    "Laptops": _draw_laptop,
    "Audio": _draw_headphones,
    "Televisions": _draw_television,
    "Wearables": _draw_watch,
    "Home Appliances": _draw_appliance,
    "Gaming": _draw_controller,
    "Cameras": _draw_camera,
}


# --------------------------------------------------------------------------- #
# STUDIO PIPELINE — soft radial studio background, contact shadow, material
# lighting (duotone recolor + specular sweep + shading) and a floor
# reflection, applied generically to any category silhouette via its alpha
# mask. This is what gives the renders their premium, photo-like feel.
# --------------------------------------------------------------------------- #
def _studio_background(size, base_hex, variant, seed=0):
    w, h = size
    base = _hex(base_hex)
    light = _lerp(base, (255, 255, 255), 0.86)
    dark = _lerp(base, (0, 0, 0), 0.08)
    cx, cy = w * 0.5, h * 0.38
    maxd = math.hypot(w * 0.75, h * 0.75)

    # Vectorized radial gradient (numpy) — pure-Python per-pixel loops were
    # far too slow at 900px-1600px canvas sizes across 22 products.
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(xx - cx, yy - cy) / maxd
    t = np.clip(d, 0, 1) ** 1.4
    t = t[..., None]  # (h, w, 1) for broadcasting over RGB channels
    light_arr = np.array(light, dtype=np.float32)
    dark_arr = np.array(dark, dtype=np.float32)
    arr = (light_arr * (1 - t) + dark_arr * t).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB")

    if variant == 2:
        overlay = Image.new("RGBA", size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        bokeh_colors = [base + (60,), (255, 255, 255, 50), _lerp(base, (255, 200, 150), 0.5) + (55,)]
        rng = random.Random(seed + 7)
        for _ in range(10):
            r = rng.randint(int(w * 0.03), int(w * 0.10))
            x, y = rng.randint(0, w), rng.randint(0, h)
            odraw.ellipse((x - r, y - r, x + r, y + r), fill=rng.choice(bokeh_colors))
        overlay = overlay.filter(ImageFilter.GaussianBlur(18))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return img


def _add_ground_shadow(img, box):
    x0, y0, x1, y1 = box
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    cx = (x0 + x1) / 2
    ew = max(20.0, (x1 - x0) * 0.62)
    eh = ew * 0.14
    sy = y1 - (y1 - y0) * 0.02
    sdraw.ellipse((cx - ew / 2, sy - eh / 2, cx + ew / 2, sy + eh / 2), fill=(10, 14, 25, 95))
    shadow = shadow.filter(ImageFilter.GaussianBlur(ew * 0.045))
    return Image.alpha_composite(img.convert("RGBA"), shadow).convert("RGB")


def _apply_material_light(overlay, colors, box, variant):
    """Recolors + relights a flat gray/white silhouette using only its own
    alpha as the shape mask: duotone-tints it into a believable
    accent-colored metal/plastic finish (preserving internal shading as
    luminance), then layers a diagonal specular highlight sweep and soft
    contact shading. Works for any category silhouette without per-shape
    gradient code."""
    w, h = overlay.size
    x0, y0, x1, y1 = box
    alpha = overlay.split()[3]

    gray = overlay.convert("L")
    dark = _lerp(_hex(colors[1]), (0, 0, 0), 0.55)
    light = _lerp((255, 255, 255), _hex(colors[1]), 0.12)
    mid = _hex(colors[1])
    tinted = ImageOps.colorize(gray, black=dark, white=light, mid=mid, midpoint=170)

    grad = Image.new("L", overlay.size, 0)
    gdraw = ImageDraw.Draw(grad)
    shift = (variant * 61) % 100
    for i in range(w + h):
        v = int(255 * max(0, 1 - abs(((i - shift) % (w + h)) / (w + h) - 0.28) * 4))
        if i < h:
            gdraw.line((0, i, i, 0), fill=v)
        else:
            gdraw.line((i - h, h, w, i - w), fill=v)
    grad = grad.filter(ImageFilter.GaussianBlur(26))
    highlight_mask = ImageChops.multiply(alpha, grad).point(lambda a: int(a * 0.5))
    white_layer = Image.new("RGB", overlay.size, (255, 255, 255))
    tinted = Image.composite(white_layer, tinted, highlight_mask)

    shade = Image.new("L", overlay.size, 0)
    sdraw = ImageDraw.Draw(shade)
    sdraw.ellipse((x0 - (x1 - x0) * 0.2, y0 + (y1 - y0) * 0.55, x1 + (x1 - x0) * 0.05, y1 + (y1 - y0) * 0.35),
                  fill=150)
    shade = shade.filter(ImageFilter.GaussianBlur(36))
    shade_mask = ImageChops.multiply(alpha, shade).point(lambda a: int(a * 0.30))
    black_layer = Image.new("RGB", overlay.size, (0, 0, 0))
    tinted = Image.composite(black_layer, tinted, shade_mask)

    tinted_rgba = tinted.convert("RGBA")
    tinted_rgba.putalpha(alpha)
    return tinted_rgba


def _reflection(img, box):
    """A soft fading mirror reflection beneath the product — classic
    Apple-style product photography floor reflection."""
    w, h = img.size
    x0, y0, x1, y1 = box
    y0i, y1i = max(0, int(y0)), min(h, int(y1))
    if y1i <= y0i:
        return img
    strip = img.crop((0, y0i, w, y1i))
    flipped = ImageOps.flip(strip)
    strip_h = max(1, int((y1i - y0i) * 0.5))
    flipped = flipped.resize((w, strip_h))
    fade = Image.new("L", flipped.size, 0)
    fdraw = ImageDraw.Draw(fade)
    for yy in range(strip_h):
        fdraw.line((0, yy, flipped.size[0], yy), fill=int(90 * (1 - yy / strip_h)))
    flipped.putalpha(fade)
    canvas = img.convert("RGBA")
    canvas.alpha_composite(flipped, (0, y1i))
    return canvas.convert("RGB")


def generate_product_studio_image(path, category, colors, variant=0, size=(900, 900), seed=0):
    """Premium studio product render: clean soft-lit background, a
    category-accurate device silhouette recolored/relit into the brand's
    accent finish, a soft contact shadow and a subtle floor reflection —
    no baked-in text, exactly like real e-commerce product photography.
    `variant` produces 4 genuinely different framings (front / 3-quarter
    angle / lifestyle context with bokeh / macro detail close-up), fully
    procedural and copyright-safe."""
    w, h = size
    bg = _studio_background(size, colors[0], variant, seed=seed)

    cx, cy = w * 0.5, h * 0.46
    s = min(w, h) * 0.5
    rot = 0
    if variant == 1:
        rot = -9
        cx += w * 0.03
    elif variant == 2:
        s *= 0.72
        cx, cy = w * 0.42, h * 0.50
    elif variant == 3:
        s *= 1.35
        cy = h * 0.50

    fn = _SILHOUETTES.get(category, _draw_bolt)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    fn(odraw, cx, cy, s, variant)
    if rot:
        overlay = overlay.rotate(rot, resample=Image.BICUBIC, center=(cx, cy))

    bbox = overlay.getbbox() or (int(cx - s / 2), int(cy - s / 2), int(cx + s / 2), int(cy + s / 2))

    canvas = _add_ground_shadow(bg, bbox)
    if variant == 3:
        canvas = canvas.filter(ImageFilter.GaussianBlur(6))
    lit_overlay = _apply_material_light(overlay, colors, bbox, variant)
    canvas = canvas.convert("RGBA")
    canvas.alpha_composite(lit_overlay)
    canvas = canvas.convert("RGB")
    canvas = _reflection(canvas, bbox)

    canvas = ImageEnhance.Contrast(canvas).enhance(1.05)
    canvas = ImageEnhance.Color(canvas).enhance(1.08)
    canvas = canvas.filter(ImageFilter.SMOOTH_MORE)
    canvas.save(path, quality=94)


def generate_gradient_image(path, title, subtitle, colors, size=(900, 900), variant=0, category=None):
    """Back-compat entry point used by seed_database() and the Admin
    Dashboard ('Add New Product' / 'Add Advertisement'). Wide/short sizes
    (aspect ratio > 1.8, e.g. hero/banner ads) render a marketing banner
    with a frosted-glass title bar; anything else renders a clean,
    text-free studio product shot via generate_product_studio_image."""
    w, h = size
    is_banner = (w / max(1, h)) > 1.8
    if not is_banner:
        generate_product_studio_image(path, category, colors, variant=variant, size=size,
                                       seed=abs(hash(title)) % 1000)
        return

    seed = abs(hash(title)) % 1000
    bg = _studio_background(size, colors[0], 0, seed=seed)
    cx, cy = w * 0.30, h * 0.52
    s = min(w, h) * 0.85
    fn = _SILHOUETTES.get(category, _draw_bolt)
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    fn(odraw, cx, cy, s, 0)
    bbox = overlay.getbbox() or (int(cx - s / 2), int(cy - s / 2), int(cx + s / 2), int(cy + s / 2))
    canvas = _add_ground_shadow(bg, bbox)
    lit_overlay = _apply_material_light(overlay, colors, bbox, 0)
    canvas = canvas.convert("RGBA")
    canvas.alpha_composite(lit_overlay)
    canvas = canvas.convert("RGB")

    # frosted-glass title panel, right-hand side (classic retail hero banner)
    panel_w = int(w * 0.46)
    panel = (w - panel_w, 0, w, h)
    glass = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glass)
    gdraw.rectangle(panel, fill=(*_hex(colors[0]), 235))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), glass).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    font_title = _get_font(int(h * 0.11))
    font_sub = _get_font(int(h * 0.055), bold=False)
    tx = panel[0] + int(w * 0.04)
    words, lines, cur = title.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if draw.textlength(trial, font=font_title) > panel_w - int(w * 0.08) and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    if cur:
        lines.append(cur)
    ty = h * 0.30 - (len(lines) - 1) * (h * 0.065)
    for line in lines[:2]:
        draw.text((tx, ty), line, font=font_title, fill="white")
        ty += h * 0.13
    if subtitle:
        draw.text((tx, ty + h * 0.02), subtitle[:48], font=font_sub, fill=(230, 233, 240))
    accent_bar = (panel[0], 0, panel[0] + 6, h)
    draw.rectangle(accent_bar, fill=_hex(colors[1]))
    canvas.save(path, quality=94)


# --------------------------------------------------------------------------- #
# VIDEO PREVIEWS — real short MP4 clips rendered with ffmpeg (Ken-Burns
# style slow zoom/pan over the studio product render). No stock footage,
# no external video downloads.
# --------------------------------------------------------------------------- #
def generate_video_preview(mp4_path, category, colors, seed=0, duration=3.4, size=(900, 900)):
    """Renders a short (silent) MP4 walkthrough clip: a slow cinematic
    zoom over a freshly generated studio product shot, using ffmpeg's
    zoompan filter. Returns False (and leaves no file) if ffmpeg is
    unavailable, so callers can degrade gracefully."""
    tmp_src = mp4_path + "_src.jpg"
    generate_product_studio_image(tmp_src, category, colors, variant=0, size=(1600, 1600), seed=seed)
    frames = int(duration * 30)
    vf = (
        f"scale=1600:1600,"
        f"zoompan=z='min(zoom+0.0016,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={size[0]}x{size[1]}:fps=30,format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", tmp_src,
        "-vf", vf, "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        mp4_path,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        ok = os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0
    except Exception:
        ok = False
    finally:
        if os.path.exists(tmp_src):
            os.remove(tmp_src)
    return ok


def generate_video_placeholder(path, title, colors, size=(900, 900), category=None):
    """Back-compat shim for the Admin Dashboard's 'Add Video Advertisement'
    form (kept so existing call sites don't break). `path` is expected to
    end in .mp4; generates a real Ken-Burns MP4 preview via ffmpeg, or a
    clean studio still image as a fallback if ffmpeg isn't available."""
    if path.lower().endswith((".mp4", ".mov", ".webm", ".m4v")):
        ok = generate_video_preview(path, category, colors, seed=abs(hash(title)) % 1000)
        if ok:
            return
        path = os.path.splitext(path)[0] + ".jpg"
    generate_product_studio_image(path, category, colors, variant=0, size=size, seed=abs(hash(title)) % 1000)


PRODUCTS = [
    ("NovaGrid AirPhone 15 Pro", "Smartphones", "NovaGrid", 79999, "6.7-inch AMOLED | A17 Chip | 256GB | 5G Dual SIM"),
    ("NovaGrid Nova X5", "Smartphones", "NovaTech", 34999, "5G | 120Hz Display | 128GB | 50MP Triple Camera"),
    ("NovaGrid Edge Lite", "Smartphones", "EdgeMobile", 18999, "6.5-inch HD+ | 5000mAh Battery | 64MP Camera"),
    ("NovaGrid TabPro 11", "Smartphones", "NovaGrid", 29999, "11-inch 2K Display | 8GB RAM | Stylus Included"),
    ("NovaGrid BookPro 14", "Laptops", "NovaGrid", 89999, "Intel i7 | 16GB RAM | 512GB SSD | 14-inch 2.8K"),
    ("NovaGrid AirBook Ultra", "Laptops", "AeroTech", 64999, "AMD Ryzen 5 | 8GB RAM | 512GB SSD | 15.6-inch FHD"),
    ("NovaGrid GameBook RTX", "Laptops", "GameForge", 124999, "RTX 4060 | 16GB RAM | 1TB SSD | 165Hz Display"),
    ("NovaGrid BeatBuds Pro", "Audio", "NovaGrid", 5999, "ANC | 40Hr Battery | IPX5 | Wireless Charging"),
    ("NovaGrid Thunder Speaker", "Audio", "SoundWave", 3499, "360° Sound | Bluetooth 5.3 | 20Hr Playback"),
    ("NovaGrid Studio Headphones", "Audio", "SoundWave", 7999, "Over-Ear | Hi-Res Audio | 60Hr Battery"),
    ("NovaGrid Vision 55 4K TV", "Televisions", "NovaGrid", 54999, "55-inch QLED | Smart TV | HDR10+ | Dolby Vision"),
    ("NovaGrid Vision 43 FHD TV", "Televisions", "NovaGrid", 27999, "43-inch Full HD | Smart TV | 20W Speakers"),
    ("NovaGrid Vision 65 8K TV", "Televisions", "NovaGrid", 129999, "65-inch 8K | Dolby Atmos | 120Hz Gaming Mode"),
    ("NovaGrid FitBand 3", "Wearables", "NovaGrid", 2999, "Heart Rate | SpO2 | 7-Day Battery | AMOLED"),
    ("NovaGrid Watch Active", "Wearables", "PulseTech", 8999, "AMOLED | GPS | 100+ Sports Modes | 5ATM"),
    ("NovaGrid ChillMax AC 1.5T", "Home Appliances", "ChillMax", 38999, "5-Star Inverter | Wifi Enabled | Copper Coil"),
    ("NovaGrid FreshAir Fridge 400L", "Home Appliances", "FreshAir", 42999, "Frost Free | Double Door | Convertible"),
    ("NovaGrid CleanWave WM 7Kg", "Home Appliances", "CleanWave", 24999, "Fully Automatic Front Load | 1200 RPM"),
    ("NovaGrid GameStation X", "Gaming", "NovaGrid", 49999, "1TB SSD | 4K Gaming | 2 Controllers Included"),
    ("NovaGrid ProController", "Gaming", "GameForge", 4499, "Wireless | Haptic Feedback | 20Hr Battery"),
    ("NovaGrid SnapShot DSLR", "Cameras", "NovaGrid", 62999, "24MP | 4K Video | Dual Lens Kit | WiFi Transfer"),
    ("NovaGrid ActionCam 4K", "Cameras", "SnapShot", 15999, "Waterproof | 4K60 | Stabilized | Voice Control"),
]

DESCRIPTIONS = {
    "Smartphones": "Experience blazing-fast performance, a stunning display and all-day battery life — engineered for the way you actually use your phone.",
    "Laptops": "Power through work and play with premium build quality, top-tier performance and a display that makes everything look better.",
    "Audio": "Immerse yourself in rich, crystal-clear sound engineered for true audiophiles, with all-day comfort for music, calls and everything in between.",
    "Televisions": "Bring the cinema home with vibrant colors, deep contrast and smart features that put every streaming app one click away.",
    "Wearables": "Track your fitness, stay connected and look great doing it with a sleek, comfortable wearable built for everyday life.",
    "Home Appliances": "Smart, energy-efficient home appliances built for modern households, designed to save you time, money and effort.",
    "Gaming": "Next-level gaming performance with immersive graphics, responsive controls and reliability that keeps up with you.",
    "Cameras": "Capture every moment in stunning clarity with professional-grade optics and intuitive controls for creators of every level.",
}

REVIEW_NAMES = [
    "Aarav Mehta", "Diya Kapoor", "Rohan Iyer", "Ananya Nair", "Vivaan Joshi",
    "Ishita Rao", "Kabir Malhotra", "Saanvi Pillai", "Aditya Bhat", "Meera Shah",
    "Arjun Desai", "Kavya Menon", "Reyansh Gupta", "Anika Verma", "Dhruv Sinha",
]
REVIEW_TITLES_POS = ["Excellent purchase!", "Worth every rupee", "Exceeded expectations",
                      "Great value for money", "Highly recommend", "Loving it so far"]
REVIEW_TITLES_MID = ["Good, but a few quirks", "Decent for the price", "Does the job"]
REVIEW_COMMENTS_POS = [
    "Build quality feels premium and performance has been smooth for daily use.",
    "Delivery was fast and the packaging was excellent. Product works exactly as described.",
    "Battery life is impressive and it looks even better in person.",
    "Setup was effortless and customer support answered my questions quickly.",
    "This has replaced my old device completely — noticeably better experience.",
]
REVIEW_COMMENTS_MID = [
    "Works well overall, though the companion app could be more polished.",
    "Good performance for the price, wish the accessories included were better.",
    "Does what it promises, nothing extraordinary but reliable so far.",
]


def build_specs(spec_line):
    parts = [p.strip() for p in spec_line.split("|")]
    return "|".join([f"{p}" for p in parts])


def seed_database(reset=False):
    if reset and os.path.exists(os.path.join(BASE_DIR, "novagrid.db")):
        os.remove(os.path.join(BASE_DIR, "novagrid.db"))

    init_db()
    session = get_session()

    if session.query(Product).count() > 0 and not reset:
        session.close()
        return  # already seeded

    if reset:
        for tbl in reversed(Base.metadata.sorted_tables):
            session.execute(tbl.delete())
        session.commit()

    random.seed(42)
    product_objs = []

    for idx, (name, cat, brand, price, spec) in enumerate(PRODUCTS, start=1):
        colors = CATEGORY_COLORS.get(cat, ("#0F172A", "#F4762C"))
        sku = f"NVG-{cat[:3].upper()}-{idx:03d}"
        custom_photos = _custom_photos_for_sku(sku)

        if custom_photos:
            cover_path_rel = custom_photos[0]
            gallery_paths = custom_photos[1:]
        else:
            cover_path = os.path.join(IMG_DIR, f"product_{idx}_0.png")
            generate_product_studio_image(cover_path, cat, colors, variant=0, seed=idx)
            cover_path_rel = os.path.relpath(cover_path, BASE_DIR)

            gallery_paths = []
            for v in range(1, 4):
                gp = os.path.join(IMG_DIR, f"product_{idx}_{v}.png")
                generate_product_studio_image(gp, cat, colors, variant=v, seed=idx)
                gallery_paths.append(os.path.relpath(gp, BASE_DIR))

        discount = random.choice([0, 5, 10, 12, 15, 18, 20, 25, 30, 35])
        stock = random.choice([0, 3, 5, 8, 15, 25, 40, 60, 100])
        rating = round(random.uniform(3.6, 4.9), 1)

        custom_video = _custom_video_for_sku(sku)
        if custom_video:
            video_path = custom_video
            has_video = True
        else:
            vpath = os.path.join(VIDEO_DIR, f"product_{idx}.mp4")
            has_video = generate_video_preview(vpath, cat, colors, seed=idx)
            video_path = os.path.relpath(vpath, BASE_DIR) if has_video else ""

        p = Product(
            sku=sku,
            name=name,
            category=cat,
            brand=brand,
            price=price,
            discount_percent=discount,
            stock=stock,
            low_stock_threshold=10,
            image_path=cover_path_rel,
            gallery_json=json.dumps(gallery_paths),
            rating=rating,
            review_count=random.randint(25, 4200),
            description=DESCRIPTIONS.get(cat, "Premium quality electronics from NovaGrid."),
            specifications=build_specs(spec),
            warranty=random.choice(["1 Year Brand Warranty", "2 Year Comprehensive Warranty",
                                     "6 Months Warranty", "3 Year Extended Warranty"]),
            delivery_days=random.choice([1, 2, 3, 4, 5]),
            emi_available=price >= 3000,
            cashback_percent=random.choice([0, 0, 2, 3, 5]),
            is_featured=idx % 4 == 0,
            is_bestseller=idx % 5 == 0,
            is_new_arrival=idx % 3 == 0,
            has_video=has_video,
            video_note="360° Product Preview" if has_video else "",
            video_path=video_path,
        )
        session.add(p)
        product_objs.append(p)

    session.commit()

    # ---------------- Reviews ---------------- #
    for p in product_objs:
        n_reviews = random.randint(3, 6)
        for _ in range(n_reviews):
            positive = random.random() < 0.75
            rating = round(random.uniform(4.2, 5.0), 1) if positive else round(random.uniform(3.0, 4.1), 1)
            session.add(Review(
                product_id=p.id,
                reviewer_name=random.choice(REVIEW_NAMES),
                rating=rating,
                title=random.choice(REVIEW_TITLES_POS if positive else REVIEW_TITLES_MID),
                comment=random.choice(REVIEW_COMMENTS_POS if positive else REVIEW_COMMENTS_MID),
                verified_purchase=random.random() < 0.85,
                helpful_count=random.randint(0, 240),
                created_at=dt.datetime.utcnow() - dt.timedelta(days=random.randint(1, 300)),
            ))
    session.commit()

    # ---------------- Advertisements ---------------- #
    ad_titles = [
        ("Mega Electronics Festival", "Up to 40% off on Smartphones & Laptops", "hero"),
        ("Season Sale Spectacular", "Big Savings & Everything Bright", "hero"),
        ("New Arrivals Spotlight", "Be the first to own the latest tech", "hero"),
        ("Audio Fest 2026", "Flat 25% off on Headphones & Speakers", "banner"),
        ("Weekend Flash Sale", "Extra 10% off - Today Only!", "flash"),
        ("Mega Discount Days", "Storewide savings up to 50% off", "festival"),
    ]
    ad_categories = ["Smartphones", "Laptops", "Audio", "Audio", "Gaming", "Televisions"]
    for i, (title, sub, pos) in enumerate(ad_titles, start=1):
        path = os.path.join(AD_DIR, f"ad_{i}.png")
        colors = list(CATEGORY_COLORS.values())[i % len(CATEGORY_COLORS)]
        generate_gradient_image(path, title, sub, colors, size=(1400, 560), variant=i,
                                 category=ad_categories[i - 1])
        session.add(Advertisement(
            title=title, subtitle=sub,
            image_path=os.path.relpath(path, BASE_DIR),
            is_active=True, position=pos,
            link_product_id=random.choice(product_objs).id,
        ))
    session.commit()

    # ---------------- Video Ads (records reuse each product's real preview) - #
    video_products = [p for p in product_objs if p.has_video]
    for p in video_products:
        session.add(VideoAd(
            product_id=p.id,
            title=f"{p.name} - Official Walkthrough",
            video_path=p.video_path,
            is_active=True,
        ))
    session.commit()

    # ---------------- Discount Rules (Buy More Save More) ---------------- #
    for p in random.sample(product_objs, 10):
        session.add(DiscountRule(
            product_id=p.id, min_qty=2, extra_discount_percent=5,
            description="Buy 2, get extra 5% off"
        ))
        session.add(DiscountRule(
            product_id=p.id, min_qty=3, extra_discount_percent=10,
            description="Buy 3+, get extra 10% off"
        ))
    session.commit()

    # ---------------- Today's Deals ---------------- #
    now = dt.datetime.utcnow()
    for p in random.sample(product_objs, 6):
        session.add(TodaysDeal(
            product_id=p.id,
            deal_discount_percent=random.choice([15, 20, 25, 30, 40]),
            starts_at=now,
            ends_at=now + dt.timedelta(hours=random.choice([4, 8, 12, 24])),
            is_active=True,
        ))
    session.commit()

    # ---------------- Dealers ---------------- #
    dealer_names = [
        ("TechHub Distributors", "North India"), ("Metro Electro Traders", "South India"),
        ("Prime Gadget Supplies", "West India"), ("EastWave Electronics", "East India"),
        ("Capital City Retailers", "North India"), ("Coastal Tech Partners", "South India"),
    ]
    for name, region in dealer_names:
        session.add(Dealer(
            name=name, region=region,
            contact_email=name.lower().replace(" ", "") + "@partners.com",
            contact_phone=f"+91-9{random.randint(100000000, 999999999)}",
            products_supplied=random.randint(20, 300),
            performance_score=round(random.uniform(60, 98), 1),
            join_date=now - dt.timedelta(days=random.randint(60, 900)),
        ))
    session.commit()

    # ---------------- Enquiries ---------------- #
    sample_customers = [
        ("Rahul Sharma", "rahul.sharma@mail.com", "9876543210"),
        ("Priya Verma", "priya.verma@mail.com", "9812345678"),
        ("Amit Kapoor", "amit.kapoor@mail.com", "9898989898"),
        ("Sneha Reddy", "sneha.reddy@mail.com", "9900112233"),
        ("Karan Mehta", "karan.mehta@mail.com", "9765432109"),
    ]
    messages = [
        "Is EMI available for this product?",
        "When will this be back in stock?",
        "Does this come with an extended warranty option?",
        "Can I get a demo before purchase?",
        "Is there any exchange offer available?",
    ]
    for i, (cname, email, phone) in enumerate(sample_customers):
        session.add(Enquiry(
            customer_name=cname, email=email, phone=phone,
            product_id=random.choice(product_objs).id,
            message=random.choice(messages),
            status=random.choice(["Open", "In Progress", "Resolved"]),
            created_at=now - dt.timedelta(days=random.randint(0, 15)),
        ))
    session.commit()

    # ---------------- Simulated historical sales (for revenue analytics) --- #
    from database.db_setup import Sale
    for _ in range(150):
        p = random.choice(product_objs)
        qty = random.randint(1, 4)
        session.add(Sale(
            product_id=p.id,
            quantity=qty,
            amount=round(p.discounted_price * qty, 2),
            timestamp=now - dt.timedelta(days=random.randint(0, 60),
                                          hours=random.randint(0, 23)),
        ))
    session.commit()

    # ---------------- Coupons ---------------- #
    coupon_defs = [
        ("NOVA10", 10, 999, 1500, "Flat 10% off on orders above ₹999"),
        ("WELCOME15", 15, 1999, 2500, "New customer special — 15% off"),
        ("FEST25", 25, 4999, 6000, "Festival mega discount — 25% off"),
        ("NOVAGOLD", 5, 0, 1000, "Loyalty reward — 5% off any order"),
    ]
    for code, pct, min_val, max_disc, desc in coupon_defs:
        session.add(Coupon(
            code=code, discount_percent=pct, min_order_value=min_val,
            max_discount_amount=max_disc, is_active=True, description=desc,
            expires_at=now + dt.timedelta(days=90),
        ))
    session.commit()

    # ---------------- Admin user ---------------- #
    if session.query(AdminUser).filter_by(username="admin").first() is None:
        session.add(AdminUser(username="admin", password="novagrid@123"))
        session.commit()
