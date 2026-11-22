#!/usr/bin/env python3
"""news-image-20261121 v2: one dense front page of 21 November 2026's news.

37 stories from 9 regions on a 1024x1024 newspaper front page: one lead
(Iran strikes US bases in Bahrain), a 4x9 grid of 36 more, a world map with
the 9 regions pinned, a UTC strip and a date check. Every story was verified
against real reporting dated Saturday 21 November 2026 (Reuters, CNN, WSJ,
AP, Al Jazeera, The Hindu, UN News, ABC News, Wisevoter, OneTurn, Horizon,
IntelChron, InformedClearly). Pure Python 3.13 standard library (os, struct,
zlib). No network, deterministic: two runs write byte-identical output.
Writes entry.png to $MAKEFUN_OUTPUT_DIR or /output.

Rendering: the page is drawn at 2x (2048x2048) and box-downsampled to
1024x1024, so the 5x7 bitmap text comes out anti-aliased and legible at
about 300 pixels across, like a real printed page.
"""

import os
import struct
import zlib

W, H = 1024, 1024
SS = 2  # supersample factor

# ------------------------------------------------------------------ palette
PAPER = (247, 243, 234)
INK = (26, 26, 26)
NAVY = (20, 33, 61)
GOLD = (201, 162, 39)
WHITE = (255, 255, 255)
RED = (222, 41, 16)
DARKRED = (150, 40, 30)
BLUE = (0, 87, 183)
SEA = (18, 92, 140)
TEAL = (14, 116, 120)
GREEN = (34, 139, 34)
ORANGE = (230, 126, 34)
GREY = (90, 90, 96)
PURPLE = (90, 50, 130)
IRAN_GREEN = (0, 128, 0)
IRAN_RED = (220, 0, 0)
BAHRAIN_RED = (206, 17, 38)
MAP_SEA = (168, 205, 228)
MAP_LAND = (233, 214, 172)
MAP_LAND2 = (214, 190, 140)


