"""Pillow 生成应用图标：蓝绿渐变圆角方块 + 白色垃圾桶"""

import math
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")


def _round_rect_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [3, 3, size - 4, size - 4], radius=radius, fill=255
    )
    return mask


def make(size: int = 1024) -> Image.Image:
    ss = 4  # 超采样
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # 渐变底
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    c1 = (49, 196, 141)
    c2 = (18, 168, 198)
    c3 = (30, 99, 214)
    for y in range(S):
        for_t = y / (S - 1)
        if for_t < 0.55:
            t = for_t / 0.55
            color = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
        else:
            t = (for_t - 0.55) / 0.45
            color = tuple(int(c2[i] + (c3[i] - c2[i]) * t) for i in range(3))
        gd.line([(0, y), (S, y)], fill=color + (255,))

    mask = _round_rect_mask(S, int(S * 0.18))
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    cx = S / 2

    # 桶盖
    lid_w = S * 0.38
    lid_h = S * 0.058
    d.rounded_rectangle(
        [cx - lid_w / 2, S * 0.295, cx + lid_w / 2, S * 0.295 + lid_h],
        radius=int(S * 0.02), fill=white
    )
    # 提手
    d.rounded_rectangle(
        [cx - S * 0.055, S * 0.252, cx + S * 0.055, S * 0.30],
        radius=int(S * 0.022), fill=white
    )

    # 桶身
    top_w = S * 0.32
    bot_w = S * 0.235
    top_y = S * 0.385
    bot_y = S * 0.765
    body = [
        (cx - top_w / 2, top_y),
        (cx + top_w / 2, top_y),
        (cx + bot_w / 2, bot_y - S * 0.01),
    ]
    # 用多边形近似 + 底部圆角
    poly = [
        (cx - top_w / 2, top_y),
        (cx + top_w / 2, top_y),
        (cx + bot_w / 2, bot_y - S * 0.055),
        (cx + bot_w / 2 - S * 0.02, bot_y - S * 0.012),
        (cx - bot_w / 2 + S * 0.02, bot_y - S * 0.012),
        (cx - bot_w / 2, bot_y - S * 0.055),
    ]
    d.polygon(poly, fill=white)
    d.rounded_rectangle(
        [cx - bot_w / 2, bot_y - S * 0.09, cx + bot_w / 2, bot_y - S * 0.01],
        radius=int(S * 0.022), fill=white
    )

    # 桶身竖纹（半透明蓝）
    stripe = (18, 120, 175, 120)
    for i in (-1, 0, 1):
        x = cx + i * S * 0.075 - S * 0.008
        d.rounded_rectangle(
            [x, S * 0.455, x + S * 0.018, S * 0.71],
            radius=int(S * 0.009), fill=stripe
        )

    return img.resize((size, size), Image.LANCZOS)


def make_check(size: int = 18) -> Image.Image:
    """白色对勾，用于勾选框选中态。"""
    ss = 4
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = S * 0.14
    p1 = (S * 0.20, S * 0.52)
    p2 = (S * 0.42, S * 0.74)
    p3 = (S * 0.82, S * 0.28)
    d.line([p1, p2], fill=(255, 255, 255, 255), width=int(w))
    d.line([p2, p3], fill=(255, 255, 255, 255), width=int(w))
    # 端点圆角
    for p in (p1, p2, p3):
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2],
                  fill=(255, 255, 255, 255))
    return img.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(ASSETS, exist_ok=True)
    base = make(1024)
    png_path = os.path.join(ASSETS, "app_icon.png")
    ico_path = os.path.join(ASSETS, "app_icon.ico")
    check_path = os.path.join(ASSETS, "check.png")
    base.resize((512, 512), Image.LANCZOS).save(png_path)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    base.save(ico_path, format="ICO", sizes=sizes)
    make_check(36).save(check_path)
    print(f"PNG {png_path} {os.path.getsize(png_path)}B")
    print(f"ICO {ico_path} {os.path.getsize(ico_path)}B")
    print(f"CHECK {check_path} {os.path.getsize(check_path)}B")


if __name__ == "__main__":
    main()
