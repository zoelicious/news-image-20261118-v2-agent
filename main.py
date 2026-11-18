#!/usr/bin/env python3
"""news-image-20261118 v2 (agent account) — one-day world news broadsheet.

Renders a deterministic 1024x1024 RGB PNG with Pillow only (no network,
no text-to-image, no randomness). Every fact comes from the Art Direction
Document (ad-doc-v2.md): 45 stories — 13 numbered cards + 32 one-line
briefs — hero row Gulf / Shenzhen / Alaska, world map with numbered pins,
region legend, sources footer.

Run:  python3 main.py        -> writes entry.png next to this file,
        or /output/entry.png when /output exists (grader layout).
Determinism: same bytes on every run (fixed fonts, fixed layout, no time
or random input). Requires Pillow 10.2.0 and the DejaVu fonts.
"""

import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
MARGIN = 22
CONTENT_W = W - 2 * MARGIN  # 980

# --- Palette (AD doc section 5; max 7 accents + black + cream) ---
CREAM = (247, 242, 230)   # paper #F7F2E6
INK = (17, 17, 17)        # #111111
RED = (179, 39, 30)       # #B3271E accent
SEA = (214, 230, 236)     # map sea, pale blue
LAND = (232, 220, 195)    # map land, pale tan
LAND_LINE = (190, 175, 140)
GREY = (107, 107, 107)    # Global region #6B6B6B
LIGHT_GREY = (120, 118, 110)
PANEL_BG = (255, 253, 247)

REGION = {  # muted region accents, one per region (AD doc section 5)
    "Europe": (47, 93, 138),       # #2F5D8A
    "Middle East": (198, 122, 46),  # #C67A2E
    "Asia": (107, 78, 155),        # #6B4E9B
    "Africa": (62, 122, 78),       # #3E7A4E
    "Americas": (169, 50, 38),     # #A93226
    "Oceania": (46, 125, 123),     # #2E7D7B
    "Global": (107, 107, 107),     # #6B6B6B
}
REGION_ORDER = ["Americas", "Europe", "Africa", "Middle East",
                "Asia", "Oceania", "Global"]

# --- Fonts (DejaVu, shipped with the VM) ---
FONT_DIR = "/usr/share/fonts/truetype/dejavu"
SERIF_B = os.path.join(FONT_DIR, "DejaVuSerif-Bold.ttf")
SERIF = os.path.join(FONT_DIR, "DejaVuSerif.ttf")
SANS_B = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
SANS = os.path.join(FONT_DIR, "DejaVuSans.ttf")

_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


# --- Story data (AD doc v2, verbatim facts; decks may be wrapped only) ---
# (number, region, topic, headline, deck)
CARDS = [
    (1, "Middle East", "Iran War",
     "Kuwait, Bahrain say they intercepted Iranian drones",
     "Iran's army says it aimed at US forces at Ali Al Salem. ADNOC says "
     "its ship was hit in Hormuz; 1 missing, 11 injured."),
    (2, "Asia", "Diplomacy",
     "Xi greets Trump on eve of Trump\u2013Xi\u2013Putin summit",
     "Xi and Putin vowed to \u201clead\u201d a multipolar world; at APEC Xi "
     "urged AI and free-trade cooperation. Talks Thursday."),
    (3, "Americas", "US Politics",
     "Democrat Peltola wins Alaska; Senate now 56\u201344",
     "AP calls it: 144,302 votes to Sullivan's 131,844. A ninth Democratic "
     "gain, the most in a midterm since 1958, AP says."),
    (4, "Europe", "Ukraine War",
     "Russia fires 141 drones at Ukraine overnight",
     "Air force: 126 downed. Officials: 5 killed, 15 injured in a day; "
     "power cut to 80+ Rivne settlements."),
    (5, "Middle East", "Gaza",
     "Board of Peace warns UN the Gaza truce may collapse",
     "First report to the Security Council (obtained by AP) says Israel "
     "blocked the civil administration."),
    (6, "Asia", "Disaster",
     "Cyclone Akvan strengthens in the Bay of Bengal",
     "IMD: landfall in Andhra Pradesh around noon Friday. Odisha readies "
     "up to 204,070 to evacuate."),
    (7, "Europe", "Economy",
     "UK inflation rises to 3.6%, highest in a year",
     "October CPI up from 3.5% as diesel hits a record high, the ONS says."),
    (8, "Africa", "Sudan War",
     "Amnesty: RSF drone strikes killed 37 civilians in El Obeid",
     "It says they should be investigated as war crimes; the RSF denies "
     "responsibility."),
    (9, "Global", "Culture",
     "Grand Theft Auto VI goes on sale after a 13-year wait",
     "Midnight launch starts in New Zealand; Sensor Tower estimates 15m+ "
     "pre-release sales."),
    (10, "Europe", "Health",
     "Europe off track on antibiotic resistance, ECDC warns",
     "Carbapenem-resistant K. pneumoniae bloodstream infections up 72% "
     "since 2019."),
    (11, "Global", "Climate",
     "COP31: 75 countries back T\u00fcrkiye's \u201c35x35\u201d power goal",
     "Electricity 35% of energy use by 2035 (Anadolu). Johan Rockstr\u00f6m "
     "warns of 2.8\u20133\u00b0C."),
    (12, "Asia", "Labour",
     "Bangladesh garment protests shut at least 55 factories",
     "Tk 30,000 minimum wage sought; Dhaka\u2013Mymensingh highway blocked, "
     "police vehicle torched."),
    (13, "Oceania", "Diplomacy",
     "Australia sanctions settler leader Daniella Weiss",
     "Also two others and four groups incl. Nachala, Amana, over West Bank "
     "settlements (Penny Wong)."),
]

