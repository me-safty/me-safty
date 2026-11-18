# /// script
# requires-python = ">=3.10"
# dependencies = ["fonttools", "uharfbuzz"]
# ///
"""Builds assets/card-*.svg. Run: uv run scripts/build_card.py

GitHub shows README SVGs as images, which cannot load web fonts, so every
string is drawn as outlines of the portfolio's two typefaces.
"""
from pathlib import Path
from urllib.request import urlretrieve

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / ".fonts"
OUT = ROOT / "assets"

FONT_URLS = {
    "InstrumentSans-VF.ttf": "https://github.com/google/fonts/raw/main/ofl/instrumentsans/InstrumentSans%5Bwdth%2Cwght%5D.ttf",
    "JetBrainsMono-Regular.ttf": "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Regular.ttf",
}

NAME = "[ MOHAMED SAFTY ]"
PLACE = "MENOFIA, EGYPT · REMOTE"
HEAD = "Senior Product Engineer"
LEDE = (
    "I work next to founders. I find the product gap, decide how it should "
    "work, build it and get it through App Store review."
)
STATS = [
    ("10×", "merged output after I built the AI-agent delivery platform"),
    ("2", "apps live on the App Store and Google Play"),
    ("4+", "years shipping TypeScript on web, mobile and backend"),
    ("5.0", "Upwork rating, 100% Job Success across 11 jobs"),
]

THEMES = {
    "dark": dict(bg="#080808", fg="#f4f4f1", soft="#c6c6c2", dim="#8c8c88", line="#ffffff", line_op=0.1),
    "light": dict(bg="#f6f6f3", fg="#121211", soft="#3b3b38", dim="#6e6e69", line="#000000", line_op=0.12),
}
LAYOUTS = {
    "": dict(w=800, pad=32, label=13, head=46, lede=18, lede_w=620, cols=4, gap=24, cap=14),
    "-mobile": dict(w=400, pad=22, label=11, head=36, lede=16, lede_w=356, cols=2, gap=20, cap=13.5),
}

CELL = 6
PANEL_COLS, PANEL_ROWS = 23, 9
GLYPHS = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "×": ["00000", "10001", "01010", "00100", "01010", "10001", "00000"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    ".": ["00", "00", "00", "00", "00", "11", "11"],
}


def num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


class Face:
    def __init__(self, path):
        self.tt = TTFont(path)
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upm = self.tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))

    def shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf)
        return [(self.order[i.codepoint], p.x_advance, p.x_offset, p.y_offset)
                for i, p in zip(buf.glyph_infos, buf.glyph_positions)]

    def width(self, text, size, tracking=0):
        shaped = self.shape(text)
        return sum(g[1] for g in shaped) * size / self.upm + tracking * size * len(shaped)

    def path(self, text, x, y, size, tracking=0):
        k = size / self.upm
        pen = SVGPathPen(self.glyphs, ntos=num)
        for name, advance, dx, dy in self.shape(text):
            self.glyphs[name].draw(TransformPen(pen, (k, 0, 0, -k, x + dx * k, y - dy * k)))
            x += advance * k + tracking * size
        return pen.getCommands()

    def wrap(self, text, size, max_width, tracking=0):
        lines, line = [], ""
        for word in text.split():
            trial = f"{line} {word}".strip()
            if line and self.width(trial, size, tracking) > max_width:
                lines.append(line)
                line = word
            else:
                line = trial
        return lines + [line]


def fonts():
    FONTS.mkdir(exist_ok=True)
    for name, url in FONT_URLS.items():
        if not (FONTS / name).exists():
            urlretrieve(url, FONTS / name)
    for weight in (400, 600):
        static = FONTS / f"InstrumentSans-{weight}.ttf"
        if not static.exists():
            vf = TTFont(FONTS / "InstrumentSans-VF.ttf")
            instantiateVariableFont(vf, {"wght": weight, "wdth": 100}).save(static)
    return (Face(FONTS / "InstrumentSans-400.ttf"),
            Face(FONTS / "InstrumentSans-600.ttf"),
            Face(FONTS / "JetBrainsMono-Regular.ttf"))


