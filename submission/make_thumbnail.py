"""Render the code-native VeriShield submission thumbnail."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
CANVAS = (1200, 675)
FONT_DIR = Path("/System/Library/Fonts/Supplemental")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_DIR / ("Arial Bold.ttf" if bold else "Arial.ttf"), size)


image = Image.new("RGB", CANVAS, "#111111")
draw = ImageDraw.Draw(image)
draw.rectangle((64, 64, 78, 154), fill="#ff4b1f")
draw.text((106, 68), "VeriShield", font=font(66, True), fill="#ffffff")
draw.text((66, 178), "Local text signals beside the articles you read", font=font(31), fill="#cccccc")
draw.rounded_rectangle((66, 274, 1134, 548), radius=8, fill="#f5f4f0")
draw.text((92, 290), "THREE REAL-SITE RESULTS", font=font(23, True), fill="#111111")
draw.line((92, 335, 1108, 335), fill="#111111", width=2)
for x, site, value in ((104, "Wikipedia", "0%"), (440, "AP News", "37%"), (790, "AP News", "100%")):
    draw.text((x, 363), site, font=font(24), fill="#111111")
    draw.text((x, 407), value, font=font(67, True), fill="#ff4b1f")
for x in (400, 750):
    draw.line((x, 357, x, 520), fill="#111111", width=2)
draw.text(
    (68, 578),
    "GPT-2-like estimates for specific text blocks · Not proof of authorship",
    font=font(22),
    fill="#a5a5a5",
)
output = ROOT / "verishield-thumbnail.png"
image.save(output, optimize=True)
print(output)