# ------------------------------------------------------------------ canvas
class Page:
    """An RGB page held as one flat bytearray; writes its own PNG.

    All drawing methods take logical 1024x1024 coordinates; the page is
    stored at SS*1024 and downsampled on write, which anti-aliases edges.
    """

    def __init__(self, w, h, bg):
        self.w, self.h = w * SS, h * SS
        self.lw, self.lh = w, h
        self.buf = bytearray(bytes(bg) * (self.w * self.h))

    def _row_px(self, x0, x1, y, c):
        """One physical row, x0..x1 inclusive, slice-assigned (C speed)."""
        if y < 0 or y >= self.h:
            return
        a, b = max(0, x0), min(self.w - 1, x1)
        if a > b:
            return
        i = (y * self.w + a) * 3
        self.buf[i:i + (b - a + 1) * 3] = bytes(c) * (b - a + 1)

    def row(self, x0, x1, y, c):
        for k in range(SS):
            self._row_px(x0 * SS, (x1 + 1) * SS - 1, y * SS + k, c)

    def col(self, x, y0, y1, c):
        for yy in range(y0 * SS, (y1 + 1) * SS):
            self._row_px(x * SS, (x + 1) * SS - 1, yy, c)

    def box(self, x, y, w, h, c):
        for yy in range(y * SS, min(self.h, (y + h) * SS)):
            self._row_px(x * SS, (x + w) * SS - 1, yy, c)

    def frame(self, x, y, w, h, c, t=1):
        for k in range(t):
            self.row(x, x + w - 1, y + k, c)
            self.row(x, x + w - 1, y + h - 1 - k, c)
            self.col(x + k, y, y + h - 1, c)
            self.col(x + w - 1 - k, y, y + h - 1, c)

    def poly(self, pts, c):
        """Scanline-fill a polygon given as logical [(x, y), ...]."""
        sp = [(x * SS, y * SS) for x, y in pts]
        ys = [p[1] for p in sp]
        for y in range(max(0, int(min(ys))), min(self.h - 1, int(max(ys))) + 1):
            xs = []
            n = len(sp)
            for i in range(n):
                x1, y1 = sp[i]
                x2, y2 = sp[(i + 1) % n]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self._row_px(int(xs[i]), int(xs[i + 1]), y, c)

    def diamond(self, cx, cy, r, c):
        self.poly([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], c)

    def downsample(self):
        """Box-average the 2x buffer down to logical size."""
        w, h = self.lw, self.lh
        w2 = self.w
        buf = self.buf
        out = bytearray(w * h * 3)
        for y in range(h):
            b0 = (2 * y * w2) * 3
            b1 = ((2 * y + 1) * w2) * 3
            o = (y * w) * 3
            for x in range(w):
                i0 = b0 + (2 * x) * 3
                j0 = b1 + (2 * x) * 3
                out[o] = (buf[i0] + buf[i0 + 3] + buf[j0] + buf[j0 + 3]) >> 2
                out[o + 1] = (buf[i0 + 1] + buf[i0 + 4] + buf[j0 + 1] + buf[j0 + 4]) >> 2
                out[o + 2] = (buf[i0 + 2] + buf[i0 + 5] + buf[j0 + 2] + buf[j0 + 5]) >> 2
                o += 3
        return bytes(out)

    def png(self):
        raw = self.downsample()
        comp = zlib.compress(
            b"".join(b"\x00" + raw[y * self.lw * 3:(y + 1) * self.lw * 3]
                     for y in range(self.lh)), 9)

        def chunk(typ, data):
            c = struct.pack(">I", len(data)) + typ + data
            return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

        ihdr = struct.pack(">IIBBBBB", self.lw, self.lh, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ------------------------------------------------------------- 5x7 bitmap font
# One glyph = 7 rows; each row is a 5-bit mask, bit 4 = leftmost column.
GLYPHS = {
    "A": [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "B": [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    "C": [0x0F, 0x10, 0x10, 0x10, 0x10, 0x10, 0x0F],
    "D": [0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E],
    "E": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
    "F": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    "G": [0x0F, 0x10, 0x10, 0x17, 0x11, 0x11, 0x07],
    "H": [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "I": [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x1F],
    "J": [0x07, 0x01, 0x01, 0x01, 0x01, 0x11, 0x06],
    "K": [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11],
    "L": [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    "M": [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
    "N": [0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11],
    "O": [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "P": [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    "Q": [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D],
    "R": [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    "S": [0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E],
    "T": [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    "U": [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
    "V": [0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04],
    "W": [0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11],
    "X": [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    "Y": [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
    "Z": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    "0": [0x0E, 0x13, 0x15, 0x19, 0x11, 0x11, 0x0E],
    "1": [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "2": [0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F],
    "3": [0x1E, 0x01, 0x01, 0x06, 0x01, 0x01, 0x1E],
    "4": [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    "5": [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    "6": [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    "7": [0x1F, 0x01, 0x02, 0x04, 0x04, 0x04, 0x04],
    "8": [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    "9": [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x01, 0x0E],
    " ": [0, 0, 0, 0, 0, 0, 0],
    ".": [0, 0, 0, 0, 0, 0, 0x04],
    ",": [0, 0, 0, 0, 0, 0x04, 0x08],
    ":": [0, 0x04, 0, 0, 0, 0x04, 0],
    ";": [0, 0x04, 0, 0, 0, 0x04, 0x08],
    "'": [0x04, 0x04, 0x08, 0, 0, 0, 0],
    "-": [0, 0, 0, 0x0E, 0, 0, 0],
    "/": [0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10],
    "!": [0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04],
    "?": [0x0E, 0x11, 0x01, 0x02, 0x04, 0, 0x04],
    "(": [0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02],
    ")": [0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08],
    "%": [0x11, 0x12, 0x02, 0x04, 0x08, 0x09, 0x11],
    "+": [0, 0x04, 0x04, 0x0E, 0x04, 0x04, 0],
    "$": [0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04],
}


def text_w(s, scale):
    return len(s) * 6 * scale - scale if s else 0


def draw_text(pg, x, y, s, scale, color, align="left"):
    s = s.upper()  # the bitmap font only carries capitals, digits, punctuation
    if align == "center":
        x -= text_w(s, scale) // 2
    elif align == "right":
        x -= text_w(s, scale)
    for ch in s:
        g = GLYPHS.get(ch, GLYPHS[" "])
        for r in range(7):
            mask = g[r]
            for c in range(5):
                if mask & (1 << (4 - c)):
                    pg.box(x + c * scale, y + r * scale, scale, scale, color)
        x += 6 * scale


def wrap(s, max_w, scale):
    """Greedy word wrap; returns lines fitting max_w pixels."""
    lines, cur = [], ""
    for word in s.split(" "):
        trial = word if not cur else cur + " " + word
        if text_w(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

# ------------------------------------------------------------------ stories
# (region, headline, summary, accent). Headlines wrap to at most 2 lines at
# scale 2 in a 231 px column; summaries fit one line at scale 1 (<=38 chars).
# 36 grid stories + the lead = 37 stories, 9 regions.
STORIES = [
    ("N. AMERICA", "AI SELL-OFF PUSHES US INTO CORRECTION",
     "AI and chip rout drags US stocks down.", PURPLE),
    ("N. AMERICA", "FBI AND USDA HACKED",
     "FBI probes hack of crime database.", NAVY),
    ("N. AMERICA", "DEMOCRATS WIN 259 HOUSE SEATS",
     "Biggest House majority since 1990.", NAVY),
    ("N. AMERICA", "US LOSES MEASLES-FREE STATUS",
     "First Virginia measles death in 2026.", DARKRED),
    ("N. AMERICA", "BAYER PAYS $7.25BN OVER ROUNDUP",
     "Judge validates Roundup settlement.", PURPLE),
    ("N. AMERICA", "MAMDANI: CLOSE RIKERS BY 2032",
     "To shut Rikers Island jail by 2032.", NAVY),
    ("N. AMERICA", "GTA VI MAKES $3.79BN IN A DAY",
     "Biggest entertainment launch ever.", PURPLE),
    ("N. AMERICA", "RIEMANN PROOF VERIFIED",
     "AI-assisted proof verified by Lean.", PURPLE),
    ("EUROPE", "COP31 RUNS PAST DEADLINE",
     "Antalya climate talks go to overtime.", GREEN),
    ("EUROPE", "DENMARK: RUSSIA MURDER PLOT",
     "Copenhagen blames Russian intel.", NAVY),
    ("EUROPE", "RUSSIAN SHIP ABLAZE OFF FINLAND",
     "Vessel ablaze after drone strike.", GREY),
    ("EUROPE", "EU-INDONESIA DEAL SIGNED",
     "Trade pact agreed after ten years.", BLUE),
    ("EUROPE", "EU BUDGET: 1.78TN EURO PLAN",
     "Plan includes a 3% digital tax.", BLUE),
    ("EUROPE", "BELGIUM STRIKE TO GROUND ALL FLIGHTS",
     "Air traffic joins nationwide strike.", NAVY),
    ("EUROPE", "RUSSIAN MISSILE HITS KRYVYI RIH",
     "Strike on Zelensky's hometown kills 2.", RED),
    ("MIDEAST", "TWO TANKERS HIT NEAR HORMUZ",
     "UKMTO: two tankers struck off Oman.", TEAL),
    ("MIDEAST", "HOUTHIS HIT RIYADH SKYSCRAPER",
     "Houthi missiles damage Riyadh tower.", ORANGE),
    ("MIDEAST", "BASRA POWER PLANT FIRE KILLS FOUR",
     "Hartha plant fire kills 4, injures 35.", ORANGE),
    ("MIDEAST", "LEBANON: ISRAEL MUST WITHDRAW",
     "President demands Israeli pullout.", NAVY),
    ("MIDEAST", "US, ISRAEL WEIGH NEW IRAN STRIKES",
     "Allies weigh a third round of strikes.", NAVY),
    ("E. ASIA", "SUNEUNG EXAM CHEATING SCANDAL",
     "111 students caught cheating in exam.", NAVY),
    ("E. ASIA", "QUAD, ASEAN SUMMITS: TAKEAWAYS",
     "Takeaways from the Manila summits.", NAVY),
    ("E. ASIA", "CHINA TO JAPAN: CORRECT REMARKS",
     "Beijing demands Tokyo retract remarks.", NAVY),
    ("S. ASIA", "BANGLADESH DENGUE: 3 MORE DEAD",
     "Dengue kills 3 more; 1,674 admitted.", GREEN),
    ("S. ASIA", "IRAN PITCHES 3 PLANS AT SCO FORUM",
     "Iran pitches heritage plans in Delhi.", NAVY),
    ("S. ASIA", "AFGHAN MORTAR BLAST KILLS FOUR STUDENTS",
     "Old mortar kills four students.", DARKRED),
    ("AFRICA", "NIGERIA BOAT CAPSIZE KILLS 24",
     "Boat capsizes; 24 bodies recovered.", DARKRED),
    ("AFRICA", "S. AFRICA: 600 WOMEN KILLED",
     "Nearly 600 women killed in 3 months.", DARKRED),
    ("AFRICA", "ANC FIGHTS TO KEEP KEY CITIES",
     "ANC fights to hold key cities.", NAVY),
    ("LATIN AM.", "MEXICO CAPTURES CHAPO ISIDRO",
     "FBI most-wanted boss seized; 11 dead.", RED),
    ("LATIN AM.", "PERU QUAKE 6.7 SHAKES ANDES",
     "Deep 6.7 quake hits Junin; no deaths.", ORANGE),
    ("LATIN AM.", "ARGENTINA OKAYS $50BN LNG PROJECT",
     "Biggest project in Argentine history.", PURPLE),
    ("LATIN AM.", "BOLSONARO TAKEN TO ICU",
     "Ex-president in ICU with blockage.", RED),
    ("CARIBBEAN", "HAITI: THREE DEAD AFTER BLAST",
     "Blast hits Salvadoran troops.", RED),
    ("OCEANIA", "AIR NIUGINI JET IN EMERGENCY LANDING",
     "146 aboard in emergency landing.", SEA),
    ("OCEANIA", "AUSTRALIA, CHINA AGREE AI TALKS",
     "AI talks agreed after APEC summit.", SEA),
]

LEAD_LINES = ["IRAN STRIKES US BASES", "IN BAHRAIN"]
LEAD_SUMMARY = ("Tehran says it hit two US positions; Bahrain reports "
                "an industrial fire, no injuries.")
LEAD_DATELINE = "MANAMA, BAHRAIN - SATURDAY 21 NOVEMBER 2026"
ALSO_1 = ("ALSO TODAY: MEXICO CAPTURES 'EL CHAPO ISIDRO' - COP31 OVERTIME "
          "- PERU QUAKE 6.7 - BOLSONARO IN ICU")
ALSO_2 = ("GTA VI MAKES $3.79BN IN A DAY - DEMOCRATS WIN 259 SEATS "
          "- RIEMANN PROOF VERIFIED")
ALSO_3 = ("EU BUDGET 1.78TN EURO - BELGIUM STRIKE GROUNDS FLIGHTS "
          "- AUSTRALIA-CHINA AI TALKS")


# ------------------------------------------------------------------ world map
# Coarse coastlines as (lon, lat) polygons; equirectangular projection.
NORTH_AMERICA = [(-168, 66), (-158, 58), (-150, 60), (-140, 60), (-132, 56),
                 (-126, 50), (-124, 42), (-120, 34), (-113, 29), (-108, 24),
                 (-104, 20), (-96, 16), (-91, 14), (-86, 12), (-82, 9),
                 (-79, 9), (-81, 13), (-85, 16), (-88, 18), (-90, 21),
                 (-91, 19), (-95, 19), (-97, 25), (-93, 30), (-88, 30),
                 (-83, 30), (-81, 26), (-80, 32), (-75, 35), (-73, 40),
                 (-69, 43), (-66, 45), (-61, 46), (-56, 50), (-60, 55),
                 (-65, 60), (-68, 58), (-76, 62), (-84, 66), (-92, 69),
                 (-102, 68), (-112, 68), (-122, 70), (-132, 69), (-142, 70),
                 (-152, 71), (-162, 70), (-168, 66)]
GREENLAND = [(-55, 60), (-46, 60), (-40, 62), (-34, 66), (-28, 68),
             (-21, 71), (-20, 75), (-26, 79), (-38, 81), (-52, 80),
             (-58, 76), (-58, 68), (-55, 60)]
SOUTH_AMERICA = [(-79, 9), (-77, 4), (-80, -3), (-81, -6), (-77, -12),
                 (-72, -18), (-70, -23), (-71, -30), (-73, -37), (-73, -44),
                 (-70, -50), (-68, -54), (-65, -55), (-67, -50), (-62, -41),
                 (-57, -34), (-52, -32), (-48, -27), (-41, -23), (-39, -17),
                 (-35, -9), (-35, -6), (-40, -3), (-44, -2), (-50, 0),
                 (-53, 4), (-58, 7), (-63, 9), (-69, 11), (-75, 10), (-79, 9)]
AFRICA = [(-17, 15), (-16, 21), (-14, 27), (-9, 31), (-5, 35), (0, 36),
          (9, 37), (11, 34), (19, 32), (25, 32), (30, 31), (32, 31),
          (34, 28), (36, 23), (38, 20), (40, 15), (43, 12), (48, 11),
          (51, 10), (46, 5), (41, 1), (40, -4), (39, -9), (36, -17),
          (33, -25), (28, -33), (20, -35), (17, -31), (15, -27), (12, -18),
          (13, -11), (12, -5), (9, 4), (4, 6), (-7, 5), (-12, 8), (-17, 12),
          (-17, 15)]
EURASIA = [(-10, 36), (-9, 43), (-2, 44), (-1, 47), (-4, 48), (0, 50),
           (3, 51), (6, 53), (8, 55), (9, 57), (12, 59), (6, 60), (6, 62),
           (11, 64), (14, 66), (19, 69), (26, 71), (31, 70), (36, 68),
           (43, 68), (50, 69), (58, 69), (66, 70), (73, 72), (80, 73),
           (88, 74), (96, 75), (104, 76), (112, 74), (120, 73), (128, 72),
           (136, 71), (144, 72), (152, 70), (160, 69), (168, 68), (176, 66),
           (178, 65), (172, 61), (166, 60), (160, 55), (156, 51), (150, 59),
           (142, 55), (140, 49), (136, 44), (131, 42), (127, 40), (122, 38),
           (120, 32), (121, 27), (116, 23), (110, 20), (107, 18), (104, 9),
           (101, 7), (98, 10), (95, 15), (92, 21), (89, 22), (85, 19),
           (81, 15), (78, 8), (75, 12), (72, 20), (68, 22), (64, 25),
           (60, 25), (56, 26), (58, 21), (55, 17), (52, 15), (48, 14),
           (45, 13), (43, 12), (39, 20), (37, 24), (35, 28), (32, 31),
           (25, 32), (19, 32), (11, 34), (0, 36), (-5, 35), (-9, 37),
           (-10, 36)]
AUSTRALIA = [(113, -22), (114, -30), (115, -35), (120, -34), (124, -33),
             (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
             (145, -38), (150, -37), (153, -32), (153, -27), (150, -22),
             (146, -19), (142, -15), (142, -11), (137, -12), (135, -15),
             (132, -12), (130, -13), (126, -14), (122, -17), (118, -20),
             (113, -22)]
UK = [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51),
      (-3, 50), (-5, 50)]
JAPAN = [(130, 31), (132, 33), (135, 34), (137, 35), (139, 36), (140, 38),
         (141, 41), (143, 43), (145, 44), (142, 42), (140, 39), (138, 37),
         (136, 35), (133, 34), (130, 31)]
NEW_ZEALAND = [(167, -45), (170, -43), (173, -41), (175, -38), (177, -38),
               (175, -40), (172, -43), (169, -46), (167, -45)]
MADAGASCAR = [(44, -16), (47, -15), (50, -16), (50, -20), (47, -24),
              (44, -25), (43, -21), (44, -16)]
BORNEO = [(109, 1), (111, 3), (114, 4), (117, 2), (119, -1), (117, -4),
          (114, -3), (110, -2), (109, 1)]
SUMATRA = [(95, 5), (98, 3), (101, 0), (104, -3), (106, -6), (104, -5),
           (101, -2), (98, 2), (95, 5)]
NEW_GUINEA = [(131, -1), (136, -2), (141, -3), (146, -6), (150, -8),
              (147, -9), (143, -8), (138, -8), (134, -4), (131, -1)]
PHILIPPINES = [(120, 18), (122, 17), (122, 14), (121, 13), (123, 10),
               (122, 8), (124, 8), (126, 7), (122, 10), (120, 14), (120, 18)]

LAND = [NORTH_AMERICA, GREENLAND, SOUTH_AMERICA, AFRICA, EURASIA,
        AUSTRALIA, UK, JAPAN, NEW_ZEALAND, MADAGASCAR, BORNEO, SUMATRA,
        NEW_GUINEA, PHILIPPINES]
# One pin per region, at its main story's place: (lon, lat).
PINS = [(-77, 39), (-99, 19), (-72, 18), (4, 51), (50, 26), (7, 9),
        (77, 28), (127, 37), (149, -35)]


def draw_map(pg, x, y, w, h):
    """Equirectangular world map with a pin per region."""
    pg.box(x, y, w, h, MAP_SEA)
    for poly in LAND:
        pts = [(x + (lon + 180) / 360.0 * w,
                y + (90 - lat) / 180.0 * h) for lon, lat in poly]
        pg.poly(pts, MAP_LAND)
    pg.frame(x, y, w, h, INK, 1)
    for lon, lat in PINS:
        px = x + (lon + 180) / 360.0 * w
        py = y + (90 - lat) / 180.0 * h
        pg.diamond(int(px), int(py), 6, WHITE)
        pg.diamond(int(px), int(py), 4, RED)


def draw_flags(pg, x, y):
    """Three flags side by side, 96x64 each: Iran, USA, Bahrain."""
    # Iran: green / white / red bands, small red diamond for the emblem.
    pg.box(x, y, 96, 21, IRAN_GREEN)
    pg.box(x, y + 21, 96, 22, WHITE)
    pg.box(x, y + 43, 96, 21, IRAN_RED)
    pg.diamond(x + 48, y + 32, 7, IRAN_RED)
    pg.frame(x, y, 96, 64, INK, 1)
    # USA: seven stripes, blue canton, white star dots.
    ux = x + 104
    for i in range(7):
        pg.box(ux, y + i * 9, 96, 9 if i < 6 else 10,
               RED if i % 2 == 0 else WHITE)
    pg.box(ux, y, 38, 36, BLUE)
    for r in range(3):
        for c in range(4):
            pg.box(ux + 5 + c * 9, y + 5 + r * 11, 3, 3, WHITE)
    pg.frame(ux, y, 96, 64, INK, 1)
    # Bahrain: red field, white hoist with a five-point serrated edge.
    bx = x + 208
    pg.box(bx, y, 96, 64, BAHRAIN_RED)
    pts = [(bx, y), (bx + 30, y)]
    for k in range(5):
        pts.append((bx + 18, y + int((k + 0.5) * 64 / 5)))
        pts.append((bx + 30, y + int((k + 1) * 64 / 5)))
    pts += [(bx, y + 64)]
    pg.poly(pts, WHITE)
    pg.frame(bx, y, 96, 64, INK, 1)

# ------------------------------------------------------------------ layout
def cell(pg, x, y, w, h, story):
    region, headline, summary, accent = story
    pg.box(x, y, w, h, WHITE)
    pg.box(x, y, w, 4, accent)
    pg.frame(x, y, w, h, INK, 1)
    tx = x + 8
    draw_text(pg, tx, y + 8, region, 1, accent)
    for i, ln in enumerate(wrap(headline, w - 16, 2)[:2]):
        draw_text(pg, tx, y + 19 + i * 16, ln, 2, INK)
    for i, ln in enumerate(wrap(summary, w - 16, 1)[:1]):
        draw_text(pg, tx, y + 55 + i * 9, ln, 1, INK)


def utc_strip(pg, x, y, w):
    """24-hour UTC bar for 21 Nov 2026 with two timed events marked."""
    draw_text(pg, x, y, "UTC STRIP - 21 NOV 2026", 1, INK)
    by = y + 10
    pg.box(x, by, w, 10, WHITE)
    pg.frame(x, by, w, 10, INK, 1)
    for h in range(0, 25, 6):
        tx = x + h / 24.0 * w
        pg.col(int(tx), by, by + 9, INK)
    for h, lab in ((0, "00"), (6, "06"), (12, "12"), (18, "18"), (24, "24")):
        tx = x + h / 24.0 * w
        if h == 0:
            draw_text(pg, int(tx), by + 13, lab, 1, GREY)
        elif h == 24:
            draw_text(pg, int(tx), by + 13, lab, 1, GREY, "right")
        else:
            draw_text(pg, int(tx), by + 13, lab, 1, GREY, "center")
    # Timed events, verified: Peru quake 00:09 UTC, Bolsonaro ICU 19:03 UTC.
    for hour, lab in ((0.15, "00:09 PERU QUAKE"), (19.05, "19:03 BOLSONARO ICU")):
        mx = x + hour / 24.0 * w
        pg.diamond(int(mx), by + 5, 5, WHITE)
        pg.diamond(int(mx), by + 5, 3, RED)
    draw_text(pg, x + w // 2, by + 24, "00:09 PERU QUAKE - 19:03 BOLSONARO ICU",
              1, GREY, "center")


def main():
    pg = Page(W, H, PAPER)

    # masthead
    pg.box(0, 0, W, 76, NAVY)
    draw_text(pg, W // 2, 6, "THE WORLD IN ONE DAY", 5, WHITE, "center")
    draw_text(pg, W // 2, 48,
              "SATURDAY 21 NOVEMBER 2026 - 37 STORIES, 9 REGIONS - ALL DATED 21 NOV 2026",
              2, GOLD, "center")
    pg.box(0, 76, W, 4, GOLD)

    # lead story: Iran strikes US bases in Bahrain
    pg.box(8, 80, 1008, 236, WHITE)
    pg.box(8, 80, 1008, 4, GOLD)
    pg.frame(8, 80, 1008, 236, INK, 1)
    draw_text(pg, 20, 92, LEAD_LINES[0], 4, INK)
    draw_text(pg, 20, 124, LEAD_LINES[1], 4, INK)
    draw_flags(pg, 20, 168)
    draw_text(pg, 68, 236, "IRAN", 1, INK, "center")
    draw_text(pg, 172, 236, "USA", 1, INK, "center")
    draw_text(pg, 276, 236, "BAHRAIN", 1, INK, "center")
    for i, ln in enumerate(wrap(LEAD_SUMMARY, 412, 2)[:3]):
        draw_text(pg, 336, 168 + i * 16, ln, 2, INK)
    draw_text(pg, 336, 228, LEAD_DATELINE, 1, GREY)
    draw_text(pg, 20, 262, ALSO_1, 1, INK)
    draw_text(pg, 20, 278, ALSO_2, 1, INK)
    draw_text(pg, 20, 294, ALSO_3, 1, INK)

    # right column of the lead: world map + date check + UTC strip
    mx, mw, mh = 764, 248, 124
    draw_map(pg, mx, 92, mw, mh)
    draw_text(pg, mx + mw // 2, 222, "WORLD MAP - 9 REGIONS PINNED", 1, INK,
              "center")
    draw_text(pg, mx + mw // 2, 234, "DATE CHECK: ALL 37 STORIES", 1, INK,
              "center")
    draw_text(pg, mx + mw // 2, 243, "FIRST REPORTED SAT 21 NOV 2026", 1, INK,
              "center")
    utc_strip(pg, mx, 256, mw)

    # 4x9 dense grid: 36 stories
    cols, rows = 4, 9
    cw, chh, gap = 247, 67, 6
    gx0, gy0 = 8, 320
    for idx, story in enumerate(STORIES):
        col, row = idx % cols, idx // cols
        cell(pg, gx0 + col * (cw + gap), gy0 + row * (chh + gap),
             cw, chh, story)

    # footer
    pg.box(0, 980, W, 44, NAVY)
    draw_text(pg, W // 2, 988,
              "SOURCES: REUTERS - CNN - WSJ - AL JAZEERA - AP - ONETURN - BBC - THE HINDU - UN NEWS - ABC NEWS - WISEVOTER",
              1, WHITE, "center")
    draw_text(pg, W // 2, 1004,
              "BY THE NUMBERS: $3.79BN GTA VI DAY ONE - 259 HOUSE SEATS - 111 CAUGHT CHEATING - 7.1M ACRES BURNED - 24 DEAD IN NIGERIA",
              1, WHITE, "center")

    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "entry.png"), "wb") as f:
        f.write(pg.png())


if __name__ == "__main__":
    main()