# (number, place, one-line brief) — AD doc v2, verbatim
BRIEFS = [
    (14, "Riyadh", "coalition says it downed a Houthi cruise missile."),
    (15, "Jerusalem", "Knesset approves 9 deputy speakers, 2 Arab."),
    (16, "Berlin", "coalition to cut power tax and cap fuel prices."),
    (17, "Germany", "accuses Russia of chemical-weapons breaches."),
    (18, "Cambridge", "\u201chuman\u201d named word of the year."),
    (19, "Shenzhen", "Xi and Lee conclude FTA services talks."),
    (20, "Manila", "Trump claims trade deal; Manila says none signed."),
    (21, "Tokyo", "Japan posts sixth straight monthly trade deficit."),
    (22, "Seoul", "court acquits Daegu mayor in martial-law case."),
    (23, "Singapore", "Princess Aiko on first imperial visit in 20 years."),
    (24, "Bangkok", "Chinese director jailed over collapsed tower."),
    (25, "Lahore", "world's most polluted big city again, AQI 339."),
    (26, "Rawalpindi", "Sri Lanka all out for 98 against Pakistan."),
    (27, "Kuala Lumpur", "ringgit at five-month low."),
    (28, "Asia markets", "Kospi +2%, Hang Seng \u22120.9%."),
    (29, "Oil", "Brent falls 1.4% to $91.82."),
    (30, "China", "Tencent revenue up 8%, below forecasts."),
    (31, "Cook Islands", "Cyclone Xavier reaches Category 5."),
    (32, "New Zealand", "tsunami advisory lifted after 60 cm surges."),
    (33, "Sydney", "Tame Impala sweeps the ARIA Awards."),
    (34, "Australia", "Bancroft says whole team knew of 2018 plot."),
    (35, "Canada", "Carney says China trade no worry for Trump."),
    (36, "Peru", "M5.9 quake off south coast, no damage reported."),
    (37, "Cincinnati", "USA beat Haiti 2\u20130, into Nations League semis."),
    (38, "Monterrey", "Mexico edge Jamaica, set up semi v USA."),
    (39, "Los Angeles", "Grimes scores 47 as Lakers win 9th straight."),
    (40, "Buenos Aires", "deputies debate Malvinas sovereignty bill."),
    (41, "Bolivia", "99 bat species recorded in Madidi park."),
    (42, "Washington", "NSA confirms outage on classified network."),
    (43, "South Africa", "inflation jumps to 5.2%, highest since 2024."),
    (44, "Johannesburg", "SA Rugby seeks full hearing on Erasmus ban."),
    (45, "Sudan", "archaeologists reach Old Dongola church floor."),
]


def wrap(draw, text, fnt, max_w):
    """Greedy word wrap by measured pixel width; returns list of lines."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_lines(draw, text, path, start_size, max_w, max_lines, min_size=8):
    """Wrap text, shrinking the font until it fits in max_lines.

    Returns (font, lines). Guarantees len(lines) <= max_lines unless even
    the minimum size overflows (then lines are hard-truncated with an
    ellipsis on the last line).
    """
    size = start_size
    while size >= min_size:
        fnt = font(path, size)
        lines = wrap(draw, text, fnt, max_w)
        if len(lines) <= max_lines:
            return fnt, lines
        size -= 1
    fnt = font(path, min_size)
    lines = wrap(draw, text, fnt, max_w)[:max_lines]
    if len(lines) == max_lines and lines:
        last = lines[-1]
        while draw.textlength(last + "\u2026", font=fnt) > max_w and len(last) > 1:
            last = last[:-1]
        lines[-1] = last + "\u2026"
    return fnt, lines


def num_badge(draw, cx, cy, n, r=9, fg=(255, 255, 255)):
    """Red numbered circle used for cards 1-13 and map pins."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED,
                 outline=INK, width=1)
    fnt = font(SANS_B, max(7, r - 2))
    txt = str(n)
    tw = draw.textlength(txt, font=fnt)
    th = fnt.getbbox(txt)[3] - fnt.getbbox(txt)[1]
    draw.text((cx - tw / 2, cy - th / 2 - 1), txt, font=fnt, fill=fg)


def kicker_line(draw, x, y, num, region, topic, max_w):
    """One red-number badge + 'REGION \u00b7 TOPIC' caps kicker; returns height."""
    num_badge(draw, x + 9, y + 8, num, r=9)
    fnt = font(SANS_B, 11)
    txt = f"{region.upper()} \u00b7 {topic.upper()}"
    draw.text((x + 22, y + 3), txt, font=fnt, fill=REGION[region])
    return 20


# ---------------------------------------------------------------------------
# Flat diagram illustrations (original drawings, Pillow vector shapes only)
# ---------------------------------------------------------------------------

def _label(draw, x, y, txt, size=9, fill=INK, bold=True, anchor="la"):
    fnt = font(SANS_B if bold else SANS, size)
    draw.text((x, y), txt, font=fnt, fill=fill, anchor=anchor)