def panel(text, x, y, fg):
    dot = f'width="{CELL - 1}" height="{CELL - 1}" rx="1"'
    cells, col = [], 1
    for ch in text:
        glyph = GLYPHS[ch]
        for row, bits in enumerate(glyph):
            cells += [f'<rect x="{(col + i) * CELL}" y="{(row + 1) * CELL}" {dot}/>'
                      for i, bit in enumerate(bits) if bit == "1"]
        col += len(glyph[0]) + 1
    return (f'<g transform="translate({num(x)} {num(y)})">'
            f'<rect width="{PANEL_COLS * CELL}" height="{PANEL_ROWS * CELL}" fill="url(#off)"/>'
            f'<g fill="{fg}">{"".join(cells)}</g></g>')


def card(theme, layout, regular, semibold, mono):
    t, L = THEMES[theme], LAYOUTS[layout]
    w, pad = L["w"], L["pad"]
    inner = w - 2 * pad
    out = []

    def text(face, string, x, y, size, fill, tracking=0):
        out.append(f'<path fill="{fill}" d="{face.path(string, x, y, size, tracking)}"/>')

    y = pad + L["label"]
    text(mono, NAME, pad, y, L["label"], t["dim"], 0.04)
    place_x = w - pad - mono.width(PLACE, L["label"], 0.04)
    text(mono, PLACE, place_x, y, L["label"], t["dim"], 0.04)
    out.append(f'<circle cx="{num(place_x - 12)}" cy="{num(y - L["label"] * 0.36)}" r="3" fill="{t["fg"]}">'
               '<animate attributeName="opacity" values="1;.25;1" dur="1.8s" repeatCount="indefinite"/></circle>')

    y += L["head"] * 0.5
    for line in semibold.wrap(HEAD, L["head"], inner, -0.025):
        y += L["head"] * 1.08
        text(semibold, line, pad, y, L["head"], t["fg"], -0.025)

    y += L["lede"] * 0.75
    for line in regular.wrap(LEDE, L["lede"], L["lede_w"]):
        y += L["lede"] * 1.5
        text(regular, line, pad, y, L["lede"], t["soft"])

    y += 30
    out.append(f'<path d="M{pad} {num(y)}H{w - pad}" stroke="{t["line"]}" stroke-opacity="{t["line_op"]}"/>')
    y += 24

    col_w = (inner - L["gap"] * (L["cols"] - 1)) / L["cols"]
    for start in range(0, len(STATS), L["cols"]):
        row_bottom = y
        for i, (value, caption) in enumerate(STATS[start:start + L["cols"]]):
            x = pad + i * (col_w + L["gap"])
            out.append(panel(value, x, y, t["fg"]))
            cy = y + PANEL_ROWS * CELL + L["cap"] * 0.5
            for line in regular.wrap(caption, L["cap"], col_w):
                cy += L["cap"] * 1.4
                text(regular, line, x, cy, L["cap"], t["dim"])
            row_bottom = max(row_bottom, cy)
        y = row_bottom + 26
    h = round(y - 26 + pad)

    label = f"Mohamed Safty, {HEAD}. {LEDE} " + " ".join(f"{v} {c}." for v, c in STATS)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">'
        f'<title>{label}</title>'
        f'<defs><pattern id="off" width="{CELL}" height="{CELL}" patternUnits="userSpaceOnUse">'
        f'<rect width="{CELL - 1}" height="{CELL - 1}" rx="1" fill="{t["fg"]}" opacity=".1"/></pattern></defs>'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="{t["bg"]}" stroke="{t["line"]}" stroke-opacity="{t["line_op"]}"/>'
        f'{"".join(out)}</svg>\n'
    )


if __name__ == "__main__":
    faces = fonts()
    OUT.mkdir(exist_ok=True)
    for theme in THEMES:
        for layout in LAYOUTS:
            target = OUT / f"card-{theme}{layout}.svg"
            target.write_text(card(theme, layout, *faces))
            print(target.relative_to(ROOT), f"{target.stat().st_size / 1024:.1f} KB")
