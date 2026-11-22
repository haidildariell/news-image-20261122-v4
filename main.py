#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - Sunday 22 November 2026.

A program that draws one newspaper-style image summing up the world news
of Sunday 22 November 2026. Pure Python standard library only: it builds
the picture pixel by pixel in memory (own 5x7 bitmap font, own polygon
world map, own PNG encoder) and writes /output/entry.png.

Deterministic: no network, no clock, no randomness; two runs write the
same bytes. 1024x1024, well under 1 MiB.

News researched 23 Nov 2026 from Reuters, AP, AFP, BBC, Al Jazeera,
UN News, Formula 1, Cricbuzz, China Daily and official statements.
Every numbered story happened, or was first reported, on 22 Nov 2026
(UTC). Stories from earlier days are named and excluded in the
DATE CHECK box. Certainty tags: CONFIRMED = 2+ outlets or official;
REPORTED = one source; CLAIM = one party's claim, unverified.
"""

import math
import os
import struct
import sys
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (250, 247, 238)      # warm newsprint
INK = (24, 24, 22)           # near-black text
INK_SOFT = (74, 72, 66)
RED = (178, 34, 28)          # masthead red
RED_DK = (128, 20, 16)
BLUE = (28, 68, 128)         # section blue
GOLD = (184, 134, 22)
TEAL = (16, 110, 104)
GREEN = (46, 110, 52)
GREY = (210, 206, 196)
GREY_DK = (150, 146, 134)
SEA = (186, 214, 228)        # map ocean
LAND = (222, 206, 170)       # map land
LAND_LINE = (150, 132, 92)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TAG_CONF = (34, 110, 52)     # confirmed green
TAG_CLAIM = (178, 90, 10)    # claim amber
TAG_REP = (28, 68, 128)      # reported blue
TAG_PEND = (110, 110, 110)   # pending grey

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def hline(self, x, y, w, c):
        self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.rect(x, y, 1, h, c)

    def line(self, x0, y0, x1, y1, c):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d <= r * r:
                        self.set(xx, yy, c)
                else:
                    if r * r - 2 * r <= d <= r * r:
                        self.set(xx, yy, c)

    def poly(self, pts, c):
        """Fill a polygon given as [(x, y), ...] (scanline fill)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    x = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
                    xs.append(x)
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(math.ceil(xs[k])), int(xs[k + 1]) + 1):
                    self.set(x, y, c)

    def polyline(self, pts, c, close=False):
        n = len(pts)
        for i in range(n - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c)
        if close and n > 2:
            self.line(pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], c)


def write_png(cv, path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows, each a 5-bit number; bit 4 is the leftmost pixel.
FONT = {
    "A": (14, 17, 17, 31, 17, 17, 17), "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14), "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31), "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15), "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14), "J": (7, 2, 2, 2, 2, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17), "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17), "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14), "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13), "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30), "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14), "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 21, 10), "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4), "Z": (31, 1, 2, 4, 8, 16, 31),
    "a": (0, 0, 14, 1, 15, 17, 15), "b": (16, 16, 30, 17, 17, 17, 30),
    "c": (0, 0, 14, 17, 16, 17, 14), "d": (1, 1, 15, 17, 17, 17, 15),
    "e": (0, 0, 14, 17, 31, 16, 14), "f": (6, 9, 8, 30, 8, 8, 8),
    "g": (0, 15, 17, 17, 15, 1, 14), "h": (16, 16, 30, 17, 17, 17, 17),
    "i": (4, 0, 12, 4, 4, 4, 14), "j": (2, 0, 6, 2, 2, 18, 12),
    "k": (16, 16, 18, 20, 24, 20, 18), "l": (12, 4, 4, 4, 4, 4, 14),
    "m": (0, 0, 26, 21, 21, 21, 21), "n": (0, 0, 30, 17, 17, 17, 17),
    "o": (0, 0, 14, 17, 17, 17, 14), "p": (0, 30, 17, 17, 30, 16, 16),
    "q": (0, 15, 17, 17, 15, 1, 1), "r": (0, 0, 22, 25, 16, 16, 16),
    "s": (0, 0, 15, 16, 14, 1, 30), "t": (8, 8, 30, 8, 8, 8, 6),
    "u": (0, 0, 17, 17, 17, 19, 13), "v": (0, 0, 17, 17, 17, 10, 4),
    "w": (0, 0, 17, 21, 21, 21, 10), "x": (0, 0, 17, 10, 4, 10, 17),
    "y": (0, 0, 17, 17, 15, 1, 14), "z": (0, 0, 31, 2, 4, 8, 31),
    "0": (14, 17, 19, 21, 25, 17, 14), "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 2, 4, 8, 31), "3": (31, 2, 4, 2, 1, 17, 14),
    "4": (2, 6, 10, 18, 31, 2, 2), "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14), "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14), "9": (14, 17, 17, 15, 1, 2, 12),
    " ": (0, 0, 0, 0, 0, 0, 0), ".": (0, 0, 0, 0, 0, 12, 12),
    ",": (0, 0, 0, 0, 12, 4, 8), ":": (0, 12, 12, 0, 12, 12, 0),
    ";": (0, 12, 12, 0, 12, 4, 8), "!": (4, 4, 4, 4, 4, 0, 4),
    "?": (14, 17, 1, 2, 4, 0, 4), "'": (4, 4, 8, 0, 0, 0, 0),
    '"': (10, 10, 10, 0, 0, 0, 0), "(": (2, 4, 8, 8, 8, 4, 2),
    ")": (8, 4, 2, 2, 2, 4, 8), "-": (0, 0, 0, 14, 0, 0, 0),
    "\u2013": (0, 0, 0, 14, 0, 0, 0), "\u2014": (0, 0, 0, 31, 0, 0, 0),
    "/": (1, 2, 2, 4, 8, 8, 16), "%": (25, 26, 2, 4, 8, 11, 19),
    "+": (0, 4, 4, 14, 4, 4, 0), "=": (0, 0, 31, 0, 31, 0, 0),
    "&": (12, 18, 20, 8, 21, 18, 13), "$": (4, 15, 20, 14, 5, 30, 4),
    "#": (10, 10, 31, 10, 10, 31, 10), "*": (0, 21, 14, 31, 14, 21, 0),
    "\u2022": (0, 0, 12, 12, 0, 0, 0), "\u00b0": (12, 18, 18, 12, 0, 0, 0),
    "\u00d7": (0, 17, 10, 4, 10, 17, 0), "[": (14, 8, 8, 8, 8, 8, 14),
    "]": (14, 2, 2, 2, 2, 2, 14), "_": (0, 0, 0, 0, 0, 0, 31),
    "<": (2, 4, 8, 16, 8, 4, 2), ">": (8, 4, 2, 1, 2, 4, 8),
    "@": (14, 17, 23, 21, 22, 16, 14), "~": (0, 0, 9, 22, 0, 0, 0),
}
BLANK = (0, 0, 0, 0, 0, 0, 0)


