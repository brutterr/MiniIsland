"""Рисует графику установщика и иконку приложения (нужен Pillow: pip install pillow).

Запуск из корня проекта:  python installer_assets/make_art.py
Создаёт: MiniIsland.ico, installer_assets/wizard_*.bmp, installer_assets/small_*.bmp
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "installer_assets")
SS = 4  # суперсэмплинг для гладких краёв

BG_TOP, BG_BOT = (28, 24, 40), (14, 14, 16)   # как у тёмной темы острова
PINK, PINK_LT = (224, 64, 127), (255, 163, 201)
CYAN = (0, 229, 255)
WHITE, SUB = (245, 245, 247), (154, 154, 160)

FONT_DIRS = ["/usr/share/fonts/opentype/inter", "C:/Windows/Fonts", "/Library/Fonts"]


def font(size, bold=True):
    for d in FONT_DIRS:
        for name in (("Inter-Bold.otf", "segoeuib.ttf") if bold else ("Inter-Regular.otf", "segoeui.ttf")):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def gradient(w, h, top, bot):
    img = Image.new("RGB", (w, h), top)
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def glow(img, cx, cy, r, color, alpha):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - r, cy - r, cx + r, cy + r], fill=color + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(r * 0.55))
    img.paste(layer, (0, 0), layer)


def pill(img, cx, cy, w, h):
    """Остров: чёрная пилюля с лёгкой обводкой и эквалайзером внутри."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    d.rounded_rectangle([x0 - 1.5 * SS / 4, y0 - 1.5 * SS / 4, x1 + 1.5 * SS / 4, y1 + 1.5 * SS / 4],
                        radius=h / 2 + 2, fill=(70, 66, 92))
    d.rounded_rectangle([x0, y0, x1, y1], radius=h / 2, fill=(6, 6, 8))
    # эквалайзер: четыре столбика слева, точка-камера справа
    bars = [0.45, 0.95, 0.6, 1.0]
    bw, gap = h * 0.11, h * 0.09
    bx = x0 + h * 0.55
    full = h * 0.46
    for i, v in enumerate(bars):
        bh = full * v
        xx = bx + i * (bw + gap)
        d.rounded_rectangle([xx, cy + bh / 2 - bh, xx + bw, cy + bh / 2], radius=bw / 2,
                            fill=PINK if i % 2 == 0 else PINK_LT)
    d.ellipse([x1 - h * 0.62, cy - h * 0.12, x1 - h * 0.38, cy + h * 0.12], fill=CYAN)


def text_c(img, cx, y, s, f, fill):
    d = ImageDraw.Draw(img)
    w = d.textlength(s, font=f)
    d.text((cx - w / 2, y), s, font=f, fill=fill)


def wizard(w, h):
    W, H = w * SS, h * SS
    img = gradient(W, H, BG_TOP, BG_BOT)
    glow(img, W * 0.5, H * 0.30, W * 0.55, PINK, 70)
    glow(img, W * 0.2, H * 0.86, W * 0.5, CYAN, 38)
    pill(img, W / 2, H * 0.30, W * 0.74, W * 0.22)
    text_c(img, W / 2, H * 0.30 + W * 0.22, "Mini-Island", font(int(W * 0.125)), WHITE)
    text_c(img, W / 2, H * 0.30 + W * 0.22 + W * 0.17, "остров для рабочего стола",
           font(int(W * 0.065), False), SUB)
    return img.resize((w, h), Image.LANCZOS)


def small(n):
    W = n * SS
    img = Image.new("RGB", (W, W), BG_BOT)
    glow(img, W * 0.5, W * 0.5, W * 0.42, PINK, 60)
    pill(img, W / 2, W / 2, W * 0.86, W * 0.40)
    return img.resize((n, n), Image.LANCZOS)


def icon(n=256):
    W = n * SS
    img = gradient(W, W, BG_TOP, BG_BOT).convert("RGBA")
    mask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, W - 1], radius=int(W * 0.22), fill=255)
    base = img.convert("RGB")
    glow(base, W * 0.5, W * 0.5, W * 0.4, PINK, 80)
    pill(base, W / 2, W / 2, W * 0.78, W * 0.30)
    out = base.convert("RGBA")
    out.putalpha(mask)
    return out.resize((n, n), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    for scale, (w, h) in {"100": (164, 314), "150": (246, 471), "200": (328, 628)}.items():
        wizard(w, h).save(os.path.join(OUT, f"wizard_{scale}.bmp"))
    for scale, n in {"100": 55, "150": 83, "200": 110}.items():
        small(n).save(os.path.join(OUT, f"small_{scale}.bmp"))
    icon(256).save(os.path.join(ROOT, "MiniIsland.ico"),
                   sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("ok:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    sys.exit(main())