def draw_gulf(draw, box):
    """Hero 1: Persian Gulf / Strait of Hormuz schematic."""
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=SEA)
    # Iran landmass (top) and Arabian peninsula (bottom)
    draw.polygon([(x0, y0), (x1, y0), (x1, y0 + 26), (x0 + 210, y0 + 34),
                  (x0 + 120, y0 + 44), (x0, y0 + 40)], fill=LAND,
                 outline=LAND_LINE)
    draw.polygon([(x0, y1), (x1, y1), (x1, y1 - 30), (x0 + 230, y1 - 44),
                  (x0 + 150, y1 - 30), (x0 + 60, y1 - 22)],
                 fill=LAND, outline=LAND_LINE)
    # Gulf water channel between the two landmasses
    draw.polygon([(x0 + 30, y0 + 42), (x0 + 215, y0 + 32), (x1 - 8, y0 + 30),
                  (x1 - 8, y1 - 32), (x0 + 235, y1 - 42), (x0 + 150, y1 - 28),
                  (x0 + 55, y1 - 20)], fill=(168, 205, 220))
    # Strait of Hormuz narrows (right), tanker + drone bursts
    draw.polygon([(x1 - 46, y0 + 44), (x1 - 14, y0 + 52), (x1 - 14, y1 - 46),
                  (x1 - 46, y1 - 52)], fill=(140, 185, 205))
    draw.rectangle([x1 - 78, y0 + 66, x1 - 40, y0 + 76], fill=INK)
    draw.rectangle([x1 - 74, y0 + 58, x1 - 62, y0 + 66], fill=INK)
    draw.rectangle([x1 - 50, y0 + 58, x1 - 44, y0 + 66], fill=INK)
    for cx, cy in ((x0 + 52, y0 + 62), (x0 + 130, y0 + 52)):
        for dx, dy in ((-7, 0), (7, 0), (0, -7), (0, 7), (-5, -5), (5, 5),
                       (-5, 5), (5, -5)):
            draw.line([cx, cy, cx + dx, cy + dy], fill=RED, width=2)
        draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=RED)
    draw.line([x0 + 52, y0 + 62, x0 + 130, y0 + 52], fill=RED, width=1)
    for i in range(6):
        d = 4 + i * 7
        draw.line([x0 + 52 + d, y0 + 62 - 3, x0 + 52 + d, y0 + 62 + 3],
                  fill=RED, width=1)
    _label(draw, x0 + 6, y0 + 4, "IRAN", 9)
    _label(draw, x0 + 6, y0 + 22, "KUWAIT", 8, fill=GREY)
    _label(draw, x0 + 78, y1 - 34, "BAHRAIN", 8, fill=GREY)
    _label(draw, x0 + 236, y1 - 14, "UAE", 8, fill=GREY)
    _label(draw, x1 - 62, y0 + 30, "HORMUZ", 8, fill=INK)
    _label(draw, x0 + 150, y0 + 88, "GULF", 8, fill=(70, 110, 130))


def draw_shenzhen(draw, box):
    """Hero 2: Shenzhen APEC round table with flags + skyline."""
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=(222, 232, 226))
    # skyline silhouettes
    for bx, bw, bh in ((8, 26, 46), (40, 20, 62), (66, 30, 38), (102, 18, 56),
                       (210, 24, 50), (240, 18, 66), (264, 30, 40)):
        draw.rectangle([x0 + bx, y1 - 46 - bh, x0 + bx + bw, y1 - 46],
                       fill=(150, 165, 175))
    # round table
    cx, cy = (x0 + x1) // 2, y0 + 74
    draw.ellipse([cx - 92, cy - 20, cx + 92, cy + 20], fill=(196, 122, 46),
                 outline=INK, width=1)
    draw.ellipse([cx - 92, cy - 20, cx + 92, cy - 8], fill=(214, 150, 80))
    # three flags on the table (US, China, Russia — muted blocks)
    for fx, cols in ((-58, (RED, (255, 255, 255), (47, 93, 138))),
                     (-8, (RED, (255, 220, 60))),
                     (42, ((255, 255, 255), (47, 93, 138), RED))):
        for i, c in enumerate(cols):
            draw.rectangle([cx + fx, cy - 14 + i * 5, cx + fx + 34,
                            cy - 9 + i * 5], fill=c)
        draw.rectangle([cx + fx, cy - 14, cx + fx + 34, cy + 1],
                       outline=INK, width=1)
    # chairs
    for px in (cx - 70, cx - 20, cx + 30, cx + 76):
        draw.ellipse([px - 9, cy + 14, px + 9, cy + 30], fill=INK)
    _label(draw, x0 + 6, y0 + 4, "SHENZHEN", 9)
    _label(draw, x1 - 6, y0 + 4, "THURSDAY", 9, fill=GREY, anchor="ra")


def draw_alaska(draw, box):
    """Hero 3: US Capitol dome + Alaska + Senate 56-44 bar."""
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=(224, 232, 226))
    # capitol dome (left, kept clear of the Senate bar below)
    cx, cy = x0 + 58, y0 + 58
    draw.rectangle([cx - 46, cy - 4, cx + 46, cy + 6], fill=INK)
    draw.rectangle([cx - 34, cy - 18, cx + 34, cy - 4], fill=INK)
    draw.pieslice([cx - 22, cy - 44, cx + 22, cy - 2], 180, 360, fill=INK)
    draw.rectangle([cx - 2, cy - 54, cx + 2, cy - 42], fill=INK)
    draw.ellipse([cx - 4, cy - 58, cx + 4, cy - 50], fill=INK)
    for i in range(5):
        draw.rectangle([cx - 28 + i * 12, cy - 16, cx - 21 + i * 12, cy - 6],
                       fill=CREAM)
    # Alaska shape (blue, right-top)
    draw.polygon([(x1 - 128, y0 + 26), (x1 - 96, y0 + 14), (x1 - 62, y0 + 20),
                  (x1 - 52, y0 + 34), (x1 - 70, y0 + 48), (x1 - 104, y0 + 52),
                  (x1 - 126, y0 + 42)], fill=(47, 93, 138))
    _label(draw, x1 - 92, y0 + 24, "ALASKA", 9, fill=(255, 255, 255),
           anchor="ma")
    # Senate bar: 56 DEM blue / 44 REP red, 100 seats (labels above the bar,
    # clear of the dome, which ends well above them)
    bx, by, bw = x0 + 10, y1 - 24, x1 - x0 - 20
    for i in range(100):
        c = (47, 93, 138) if i < 56 else (169, 50, 38)
        draw.rectangle([bx + i * (bw / 100), by,
                        bx + (i + 1) * (bw / 100) - 1, by + 12], fill=c)
    _label(draw, x0 + 10, by - 13, "56 DEM", 9, fill=(47, 93, 138))
    _label(draw, x1 - 10, by - 13, "44 REP", 9, fill=(169, 50, 38),
           anchor="ra")


