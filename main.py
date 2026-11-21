#!/usr/bin/env python3
"""Sum up Friday 20 November 2026's world news in one image.

Pure Python 3.13 standard library: draws a newspaper front page with a
hand-built 5x7 pixel font and writes a deterministic PNG (zlib + CRC).
No network, no randomness, no timestamps: two runs write identical bytes.

Stories drawn (all verified 20 Nov 2026 from reputable outlets):
  1. KYIV - Russia fires 400+ drones and 110+ missiles; three Kyiv
     bridges hit; missiles and a drone fall in Poland (BBC / Reuters / AP).
  2. MARKETS - Nasdaq -5.3%, S&P 500 -3.7% in an AI sell-off; Nvidia
     -14% after Reuters reported an SEC accounting probe (Reuters).
  3. RIYADH - Houthi missile hits Riyadh's PIF Tower, blowing out
     windows; no injuries reported (multiple 20 Nov round-ups).
  4. THE HAGUE - Myanmar rejects the ICJ genocide ruling on Friday;
     the court found Myanmar committed genocide against the Rohingya,
     the first state ever held responsible (Reuters / CNN / WSJ).
"""
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- font: 5x7
# Each glyph: 7 rows of 5 bits, written as strings of 0/1.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
}


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(px, x, y, text, color, scale=2):
    """Draw uppercase pixel text; unknown chars become a space."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            px[cx + col * scale + dx, y + row * scale + dy] = color
        cx += 6 * scale
    return cx


def draw_text_centered(px, cx, y, text, color, scale=2):
    draw_text(px, cx - text_width(text, scale) // 2, y, text, color, scale)

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.buf = bytearray(bg * (w * h))

    def __setitem__(self, pos, color):
        x, y = pos
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = color

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self[xx, yy] = color

    def hline(self, x, y, w, color, t=1):
        self.rect(x, y, w, t, color)

    def vline(self, x, y, h, color, t=1):
        self.rect(x, y, t, h, color)

    def circle(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self[xx, yy] = color

    def disc_ring(self, cx, cy, r, color, t=3):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - t) ** 2 <= d <= r * r:
                    self[xx, yy] = color

    def burst(self, cx, cy, r, color):
        """Starburst: filled disc plus 8 spikes."""
        self.circle(cx, cy, r // 2, color)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (-1, -1), (1, -1), (-1, 1)):
            for k in range(1, r + 1):
                for t in (-1, 0, 1):
                    if dx == 0:
                        self[cx + t, cy + dy * k] = color
                    elif dy == 0:
                        self[cx + dx * k, cy + t] = color
                    else:
                        self[cx + dx * k, cy + dy * k] = color

    def diag(self, x0, y0, x1, y1, color, t=3):
        """Thick straight line via steps."""
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for k in range(steps + 1):
            x = x0 + (x1 - x0) * k // steps
            y = y0 + (y1 - y0) * k // steps
            for dy in range(-t // 2, t // 2 + 1):
                for dx in range(-t // 2, t // 2 + 1):
                    self[x + dx, y + dy] = color


def chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path, canvas):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.buf[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---------------------------------------------------------------- palette
PAPER = bytes((247, 243, 232))
INK = bytes((20, 20, 20))
NAVY = bytes((18, 40, 75))
RED = bytes((179, 38, 30))
ORANGE = bytes((232, 106, 28))
GOLD = bytes((212, 160, 32))
SKY = bytes((43, 94, 167))
LIGHT = bytes((214, 228, 244))
GREY = bytes((120, 120, 120))
WHITE = bytes((255, 255, 255))
DARK = bytes((30, 30, 40))


def panel(c, x, y, w, h, accent, kicker, scene):
    c.rect(x, y, w, h, WHITE)
    c.rect(x, y, w, 4, accent)
    c.rect(x, y, w, 46, accent)
    draw_text(c, x + 16, y + 14, kicker, WHITE, 2)
    scene(c, x + 16, y + 46, w - 32, 168)
    c.rect(x, y + 46, w, 2, INK)
    c.rect(x, y + 214, w, 2, INK)


def headline(c, x, y, lines, color=INK):
    for i, line in enumerate(lines):
        draw_text(c, x, y + i * 26, line, color, 3)


def subtext(c, x, y, lines, color=INK):
    for i, line in enumerate(lines):
        draw_text(c, x, y + i * 20, line, color, 2)


# ---------------------------------------------------------------- scenes
def scene_kyiv(c, x, y, w, h):
    c.rect(x, y, w, h, bytes((38, 52, 84)))          # night sky
    c.rect(x, y + h - 42, w, 42, bytes((70, 110, 150)))  # river
    c.rect(x, y + h - 46, w, 4, INK)                # far bank
    # bridge deck + towers
    c.rect(x, y + h - 78, w, 6, WHITE)
    for bx in (x + 60, x + w // 2 - 4, x + w - 76):
        c.rect(bx, y + h - 128, 8, 56, WHITE)
    c.diag(x + 60, y + h - 128, x + w // 2, y + h - 78, WHITE, 3)
    c.diag(x + w // 2, y + h - 128, x + w - 68, y + h - 78, WHITE, 3)
    # explosions on the bridge
    c.burst(x + 110, y + h - 92, 26, ORANGE)
    c.burst(x + 112, y + h - 94, 12, GOLD)
    c.burst(x + w - 120, y + h - 96, 22, ORANGE)
    # incoming missiles
    c.diag(x + 40, y + 12, x + 100, y + 52, GOLD, 4)
    c.diag(x + w - 60, y + 8, x + w - 120, y + 48, GOLD, 4)


def scene_markets(c, x, y, w, h):
    c.rect(x, y, w, h, WHITE)
    for gy in range(y + 24, y + h - 8, 28):
        c.hline(x, gy, w, bytes((225, 225, 225)), 1)
    # falling bars
    tops = (30, 48, 66, 92, 118)
    bw = w // 6
    for i, t in enumerate(tops):
        c.rect(x + 20 + i * bw, y + t, bw - 14, h - t - 12, bytes((150, 150, 150)))
    # steep red fall line + arrowhead
    c.diag(x + 24, y + 26, x + w - 30, y + h - 22, RED, 6)
    c.diag(x + w - 30, y + h - 22, x + w - 62, y + h - 26, RED, 5)
    c.diag(x + w - 30, y + h - 22, x + w - 34, y + h - 54, RED, 5)
    draw_text(c, x + w - 108, y + 6, "-5.3%", RED, 3)


def scene_riyadh(c, x, y, w, h):
    c.rect(x, y, w, h, bytes((16, 24, 48)))          # night sky
    c.circle(x + 60, y + 34, 14, bytes((240, 240, 210)))  # moon
    # PIF tower: tall slab, tapering top
    tx = x + w // 2 - 34
    c.rect(tx, y + 30, 68, h - 30, bytes((70, 90, 130)))
    c.rect(tx + 8, y + 14, 52, 18, bytes((70, 90, 130)))
    for wy in range(y + 44, y + h - 14, 16):
        for wx in range(tx + 10, tx + 58, 14):
            c.rect(wx, wy, 7, 8, GOLD)
    # blast at the tower top
    c.burst(tx + 34, y + 30, 26, ORANGE)
    c.burst(tx + 34, y + 30, 12, GOLD)
    c.diag(x + w - 30, y + 10, tx + 60, y + 34, GOLD, 4)


def scene_hague(c, x, y, w, h):
    c.rect(x, y, w, h, LIGHT)
    # courthouse: pediment + columns
    c.rect(x + 40, y + 30, w - 80, 14, NAVY)
    for i in range(5):
        cx = x + 70 + i * ((w - 140) // 4)
        c.rect(cx, y + 44, 14, 74, WHITE)
        c.rect(cx - 4, y + 40, 22, 6, WHITE)
    c.rect(x + 40, y + 118, w - 80, 10, NAVY)
    # gavel resting on the steps
    c.rect(x + w // 2 - 66, y + 132, 52, 16, bytes((120, 72, 32)))
    c.diag(x + w // 2 - 14, y + 140, x + w // 2 + 58, y + 140, bytes((90, 54, 24)), 6)


# ---------------------------------------------------------------- layout
def build():
    c = Canvas(W, H, PAPER)
    # masthead
    c.rect(0, 0, W, 128, NAVY)
    draw_text_centered(c, W // 2, 14, "THE WORLD IN ONE DAY", GOLD, 2)
    draw_text_centered(c, W // 2, 44, "FRIDAY 20 NOVEMBER 2026", WHITE, 4)
    c.hline(60, 102, W - 120, GOLD, 3)
    draw_text_centered(c, W // 2, 110, "FOUR STORIES THAT DEFINED THE DAY", WHITE, 2)

    px, py, pw, ph = 16, 144, 488, 402
    gx, gy = 16, 16
    # 1 - Kyiv
    panel(c, px, py, pw, ph, RED, "1 - KYIV - WAR", scene_kyiv)
    headline(c, px + 16, py + 232, ["MISSILES HIT 3", "KYIV BRIDGES"])
    subtext(c, px + 16, py + 292, ["400+ DRONES, 110+ MISSILES",
                                   "8 KILLED; DEBRIS FALLS",
                                   "IN NATO POLAND"], INK)
    # 2 - Markets
    panel(c, px + pw + gx, py, pw, ph, DARK, "2 - MARKETS - MONEY", scene_markets)
    headline(c, px + pw + gx + 16, py + 232, ["STOCKS PLUNGE AS", "AI SELLS OFF"])
    subtext(c, px + pw + gx + 16, py + 292, ["NASDAQ -5.3%, S&P -3.7%",
                                             "NVIDIA -14% ON SEC",
                                             "PROBE REPORT"], INK)
    # 3 - Riyadh
    panel(c, px, py + ph + gy, pw, ph, ORANGE, "3 - RIYADH - MIDDLE EAST", scene_riyadh)
    headline(c, px + 16, py + ph + gy + 232, ["MISSILE HITS RIYADH", "TALLEST TOWER"])
    subtext(c, px + 16, py + ph + gy + 292, ["HOUTHI STRIKE BLOWS OUT",
                                             "WINDOWS ON 7 FLOORS;",
                                             "NO INJURIES REPORTED"], INK)
    # 4 - The Hague
    panel(c, px + pw + gx, py + ph + gy, pw, ph, SKY, "4 - THE HAGUE - JUSTICE", scene_hague)
    headline(c, px + pw + gx + 16, py + ph + gy + 232, ["MYANMAR REJECTS", "GENOCIDE RULING"])
    subtext(c, px + pw + gx + 16, py + ph + gy + 292, ["ICJ: MYANMAR COMMITTED",
                                                       "GENOCIDE VS ROHINGYA;",
                                                       "A FIRST FOR A STATE"], INK)
    # footer
    c.rect(0, 978, W, 46, NAVY)
    draw_text_centered(c, W // 2, 994, "SOURCES: BBC - REUTERS - AP - CNN - WSJ - 20 NOV 2026", WHITE, 2)
    return c


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or os.environ.get("OUTPUT_DIR")
    if outdir:
        path = os.path.join(outdir, "entry.png")
    else:
        path = "/output/entry.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_png(path, build())


if __name__ == "__main__":
    main()
