"""Render a short walkthrough from the captured Chrome view of a public site."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "real-site-frames" / "00-overview.png"
OUTPUT = ROOT / "veribar-real-site-walkthrough.mp4"
IMAGE = Image.open(SOURCE).convert("RGB")
FPS = 12
WIDTH, HEIGHT = 1280, 720
FRAMES = [
    (5, None, "VERIBAR ON A REAL WEBSITE", "Wikipedia · Photosynthesis"),
    (15, (0, 80, 2400, 1430), "REAL PAGE RESULT", "The Chrome extension scores text on a public Wikipedia article."),
    (14, (360, 360, 2100, 1340), "TEXT SIGNAL", "GPT-2-like: 0% · A model estimate, not proof of authorship."),
    (14, (850, 540, 2290, 1350), "MEDIA SIGNAL", "The image is marked NOT ANALYZED; media verification is not active."),
    (12, (1800, 1150, 2400, 1462), "PAGE INDEX", "The extension reports one scanned text item on this page."),
    (10, (0, 80, 2400, 1430), "REAL-SITE CHECK COMPLETE", "Source: en.wikipedia.org/wiki/Photosynthesis"),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    return ImageFont.truetype(f"/System/Library/Fonts/Supplemental/{name}", size)


def ease(value: float) -> float:
    return value * value * (3 - 2 * value)


def draw_frame(section: int, progress: float) -> Image.Image:
    duration, crop, heading, caption = FRAMES[section]
    if crop is None:
        frame = Image.new("RGB", (WIDTH, HEIGHT), "#101010")
        draw = ImageDraw.Draw(frame)
        draw.rectangle((70, 115, 92, 180), fill="#ec3611")
        draw.text((120, 115), heading, font=font(54, True), fill="white")
        draw.text((120, 205), caption, font=font(38), fill="#ededed")
        draw.text((120, 595), "Captured in Chrome on 25 October 2026", font=font(25), fill="#a8a8a8")
        return frame

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
    x0, x1 = max(0, x0), min(IMAGE.width, x1)
    y0, y1 = max(0, y0), min(IMAGE.height, y1)
    view = IMAGE.crop((round(x0), round(y0), round(x1), round(y1)))
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
