"""Render a short walkthrough from captured Chrome views of public sites."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SOURCES = {
    "wiki": Image.open(ROOT / "real-site-frames" / "00-overview.jpg").convert("RGB"),
    "ap": Image.open(ROOT / "real-site-frames" / "02-ap-news-37.jpg").convert("RGB"),
}
OUTPUT = ROOT / "veribar-real-site-walkthrough.mp4"
FPS = 12
WIDTH, HEIGHT = 1280, 720
FRAMES = [
    (5, None, None, "VERIBAR ON REAL WEBSITES", "Wikipedia + AP News"),
    (15, "wiki", (0, 80, 2400, 1430), "WIKIPEDIA RESULT", "The Chrome extension scores text on a public Wikipedia article."),
    (14, "wiki", (360, 360, 2100, 1340), "TEXT SIGNAL", "GPT-2-like: 0% · A model estimate, not proof of authorship."),
    (14, "wiki", (850, 540, 2290, 1350), "MEDIA SIGNAL", "The image is marked NOT ANALYZED; media verification is not active."),
    (12, "wiki", (1800, 1150, 2400, 1454), "PAGE INDEX", "The extension reports one scanned text item on this page."),
    (17, "ap", (0, 0, 2560, 1430), "AP NEWS / NONZERO RESULT", "37% GPT-2-like on a 40-word photo-area text block."),
    (15, "ap", (1050, 590, 1800, 900), "EXPANDED DETECTOR RESULT", "37% is a model estimate; the full article body scored 0%."),
    (10, "wiki", (0, 80, 2400, 1430), "REAL-SITE CHECK COMPLETE", "Sources: Wikipedia Photosynthesis + AP News data-center report."),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    return ImageFont.truetype(f"/System/Library/Fonts/Supplemental/{name}", size)


def ease(value: float) -> float:
    return value * value * (3 - 2 * value)


def draw_frame(section: int, progress: float) -> Image.Image:
    duration, source, crop, heading, caption = FRAMES[section]
    if crop is None:
        frame = Image.new("RGB", (WIDTH, HEIGHT), "#101010")
        draw = ImageDraw.Draw(frame)
        draw.rectangle((70, 115, 92, 180), fill="#ec3611")
        draw.text((120, 115), heading, font=font(54, True), fill="white")
        draw.text((120, 205), caption, font=font(38), fill="#ededed")
        draw.text((120, 595), "Captured in Chrome on 25 October 2026", font=font(25), fill="#a8a8a8")
        return frame

    image = SOURCES[source]
    left, top, right, bottom = crop
    crop_width, crop_height = right - left, bottom - top
    # A restrained pan keeps the source capture readable without implying clicks.
    amount = ease(progress)
    inset = 0.02 * amount
    shift_x = (section % 2 * 2 - 1) * 0.012 * crop_width * amount
    shift_y = 0.01 * crop_height * amount
    x0 = left + crop_width * inset / 2 + shift_x
    y0 = top + crop_height * inset / 2 + shift_y
    x1 = right - crop_width * inset / 2 + shift_x
    y1 = bottom - crop_height * inset / 2 + shift_y
    x0, x1 = max(0, x0), min(image.width, x1)
    y0, y1 = max(0, y0), min(image.height, y1)
    view = image.crop((round(x0), round(y0), round(x1), round(y1)))
    scale = max(WIDTH / view.width, HEIGHT / view.height)
    view = view.resize((math.ceil(view.width * scale), math.ceil(view.height * scale)), Image.Resampling.LANCZOS)
    ox = (view.width - WIDTH) // 2
    oy = (view.height - HEIGHT) // 2
    frame = view.crop((ox, oy, ox + WIDTH, oy + HEIGHT))
    draw = ImageDraw.Draw(frame)
    draw.rectangle((0, 608, WIDTH, HEIGHT), fill="#111111")
    draw.rectangle((0, 608, 13, HEIGHT), fill="#ec3611")
    draw.text((34, 622), heading, font=font(28, True), fill="#ff5a32")
    draw.text((34, 662), caption, font=font(24), fill="white")
    return frame


def main() -> None:
    command = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size",
        f"{WIDTH}x{HEIGHT}", "-framerate", str(FPS), "-i", "-", "-an", "-c:v",
        "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(OUTPUT),
    ]
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) as process:
        assert process.stdin is not None
        for section, (duration, *_rest) in enumerate(FRAMES):
            total = duration * FPS
            for index in range(total):
                process.stdin.write(draw_frame(section, index / max(total - 1, 1)).tobytes())
        process.stdin.close()
        error = process.stderr.read().decode() if process.stderr else ""
        if process.wait() != 0:
            raise RuntimeError(error)
    print(OUTPUT)


if __name__ == "__main__":
    main()