HERO_DRAW = {1: draw_gulf, 2: draw_shenzhen, 3: draw_alaska}


def draw_icon(draw, box, n):
    """Small flat illustration for grid cards 4-13."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    w, h = x1 - x0, y1 - y0
    if n == 4:  # drones + pylon
        draw.rectangle(box, fill=(216, 226, 232))
        draw.line([cx, y0 + 8, cx, y1 - 6], fill=INK, width=3)
        draw.line([cx - 16, y0 + 22, cx + 16, y0 + 22], fill=INK, width=2)
        draw.line([cx - 12, y0 + 32, cx + 12, y0 + 32], fill=INK, width=2)
        for dx, dy in ((-58, -8), (-30, -16), (34, -14), (58, -4)):
            draw.line([cx + dx - 6, cy + dy, cx + dx + 6, cy + dy],
                      fill=INK, width=2)
            draw.line([cx + dx, cy + dy - 3, cx + dx, cy + dy + 3],
                      fill=INK, width=2)
    elif n == 5:  # olive branch over hills
        draw.rectangle(box, fill=(240, 224, 216))
        draw.polygon([(x0, y1), (x0 + 60, y0 + 26), (x1, y1)], fill=(150, 170, 130))
        draw.polygon([(x0 + 70, y1), (x0 + 130, y0 + 34), (x1, y1)],
                     fill=(120, 145, 105))
        draw.arc([cx - 52, y0 + 2, cx + 52, y0 + 44], 200, 340, fill=(62, 122, 78), width=3)
        for a in (215, 245, 275, 305, 330):
            import math
            rx, ry = cx + 46 * math.cos(math.radians(a)), y0 + 22 + 20 * math.sin(math.radians(a))
            draw.ellipse([rx - 7, ry - 3, rx + 7, ry + 3], fill=(62, 122, 78))
    elif n == 6:  # cyclone spiral over the Bay of Bengal
        draw.rectangle(box, fill=(206, 224, 232))
        draw.polygon([(x0 + 30, y0 + 8), (x0 + 62, y0 + 4), (x0 + 74, y0 + 30),
                      (x0 + 52, y0 + 46), (x0 + 26, y0 + 36)], fill=LAND,
                     outline=LAND_LINE)
        for r in (22, 16, 10, 5):
            draw.arc([cx + 18 - r, cy - 2 - r, cx + 18 + r, cy - 2 + r],
                     30 + r * 8, 330, fill=(107, 78, 155), width=3)
        _label(draw, x1 - 4, y1 - 12, "BAY OF BENGAL", 7, fill=GREY, anchor="ra")
    elif n == 7:  # petrol pump + rising arrow, 3.6%
        draw.rectangle(box, fill=(232, 228, 210))
        draw.rectangle([x0 + 14, y0 + 8, x0 + 52, y1 - 8], fill=INK)
        draw.rectangle([x0 + 22, y0 + 16, x0 + 44, y0 + 30], fill=CREAM)
        _label(draw, x0 + 33, y0 + 17, "\u00a3", 12, fill=INK, anchor="ma")
        draw.line([x0 + 66, y1 - 12, x0 + 104, y0 + 26, x1 - 12, y0 + 10],
                  fill=RED, width=3)
        draw.polygon([(x1 - 12, y0 + 10), (x1 - 26, y0 + 10), (x1 - 12, y0 + 24)],
                     fill=RED)
        _label(draw, x1 - 6, y0 + 2, "3.6%", 12, fill=RED, anchor="ra")
    elif n == 8:  # Sudan map + magnifier + document
        draw.rectangle(box, fill=(232, 222, 204))
        draw.polygon([(x0 + 30, y0 + 6), (x0 + 74, y0 + 6), (x0 + 82, y0 + 26),
                      (x0 + 66, y0 + 46), (x0 + 34, y0 + 44), (x0 + 24, y0 + 24)],
                     fill=(198, 122, 46), outline=INK)
        draw.ellipse([x1 - 66, y0 + 6, x1 - 22, y0 + 50], outline=INK, width=3)
        draw.line([x1 - 32, y0 + 42, x1 - 14, y1 - 8], fill=INK, width=3)
        _label(draw, x0 + 8, y1 - 12, "EL OBEID", 7, fill=GREY)
    elif n == 9:  # game controller + midnight clock
        draw.rectangle(box, fill=(226, 224, 236))
        draw.rounded_rectangle([x0 + 12, y0 + 16, x0 + 96, y0 + 46], radius=10,
                               fill=INK)
        draw.line([x0 + 30, y0 + 26, x0 + 30, y0 + 36], fill=CREAM, width=3)
        draw.line([x0 + 25, y0 + 31, x0 + 35, y0 + 31], fill=CREAM, width=3)
        for dx, dy in ((58, -4), (68, 4), (58, 12)):
            draw.ellipse([x0 + dx, y0 + 22 + dy, x0 + dx + 6, y0 + 28 + dy],
                         fill=CREAM)
        draw.ellipse([x1 - 48, y0 + 6, x1 - 6, y0 + 48], fill=CREAM,
                     outline=INK, width=2)
        draw.line([x1 - 27, y0 + 27, x1 - 27, y0 + 13], fill=INK, width=2)
        draw.line([x1 - 27, y0 + 27, x1 - 27, y0 + 41], fill=INK, width=2)
    elif n == 10:  # capsule + bacteria, arrow up
        draw.rectangle(box, fill=(222, 232, 226))
        draw.rounded_rectangle([x0 + 10, y0 + 16, x0 + 74, y0 + 34], radius=9,
                               fill=(47, 93, 138))
        draw.rounded_rectangle([x0 + 42, y0 + 16, x0 + 74, y0 + 34], radius=9,
                               fill=(230, 230, 230), outline=INK, width=1)
        for dx, dy in ((96, 10), (112, 26), (128, 12)):
            draw.ellipse([x0 + dx, y0 + dy, x0 + dx + 12, y0 + dy + 7],
                         fill=(62, 122, 78))
        draw.line([x1 - 22, y1 - 8, x1 - 22, y0 + 8], fill=RED, width=3)
        draw.polygon([(x1 - 30, y0 + 16), (x1 - 14, y0 + 16), (x1 - 22, y0 + 4)],
                     fill=RED)
    elif n == 11:  # globe + thermometer
        draw.rectangle(box, fill=(214, 230, 226))
        draw.ellipse([x0 + 12, y0 + 6, x0 + 66, y0 + 52], fill=(120, 180, 200),
                     outline=INK, width=1)
        draw.arc([x0 + 18, y0 + 12, x0 + 60, y0 + 46], 300, 120,
                 fill=(62, 122, 78), width=3)
        draw.arc([x0 + 30, y0 + 30, x0 + 66, y0 + 52], 120, 300,
                 fill=(62, 122, 78), width=3)
        draw.rectangle([x1 - 34, y0 + 8, x1 - 24, y0 + 38], fill=CREAM,
                       outline=INK, width=1)
        draw.ellipse([x1 - 38, y0 + 34, x1 - 20, y0 + 52], fill=RED,
                     outline=INK, width=1)
        _label(draw, x1 - 4, y0 + 2, "3\u00b0C", 9, fill=RED, anchor="ra")
    elif n == 12:  # factory with SHUT sign
        draw.rectangle(box, fill=(232, 226, 208))
        draw.rectangle([x0 + 16, y0 + 22, x0 + 96, y1 - 8], fill=(150, 150, 145))
        draw.polygon([(x0 + 16, y0 + 22), (x0 + 36, y0 + 6), (x0 + 56, y0 + 22)],
                     fill=(120, 120, 115))
        draw.rectangle([x0 + 104, y0 + 8, x0 + 116, y1 - 8], fill=INK)
        for wx in (26, 48, 70):
            draw.rectangle([x0 + wx, y0 + 30, x0 + wx + 12, y0 + 42],
                           fill=CREAM)
        draw.rectangle([x1 - 58, y0 + 12, x1 - 8, y0 + 28], fill=(230, 200, 60),
                       outline=INK, width=1)
        _label(draw, x1 - 33, y0 + 14, "SHUT", 9, fill=INK, anchor="ma")
    elif n == 13:  # padlock + parliament building
        draw.rectangle(box, fill=(226, 228, 232))
        draw.rectangle([x0 + 12, y1 - 22, x0 + 100, y1 - 6], fill=(150, 160, 170))
        draw.polygon([(x0 + 12, y1 - 22), (x0 + 56, y0 + 12), (x0 + 100, y1 - 22)],
                     fill=(130, 140, 150))
        for px in (24, 44, 64, 84):
            draw.rectangle([x0 + px, y1 - 20, x0 + px + 6, y1 - 8],
                           fill=CREAM)
        draw.rounded_rectangle([x1 - 46, y0 + 14, x1 - 10, y0 + 44], radius=4,
                               fill=(169, 50, 38), outline=INK, width=1)
        draw.arc([x1 - 40, y0 + 2, x1 - 16, y0 + 22], 180, 360, fill=INK,
                 width=3)
        draw.ellipse([x1 - 32, y0 + 24, x1 - 24, y0 + 32], fill=CREAM)
        draw.rectangle([x1 - 30, y0 + 30, x1 - 26, y0 + 38], fill=CREAM)


# ---------------------------------------------------------------------------
# World map (equirectangular, simplified original coastline polygons)
# ---------------------------------------------------------------------------

NA = [(-168, 66), (-158, 58), (-152, 60), (-140, 60), (-135, 58), (-130, 54),
      (-125, 49), (-124, 42), (-120, 34), (-114, 29), (-110, 24), (-105, 20),
      (-97, 16), (-94, 17), (-90, 14), (-86, 12), (-83, 9), (-79, 9),
      (-81, 13), (-83, 15), (-87, 16), (-88, 18), (-90, 21), (-97, 26),
      (-93, 30), (-89, 30), (-84, 30), (-81, 26), (-80, 32), (-76, 35),
      (-74, 40), (-70, 42), (-68, 45), (-65, 44), (-60, 47), (-55, 47),
      (-60, 50), (-65, 50), (-60, 52), (-64, 58), (-68, 55), (-72, 58),
      (-78, 62), (-85, 66), (-90, 66), (-95, 69), (-110, 68), (-125, 70),
      (-140, 70), (-155, 71), (-165, 68)]
SA = [(-79, 9), (-77, 4), (-80, -3), (-81, -6), (-77, -12), (-72, -18),
      (-70, -23), (-70, -30), (-72, -37), (-73, -44), (-74, -50), (-70, -54),
      (-66, -55), (-68, -50), (-65, -45), (-62, -41), (-58, -38), (-52, -33),
      (-48, -28), (-41, -23), (-39, -17), (-35, -9), (-35, -6), (-40, -3),
      (-44, -2), (-50, 0), (-53, 4), (-58, 6), (-62, 9), (-68, 11),
      (-72, 12), (-76, 10)]
AF = [(-6, 35), (-10, 31), (-15, 27), (-17, 21), (-17, 15), (-15, 11),
      (-13, 8), (-8, 5), (-4, 5), (0, 6), (6, 4), (9, 4), (9, -1),
      (12, -5), (13, -10), (12, -17), (14, -22), (16, -28), (19, -34),
      (26, -34), (32, -29), (35, -24), (40, -16), (40, -11), (39, -5),
      (41, -2), (46, 0), (51, 2), (51, 11), (44, 11), (40, 15), (38, 18),
      (37, 22), (34, 27), (32, 31), (22, 33), (11, 34), (10, 37), (5, 37),
      (-1, 35)]
EU = [(-10, 36), (-9, 38), (-9, 43), (-2, 44), (-1, 46), (-5, 48), (-2, 50),
      (2, 51), (4, 53), (7, 54), (8, 57), (11, 58), (18, 56), (21, 55),
      (24, 58), (21, 60), (18, 62), (12, 64), (18, 69), (25, 71), (30, 70),
      (35, 67), (40, 67), (45, 68), (50, 68), (55, 68), (60, 69), (60, 62),
      (55, 55), (50, 52), (45, 48), (40, 47), (35, 45), (30, 46), (28, 44),
      (23, 40), (20, 40), (22, 37), (26, 36), (28, 37), (30, 36), (27, 37),
      (23, 36), (19, 42), (16, 44), (12, 44), (8, 44), (3, 42), (0, 40),
      (-2, 37), (-6, 36)]
AS = [(60, 69), (65, 69), (75, 72), (85, 73), (95, 75), (105, 77), (115, 73),
      (125, 72), (135, 71), (145, 72), (155, 70), (162, 66), (170, 66),
      (178, 65), (178, 62), (170, 60), (162, 58), (158, 52), (155, 55),
      (150, 60), (142, 59), (140, 55), (138, 50), (135, 43), (130, 42),
      (127, 40), (122, 38), (120, 32), (122, 28), (118, 25), (110, 20),
      (108, 15), (105, 9), (103, 7), (100, 8), (98, 12), (95, 16), (92, 21),
      (90, 22), (88, 22), (86, 20), (83, 18), (80, 15), (77, 8), (75, 12),
      (72, 20), (68, 23), (65, 25), (61, 25), (58, 26), (56, 27), (54, 27),
      (52, 28), (50, 29), (48, 30), (48, 26), (44, 22), (42, 18), (40, 15),
      (43, 12), (45, 13), (48, 14), (52, 15), (55, 17), (58, 20), (59, 22),
      (57, 25), (56, 27), (54, 25), (52, 26), (50, 26), (50, 30), (48, 30),
      (44, 29), (40, 31), (36, 36), (30, 36), (27, 37), (30, 41), (33, 42),
      (36, 42), (39, 41), (41, 42), (44, 43), (47, 44), (50, 45), (50, 48),
      (50, 52), (52, 55), (55, 57), (58, 60), (60, 63)]
AU = [(114, -22), (114, -30), (115, -33), (118, -35), (124, -33), (129, -32),
      (132, -32), (135, -35), (138, -35), (140, -38), (145, -38), (150, -37),
      (153, -32), (153, -27), (150, -23), (146, -19), (142, -15), (142, -11),
      (137, -12), (135, -15), (132, -12), (130, -13), (126, -14), (122, -17),
      (118, -20)]
UK = [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (1, 53), (1, 51),
      (-3, 50)]
JP = [(130, 31), (132, 33), (135, 34), (137, 35), (139, 37), (140, 39),
      (141, 41), (143, 42), (145, 44), (143, 44), (141, 40), (140, 36),
      (137, 34), (134, 34), (131, 33)]
NZ = [(167, -45), (170, -43), (173, -41), (175, -38), (178, -38),
      (175, -40), (173, -42), (169, -46)]
MG = [(44, -16), (47, -15), (50, -16), (50, -20), (47, -25), (44, -25),
      (43, -20)]
IDN = [(95, 5), (100, 0), (105, -3), (110, -7), (115, -8), (120, -9),
       (125, -9), (130, -4), (135, -3), (140, -4), (141, -1), (138, 1),
       (132, 0), (128, 2), (122, 1), (118, 0), (112, -2), (106, -2),
       (100, -1)]
LAND_POLYS = [NA, SA, AF, EU, AS, AU, UK, JP, NZ, MG, IDN]

# (lon, lat) of numbered stories 1-13; (dx, dy) nudges in px for crowded pins
PIN_LONLAT = {
    1: (48, 26, 10, -4), 2: (114, 22.5, 0, 0), 3: (-150, 64, 0, 0),
    4: (32, 49, 6, -2), 5: (34.5, 31.5, 8, 8), 6: (85, 16, 0, 0),
    7: (-1, 54, -8, -6), 8: (30.2, 13.2, 0, 4), 9: (172, -41, 0, 0),
    10: (18, 59, 8, -6), 11: (33, 39, 6, 2), 12: (90.4, 23.8, 0, 0),
    13: (149, -35, 0, 0),
}
# (lon, lat) of brief dots 14-45
DOT_LONLAT = {
    14: (46.7, 24.6), 15: (35.2, 31.8), 16: (13.4, 52.5), 17: (10, 51),
    18: (-0.1, 52.2), 19: (114, 22.5), 20: (121, 14.6), 21: (139.7, 35.7),
    22: (127, 37.5), 23: (103.8, 1.35), 24: (100.5, 13.75),
    25: (74.3, 31.5), 26: (73, 33.6), 27: (101.7, 3.1), 28: (114.2, 22.3),
    29: (-0.1, 51.5), 30: (114, 22.5), 31: (-160, -21), 32: (172, -41),
    33: (151.2, -33.9), 34: (115.9, -31.95), 35: (-75.7, 45.4),
    36: (-77, -12), 37: (-84.5, 39.1), 38: (-100.3, 25.7),
    39: (-118.2, 34), 40: (-58.4, -34.6), 41: (-68, -14),
    42: (-77, 38.9), 43: (28, -26), 44: (28, -26.2), 45: (30.5, 19.2),
}
PIN_REGION = {1: "Middle East", 2: "Asia", 3: "Americas", 4: "Europe",
              5: "Middle East", 6: "Asia", 7: "Europe", 8: "Africa",
              9: "Global", 10: "Europe", 11: "Global", 12: "Asia",
              13: "Oceania"}


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

DOT_REGION = {
    14: "Middle East", 15: "Middle East", 16: "Europe", 17: "Europe",
    18: "Europe", 19: "Asia", 20: "Asia", 21: "Asia", 22: "Asia",
    23: "Asia", 24: "Asia", 25: "Asia", 26: "Asia", 27: "Asia",
    28: "Asia", 29: "Global", 30: "Asia", 31: "Oceania", 32: "Oceania",
    33: "Oceania", 34: "Oceania", 35: "Americas", 36: "Americas",
    37: "Americas", 38: "Americas", 39: "Americas", 40: "Americas",
    41: "Americas", 42: "Americas", 43: "Africa", 44: "Africa",
    45: "Africa",
}


def draw_masthead(draw):
    # Kicker row
    fnt = font(SANS_B, 14)
    draw.text((MARGIN, 8), "THE DAY IN WORLD NEWS", font=fnt, fill=RED)
    right = "45 STORIES \u00b7 6 CONTINENTS \u00b7 ONE DAY"
    draw.text((W - MARGIN, 8), right, font=fnt, fill=INK, anchor="ra")
    # Masthead: largest serif bold that fits one line
    size = 64
    while size > 40:
        fnt = font(SERIF_B, size)
        if draw.textlength("Wednesday 18 November 2026", font=fnt) <= CONTENT_W:
            break
        size -= 1
    draw.text((MARGIN, 26), "Wednesday 18 November 2026", font=fnt, fill=INK)
    # Rules: thick black + segmented region-colour bar
    draw.rectangle([MARGIN, 98, W - MARGIN, 101], fill=INK)
    seg = CONTENT_W / len(REGION_ORDER)
    for i, reg in enumerate(REGION_ORDER):
        x0 = MARGIN + i * seg
        draw.rectangle([x0, 104, x0 + seg, 108], fill=REGION[reg])


def draw_hero(draw, y, h):
    pw, gap = 320, 10
    for i, card in enumerate(CARDS[:3]):
        num, region, topic, headline, deck = card
        x = MARGIN + i * (pw + gap)
        draw.rectangle([x, y, x + pw, y + h], fill=PANEL_BG, outline=INK,
                       width=1)
        HERO_DRAW[num](draw, (x + 1, y + 1, x + pw - 1, y + 113))
        draw.line([x, y + 113, x + pw, y + 113], fill=INK, width=1)
        kicker_line(draw, x + 6, y + 118, num, region, topic, pw - 12)
        hf, hl = fit_lines(draw, headline, SERIF_B, 20, pw - 14, 3, 15)
        yy = y + 142
        for line in hl:
            draw.text((x + 7, yy), line, font=hf, fill=INK)
            yy += 23 if hf.size >= 19 else 21
        df, dl = fit_lines(draw, deck, SANS, 11, pw - 14, 3, 9)
        yy = y + h - 6 - len(dl) * 14
        for line in dl:
            draw.text((x + 7, yy), line, font=df, fill=(40, 40, 40))
            yy += 14


def draw_grid(draw, y, h):
    cols, rows = 5, 2
    cw = (CONTENT_W - (cols - 1) * 8) // cols   # 192
    ch = (h - (rows - 1) * 8) // rows           # 158
    for idx, card in enumerate(CARDS[3:]):
        num, region, topic, headline, deck = card
        r, c = divmod(idx, cols)
        x = MARGIN + c * (cw + 8)
        yy = y + r * (ch + 8)
        draw.rectangle([x, yy, x + cw, yy + ch], fill=PANEL_BG,
                       outline=INK, width=1)
        draw_icon(draw, (x + 1, yy + 1, x + cw - 1, yy + 45), num)
        draw.line([x, yy + 45, x + cw, yy + 45], fill=INK, width=1)
        # kicker: small badge + caps region/topic
        num_badge(draw, x + 13, yy + 57, num, r=8)
        kf = font(SANS_B, 9)
        ktxt = f"{region.upper()} \u00b7 {topic.upper()}"
        if draw.textlength(ktxt, font=kf) > cw - 28:
            kf = font(SANS_B, 8)
        draw.text((x + 24, yy + 51), ktxt, font=kf, fill=REGION[region])
        hf, hl = fit_lines(draw, headline, SERIF_B, 14, cw - 12, 3, 11)
        ty = yy + 68
        lh = 17 if hf.size >= 13 else 15
        for line in hl:
            draw.text((x + 6, ty), line, font=hf, fill=INK)
            ty += lh
        df, dl = fit_lines(draw, deck, SANS, 10, cw - 12, 4, 8)
        dy = yy + ch - 4 - len(dl) * 12
        for line in dl:
            draw.text((x + 6, dy), line, font=df, fill=(40, 40, 40))
            dy += 12


def draw_map(draw, box):
    """World map with numbered pins 1-13 and dots for briefs 14-45."""
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=SEA, outline=INK, width=1)
    w, h = x1 - x0, y1 - y0
    lon0, lon1, lat0, lat1 = -170, 190, 83, -57
    sx = w / (lon1 - lon0)
    sy = h / (lat0 - lat1)

    def proj(lon, lat):
        return (x0 + (lon - lon0) * sx, y0 + (lat0 - lat) * sy)

    for poly in LAND_POLYS:
        pts = [proj(lon, lat) for lon, lat in poly]
        draw.polygon(pts, fill=LAND, outline=LAND_LINE)
    # brief dots first (under pins)
    for n, (lon, lat) in DOT_LONLAT.items():
        px, py = proj(lon, lat)
        c = REGION[DOT_REGION[n]]
        draw.ellipse([px - 2.5, py - 2.5, px + 2.5, py + 2.5], fill=c,
                     outline=(255, 255, 255), width=1)
    # numbered pins with hairline nudges where crowded
    for n, (lon, lat, dx, dy) in PIN_LONLAT.items():
        px, py = proj(lon, lat)
        qx, qy = px + dx, py + dy
        if dx or dy:
            draw.line([px, py, qx, qy], fill=INK, width=1)
            draw.ellipse([px - 1.5, py - 1.5, px + 1.5, py + 1.5], fill=INK)
        num_badge(draw, qx, qy, n, r=8)


def draw_bottom(draw, y, h):
    # Section headers
    hf = font(SANS_B, 13)
    draw.text((MARGIN, y), "WHERE IT HAPPENED", font=hf, fill=INK)
    draw.text((MARGIN, y), "WHERE IT HAPPENED", font=hf, fill=INK)
    bx = MARGIN + 340
    draw.text((bx, y), "ALSO ON WEDNESDAY 18 NOVEMBER", font=hf, fill=INK)
    draw.line([MARGIN, y + 18, MARGIN + 330, y + 18], fill=INK, width=1)
    draw.line([bx, y + 18, W - MARGIN, y + 18], fill=INK, width=1)
    # Map
    map_box = (MARGIN, y + 24, MARGIN + 330, y + 24 + 208)
    draw_map(draw, map_box)
    # Legend under the map (two rows)
    ly = y + 24 + 208 + 10
    lf = font(SANS_B, 10)
    tf = font(SANS, 10)
    lx = MARGIN
    for i, reg in enumerate(REGION_ORDER[:4]):
        draw.ellipse([lx, ly + 2, lx + 8, ly + 10], fill=REGION[reg])
        draw.text((lx + 12, ly), reg, font=tf, fill=INK)
        lx += 12 + int(draw.textlength(reg, font=tf)) + 12
    lx = MARGIN
    ly += 17
    for reg in REGION_ORDER[4:]:
        draw.ellipse([lx, ly + 2, lx + 8, ly + 10], fill=REGION[reg])
        draw.text((lx + 12, ly), reg, font=tf, fill=INK)
        lx += 12 + int(draw.textlength(reg, font=tf)) + 12
    ly += 17
    num_badge(draw, MARGIN + 8, ly + 5, 1, r=8)
    draw.text((MARGIN + 20, ly), "numbered pin: stories 1\u201313 above",
              font=tf, fill=INK)
    draw.ellipse([MARGIN + 218, ly + 2, MARGIN + 226, ly + 10], fill=GREY)
    draw.text((MARGIN + 230, ly), "dot: briefs 14\u201345", font=tf, fill=INK)
    # Briefs list, two columns, one line each; auto-fit font size
    col_w = (W - MARGIN - bx - 14) // 2
    size = 10
    bf = font(SANS, size)
    while size > 8:
        bf = font(SANS, size)
        nbf = font(SANS_B, size)
        worst = 0
        for n, place, text in BRIEFS:
            wd = (draw.textlength(f"{n} ", font=nbf)
                  + draw.textlength(f"{place}: {text}", font=bf))
            worst = max(worst, wd)
        if worst <= col_w:
            break
        size -= 1
    nbf = font(SANS_B, size)
    bf = font(SANS, size)
    row_h = (h - 24) / 16
    for i, (n, place, text) in enumerate(BRIEFS):
        col, row = divmod(i, 16)
        xx = bx + col * (col_w + 14)
        yy = y + 24 + row * row_h + 2
        draw.text((xx, yy), f"{n} ", font=nbf, fill=RED)
        off = draw.textlength(f"{n} ", font=nbf)
        draw.text((xx + off, yy), f"{place}: {text}", font=bf, fill=INK)


def draw_footer(draw, y):
    fnt = font(SANS, 10)
    line1 = ("Every story was reported on Wednesday 18 November 2026; "
             "disputed claims are attributed.")
    line2 = ("Sources: AP \u00b7 Reuters \u00b7 AFP \u00b7 BBC \u00b7 Al Jazeera "
             "\u00b7 UN News. Original drawings.")
    draw.text((W // 2, y), line1, font=fnt, fill=(60, 60, 60), anchor="ma")
    draw.text((W // 2, y + 14), line2, font=fnt, fill=(60, 60, 60),
              anchor="ma")


def build():
    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)
    draw_masthead(draw)
    draw_hero(draw, 113, 236)
    draw_grid(draw, 357, 324)
    draw_bottom(draw, 689, 296)
    draw_footer(draw, 991)
    return img


def main():
    out_dir = Path("/output")
    out = (out_dir / "entry.png" if out_dir.is_dir()
           else Path(__file__).resolve().parent / "entry.png")
    img = build()
    img.save(out, format="PNG")
    print(f"wrote {out} ({img.size[0]}x{img.size[1]} RGB)")


if __name__ == "__main__":
    main()
