"""生成安装包图标与界面素材：品牌蓝盾图标、勾选框、扫描动图、SVG 品牌图"""

import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
ICONS = os.path.join(ASSETS, "icons")

BLUE = (43, 124, 246)
BLUE_DEEP = (25, 96, 210)
INK = (23, 33, 48)


def _round_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [2, 2, size - 3, size - 3], radius=radius, fill=255
    )
    return mask


def _shield(d: ImageDraw.ImageDraw, S: int, ink, mark) -> None:
    """盾牌轮廓 + 中间对勾，小尺寸下仍然认得出。"""
    cx = S / 2
    top = S * 0.20
    w = S * 0.285
    p = [
        (cx - w, top + S * 0.06),
        (cx, top - S * 0.02),
        (cx + w, top + S * 0.06),
        (cx + w, top + S * 0.26),
        (cx, S * 0.80),
        (cx - w, top + S * 0.26),
    ]
    d.polygon(p, outline=None, fill=ink)
    # 对勾
    lw = int(S * 0.052)
    a = (cx - S * 0.125, S * 0.470)
    b = (cx - S * 0.018, S * 0.572)
    c = (cx + S * 0.140, S * 0.372)
    d.line([a, b], fill=mark, width=lw)
    d.line([b, c], fill=mark, width=lw)
    for p1, p2 in ((a, b), (b, c)):
        for q in (p1, p2):
            d.ellipse([q[0] - lw / 2, q[1] - lw / 2, q[0] + lw / 2, q[1] + lw / 2],
                      fill=mark)


def make(size: int = 1024) -> Image.Image:
    ss = 4
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / (S - 1)
        color = tuple(int(BLUE[i] + (BLUE_DEEP[i] - BLUE[i]) * t) for i in range(3))
        gd.line([(0, y), (S, y)], fill=color + (255,))

    img.paste(grad, (0, 0), _round_mask(S, int(S * 0.19)))
    d = ImageDraw.Draw(img)
    _shield(d, S, (255, 255, 255, 255), BLUE)
    return img.resize((size, size), Image.LANCZOS)


def make_check(size: int = 18, color=(255, 255, 255, 255)) -> Image.Image:
    ss = 4
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = S * 0.16
    p1 = (S * 0.18, S * 0.52)
    p2 = (S * 0.40, S * 0.74)
    p3 = (S * 0.84, S * 0.26)
    d.line([p1, p2], fill=color, width=int(w))
    d.line([p2, p3], fill=color, width=int(w))
    for p in (p1, p2, p3):
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=color)
    return img.resize((size, size), Image.LANCZOS)


def make_scan_gif(size: int = 48, frames: int = 36):
    """蓝色扫描环：一段弧绕圈，尾部渐隐。透明底，供 QMovie 播放。"""
    ss = 4
    S = size * ss
    out = []
    box = [int(S * 0.06), int(S * 0.06), int(S * 0.94), int(S * 0.94)]
    width = max(2, int(S * 0.055))
    for i in range(frames):
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.arc(box, 0, 360, fill=(43, 124, 246, 38), width=width)
        head = i * 360 / frames
        for k in range(7):
            t = k / 6
            a = int(230 * (1 - t) + 30)
            span = 16
            d.arc(box, head - span * (k + 1), head - span * k,
                  fill=(43, 124, 246, a), width=width)
        d.arc(box, head - span, head, fill=(255, 255, 255, 210), width=width)
        out.append(img.resize((size, size), Image.LANCZOS))
    return out


