"""청집사 앱 아이콘 생성 — '집 + 직지(금속활자판)' 모티브.

청주 상징(직지: 세계 최고 금속활자본) × 집사(집·데이터) 퓨전:
  지붕(집) 아래에 활자 조판 블록 격자(직지) — '기록/데이터를 담은 집'.
브랜드 teal 그라데이션 유지. 산출: frontend/public/icons/*.png
(maskable 은 안전영역 60% 안에 요소 배치)

사용: python -m scripts.gen_icons
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "icons"
TEAL_TOP = (31, 165, 148)     # #1FA594
TEAL_BOT = (14, 124, 113)     # #0E7C71
WHITE = (255, 255, 255, 255)
ACCENT = (255, 214, 120, 255)  # 활자 하나 포인트(금속활자 느낌의 옅은 금색)


def _gradient(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size))
    for y in range(size):
        t = y / max(size - 1, 1)
        c = tuple(round(a + (b - a) * t) for a, b in zip(TEAL_TOP, TEAL_BOT))
        for x in range(size):
            img.putpixel((x, y), c)
    return img.convert("RGBA")


def _draw_motif(d: ImageDraw.ImageDraw, size: int, scale: float = 1.0):
    """지붕 + 활자판. scale<1 이면 중앙 축소(maskable 안전영역)."""
    s = size * scale
    ox = oy = (size - s) / 2
    lw = max(round(s * 0.055), 4)
    # 지붕(집): 처마 살짝 올라간 한옥 느낌의 직선 지붕
    apex = (ox + s * 0.50, oy + s * 0.16)
    l_e = (ox + s * 0.12, oy + s * 0.46)
    r_e = (ox + s * 0.88, oy + s * 0.46)
    d.line([l_e, apex, r_e], fill=WHITE, width=lw, joint="curve")
    # 몸체(활자판 틀)
    bx0, by0 = ox + s * 0.20, oy + s * 0.46
    bx1, by1 = ox + s * 0.80, oy + s * 0.86
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=s * 0.045,
                        outline=WHITE, width=lw)
    # 활자 블록 3×2 (직지 조판) — 한 블록만 금색 포인트
    cols, rows = 3, 2
    gx, gy = (bx1 - bx0) * 0.10, (by1 - by0) * 0.14
    cw = (bx1 - bx0 - gx * (cols + 1)) / cols
    ch = (by1 - by0 - gy * (rows + 1)) / rows
    for r in range(rows):
        for c in range(cols):
            x0 = bx0 + gx * (c + 1) + cw * c
            y0 = by0 + gy * (r + 1) + ch * r
            fill = ACCENT if (r, c) == (0, 1) else WHITE
            d.rounded_rectangle([x0, y0, x0 + cw, y0 + ch],
                                radius=s * 0.022, fill=fill)


def _rounded(img: Image.Image, radius_ratio: float) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, img.size[0], img.size[1]], radius=img.size[0] * radius_ratio, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def make(size: int, maskable: bool = False, rounded: float = 0.0) -> Image.Image:
    big = size * 4                      # 4x 슈퍼샘플 → 다운스케일 안티앨리어싱
    img = _gradient(big)
    _draw_motif(ImageDraw.Draw(img), big, scale=0.62 if maskable else 0.86)
    img = img.resize((size, size), Image.LANCZOS)
    if rounded:
        img = _rounded(img, rounded)
    return img


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    make(192).save(OUT / "icon-192.png")
    make(512).save(OUT / "icon-512.png")
    make(512, maskable=True).save(OUT / "icon-maskable-512.png")
    make(180).save(OUT / "apple-touch-icon-180.png")
    print("아이콘 4종 생성:", OUT)


if __name__ == "__main__":
    run()
