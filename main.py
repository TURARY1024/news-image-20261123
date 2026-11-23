#!/usr/bin/env python3
"""Render one 1024x1024 poster that sums up Monday 23 November 2026's world news.

Pure standard library: reads stories.json, draws with a hand-built 5x7 bitmap
font, and writes a deterministic PNG (zlib, no timestamps) to
$MAKEFUN_OUTPUT_DIR/entry.png (default: out/entry.png).

Layout, top to bottom:
  masthead  -> title + date + mood
  lead      -> the day's three biggest stories, numbered
  brief     -> twelve more headlines in two columns
  timeline  -> UTC hours of the day
  footer    -> story count, sourcing and date-audit note
"""

import json
import os
import struct
import sys
import zlib

W, H = 1024, 1024

NAVY = (13, 27, 44)
PANEL = (19, 37, 59)
PANEL2 = (24, 46, 72)
CREAM = (242, 234, 216)
GOLD = (232, 180, 74)
RED = (228, 87, 46)
TEAL = (42, 157, 143)
SKY = (96, 165, 250)
MUTED = (148, 163, 184)
LINE = (58, 79, 104)
WHITE = (255, 255, 255)

# 5x7 bitmap font. Each glyph is 7 rows of 5 bits, '1' = on, '0' = off.
# Uppercase letters, digits and the punctuation this poster needs.
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
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
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
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "%": ("10001", "10010", "00010", "00100", "01000", "01001", "10001"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "10101", "00000", "00000", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    ">": ("10000", "01000", "00100", "00010", "00100", "01000", "10000"),
    "<": ("00001", "00010", "00100", "01000", "00100", "00010", "00001"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
}


class Canvas:
    """A flat RGB pixel buffer with tiny drawing helpers."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def hline(self, x, y, length, color, thick=1):
        self.rect(x, y, length, thick, color)

    def vline(self, x, y, length, color, thick=1):
        self.rect(x, y, thick, length, color)

    def circle(self, cx, cy, r, color, thick=2):
        # Midpoint circle outline, drawn thick by stamping small squares.
        x, y, d = 0, r, 1 - r
        while x <= y:
            for px, py in ((cx + x, cy + y), (cx - x, cy + y), (cx + x, cy - y),
                           (cx - x, cy - y), (cx + y, cy + x), (cx - y, cy + x),
                           (cx + y, cy - x), (cx - y, cy - x)):
                self.rect(px - thick // 2, py - thick // 2, thick, thick, color)
            x += 1
            if d < 0:
                d += 2 * x + 1
            else:
                y -= 1
                d += 2 * (x - y) + 1

    def text_width(self, text, scale):
        return len(text) * 6 * scale - scale

    def draw_text(self, text, x, y, scale, color):
        """Draw uppercase text; unknown glyphs become a blank cell."""
        cx = x
        for ch in text.upper():
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx

    def wrap(self, text, max_chars):
        """Greedy word wrap to lines of at most max_chars characters."""
        words, lines, cur = text.split(), [], ""
        for word in words:
            if cur and len(cur) + 1 + len(word) > max_chars:
                lines.append(cur)
                cur = word
            else:
                cur = (cur + " " + word).strip()
        if cur:
            lines.append(cur)
        return lines


def png_bytes(canvas):
    """Encode the canvas as a PNG (filter 0, zlib level 9). Deterministic."""

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * stride:(y + 1) * stride]
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def load_stories(path):
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    stories = sorted(data["stories"], key=lambda s: s["n"])
    assert len(stories) == 50, f"expected 50 stories, got {len(stories)}"
    return data, stories


def draw_masthead(cv, data):
    cv.rect(0, 0, W, 8, RED)
    cv.draw_text("MAKE.FUN NEWS IMAGE", 48, 30, 2, GOLD)
    cv.draw_text("MOOD: " + data["mood"].upper(), 700, 30, 2, MUTED)
    cv.draw_text("THE WORLD IN", 48, 62, 4, CREAM)
    cv.draw_text("ONE IMAGE", 48, 94, 4, CREAM)
    cv.draw_text("MONDAY 23 NOVEMBER 2026", 560, 66, 3, GOLD)
    cv.draw_text("50 STORIES", 560, 100, 3, CREAM)
    cv.hline(48, 140, W - 96, RED, 4)


def draw_lead(cv, stories):
    cv.draw_text("TOP THREE STORIES OF THE DAY", 48, 162, 2, TEAL)
    y = 196
    colors = (RED, GOLD, SKY)
    for i, story in enumerate(stories[:3]):
        cv.draw_text(f"0{i + 1}", 48, y, 4, colors[i])
        head = cv.wrap(story["headline"], 30)
        fy = y
        for line in head:
            cv.draw_text(line, 150, fy, 3, CREAM)
            fy += 26
        fact = cv.wrap(story["fact"], 62)
        for line in fact:
            cv.draw_text(line, 150, fy, 2, MUTED)
            fy += 18
        y = fy + 16
        if i < 2:
            cv.hline(48, y - 8, W - 96, LINE, 1)


def draw_brief(cv, stories):
    cv.draw_text("THE DAY IN BRIEF", 48, 480, 2, TEAL)
    cv.hline(48, 504, W - 96, LINE, 1)
    brief = stories[3:15]
    col_x = (48, 528)
    for idx, story in enumerate(brief):
        col = idx // 6
        row = idx % 6
        x = col_x[col]
        y = 522 + row * 62
        tag = f"{story['n']:02d}"
        cv.draw_text(tag, x, y, 2, GOLD)
        lines = cv.wrap(story["headline"], 34)
        ly = y
        for line in lines[:2]:
            cv.draw_text(line, x + 44, ly, 2, CREAM)
            ly += 18
        cv.draw_text(story["cat"], x + 44, ly, 1, MUTED)


def draw_timeline(cv):
    y = 912
    cv.draw_text("THE DAY, HOUR BY HOUR  (UTC)", 48, y, 2, TEAL)
    cv.hline(48, y + 30, W - 96, LINE, 2)
    marks = [("00", 48), ("04", 208), ("08", 368), ("12", 528),
             ("16", 688), ("20", 848), ("24", 968)]
    for label, x in marks:
        cv.vline(x, y + 30, 10, GOLD, 3)
        cv.draw_text(label, x - 12, y + 46, 2, MUTED)


def draw_footer(cv):
    cv.rect(0, 968, W, 56, PANEL2)
    cv.draw_text("50 STORIES - EVERY ONE SOURCED - DATE-AUDITED", 48, 984, 2, CREAM)
    cv.draw_text("FULL LIST + SOURCES IN THIS REPO", 48, 1006, 2, MUTED)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data, stories = load_stories(os.path.join(here, "stories.json"))
    cv = Canvas(W, H, NAVY)
    # faint vertical bands for depth
    for bx in range(0, W, 128):
        cv.rect(bx, 0, 64, H, (15, 30, 48))
    draw_masthead(cv, data)
    draw_lead(cv, stories)
    draw_brief(cv, stories)
    draw_timeline(cv)
    draw_footer(cv)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", os.path.join(here, "out"))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(png_bytes(cv))
    print(f"wrote {path} ({os.path.getsize(path)} bytes, {W}x{H})")


if __name__ == "__main__":
    sys.exit(main())
