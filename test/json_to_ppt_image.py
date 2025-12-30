import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def wrap_line(line: str, max_chars: int) -> list[str]:
    if len(line) <= max_chars:
        return [line]
    out = []
    i = 0
    while i < len(line):
        out.append(line[i : i + max_chars])
        i += max_chars
    return out


def main() -> None:
    # Input / output
    json_path = Path(r"test\08_algo_comparison_weeks_disjoint_success.json")
    out_path = Path(r"test\08_algo_comparison_weeks_disjoint_success.png")

    # Render settings (tweak if you need larger text)
    font_path = Path(r"C:\Windows\Fonts\consola.ttf")  # Consolas
    font_size = 18
    padding = 30
    line_spacing = 6
    bg = (255, 255, 255)
    fg = (20, 20, 20)

    # Wrap settings: increase if you want wider lines (slide is landscape)
    max_chars_per_line = 120

    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = json.dumps(data, indent=2, ensure_ascii=False)

    # Prepare font
    font = ImageFont.truetype(str(font_path), font_size)

    # Wrap lines
    raw_lines = text.splitlines()
    lines: list[str] = []
    for ln in raw_lines:
        lines.extend(wrap_line(ln, max_chars_per_line))

    # Measure
    dummy = Image.new("RGB", (10, 10), bg)
    draw = ImageDraw.Draw(dummy)

    widths = []
    heights = []
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])

    img_w = max(widths, default=0) + padding * 2
    line_h = (max(heights, default=0) + line_spacing)
    img_h = len(lines) * line_h + padding * 2

    # Render
    img = Image.new("RGB", (img_w, img_h), bg)
    draw = ImageDraw.Draw(img)

    y = padding
    for ln in lines:
        draw.text((padding, y), ln, fill=fg, font=font)
        y += line_h

    img.save(out_path, format="PNG", optimize=True)
    print(f"Wrote: {out_path.resolve()}")


if __name__ == "__main__":
    main()