def text_w(s, scale):
    return len(s) * 6 * scale


def draw_text(cv, x, y, s, scale, color, bold=False):
    """Draw text; returns width in pixels. Unknown chars render blank."""
    cx = x
    for ch in s:
        g = FONT.get(ch, BLANK)
        for row in range(7):
            bits = g[row]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    cv.rect(cx + col * scale, y + row * scale, scale, scale, color)
                    if bold:
                        cv.rect(cx + col * scale + 1, y + row * scale,
                                scale, scale, color)
        cx += 6 * scale
    return cx - x


def text_h(scale):
    return 7 * scale


def wrap(s, max_chars):
    """Greedy word wrap to at most max_chars per line."""
    words = s.split(" ")
    lines = []
    cur = ""
    for w in words:
        if cur == "":
            cur = w
        elif len(cur) + 1 + len(w) <= max_chars:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, s, scale, color, max_chars, line_h=None, bold=False):
    lh = line_h if line_h is not None else 7 * scale + 2
    for ln in wrap(s, max_chars):
        draw_text(cv, x, y, ln, scale, color, bold=bold)
        y += lh
    return y


def center_text(cv, cx, y, s, scale, color, bold=False):
    w = text_w(s, scale)
    draw_text(cv, cx - w // 2, y, s, scale, color, bold=bold)
    return w

# ---------------------------------------------------------------- tags
TAG_COLORS = {"CONFIRMED": TAG_CONF, "CLAIM": TAG_CLAIM,
              "REPORTED": TAG_REP, "PENDING": TAG_PEND}


def draw_tag(cv, x, y, tag):
    """Small certainty chip; returns width used."""
    c = TAG_COLORS.get(tag, TAG_PEND)
    w = text_w(tag, 1) + 8
    cv.rect(x, y, w, 11, c)
    draw_text(cv, x + 4, y + 2, tag, 1, WHITE, bold=True)
    return w


# ---------------------------------------------------------------- icons
def icon_globe(cv, x, y, s, c):
    cv.circle(x + s // 2, y + s // 2, s // 2, c, fill=False)
    cv.hline(x, y + s // 2, s, c)
    cv.vline(x + s // 2, y, s, c)
    cv.circle(x + s // 2, y + s // 2, s // 4, c, fill=False)


def icon_flame(cv, x, y, s, c):
    pts = [(x + s // 2, y), (x + s * 3 // 4, y + s // 3),
           (x + s, y + s * 2 // 3), (x + s * 3 // 4, y + s),
           (x + s // 4, y + s), (x, y + s * 2 // 3),
           (x + s // 4, y + s // 3)]
    cv.poly(pts, c)
    cv.circle(x + s // 2, y + s * 2 // 3, s // 6, PAPER)


def icon_ballot(cv, x, y, s, c):
    cv.rect(x + s // 6, y + s // 3, s * 2 // 3, s // 2, c)
    cv.rect(x + s // 4, y + s // 5, s // 2, s // 6, PAPER)
    cv.rect(x + s // 4, y + s // 5, s // 2, 2, c)
    cv.line(x + s // 3, y + s * 2 // 3, x + s // 2, y + s * 5 // 6, WHITE)
    cv.line(x + s // 2, y + s * 5 // 6, x + s * 5 // 6, y + s // 2, WHITE)


def icon_ball(cv, x, y, s, c):
    cv.circle(x + s // 2, y + s // 2, s // 2, c, fill=False)
    cv.line(x + s // 2, y, x + s // 2, y + s, c)
    cv.line(x, y + s // 2, x + s, y + s // 2, c)


def icon_trophy(cv, x, y, s, c):
    cv.rect(x + s // 3, y + s // 6, s // 3, s // 2, c)
    cv.rect(x + s // 6, y + s // 6, s // 6, s // 4, c)
    cv.rect(x + s * 5 // 6 - s // 6, y + s // 6, s // 6, s // 4, c)
    cv.rect(x + s // 2 - 1, y + s * 2 // 3, 2, s // 6, c)
    cv.rect(x + s // 3, y + s * 5 // 6, s // 3, 2, c)


def icon_radar(cv, x, y, s, c):
    cv.circle(x + s // 2, y + s // 2, s // 2, c, fill=False)
    cv.circle(x + s // 2, y + s // 2, s // 4, c, fill=False)
    cv.line(x + s // 2, y + s // 2, x + s, y + s // 4, c)
    cv.circle(x + s // 2, y + s // 2, 2, c)


def icon_ship(cv, x, y, s, c):
    cv.line(x + s // 2, y, x + s // 2, y + s // 2, c)
    cv.line(x + s // 2, y, x + s * 3 // 4, y + s // 2, c)
    pts = [(x, y + s // 2), (x + s, y + s // 2), (x + s * 5 // 6, y + s),
           (x + s // 6, y + s)]
    cv.poly(pts, c)


def icon_bolt(cv, x, y, s, c):
    pts = [(x + s * 2 // 3, y), (x + s // 3, y + s // 2),
           (x + s // 2, y + s // 2), (x + s // 3, y + s),
           (x + s * 2 // 3, y + s // 2), (x + s // 2, y + s // 2)]
    cv.poly(pts, c)


def icon_building(cv, x, y, s, c):
    cv.rect(x + s // 6, y + s // 4, s * 2 // 3, s * 3 // 4, c)
    for r in range(3):
        for col in range(2):
            cv.rect(x + s // 4 + col * s // 4, y + s // 3 + r * s // 5,
                    s // 8, s // 8, PAPER)


def icon_droplet(cv, x, y, s, c):
    pts = [(x + s // 2, y), (x + s, y + s * 2 // 3), (x + s // 2, y + s),
           (x, y + s * 2 // 3)]
    cv.poly(pts, c)


def icon_scale(cv, x, y, s, c):
    cv.vline(x + s // 2, y + s // 6, s * 2 // 3, c)
    cv.hline(x + s // 6, y + s // 6, s * 2 // 3, c)
    cv.line(x + s // 6, y + s // 6, x + s // 6, y + s // 2, c)
    cv.line(x + s * 5 // 6, y + s // 6, x + s * 5 // 6, y + s // 2, c)
    cv.hline(x + s // 6 - 3, y + s // 2, 7, c)
    cv.hline(x + s * 5 // 6 - 3, y + s // 2, 7, c)
    cv.hline(x + s // 4, y + s * 5 // 6, s // 2, c)


def icon_flag(cv, x, y, s, c):
    cv.vline(x + s // 4, y, s, c)
    pts = [(x + s // 4, y), (x + s, y + s // 6), (x + s // 4, y + s // 3)]
    cv.poly(pts, c)


def icon_star(cv, x, y, s, c):
    pts = [(x + s // 2, y), (x + s * 3 // 5, y + s // 3),
           (x + s, y + s // 3), (x + s * 2 // 3, y + s * 3 // 5),
           (x + s * 4 // 5, y + s), (x + s // 2, y + s * 3 // 4),
           (x + s // 5, y + s), (x + s // 3, y + s * 3 // 5),
           (x, y + s // 3), (x + s * 2 // 5, y + s // 3)]
    cv.poly(pts, c)


def icon_mic(cv, x, y, s, c):
    cv.rect(x + s // 3, y, s // 3, s // 2, c)
    cv.hline(x + s // 4, y + s * 2 // 3, s // 2, c)
    cv.vline(x + s // 2, y + s * 2 // 3, s // 4, c)


def icon_plane(cv, x, y, s, c):
    pts = [(x + s // 2, y), (x + s * 2 // 3, y + s // 2),
           (x + s, y + s // 2), (x + s * 2 // 3, y + s * 2 // 3),
           (x + s * 3 // 5, y + s), (x + s // 2, y + s * 2 // 3),
           (x + s // 3, y + s), (x + s // 3, y + s * 2 // 3),
           (x, y + s // 2), (x + s // 3, y + s // 2)]
    cv.poly(pts, c)


def icon_chart(cv, x, y, s, c):
    for i, h in enumerate((s // 3, s // 2, s * 2 // 3)):
        cv.rect(x + i * s // 3 + 1, y + s - h, s // 4, h, c)


ICONS = {"globe": icon_globe, "flame": icon_flame, "ballot": icon_ballot,
         "ball": icon_ball, "trophy": icon_trophy, "radar": icon_radar,
         "ship": icon_ship, "bolt": icon_bolt, "building": icon_building,
         "droplet": icon_droplet, "scale": icon_scale, "flag": icon_flag,
         "star": icon_star, "mic": icon_mic, "plane": icon_plane,
         "chart": icon_chart}


# ---------------------------------------------------------------- world map
# Rough continent outlines as (lon, lat) points, equirectangular.
# Deliberately schematic; pins use real coordinates.
CONTINENTS = [
    # North America
    [(-168, 66), (-158, 71), (-140, 70), (-130, 71), (-125, 72),
     (-120, 70), (-110, 68), (-95, 69), (-85, 66), (-80, 73),
     (-70, 62), (-60, 55), (-55, 47), (-60, 45), (-70, 42),
     (-75, 35), (-80, 32), (-81, 26), (-85, 29), (-90, 21),
     (-94, 18), (-97, 16), (-105, 20), (-110, 24), (-115, 28),
     (-120, 34), (-125, 40), (-125, 48), (-130, 55), (-140, 60),
     (-155, 58), (-165, 60)],
    # Greenland
    [(-58, 64), (-52, 60), (-43, 60), (-32, 68), (-25, 70),
     (-20, 76), (-30, 80), (-50, 80), (-60, 76), (-62, 70)],
    # South America
    [(-78, 7), (-72, 11), (-62, 9), (-52, 5), (-50, 0), (-44, -3),
     (-35, -8), (-38, -15), (-40, -22), (-48, -28), (-53, -34),
     (-58, -38), (-62, -41), (-66, -45), (-68, -50), (-70, -54),
     (-73, -50), (-73, -40), (-72, -30), (-70, -18), (-77, -12),
     (-80, -5), (-81, 0), (-79, 5)],
    # Africa
    [(-17, 15), (-16, 20), (-10, 30), (-5, 35), (10, 37), (11, 34),
     (20, 32), (30, 31), (33, 27), (37, 22), (39, 18), (43, 12),
     (51, 11), (48, 5), (41, -2), (40, -10), (36, -18), (33, -26),
     (28, -33), (20, -35), (16, -28), (12, -18), (13, -12), (9, -1),
     (9, 4), (-8, 5), (-13, 8), (-17, 12)],
    # Eurasia
    [(-10, 36), (-9, 43), (-2, 44), (-2, 48), (0, 50), (2, 51),
     (5, 53), (8, 55), (8, 58), (12, 56), (18, 56), (21, 55),
     (24, 59), (28, 60), (30, 62), (32, 66), (35, 68), (45, 68),
     (55, 69), (65, 69), (75, 72), (85, 74), (95, 76), (105, 76),
     (110, 74), (120, 73), (130, 71), (140, 72), (150, 70),
     (160, 69), (170, 67), (178, 65), (170, 60), (162, 56),
     (158, 52), (150, 59), (142, 55), (140, 48), (135, 43),
     (130, 42), (127, 40), (122, 38), (120, 32), (122, 28),
     (115, 22), (108, 18), (105, 10), (100, 8), (98, 14),
     (95, 16), (92, 21), (89, 22), (86, 20), (80, 16),
     (77, 8), (73, 16), (68, 22), (62, 25), (57, 26),
     (52, 27), (50, 29), (48, 30), (44, 29), (40, 30),
     (36, 36), (33, 36), (30, 36), (27, 37), (23, 36),
     (22, 38), (19, 42), (15, 44), (12, 44), (8, 44),
     (3, 42), (-1, 38), (-6, 36)],
    # United Kingdom (small)
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (1, 51), (0, 50)],
    # Japan
    [(130, 31), (132, 34), (136, 35), (139, 38), (141, 41), (144, 43),
     (142, 45), (140, 40), (136, 37), (132, 34)],
    # Australia
    [(113, -22), (114, -30), (115, -34), (118, -35), (124, -33),
     (130, -32), (135, -35), (138, -35), (140, -38), (145, -38),
     (150, -37), (153, -32), (153, -27), (150, -23), (146, -19),
     (142, -11), (137, -12), (135, -15), (132, -12), (130, -13),
     (126, -14), (122, -17), (118, -20)],
    # New Zealand
    [(167, -45), (170, -43), (173, -41), (175, -38), (178, -38),
     (176, -40), (173, -42), (169, -46)],
    # Indonesia (schematic: Sumatra + Java + Borneo + New Guinea)
    [(95, 5), (98, 2), (100, -1), (104, -3), (106, -6), (110, -7),
     (114, -8), (114, -9), (110, -7), (106, -6), (102, -4), (98, 1)],
    [(109, -1), (113, -2), (116, -3), (119, -1), (117, 1), (114, 2),
     (110, 1), (109, -1)],
    [(131, -1), (136, -2), (141, -3), (141, -8), (136, -8), (132, -4)],
]


def project(lon, lat, x0, y0, w, h):
    """Equirectangular: lon -180..180 -> x, lat 75..-60 -> y."""
    x = x0 + (lon + 180.0) / 360.0 * w
    y = y0 + (75.0 - lat) / 135.0 * h
    return int(round(x)), int(round(y))


def draw_map(cv, x0, y0, w, h, pins):
    cv.rect(x0, y0, w, h, SEA)
    # graticule
    for lon in range(-150, 181, 30):
        gx, _ = project(lon, 0, x0, y0, w, h)
        for yy in range(y0, y0 + h, 4):
            cv.set(gx, yy, (160, 195, 212))
    for lat in (-60, -30, 0, 30, 60):
        _, gy = project(0, lat, x0, y0, w, h)
        for xx in range(x0, x0 + w, 4):
            cv.set(xx, gy, (160, 195, 212))
    for poly in CONTINENTS:
        pts = [project(lon, lat, x0, y0, w, h) for lon, lat in poly]
        cv.poly(pts, LAND)
        cv.polyline(pts, LAND_LINE, close=True)
    cv.rect(x0, y0, w, 2, INK)
    cv.rect(x0, y0 + h - 2, w, 2, INK)
    # pins
    for num, lon, lat, dx, dy in pins:
        px, py = project(lon + dx, lat + dy, x0, y0, w, h)
        cv.circle(px, py, 7, RED)
        cv.circle(px, py, 7, WHITE, fill=False)
        s = str(num)
        tw = text_w(s, 1)
        draw_text(cv, px - tw // 2, py - 3, s, 1, WHITE, bold=True)

# ---------------------------------------------------------------- stories
# Fields: num, region, headline, dek, source, tag, lat, lon, icon.
# All 35 happened or were first reported on Sun 22 Nov 2026 (UTC).
# Dek is 1-2 lines at render time; source is the outlet of record.
STORIES = [
    (1, "EUROPE", "COP31 COLLAPSES: NO DEAL",
     "EU, UK and Panama reject the final text: it never names fossil "
     "fuels. Kurum admits no consensus.",
     "Reuters / UN News", "CONFIRMED", 36.90, 30.71, "globe"),
    (2, "EUROPE", "186 DRONES, 161 DOWNED",
     "Russia's overnight raid hits 18 places. A drone flattens a stairwell "
     "in Dymer: 3 killed, 14 trapped.",
     "AP / Ukraine Air Force", "CONFIRMED", 50.45, 30.52, "bolt"),
    (3, "EUROPE", "DENMARK EXPELS RUSSIAN ATTACHE",
     "Copenhagen orders the defence attache out over an alleged plot "
     "targeting a Ukrainian rapper, and tightens Russian visas.",
     "Al Jazeera", "REPORTED", 55.68, 12.57, "flag"),
    (4, "EUROPE", "EU GIVES UKRAINE 1 BILLION MORE",
     "Brussels approves an extra 1 billion euros in military aid as "
     "peace talks stall over security guarantees.",
     "Al Jazeera", "REPORTED", 50.85, 4.35, "scale"),
    (5, "EUROPE", "FRANCE SEEKS UN MEETING",
     "Paris calls for a UN session after Russian strikes hit foreign "
     "missions in Kyiv during the overnight barrage.",
     "Al Jazeera", "REPORTED", 48.86, 2.35, "building"),
    (6, "EUROPE", "ZELENSKYY: TALKS MUST DELIVER",
     "Ukraine's president says the next four-party peace talks must bring "
     "meaningful progress, not another round of words.",
     "Al Jazeera", "REPORTED", 50.45, 30.52, "mic"),
    (7, "EUROPE", "EU BACKS POLAND AFTER AIRSPACE ROW",
     "EU leaders condemn Moscow's airspace violation and promise more "
     "support for Poland after the Warsaw incursion scare.",
     "Al Jazeera", "REPORTED", 52.23, 21.01, "plane"),
    (8, "EUROPE", "MOSCOW: 170 UKRAINIAN DRONES DOWNED",
     "Russia says its defences shot down or jammed 170 Ukrainian drones "
     "overnight, over its regions and the Black Sea.",
     "QNA / AP", "REPORTED", 55.76, 37.62, "radar"),
    (9, "MIDDLE EAST", "IRAN CLAIMS PATRIOT RADAR STRIKES",
     "IRGC says it hit two US Patriot radars at al-Riffa and Awali. "
     "Bahrain: 2 hurt. US denies an F-16 was hit.",
     "Reuters / IRNA", "CLAIM", 26.23, 50.59, "radar"),
    (10, "MIDDLE EAST", "7 KILLED IN GAZA DESPITE CEASEFIRE",
     "Strikes kill seven, wound 13. An aid truck in Gaza City is hit: three dead.",
     "AP / Al Jazeera", "CONFIRMED", 31.50, 34.47, "flame"),
    (11, "MIDDLE EAST", "129 BODIES PULLED FROM RUBBLE",
     "Rescue teams recover the remains of 129 Palestinians from wreckage "
     "in central Gaza as the ceasefire's toll keeps rising.",
     "Al Jazeera", "REPORTED", 31.42, 34.38, "building"),
    (12, "MIDDLE EAST", "SAUDIS SAY THEY STOPPED HOUTHI MISSILE",
     "The Saudi-led coalition says it intercepted a Houthi missile aimed "
     "at western Saudi Arabia as Gulf tensions climb.",
     "Al Jazeera", "REPORTED", 24.71, 46.68, "bolt"),
    (13, "MIDDLE EAST", "BASRA POWER PLANT FIRE KILLS 4",
     "A blaze at the Hartha power station north of Basra kills four "
     "workers and injures 30, officials say.",
     "Reuters", "CONFIRMED", 30.50, 47.78, "flame"),
    (14, "AMERICAS", "DEMOCRATS CLINCH 258 HOUSE SEATS",
     "Best House result since 1992: at least 258 seats, a gain of 44.",
     "AP", "CONFIRMED", 38.90, -77.04, "ballot"),
    (15, "AMERICAS", "HUBBARD BEATS FOXX AFTER RECOUNT",
     "Democrat Chuck Hubbard unseats Republican Virginia Foxx in North "
     "Carolina after a recount, adding to the midterm tally.",
     "AP", "CONFIRMED", 35.78, -78.64, "ballot"),
    (16, "AMERICAS", "SPY CHIEF BACKS TRUMP ON PUTIN",
     "Director of National Intelligence Jay Clayton calls it entirely "
     "appropriate for Trump to call Putin a friend.",
     "AP", "REPORTED", 38.90, -77.04, "mic"),
    (17, "AMERICAS", "WEMBY 50 AS SPURS ROLL 114-91",
     "Wembanyama drops 50 points, 19 rebounds, five blocks, four steals.",
     "AP", "CONFIRMED", 29.42, -98.49, "ball"),
    (18, "AMERICAS", "VERSTAPPEN WINS WILD VEGAS GP",
     "35 lead changes in 50 laps. Verstappen beats Norris by 0.639s.",
     "Formula 1", "CONFIRMED", 36.17, -115.14, "trophy"),
    (19, "AMERICAS", "FBI CRIME DATABASE BREACHED",
     "The FBI's criminal databank is breached in another cyberattack on "
     "the agency, reports say, as officials stay silent on scope.",
     "Al Jazeera", "REPORTED", 38.90, -77.04, "bolt"),
    (20, "AMERICAS", "ICE ARREST DELAYS LA FLIGHT",
     "Officers arrest passengers on a Seattle jet bridge as they board "
     "a Los Angeles-bound flight, delaying take-off.",
     "New York Post", "REPORTED", 34.05, -118.24, "plane"),
    (21, "ASIA-PACIFIC", "HONG KONG POLLS: 98.79% TURNOUT",
     "5,640 voters pick 723 of 856 candidates for the Election Committee.",
     "China Daily / EAC", "CONFIRMED", 22.32, 114.17, "ballot"),
    (22, "ASIA-PACIFIC", "INDIA DECLARE AT 720 FOR 9",
     "Pant 128, Rahul 136. India's 720 is the highest Test total ever in NZ.",
     "Cricbuzz / AFP", "CONFIRMED", -41.29, 174.78, "ball"),
    (23, "ASIA-PACIFIC", "CIKANDE FIRE: 24 BODY BAGS OUT",
     "Police carry out 24 body bags a day after the blaze; 29 still missing.",
     "Reuters", "CONFIRMED", -6.20, 106.20, "flame"),
    (24, "ASIA-PACIFIC", "CHINA EASES MARGIN RULES",
     "Bourses cut the minimum margin ratio to 80% to prop up stocks.",
     "Reuters", "CONFIRMED", 31.23, 121.47, "chart"),
    (25, "ASIA-PACIFIC", "TRUMP: CHINA BUILD-UP HOT AND HEAVY",
     "A day after meeting Xi, Trump says China's nuclear build-up is hot "
     "and heavy, as the Shenzhen summit draws mixed reviews.",
     "AP", "REPORTED", 39.90, 116.40, "mic"),
    (26, "ASIA-PACIFIC", "MONGOLIA PRESIDENT RESIGNS",
     "The president steps down, setting up elections within four months "
     "in a country caught between Russia and China.",
     "Al Jazeera", "REPORTED", 47.92, 106.92, "flag"),
    (27, "ASIA-PACIFIC", "MALAYSIA TAKES ROHINGYA CASE TO UN",
     "Kuala Lumpur says it will consult the UN and the OIC over the "
     "Myanmar genocide ruling on the Rohingya.",
     "Al Jazeera", "REPORTED", 3.14, 101.69, "scale"),
    (28, "ASIA-PACIFIC", "PAKISTAN PROVINCES REFERENDUM PUSH",
     "The ruling PML-N pushes a referendum on new provinces; coalition "
     "partner PPP objects, opening a rift in Islamabad.",
     "Al Jazeera", "REPORTED", 33.68, 73.05, "ballot"),
    (29, "ASIA-PACIFIC", "CHINA, AUSTRALIA IN GREEN + AI PACT",
     "Premier Li Qiang and PM Anthony Albanese agree in Beijing to expand "
     "cooperation on green energy and artificial intelligence.",
     "Australia Times", "REPORTED", 39.90, 116.40, "globe"),
    (30, "AFRICA", "DRONES HIT UN SITES IN KHARTOUM",
     "Drone strikes damage UN and civilian buildings in Sudan's capital.",
     "Al Jazeera", "REPORTED", 15.50, 32.56, "bolt"),
    (31, "AFRICA", "1,630 SUDAN CIVILIANS KILLED BY DRONES",
     "UN human-rights data counts about 1,630 civilian deaths from drone "
     "strikes in Sudan from January to October 2026.",
     "UN / Al Jazeera", "REPORTED", 13.00, 24.50, "scale"),
    (32, "AFRICA", "NIGERIA BOAT SINKS: 24 DEAD",
     "Boat carrying funeral mourners capsizes in southern Nigeria: 24 dead.",
     "OneTurn / Reuters", "CONFIRMED", 5.50, 7.00, "droplet"),
    (33, "OCEANIA", "HUMAN FAMILY TREE MAY NEED REWRITE",
     "Monash University research challenges how scientists classify some "
     "ancient human ancestors, and the tree may need an overhaul.",
     "ScienceDaily", "REPORTED", -37.81, 144.96, "star"),
    (34, "OCEANIA", "FIRE ANTS FOUND IN WEST SYDNEY",
     "Red imported fire ants, one of the world's worst invasive species, "
     "are found in Sydney for the second time in as many months.",
     "ABC News", "CONFIRMED", -33.87, 151.21, "flame"),
    (35, "WORLD", "15M DEUTSCHE BANK FILES LEAKED",
     "A massive leak of 15 million files from Deutsche Bank, the lender "
     "that bankrolled Trump, surfaces in a trove under review.",
     "Background Briefing", "REPORTED", 50.11, 8.68, "building"),
]

LEADS = (1, 2, 9)
SMALL = (14, 17, 18, 21, 22, 23, 10, 24, 30, 32)
ALSO = [s for s in STORIES if s[0] not in LEADS and s[0] not in SMALL]

# One-line versions for the ALSO list: (num, text, source)
ALSO_LINES = [
    (3, "Denmark expels Russian defence attache over alleged plot", "Al Jazeera"),
    (4, "EU approves 1bn euros more military aid for Ukraine", "Al Jazeera"),
    (5, "France seeks UN meeting over strikes on Kyiv missions", "Al Jazeera"),
    (6, "Zelenskyy: next four-party talks must bring real progress", "Al Jazeera"),
    (7, "EU backs Poland after Moscow airspace violation", "Al Jazeera"),
    (8, "Russia says it downed 170 Ukrainian drones overnight", "QNA"),
    (11, "129 bodies pulled from rubble in central Gaza", "Al Jazeera"),
    (12, "Saudi coalition says it stopped a Houthi missile", "Al Jazeera"),
    (13, "Basra power station fire kills 4, injures 30", "Reuters"),
    (15, "Hubbard beats Foxx in North Carolina after recount", "AP"),
    (16, "Spy chief: calling Putin a friend is entirely appropriate", "AP"),
    (19, "FBI criminal databank breached in cyberattack", "Al Jazeera"),
    (20, "ICE arrest on jet bridge delays LA-bound flight", "NY Post"),
    (25, "Trump: China's nuclear build-up is hot and heavy", "AP"),
    (26, "Mongolia president resigns; vote due within 4 months", "Al Jazeera"),
    (27, "Malaysia takes Rohingya ruling to UN and OIC", "Al Jazeera"),
    (28, "Pakistan ruling party pushes provinces referendum", "Al Jazeera"),
    (29, "China and Australia agree green + AI cooperation", "Australia Times"),
    (31, "UN: 1,630 Sudan civilians killed by drone strikes in 2026", "UN"),
    (33, "Monash: human family tree may need a rewrite", "ScienceDaily"),
    (34, "Red fire ants found in Western Sydney again", "ABC News"),
    (35, "15m Deutsche Bank files leaked, reports say", "Background Briefing"),
]

# Six big numbers for the strip: (number, label)
BIG_NUMBERS = [
    ("186", "drones fired at Ukraine"),
    ("161", "drones downed or jammed"),
    ("720/9", "India declare, Wellington"),
    ("98.79%", "Hong Kong poll turnout"),
    ("258", "Democrats' House seats"),
    ("0", "climate deals at COP31"),
]

REGION_COUNTS = [
    ("EUROPE", 8), ("MIDDLE EAST", 5), ("AMERICAS", 7),
    ("ASIA-PACIFIC", 9), ("AFRICA", 3), ("OCEANIA", 2), ("WORLD", 1),
]

# The day in UTC: (time, text)
TIMELINE = [
    ("05:11", "IRGC claims Patriot radar strikes in Bahrain"),
    ("06:00", "Verstappen wins the Las Vegas GP by 0.639s"),
    ("06:00", "Kyiv counts 161 of 186 Russian drones downed"),
    ("09:42", "129 bodies pulled from rubble in central Gaza"),
    ("13:37", "7 killed in Israeli strikes across Gaza"),
    ("14:15", "Hong Kong vote count done: turnout 98.79%"),
    ("16:51", "Israeli strike kills 3 in a Gaza aid truck"),
    ("19:42", "AP: Democrats clinch 258 House seats"),
]

# Stories deliberately left out because they are NOT 22 Nov.
DATE_CHECK = [
    ("El Chapo Isidro captured", "Fri 21 Nov"),
    ("Peru M6.7 earthquake", "Fri 20 Nov"),
    ("GTA 6: $3.8bn first-day sales", "Fri 20 Nov"),
    ("Cyclone Akvan hits Odisha", "Fri 20 Nov"),
    ("Cyclone Xavier Cat 5, Cook Is.", "Wed 18 Nov"),
    ("Trump-Xi Shenzhen meeting", "Sat 21 Nov"),
    ("Iran strikes on Bahrain bases", "Sat night 21 Nov"),
]

# ---------------------------------------------------------------- layout
REGION_COLORS = {"EUROPE": BLUE, "MIDDLE EAST": RED_DK, "AMERICAS": TEAL,
                 "ASIA-PACIFIC": (150, 105, 10), "AFRICA": GREEN,
                 "OCEANIA": (120, 60, 140), "WORLD": INK}
PIN_OFFSETS = {6: (3.0, 1.5), 16: (2.0, -1.0), 19: (-2.0, 1.5),
               29: (2.5, -1.5), 11: (1.5, -1.5)}


def by_num(n):
    for s in STORIES:
        if s[0] == n:
            return s
    raise KeyError(n)


def draw_masthead(cv):
    cv.rect(0, 0, W, 4, RED)
    center_text(cv, W // 2, 10, "THE WORLD IN ONE DAY", 4, INK, bold=True)
    center_text(cv, W // 2, 44, "SUNDAY 22 NOVEMBER 2026", 3, RED, bold=True)
    center_text(cv, W // 2, 72,
                "35 STORIES  \u2022  7 REGIONS  \u2022  EVERY EVENT SUNDAY 22 NOV 2026 (UTC)",
                1, INK_SOFT)
    cv.hline(8, 86, W - 16, INK)
    cv.hline(8, 88, W - 16, INK)


def draw_numbers(cv):
    y = 91
    cell = W // 6
    for i, (num, label) in enumerate(BIG_NUMBERS):
        cx = i * cell + cell // 2
        col = RED if num == "0" else INK
        center_text(cv, cx, y, num, 3, col, bold=True)
        center_text(cv, cx, y + 23, label, 1, INK_SOFT)
        if i:
            cv.vline(i * cell, y + 2, 28, GREY_DK)
    cv.hline(8, 123, W - 16, GREY_DK)


def draw_regions(cv):
    y = 129
    parts = []
    total = 0
    for name, count in REGION_COUNTS:
        s = "%s %d" % (name, count)
        parts.append((s, REGION_COLORS[name]))
        total += text_w(s, 1) + text_w("  \u2022  ", 1)
    total -= text_w("  \u2022  ", 1)
    x = (W - total) // 2
    for i, (s, col) in enumerate(parts):
        draw_text(cv, x, y, s, 1, col, bold=True)
        x += text_w(s, 1)
        if i < len(parts) - 1:
            draw_text(cv, x, y, "  \u2022  ", 1, GREY_DK)
            x += text_w("  \u2022  ", 1)
    cv.hline(8, 143, W - 16, INK)


def draw_lead_scene(cv, x, y, w, h, num):
    if num == 1:  # COP31: sun over a summit hall, NO DEAL stamp
        cv.rect(x, y, w, h, (22, 96, 92))
        cv.circle(x + 62, y + 34, 22, GOLD)
        cv.rect(x, y + h - 34, w, 34, (16, 60, 58))
        for bx in range(0, w, 46):
            cv.rect(x + bx + 8, y + h - 58, 30, 24, (12, 44, 42))
        cv.rect(x + w - 118, y + 12, 106, 30, WHITE)
        cv.rect(x + w - 118, y + 12, 106, 30, RED)
        draw_text(cv, x + w - 110, y + 20, "NO DEAL", 2, WHITE, bold=True)
    elif num == 2:  # Ukraine: night sky, skyline, blast, drones
        cv.rect(x, y, w, h, (18, 26, 52))
        for dx, dy in ((40, 18), (120, 10), (210, 22), (280, 12)):
            cv.circle(x + dx, y + dy, 2, WHITE)
        cv.rect(x, y + h - 40, w, 40, (10, 14, 30))
        for bx, bw, bh in ((10, 40, 26), (60, 28, 34), (100, 46, 20),
                           (160, 34, 30), (210, 44, 24), (266, 36, 32)):
            cv.rect(x + bx, y + h - 40 - bh + 20, bw, bh, (30, 42, 74))
        cv.circle(x + 150, y + 34, 12, (240, 140, 30))
        cv.circle(x + 150, y + 34, 6, (255, 220, 120))
        for dx, dy in ((60, 26), (240, 20)):
            cv.circle(x + dx, y + dy, 3, (200, 200, 200))
            cv.line(x + dx - 8, y + dy, x + dx + 8, y + dy, (200, 200, 200))
    else:  # Bahrain: sea, radar arcs, streaks
        cv.rect(x, y, w, h, (24, 74, 110))
        cv.rect(x, y + h - 26, w, 26, (16, 52, 84))
        cv.circle(x + 70, y + h - 26, 34, (140, 190, 220), fill=False)
        cv.circle(x + 70, y + h - 26, 22, (140, 190, 220), fill=False)
        cv.circle(x + 70, y + h - 26, 10, (140, 190, 220), fill=False)
        cv.line(x + 70, y + h - 26, x + 108, y + h - 58, (255, 255, 255))
        cv.line(x + 180, y + 14, x + 250, y + 40, (255, 200, 90))
        cv.line(x + 200, y + 8, x + 262, y + 30, (255, 200, 90))
        cv.circle(x + 250, y + 40, 4, (255, 120, 60))
        cv.rect(x + w - 90, y + h - 18, 80, 10, (10, 40, 66))


def draw_leads(cv):
    col_w = 324
    xs = [8, 348, 688]
    for ci, num in enumerate(LEADS):
        s = by_num(num)
        _, region, headline, dek, source, tag, _, _, _ = s
        x = xs[ci]
        y = 149
        draw_lead_scene(cv, x, y, col_w, 84, num)
        y += 92
        draw_text(cv, x, y, region, 1, REGION_COLORS[region], bold=True)
        tw = draw_tag(cv, x + col_w - 78, y - 1, tag)
        y += 16
        y = draw_para(cv, x, y, headline, 2, INK, 27, line_h=16, bold=True)
        y += 4
        y = draw_para(cv, x, y, dek, 2, INK_SOFT, 27, line_h=15)
        y += 6
        draw_text(cv, x, y, "Source: " + source, 1, INK_SOFT)
        draw_text(cv, x + col_w - 22, y - 2, "#%d" % num, 1, RED, bold=True)
        cv.hline(x, 372, col_w, GREY_DK)


def draw_timeline_and_datecheck(cv):
    x = 8
    w = 348
    y = 380
    draw_text(cv, x, y, "THE DAY IN UTC", 2, INK, bold=True)
    cv.hline(x, y + 16, w, INK)
    y += 24
    for t, text in TIMELINE:
        draw_text(cv, x, y, t, 1, RED, bold=True)
        yy = draw_para(cv, x + 44, y, text, 1, INK, 46, line_h=9)
        y = max(y + 11, yy + 2)
    y += 10
    draw_text(cv, x, y, "DATE CHECK: LEFT OUT ON PURPOSE", 2, RED, bold=True)
    cv.hline(x, y + 16, w, RED)
    y += 24
    for name, when in DATE_CHECK:
        draw_text(cv, x, y, "\u2022 " + name, 1, INK, bold=False)
        tw = text_w(when, 1)
        draw_text(cv, x + w - tw, y, when, 1, RED, bold=True)
        y += 12
    y += 4
    draw_para(cv, x, y,
              "Sat-night US sport counts only because play ended after "
              "00:00 UTC Sunday.", 1, INK_SOFT, 52, line_h=9)


def draw_map_panel(cv):
    x0, y0, w, h = 364, 400, 652, 290
    draw_text(cv, x0, 380, "WHERE IT HAPPENED: 35 STORIES, PINNED", 2, INK,
              bold=True)
    pins = []
    for s in STORIES:
        num, _, _, _, _, _, lat, lon, _ = s
        dx, dy = PIN_OFFSETS.get(num, (0.0, 0.0))
        pins.append((num, lon, lat, dx, dy))
    draw_map(cv, x0, y0, w, h, pins)
    cv.rect(x0, y0 + h - 18, w, 18, INK)
    draw_text(cv, x0 + 6, y0 + h - 13,
              "Pins use real lat/lon.  Number = story number.", 1, WHITE)


def draw_small(cv):
    # 10 small stories: 2 columns x 5 rows, icon + headline + dek + source
    col_x = [8, 516]
    col_w = 500
    row_h = 38
    y0 = 694
    for i, num in enumerate(SMALL):
        s = by_num(num)
        _, region, headline, dek, source, tag, _, _, icon = s
        col = i % 2
        row = i // 2
        x = col_x[col]
        y = y0 + row * row_h
        # icon tile
        cv.rect(x, y, 34, 34, REGION_COLORS[region])
        ICONS[icon](cv, x + 4, y + 4, 26, WHITE)
        tx = x + 40
        draw_text(cv, tx, y, headline, 2, INK, bold=True)
        draw_text(cv, tx + col_w - 40 - 22, y, "#%d" % num, 1, RED, bold=True)
        draw_text(cv, tx, y + 15, dek, 1, INK_SOFT)
        draw_text(cv, tx, y + 26, source, 1, INK_SOFT)
        draw_tag(cv, tx + 210, y + 25, tag)
        if row < 4:
            cv.hline(x, y + 36, col_w, GREY)


def draw_also(cv):
    y = 888
    draw_text(cv, 8, y, "ALSO ON SUNDAY", 2, INK, bold=True)
    cv.hline(8, y + 16, W - 16, INK)
    y += 22
    col_x = [8, 516]
    for i, (num, text, source) in enumerate(ALSO_LINES):
        col = i % 11
        row = i // 11
        x = col_x[row]
        yy = y + col * 7
        line = "%d  %s (%s)" % (num, text, source)
        draw_text(cv, x, yy, line, 1, INK)


def draw_footer(cv):
    y = 990
    x = 8
    draw_text(cv, x, y, "CERTAINTY:", 1, INK, bold=True)
    x += text_w("CERTAINTY: ", 1)
    for tag, note in (("CONFIRMED", "2+ outlets or official"),
                      ("CLAIM", "one party, unverified"),
                      ("REPORTED", "one source")):
        w = draw_tag(cv, x, y - 1, tag)
        x += w + 4
        draw_text(cv, x, y, note, 1, INK_SOFT)
        x += text_w(note, 1) + 10
    y += 12
    draw_text(cv, 8, y,
              "All 35 stories happened or were first reported Sun 22 Nov 2026 "
              "(UTC). Sources: Reuters, AP, AFP, Al Jazeera, UN News, "
              "Formula 1, Cricbuzz, China Daily, ABC News.", 1, INK_SOFT)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)
    draw_numbers(cv)
    draw_regions(cv)
    draw_leads(cv)
    draw_timeline_and_datecheck(cv)
    draw_map_panel(cv)
    draw_small(cv)
    draw_also(cv)
    draw_footer(cv)
    path = os.path.join(outdir, "entry.png")
    size = write_png(cv, path)
    sys.stdout.write("wrote %s %d bytes\n" % (path, size))


if __name__ == "__main__":
    main()