SVGS = {
    "brand-mark.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="2" y="2" width="60" height="60" rx="13" fill="#2B7CF6"/>
  <path d="M32 12c5 4 9 5 13 5v15c0 9-6 15-13 19-7-4-13-10-13-19V17c4 0 8-1 13-5z"
        fill="none" stroke="#fff" stroke-width="2.4"/>
  <path d="M25 33l5 5 10-11" fill="none" stroke="#fff" stroke-width="2.8"/>
</svg>
""",
    "glyph-shield.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M12 3l7 3v6c0 5-3 8-7 10-4-2-7-5-7-10V6l7-3z" fill="none"
        stroke="#2B7CF6" stroke-width="1.6"/>
  <path d="M9 12l2 2 4-4" fill="none" stroke="#2B7CF6" stroke-width="1.6"/>
</svg>
""",
    "glyph-radar.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <circle cx="12" cy="12" r="8.5" fill="none" stroke="#2B7CF6" stroke-width="1.4"/>
  <circle cx="12" cy="12" r="4.6" fill="none" stroke="#2B7CF6" stroke-width="1.2" opacity=".55"/>
  <path d="M12 12L18 6" stroke="#2B7CF6" stroke-width="1.6"/>
  <circle cx="16.2" cy="8.4" r="1.5" fill="#2B7CF6"/>
</svg>
""",
    "glyph-broom.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M15.5 4.5l4 4-2.4 2.4-4-4z" fill="#2B7CF6"/>
  <path d="M13 8l3 3-6 6-4.4 1.4L6.4 15 13 8z" fill="#2B7CF6" opacity=".85"/>
  <path d="M6.4 15l2.6 2.6-3.6 1-1-3.6z" fill="#8B939E"/>
</svg>
""",
    "glyph-route.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M5 18c0-4 4-4 7-4s7 0 7-4" fill="none" stroke="#2B7CF6" stroke-width="1.6"
        stroke-dasharray="3 2"/>
  <circle cx="5" cy="18" r="2.2" fill="#2B7CF6"/>
  <circle cx="12" cy="14" r="2.2" fill="#2B7CF6"/>
  <circle cx="19" cy="10" r="2.2" fill="#2B7CF6"/>
</svg>
""",
    "ad-ai-office.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <rect x="3" y="4" width="18" height="14" rx="3" fill="none" stroke="#2B7CF6" stroke-width="1.5"/>
  <circle cx="9" cy="11" r="1.6" fill="#2B7CF6"/>
  <circle cx="15" cy="11" r="1.6" fill="#2B7CF6"/>
  <path d="M9 15h6" stroke="#2B7CF6" stroke-width="1.4"/>
  <path d="M12 4v-1.6M10.4 2.4h3.2" stroke="#2B7CF6" stroke-width="1.4"/>
</svg>
""",
    "ad-bird-wallpaper.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <path d="M20 7c-1.6.6-2.4 1.6-2.6 2.8 1 .1 1.8-.2 2.4-.7-.4 2.8-2.4 4.6-5.6 4.7-3.6.1-6-2-6-5.2
        0-1.2.3-2.2.9-3 1.6-3.4 3.2-2.6 5.4-2.4 4.8.3 7 3 7 6.6 3.6 5.2 2.3.9 1.6-2.4 1.7-4.3-.7-1.8-1.6
        -3.2-1.2-5.4.4" fill="none" stroke="#2B7CF6" stroke-width="1.5"/>
  <circle cx="16.4" cy="8.2" r=".9" fill="#2B7CF6"/>
</svg>
""",
    "glyph-onekey.svg": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <circle cx="12" cy="12" r="8.6" fill="none" stroke="#2B7CF6" stroke-width="1.6"/>
  <path d="M12 7.2v5l3.2 2" stroke="#2B7CF6" stroke-width="1.6"/>
  <path d="M7.4 3.6L5.2 5.4M16.6 3.6l2.2 1.8" stroke="#8B939E" stroke-width="1.3"/>
</svg>
""",
}


def main():
    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(ICONS, exist_ok=True)

    base = make(1024)
    png_path = os.path.join(ASSETS, "app_icon.png")
    ico_path = os.path.join(ASSETS, "app_icon.ico")
    base.resize((512, 512), Image.LANCZOS).save(png_path)
    base.save(ico_path, format="ICO",
              sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])

    make_check(36).save(os.path.join(ASSETS, "check.png"))

    frames = make_scan_gif(48, 36)
    frames[0].save(os.path.join(ASSETS, "scan_ring.gif"), save_all=True,
                   append_images=frames[1:], duration=40, loop=0, disposal=2,
                   transparency=0)

    for name, body in SVGS.items():
        with open(os.path.join(ICONS, name), "w", encoding="utf-8") as f:
            f.write(body.strip() + "\n")

    print(f"PNG {png_path} {os.path.getsize(png_path)}B")
    print(f"ICO {ico_path} {os.path.getsize(ico_path)}B")
    for name in ("check.png", "scan_ring.gif"):
        p = os.path.join(ASSETS, name)
        print(f"ASSET {p} {os.path.getsize(p)}B")
    for name in SVGS:
        p = os.path.join(ICONS, name)
        print(f"SVG {p} {os.path.getsize(p)}B")


if __name__ == "__main__":
    main()
