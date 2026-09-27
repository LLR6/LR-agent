from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1200
HEIGHT = 675
BG = (7, 10, 19)
PANEL = (15, 23, 42)
TEXT = (241, 245, 249)
MUTED = (148, 163, 184)
CYAN = (103, 232, 249)
PURPLE = (196, 181, 253)
PINK = (249, 168, 212)
GREEN = (134, 239, 172)
RED = (252, 165, 165)
TRACK = (30, 41, 59)


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


F_TITLE = font(48, True)
F_H2 = font(28, True)
F_BODY = font(23)
F_SMALL = font(18)
F_MONO = font(20, True)


def rounded(draw, box, radius=20, fill=PANEL, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def label(draw, x, y, text, color, width=220):
    rounded(draw, (x, y, x + width, y + 44), 18, fill=(18, 27, 48), outline=color, width=2)
    draw.text((x + 15, y + 10), text, font=F_SMALL, fill=color)


def bar(draw, x, y, value, color, label_text):
    w = 520
    draw.text((x, y), label_text, font=F_BODY, fill=TEXT)
    y2 = y + 36
    draw.rounded_rectangle((x, y2, x + w, y2 + 18), 9, fill=TRACK)
    draw.rounded_rectangle((x, y2, x + int(w * value), y2 + 18), 9, fill=color)
    draw.text((x + w + 18, y2 - 5), f"{int(value * 100)}%", font=F_SMALL, fill=color)


def base_frame(step: str, subtitle: str) -> Image.Image:
    im = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(im)
    d.text((58, 44), "LR-Agent · ChronoForge", font=F_TITLE, fill=TEXT)
    d.text((60, 102), "DETERMINISTIC SHOWCASE · NOT A BENCHMARK", font=F_SMALL, fill=PINK)
    d.text((60, 146), step, font=F_H2, fill=CYAN)
    d.text((60, 186), subtitle, font=F_BODY, fill=MUTED)
    return im


def patch_card(draw, x, y, name, status, detail, color):
    rounded(draw, (x, y, x + 500, y + 150), 24, fill=PANEL, outline=color, width=2)
    draw.text((x + 24, y + 20), name, font=F_H2, fill=TEXT)
    draw.text((x + 24, y + 68), status, font=F_MONO, fill=color)
    draw.text((x + 24, y + 108), detail, font=F_SMALL, fill=MUTED)


def make_frames():
    frames = []

    im = base_frame(
        "1 · Two patches pass today's tests",
        "Present-time correctness cannot tell us which design will be cheaper to maintain later.",
    )
    d = ImageDraw.Draw(im)
    patch_card(d, 60, 270, "Patch A", "pytest  ✓ PASS", "Current behavior verified", GREEN)
    patch_card(d, 640, 270, "Patch B", "pytest  ✓ PASS", "Current behavior verified", GREEN)
    d.text((390, 520), "Both are correct today.", font=F_H2, fill=TEXT)
    frames += [im] * 12

    im = base_frame(
        "2 · Freeze the same future matrix",
        "Both candidates are exposed to the same categories of future maintenance pressure.",
    )
    d = ImageDraw.Draw(im)
    xs = [70, 340, 610, 880]
    items = [
        ("g1", "Dependency\nupgrade", CYAN),
        ("g2", "API\ndeprecation", PURPLE),
        ("g3", "Schema\nmigration", PINK),
        ("g4", "Adjacent\nfeature", GREEN),
    ]
    for x, (g, name, color) in zip(xs, items):
        rounded(d, (x, 280, x + 220, 430), 22, fill=PANEL, outline=color, width=2)
        d.text((x + 20, 300), g, font=F_H2, fill=color)
        for i, line in enumerate(name.split("\n")):
            d.text((x + 20, 350 + i * 30), line, font=F_BODY, fill=TEXT)
    d.text((310, 510), "g2 inherits the real code produced by g1.", font=F_H2, fill=TEXT)
    frames += [im] * 12

    future_states = [
        ("g1 · Dependency upgrade", True, True, "both survive"),
        ("g2 · API deprecation", False, True, "Patch A breaks the seed behavior"),
        ("g3 · Schema migration", False, True, "Patch B keeps the contract"),
        ("g4 · Adjacent feature", False, True, "Patch B survives the full showcase"),
    ]
    for index, (title, a_ok, b_ok, detail) in enumerate(future_states, start=1):
        im = base_frame(
            f"3 · Future generation {index}",
            title + " — future maintainers make real repository edits, then seed checks are replayed.",
        )
        d = ImageDraw.Draw(im)
        patch_card(
            d, 60, 270, "Patch A",
            "✓ ALIVE" if a_ok else "✕ DEAD",
            "seed verification passes" if a_ok else "seed verification failed at g2",
            GREEN if a_ok else RED,
        )
        patch_card(
            d, 640, 270, "Patch B",
            "✓ ALIVE" if b_ok else "✕ DEAD",
            "seed verification passes" if b_ok else "seed verification failed",
            GREEN if b_ok else RED,
        )
        d.text((60, 500), detail, font=F_H2, fill=TEXT)
        frames += [im] * 9

    im = base_frame(
        "4 · Patch Life Report",
        "The report keeps raw survival and maintenance evidence visible instead of pretending to predict reality perfectly.",
    )
    d = ImageDraw.Draw(im)
    rounded(d, (60, 260, 1140, 585), 26, fill=PANEL, outline=PURPLE, width=2)
    d.text((95, 292), "Temporal Survival Curve", font=F_H2, fill=TEXT)
    bar(d, 95, 355, 0.50, RED, "Patch A")
    bar(d, 95, 435, 1.00, GREEN, "Patch B")
    d.text((95, 525), "Question: two patches pass now — which one leaves more future options?", font=F_BODY, fill=MUTED)
    frames += [im] * 18

    im = base_frame(
        "Try the real system",
        "Counterfactual Forge → Causal Genome → ChronoForge",
    )
    d = ImageDraw.Draw(im)
    rounded(d, (60, 270, 1140, 520), 28, fill=PANEL, outline=CYAN, width=2)
    d.text((100, 310), "github.com/LLR6/LR-agent", font=font(38, True), fill=TEXT)
    d.text((100, 380), "5-minute demo · research notes · reproducible tests", font=F_H2, fill=PURPLE)
    d.text((100, 445), "Counterexamples welcome.", font=F_H2, fill=PINK)
    frames += [im] * 18

    return frames


def main() -> None:
    out = Path("docs/media/chronoforge-showcase.gif")
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = make_frames()
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=90,
        loop=0,
        optimize=True,
    )
    print(out)


if __name__ == "__main__":
    main()
