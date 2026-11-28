"""Night over the Nile: one tall character-art piece, rendered from code.
Usage: python nile.py OUTDIR [--still]"""
import sys, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

N, MS = 24, 110  # frames, ms per frame (seamless loop)

NAVY = np.array([6, 10, 28.])
DEEP = np.array([14, 28, 66.])
CYAN = np.array([46, 214, 232.])
TEAL = np.array([18, 108, 156.])
AMBER = np.array([255, 170, 48.])
EMBER = np.array([150, 70, 28.])
WHITE = np.array([238, 240, 250.])

SKILLS = ["python", "java", "javascript", "typescript", "c", "c++", "sql", "postgresql", "mysql", "mongodb",
          "spark", "kafka", "tensorflow", "pytorch", "langchain", "mlflow", "huggingface", "flask", "django",
          "node.js", "aws", "gcp", "azure", "docker", "kubernetes", "html", "css", "react", "vite", "vercel",
          "firebase", "supabase", "git", "linux", "bash", "vscode"]

FONT = {  # 5x7 pixel letters
    "A": "01110 10001 10001 11111 10001 10001 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "I": "11111 00100 00100 00100 00100 00100 11111", "Y": "10001 10001 01010 00100 00100 00100 00100",
    "N": "10001 11001 11001 10101 10011 10011 10001",
    "a": "00000 00000 01110 00001 01111 10001 01111", "l": "01100 00100 00100 00100 00100 00100 01110",
    "i": "00100 00000 01100 00100 00100 00100 01110", "c": "00000 00000 01110 10000 10000 10001 01110",
    "r": "00000 00000 10110 11001 10000 10000 10000", "o": "00000 00000 01110 10001 10001 10001 01110",
    "@": "01110 10001 10111 10101 10111 10000 01110", ":": "00000 00100 00100 00000 00100 00100 00000",
    "~": "00000 00000 01000 10101 00010 00000 00000", "$": "00100 01111 10100 01110 00101 11110 00100",
}

# line glyphs drawn by hand (up, right, down, left, style) so every platform shows them
LINES = {"─": (0, 1, 0, 1, 0), "│": (1, 0, 1, 0, 0), "┃": (1, 0, 1, 0, 0), "╭": (0, 1, 1, 0, 0), "╮": (0, 0, 1, 1, 0),
         "╰": (1, 1, 0, 0, 0), "╯": (1, 0, 0, 1, 0), "┌": (0, 1, 1, 0, 0), "┐": (0, 0, 1, 1, 0), "└": (1, 1, 0, 0, 0),
         "┘": (1, 0, 0, 1, 0), "╌": (0, 1, 0, 1, 1), "╎": (1, 0, 1, 0, 1), "═": (0, 1, 0, 1, 2), "║": (1, 0, 1, 0, 2),
         "╔": (0, 1, 1, 0, 2), "╗": (0, 0, 1, 1, 2), "╚": (1, 1, 0, 0, 2), "╝": (1, 0, 0, 1, 2)}

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + .5) / 16


def vnoise(x, y, seed=0):
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    xf, yf = x - xi, y - yi

    def h(a, b):
        n = (a * 374761393 + b * 668265263 + seed * 1442695041) & 0xffffffff
        n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
        return (n ^ (n >> 16)) / 0xffffffff
    u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    return (h(xi, yi) * (1 - u) + h(xi + 1, yi) * u) * (1 - v) + (h(xi, yi + 1) * (1 - u) + h(xi + 1, yi + 1) * u) * v


def fbm(x, y, seed=0, o=4):
    return sum(vnoise(x * 2 ** i, y * 2 ** i, seed + i) * .5 ** i for i in range(o)) / (2 - .5 ** (o - 1))


def font_path(bold):
    for p, i in [("/System/Library/Fonts/Menlo.ttc", 1 if bold else 0),
                 ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono%s.ttf" % ("-Bold" if bold else ""), 0)]:
        if os.path.exists(p):
            return p, i
    raise SystemExit("no monospace font found")


class Grid:
    """A character canvas: every cell has a glyph, a glyph colour and a ground colour, per frame."""

    def __init__(s, W, rows, cw, ch):
        s.W, s.cw, s.ch, s.cols, s.rows = W, cw, ch, W // cw, rows
        p, i = font_path(True)
        s.font = ImageFont.truetype(p, int(ch * .86), index=i)
        s.cache, s.glyphs, s.masks = {}, [], []
        s.g = np.zeros((N, rows, s.cols), np.int32)
        s.fg = np.zeros((N, rows, s.cols, 3), np.float32)
        s.bg = np.zeros((N, rows, s.cols, 3), np.float32)
        s.id(" ")

    def id(s, c):
        if c not in s.cache:
            cw, ch = s.cw, s.ch
            im = Image.new("L", (cw, ch), 0)
            d = ImageDraw.Draw(im)
            if c in "█▓▒░▀▄":
                m = np.zeros((ch, cw), np.uint8)
                if c == "█": m[:, :] = 255
                elif c == "▀": m[:ch // 2] = 255
                elif c == "▄": m[ch // 2:] = 255
                else:
                    step = {"▓": 3, "▒": 2, "░": 4}[c]
                    yy, xx = np.mgrid[:ch, :cw] // 2
                    on = ((xx + yy) % 2 == 0) if c == "▒" else ((xx + 2 * yy) % 4 == 0 if c == "░" else (xx + yy) % 3 != 0)
                    m[on] = 255
                im = Image.fromarray(m)
            elif c in LINES:
                u, r_, dn, l, kind = LINES[c]
                mx_, my_, w_ = cw // 2, ch // 2, 2
                for on, x0, y0, x1, y1 in [(u, mx_, 0, mx_, my_), (r_, mx_, my_, cw, my_), (dn, mx_, my_, mx_, ch), (l, 0, my_, mx_, my_)]:
                    if on:
                        offs = (-3, 3) if kind == 2 else (0,)
                        for o in offs:
                            dx, dy = (o, 0) if x0 == x1 else (0, o)
                            d.line([x0 + dx, y0 + dy, x1 + dx, y1 + dy], fill=255, width=w_)
                if kind == 1:  # dashed
                    a = np.array(im)
                    if l or r_: a[:, ::5] = 0; a[:, 1::5] = 0
                    else: a[::6] = 0; a[1::6] = 0
                    im = Image.fromarray(a)
            elif "\u2800" <= c <= "\u28ff":
                bits = ord(c) - 0x2800
                for b, (x, y) in enumerate([(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3)]):
                    if bits >> b & 1:
                        px, py, r = (x + .5) * cw / 2, (y + .5) * ch / 4, cw * .17
                        d.ellipse([px - r, py - r, px + r, py + r], fill=255)
            else:
                d.text((cw / 2, ch / 2), c, font=s.font, fill=255, anchor="mm")
            s.cache[c] = len(s.glyphs)
            s.glyphs.append(c)
            s.masks.append(np.asarray(im, np.float32) / 255)
        return s.cache[c]

    def put(s, t, y, x, c, fg=None, bg=None):
        if 0 <= y < s.rows and 0 <= x < s.cols:
            f = slice(None) if t is None else t
            s.g[f, y, x] = s.id(c)
            if fg is not None: s.fg[f, y, x] = fg
            if bg is not None: s.bg[f, y, x] = bg

    def render(s, t):
        m = np.stack(s.masks)[s.g[t]].transpose(0, 2, 1, 3)  # rows,ch,cols,cw
        fg = s.fg[t][:, None, :, None, :]
        bg = s.bg[t][:, None, :, None, :]
        out = bg + (fg - bg) * m[..., None]
        out = out.transpose(0, 1, 2, 3, 4).reshape(s.rows * s.ch, s.cols * s.cw, 3)
        # quantise: keeps the palette tight and the files small
        return np.clip(np.round(out / 6) * 6, 0, 255).astype(np.uint8)


def mix(a, b, t):
    t = np.asarray(t)[..., None]
    return a + (b - a) * t


def ramp_fill(G, mask, lum, ramp, seed, t=None):
    """Dithered glyph choice by luminance."""
    r, c = np.nonzero(mask)
    ids = np.array([G.id(ch) for ch in ramp])
    v = lum[r, c] * (len(ramp) - 1) + BAYER[r % 4, c % 4] - .5
    v = np.clip(np.round(v), 0, len(ramp) - 1).astype(int)
    if t is None: G.g[:, r, c] = ids[v]
    else: G.g[t, r, c] = ids[v]


def build(phone):
    if phone:
        G = Grid(616, 154, 14, 22)
        L = dict(star=(40, 52), city=52, hor=92, river=94, ground=132, links=145)
        name = []
        motto_row = 31
    else:
        G = Grid(1692, 153, 12, 20)
        L = dict(star=(38, 48), city=48, hor=91, river=93, ground=135, links=145)
        name = []
        motto_row = 32
    R, C = G.rows, G.cols
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[:R, :C].astype(float)
    asp = G.ch / G.cw
    hor, rv, gr = L["hor"], L["river"], L["ground"]

    # ---------------- sky
    sky = yy < hor
    h = np.clip(yy / hor, 0, 1)
    warp = fbm(xx / 18, yy / 11, 3)
    band = np.exp(-(((yy - (4 + (C - xx) * (.30 if phone else .20)) + (warp - .5) * 22) / (8 if phone else 7.5)) ** 2))
    band2 = np.exp(-(((yy - (30 + xx * .12) + (warp - .5) * 26) / 6.5) ** 2))
    neb = np.clip((band + band2 * .7) * (fbm(xx / 7, yy / 5, 11) * 1.9 - .45), 0, 1)
    glow = np.clip((h - .52) / .48, 0, 1) ** 1.6
    base = mix(NAVY, DEEP, np.clip(h * .9, 0, 1))
    base = mix(base, TEAL, neb * .38)
    base = mix(base, EMBER, glow * .80)
    skyfg = mix(mix(DEEP * 1.9, CYAN, np.clip(neb * 1.25, 0, 1)), AMBER, np.clip(glow * 1.3, 0, 1))
    lum = np.clip(.10 + neb * .85 + glow * .72 + (fbm(xx / 3, yy / 2, 5) - .5) * .30, 0, 1)
    G.bg[:, sky] = base[sky]
    G.fg[:, sky] = skyfg[sky]
    ramp_fill(G, sky, lum, [" ", "⠀", "⠂", "⠄", "⠌", "⠕", "⠞", ":", "+", "x", "%", "&"], 1)
    # dim flickering characters
    digits = "0123456789abcdef<>/\\{}[]=*"
    sel = sky & (rng.random((R, C)) < .07 + neb * .22)
    for r, c in zip(*np.nonzero(sel)):
        ph, ch = rng.integers(N), digits[rng.integers(len(digits))]
        G.put(None, r, c, ch, mix(base[r, c], skyfg[r, c], .55 + .45 * neb[r, c]))
        if rng.random() < .22:
            for k in range(3):
                G.put((ph + k) % N, r, c, digits[rng.integers(len(digits))], mix(base[r, c], WHITE, .55 - .12 * k))
    # stars
    for _ in range(int(C * hor * .016)):
        r, c = rng.integers(0, int(hor * .78)), rng.integers(C)
        ph, sp = rng.random(), rng.integers(1, 3)
        col = [WHITE, WHITE, CYAN, AMBER][rng.integers(4)]
        big = rng.random() < .13
        for t in range(N):
            k = .5 + .5 * math.sin(2 * math.pi * (sp * t / N + ph))
            ch = ("✦" if k > .6 else "+") if big else ("*" if k > .8 else "·")
            G.put(t, r, c, ch, mix(base[r, c], col, .35 + .65 * k))
    # crescent moon, dithered
    mx, my, mr = (C - 8, 44, 5.2) if phone else (C - 18, 31, 7.2)
    if phone: mx, my, mr = C - 7, 34 + 12, 4.2
    d1 = np.hypot((xx - mx) / asp, yy - my)
    d2 = np.hypot((xx - mx + mr * .62 * asp) / asp, yy - my + mr * .32)
    halo = np.exp(-((np.clip(d1 - mr, 0, None) / 3.2) ** 2))
    hm = (halo > .12) & (d1 > mr) & sky
    G.bg[:, hm] = mix(base, AMBER, halo * .22)[hm]
    moon = (d1 <= mr) & (d2 > mr * .93)
    ml = np.clip(1.05 - (mr - d1) / mr * .9 + (fbm(xx / 2, yy / 1.5, 9) - .5) * .5, .25, 1)
    G.bg[:, moon] = mix(EMBER, AMBER, ml)[moon] * .72
    G.fg[:, moon] = mix(AMBER, WHITE, np.clip(ml - .35, 0, 1))[moon]
    ramp_fill(G, moon, ml, list("-=+o0#@@"), 2)
    # a shooting star
    sy, sx = (hor - 50, 3) if phone else (24, 4)
    for t in range(N):
        if t < 12:
            for k in range(7):
                if t - k >= 0:
                    G.put(t, sy + (t - k) // 3, sx + (t - k), "*" if k == 0 else "-·"[k > 3], mix(WHITE, DEEP * 1.6, k / 7))

    # ---------------- name
    scale = 1 if phone else 2
    for text, top in name:
        w = (len(text) * 6 - 1) * scale - (2 * scale if " " in text else 0)
        x = (C - w) // 2
        cells = []
        for chn in text:
            if chn == " ":
                x += 4 * scale
                continue
            for j, row in enumerate(FONT[chn].split()):
                for i, b in enumerate(row):
                    if b == "1":
                        for a in range(scale):
                            for bb in range(scale):
                                cells.append((top + j * scale + a, x + i * scale + bb, j * scale + a))
            x += 6 * scale
        on = {(r, c) for r, c, _ in cells}
        for r, c, _ in cells:  # clear a dark halo so the letters stand out
            for dr in range(-2, 3):
                for dc in range(-3, 4):
                    q = (r + dr, c + dc)
                    if q not in on and 0 <= q[0] < R and 0 <= q[1] < C:
                        G.put(None, q[0], q[1], " " if abs(dr) < 2 and abs(dc) < 3 else "⠂", NAVY * 2.6, mix(NAVY, base[q], .25))
        for r, c, j in cells:
            k = j / (7 * scale - 1)
            col = mix(WHITE, AMBER, min(1, k * 1.15))
            vertex = sum((r + a, c + b) in on for a, b in [(1, 0), (-1, 0), (0, 1), (0, -1)]) <= (1 if phone else 1)
            ch = "A@#&8B%W"[rng.integers(8)]
            G.put(None, r, c, ch, mix(col, NAVY, .5), mix(col, WHITE, .08))
            ph = rng.integers(N)
            if rng.random() < .18:
                for k2 in range(4):
                    G.put((ph + k2) % N, r, c, "01*+"[rng.integers(4)], WHITE, col * .72)
            if vertex:
                for t in range(N):
                    G.put(t, r, c, "✦" if (t + ph) % N < 8 else "★", WHITE, col * .8)
        # drop shadow
        for r, c, _ in cells:
            q = (r + 1, c + 1)
            if q not in on:
                G.put(None, q[0], q[1], "▒", EMBER * .75, NAVY)
    # motto slot (empty)
    w = int(C * (.6 if phone else .34))
    for c in range((C - w) // 2, (C + w) // 2):
        if c % 2 == 0:
            G.put(None, motto_row, c, "·", TEAL * .9, NAVY * 1.2)

    # ---------------- far dunes and far skyline
    farh = hor - (13 if phone else 15) - (fbm(xx / 5, yy * 0, 21, 2) * 14).astype(int)
    farh = np.floor(farh[0] / 1)
    far = (yy >= farh[None, :]) & sky
    G.bg[:, far] = mix(EMBER * .55, DEEP, .45)
    G.fg[:, far] = mix(EMBER, AMBER, .15)
    ramp_fill(G, far, np.clip(.25 + (fbm(xx / 2, yy / 1.2, 23) - .5), 0, 1), list(" ·:|¦"), 3)
    for _ in range(C // 4):
        c = rng.integers(C)
        r = int(farh[c]) + rng.integers(1, 8)
        if r < hor: G.put(None, r, c, "▪", AMBER * .85)

    # ---------------- city
    ids = np.zeros((R, C), int)   # building id per cell
    trim = []                     # outline decorations

    def rect(x0, x1, top, i):
        ids[max(top, 0):hor, max(x0, 0):max(min(x1, C), 0)] = i

    def dome(cx, half, base_r, height, i):
        for r in range(base_r - height, base_r):
            u = (base_r - r - .5) / height
            wdt = half * math.sqrt(max(0, 1 - u * u)) * (1 + .12 * math.sin(math.pi * min(u * 1.6, 1)))
            a, b = int(round(cx - wdt)), int(round(cx + wdt))
            ids[r, max(a, 0):max(min(b + 1, C), 0)] = i
        trim.append((base_r - height - 1, cx, "┃"))
        trim.append((base_r - height - 2, cx, "☾"))

    def minaret(cx, top, i):
        rect(cx - 1, cx + 2, top + 6, i)
        rect(cx - 2, cx + 3, top + 12, i)
        for bal in (top + 6, top + 17):
            if bal < hor:
                ids[bal, max(cx - 3, 0):cx + 4] = i
        ids[top + 3:top + 6, cx] = i
        ids[top + 4:top + 6, max(cx - 1, 0):cx + 2] = i
        trim.append((top + 2, cx, "▲"))
        trim.append((top + 1, cx, "│"))
        trim.append((top, cx, "☾"))

    k = 1
    if phone:
        plan = [("r", 0, 11, 74), ("r", 33, 44, 70), ("r", 9, 22, 80), ("d", 27, 9, 79, 11), ("r", 18, 37, 79),
                ("m", 5, 55), ("m", 38, 59), ("r", 0, 14, 85), ("r", 30, 44, 84), ("d", 14, 6, 86, 6), ("r", 8, 21, 86)]
    else:
        plan = [("r", 0, 13, 76), ("r", 11, 25, 70), ("r", 34, 46, 73), ("m", 29, 56), ("r", 52, 66, 79),
                ("d", 77, 13, 75, 15), ("r", 64, 91, 75), ("m", 60, 52), ("m", 95, 59), ("r", 99, 111, 68),
                ("r", 109, 125, 78), ("m", 129, 62), ("r", 127, 141, 72),
                ("r", 20, 38, 81), ("d", 44, 8, 83, 8), ("r", 35, 54, 83), ("r", 80, 100, 82),
                ("d", 117, 8, 81, 8), ("r", 108, 127, 81), ("r", 0, 17, 84), ("r", 125, 141, 84), ("r", 55, 79, 85)]
    for p in plan:
        if p[0] == "r": rect(p[1], p[2], p[3], k)
        elif p[0] == "d": dome(p[1], p[2], p[3], p[4], k)
        else: minaret(p[1], p[2], k)
        k += 1
    # ground floor so words run unbroken at the base
    for c in range(C):
        top = hor - 4 - int(fbm(np.array(c / 9.), np.array(0.), 31) * 3)
        ids[top:hor, c] = np.where(ids[top:hor, c] > 0, ids[top:hor, c], k)

    city = ids > 0
    pad = np.pad(ids, 1, mode="edge")
    topedge = city & (pad[:-2, 1:-1] != ids)
    side = city & ((pad[1:-1, :-2] != ids) | (pad[1:-1, 2:] != ids)) & ~topedge
    tone = (np.array([0, .0, .55, .2, .8, .35, 1, .1, .65, .45, .9, .25] * 4))[ids % 48]
    face = mix(np.array([10, 12, 34.]), np.array([40, 24, 36.]), tone)
    face = mix(face, EMBER * .55, np.clip((yy - (hor - 18)) / 18, 0, 1) * .5)
    G.bg[:, city] = face[city]
    keep = {(r, c) for r, c, _ in trim}
    queue = list(SKILLS)
    count = 0
    words_at = []
    for r in range(hor):
        c = 0
        while c < C:
            if not city[r, c] or side[r, c] or (r, c) in keep:
                c += 1
                continue
            e = c
            while e < C and city[r, e] and not side[r, e] and ids[r, e] == ids[r, c] and (r, e) not in keep:
                e += 1
            x = c
            while x < e:
                room = e - x
                hit = next((n for n, w in enumerate(queue) if len(w) <= room and (len(w) > 1 or room < 4)), None)
                if hit is None:
                    for q in range(x, e): G.put(None, r, q, "░", mix(face[r, q], AMBER, .25))
                    break
                w = queue.pop(hit)
                queue.append(w)
                col = [AMBER, WHITE, AMBER * .78 + EMBER * .22, CYAN][count % 4]
                count += 1
                for q, ch in enumerate(w):
                    G.put(None, r, x + q, ch, col)
                words_at.append((r, x, len(w), w))
                x += len(w)
                if x < e:
                    G.put(None, r, x, "▪" if rng.random() < .2 else "·", mix(face[r, x], AMBER, .4))
                    x += 1
            c = e
    for r, c in zip(*np.nonzero(side)):
        left = c == 0 or ids[r, c - 1] != ids[r, c]
        G.put(None, r, c, "▌" if False else ("▓" if left else "▒"), mix(face[r, c], AMBER, .85 if left else .4))
    for r, c in zip(*np.nonzero(topedge & (G.g[0] != 0))):
        G.bg[:, r, c] = mix(face[r, c], AMBER, .36)
    for r, c, ch in trim:
        G.put(None, r, c, ch, AMBER if ch != "☾" else WHITE)
    # blinking windows / words lighting up
    for i in rng.choice(len(words_at), min(len(words_at) // 6, 60), replace=False):
        r, x, n, w = words_at[i]
        ph = rng.integers(N)
        for k2 in range(5):
            t = (ph + k2) % N
            G.bg[t, r, x:x + n] = mix(face[r, x], AMBER, [.25, .5, .6, .45, .2][k2])
            G.fg[t, r, x:x + n] = WHITE

    # ---------------- shore line
    for r in range(hor, rv):
        for c in range(C):
            G.put(None, r, c, "▀" if r == hor else "≡", AMBER * (.85 if r == hor else .6), EMBER * (.45 if r == hor else .3))

    # ---------------- river and banks
    water = np.zeros((R, C), bool)
    low = (yy >= rv) & (yy < gr)
    u = np.clip((yy - rv) / (gr - rv), 0, 1)
    center = C * (.50 + .22 * np.sin(u * 5.2 + .2) * np.clip(u * 2.2, 0, 1) * (1 - u * .35))
    half = C * ((.12 if phone else .08) + (.30 if phone else .27) * u ** 1.25) + (fbm(xx * 0, yy / 4, 41) - .5) * 5
    # the mouth under the city is wide, then narrows into the bend
    half = half + C * .42 * np.exp(-u * 17)
    dist = (np.abs(xx - center) - half)
    water = low & (dist < 0)
    bank = low & ~water
    dn = fbm(xx / 14 + yy / 40, yy / 4.5, 51)
    ridge = np.clip(np.sin(yy * .55 + xx * .09 * np.sign(center - xx) + dn * 7) * .5 + .5, 0, 1)
    bl = np.clip(ridge * .75 * (.35 + dn) + np.exp(-dist / 2.0) * .35, 0, 1)
    G.bg[:, bank] = mix(NAVY * 1.1, EMBER * .50, bl * (1 - u * .35))[bank]
    G.fg[:, bank] = mix(EMBER * .8, AMBER, np.clip(bl * 1.4 - .45, 0, 1))[bank]
    ramp_fill(G, bank, bl, [" ", "⠂", "⠄", "⠢", "⠪", ":", "=", "%", "#"], 4)
    edge = bank & (dist < 1.4)
    for r, c in zip(*np.nonzero(edge)):
        G.put(None, r, c, '"vw*'[rng.integers(4)], mix(AMBER, CYAN, .3), EMBER * .35)
    # water: flowing glyphs
    refl = np.zeros((R, C))
    for r, c in zip(*np.nonzero(topedge | side)):
        pass
    lights = [(p[1] if p[0] != "r" else (p[1] + p[2]) // 2) for p in plan[:14]]
    for lx in lights:
        refl = np.maximum(refl, np.exp(-((xx - lx - np.sin(yy * .9) * 1.2) / 1.3) ** 2) * np.exp(-(yy - rv) / (13 + lx % 7)))
    moonref = np.exp(-((xx - mx) / (2.5 + u * 5)) ** 2) * (1 - u * .6)
    wr, wc = np.nonzero(water)
    ramp = [" ", "·", "-", "~", "~", "≈", "≈", "="]
    rid = np.array([G.id(c) for c in ramp])
    depth = np.clip(-dist / 9, 0, 1)
    dig = np.array([G.id(c) for c in "01<>sqlnile"])
    spark = rng.random((R, C))
    for t in range(N):
        ph = 2 * math.pi * t / N
        # streamlines follow the bend and move downstream
        lat = (xx - center) / np.maximum(half, 1)
        w1 = np.sin(yy * .78 - ph * 1 + np.sin(lat * 6.0 + yy * .09) * 2.1)
        w2 = np.sin(yy * .31 + lat * 9.5 - ph * 2)
        w3 = np.sin(xx * .55 + yy * 1.7 - ph * 1 + spark * 1.5)
        v = np.clip(.5 + .27 * w1 + .17 * w2 + .12 * w3, 0, 1) ** 1.25
        wl = v * (.45 + .55 * depth)
        col = mix(TEAL, CYAN, np.clip(v * 1.5 - .45, 0, 1))
        col = mix(col, WHITE, np.clip(v * 2.4 - 1.6, 0, 1))
        am = np.clip((refl + moonref * .55) * (.4 + v), 0, 1)
        col = mix(col, AMBER, am)
        bg = mix(NAVY * 1.3, TEAL * .72, wl)
        bg = mix(bg, EMBER * .9, am * .7)
        G.bg[t, wr, wc] = bg[wr, wc]
        G.fg[t, wr, wc] = col[wr, wc]
        q = np.clip(np.round(np.clip(wl * 1.15 + am * .35, 0, 1)[wr, wc] * 7 + BAYER[wr % 4, wc % 4] - .5), 0, 7).astype(int)
        gid = rid[q]
        fl = (spark[wr, wc] > .90) & (v[wr, wc] > .45)
        gid[fl] = dig[((spark[wr, wc][fl] * 9973).astype(int) + t // 6) % len(dig)]
        G.g[t, wr, wc] = gid
    # feluccas: two small sails drifting
    for (fy, off, sc) in [(rv + int((gr - rv) * .30), -.15, 0), (rv + int((gr - rv) * .70), .30, 1)]:
        sail = ["   |\\    ", "   |=\\   ", "   |==\\  ", "   |===\\ ", "   |====\\", " __|_____ ", " \\▓▓▓▓▓▓/ "]
        if not sc: sail = sail[1:]
        fx = int(center[fy, 0] + half[fy, 0] * off) - 5
        for t in range(N):
            bob = int(round(math.sin(2 * math.pi * t / N + sc * 2) * .6))
            for j, row in enumerate(sail):
                for i, ch in enumerate(row):
                    if ch != " ":
                        G.put(t, fy + j - 3, fx + i + bob, ch, AMBER if j >= len(sail) - 1 else WHITE)
    # palms on the banks
    def palm(r, c, h_):
        for j in range(-h_ - 4, 2):
            for i in range(-7, 12):
                q, w_ = r + j, c + i
                if rv <= q < gr and 0 <= w_ < C and ((i - 2) / 9) ** 2 + ((j + h_) / 5) ** 2 < 1:
                    G.bg[:, q, w_] = G.bg[0, q, w_] * .45
                    G.fg[:, q, w_] = G.fg[0, q, w_] * .4
        for j in range(h_):
            x = c + int(round((j / h_) ** 2 * 2))
            G.put(None, r - j, x, "▓" if j % 2 else "▒", AMBER * .9, EMBER * .5)
            G.put(None, r - j, x + 1, "▒", AMBER * .6, EMBER * .35)
        tx, ty = c + 2, r - h_
        for ang, ln in [(-170, 6), (-142, 6), (-108, 4), (-72, 4), (-38, 6), (-8, 6)]:
            for s_ in range(1, ln + 1):
                a = math.radians(ang)
                px = tx + int(round(math.cos(a) * s_ * 1.25))
                py = ty + int(round(math.sin(a) * s_ * .8 + (s_ / ln) ** 2 * 2.6))
                ch = "=" if abs(math.cos(a)) > .9 else ("\\" if math.cos(a) < 0 else "/")
                if s_ == ln: ch = "v"
                G.put(None, py, px, ch if s_ % 2 else "*", mix(WHITE, CYAN, s_ / ln * 1.4 if s_ / ln < .7 else 1))
        G.put(None, ty, tx, "@", AMBER)
    for fy, f, h_ in [(.20, .08, 7), (.34, .88, 9), (.30, .93, 6), (.80, .07, 11), (.73, .13, 8), (.93, .93, 10)]:
        r = rv + int((gr - rv) * fy)
        c = int(C * f)
        if dist[r, min(c, C - 1)] > 2:
            palm(r, c, h_)
    # hobbies slot on the bank (empty frame)
    sw, sh = (18, 7) if phone else (30, 8)
    best = None
    for r in range(rv + 8, gr - sh - 2):
        for c in range(2, C - sw - 2):
            clear = dist[r:r + sh, c:c + sw].min()
            score = min(clear, 3) * 100 - abs(r - (rv + (gr - rv) * .55))
            if best is None or score > best[0]: best = (score, r, c)
    _, r0, c0 = best
    for j in range(sh):
        for i in range(sw):
            e_ = j in (0, sh - 1) or i in (0, sw - 1)
            ch = " "
            if e_: ch = ("╌" if j in (0, sh - 1) else "╎")
            if (j, i) in [(0, 0)]: ch = "┌"
            if (j, i) == (0, sw - 1): ch = "┐"
            if (j, i) == (sh - 1, 0): ch = "└"
            if (j, i) == (sh - 1, sw - 1): ch = "┘"
            if not e_ and j == sh // 2 and 3 <= i < sw - 3 and i % 2: ch = "·"
            G.put(None, r0 + j, c0 + i, ch, TEAL * 1.15, NAVY * 1.15)

    # ---------------- ground: terminal prompt
    gm = yy >= gr
    gl = np.clip(fbm(xx / 8, yy / 3, 61) * .9 - .25 + .5 * np.exp(-((yy - (gr + 5.5)) / 4) ** 2), 0, 1)
    G.bg[:, gm] = mix(NAVY, TEAL * .22, gl)[gm]
    G.fg[:, gm] = (TEAL * .75)
    ramp_fill(G, gm, gl * .7, [" ", "⠀", "⠂", "⠄", "⠆", ":", "1", "0"], 5)
    for c in range(C):
        G.put(None, gr, c, "▀", mix(TEAL, AMBER, .5 + .5 * math.sin(c / 7)), NAVY)
    text = "ali@cairo:~$"
    if phone:
        # large live text: the pixel font would be wider than a phone
        tw = None
    else:
        w = len(text) * 6 + 7
        x = (C - w) // 2
        top = gr + 2
        for r in range(top - 1, top + 8):
            for c in range(x - 2, x + w + 1):
                G.put(None, r, c, " ", NAVY, NAVY * .8)
        for n, chn in enumerate(text):
            col = CYAN if n < 3 else (WHITE if n == 3 else (AMBER if n < 9 else WHITE))
            for j, row in enumerate(FONT[chn].split()):
                for i, b in enumerate(row):
                    if b == "1":
                        G.put(None, top + j, x + i, "$#@&"[rng.integers(4)], mix(col, NAVY, .45), col)
            x += 6
        for t in range(N):
            if t < N // 2:
                for j in range(7):
                    for i in range(5): G.put(t, top + j, x + 1 + i, "█", AMBER, AMBER * .6)

    # ---------------- link band
    lk = L["links"]
    lm = yy >= lk
    G.bg[:, lm] = NAVY
    G.fg[:, lm] = TEAL * .7
    ramp_fill(G, lm, np.clip(fbm(xx / 5, yy / 2, 71) - .3, 0, 1), [" ", "⠀", "⠂", "⠄", "⠆", ":"], 6)
    mid = C // 2
    for side_, (c0, c1, col) in enumerate([(1, mid - 1, CYAN), (mid + 1, C - 1, AMBER)]):
        y0, y1 = lk + 0, R - 1
        for r in range(y0, y1 + 1):
            for c in range(c0, c1):
                e_ = r in (y0, y1) or c in (c0, c1 - 1)
                if e_:
                    ch = "═" if r in (y0, y1) else "║"
                    if r == y0: ch = "╔" if c == c0 else ("╗" if c == c1 - 1 else ch)
                    if r == y1: ch = "╚" if c == c0 else ("╝" if c == c1 - 1 else ch)
                    G.put(None, r, c, ch, col * .85, NAVY)
                else:
                    G.put(None, r, c, " " if rng.random() < .8 else "·", col * .35, mix(NAVY, col, .09))
        for t in range(N):  # light running round the frame
            per = [(y0, c) for c in range(c0, c1)] + [(r, c1 - 1) for r in range(y0 + 1, y1)] + \
                  [(y1, c) for c in range(c1 - 1, c0 - 1, -1)] + [(r, c0) for r in range(y1 - 1, y0, -1)]
            head = int(t / N * len(per))
            for k2 in range(8):
                r, c = per[(head - k2) % len(per)]
                G.fg[t, r, c] = mix(WHITE, col, k2 / 8)

    # star-of-the-day window (frame only; the daily script fills it)
    s0, s1 = L["star"]
    fw = 34 if phone else 40
    fx = 2 if phone else (C - fw) // 2
    if phone: fw, fx = 27, 1
    for r in range(s0, s1):
        for c in range(fx, fx + fw):
            e_ = r in (s0, s1 - 1) or c in (fx, fx + fw - 1)
            if e_:
                ch = "─" if r in (s0, s1 - 1) else "│"
                if r == s0: ch = "╭" if c == fx else ("╮" if c == fx + fw - 1 else ch)
                if r == s1 - 1: ch = "╰" if c == fx else ("╯" if c == fx + fw - 1 else ch)
                G.put(None, r, c, ch, TEAL * 1.25, NAVY * 1.15)
            else:
                G.put(None, r, c, " ", NAVY, NAVY * 1.15)
    label = " ✦ star of the day "
    for i, ch in enumerate(label):
        G.put(None, s0, fx + 3 + i, ch, AMBER, NAVY * 1.15)

    star_box = ((fx + 1) * G.cw, (s0 + 1) * G.ch, (fx + fw - 1) * G.cw, (s1 - 1) * G.ch)
    cuts = dict(sky=(0, s0), star=(s0, s1), city=(s1, rv), river=(rv, gr), ground=(gr, lk), links=(lk, R))
    return G, L, cuts, star_box, set(w for *_, w in words_at)


def save(frames, path, still=False):
    ims = [Image.fromarray(f) for f in frames]
    if still:
        ims[0].save(path.replace(".webp", ".png"))
    else:
        ims[0].save(path, save_all=True, append_images=ims[1:], duration=MS, loop=0, lossless=True,
                    quality=70, method=4, minimize_size=False)


def main():
    out = sys.argv[1]
    still = "--still" in sys.argv
    os.makedirs(out, exist_ok=True)
    for phone in (False, True):
        G, L, cuts, box, used = build(phone)
        missing = set(SKILLS) - used
        pre = "phone" if phone else "desk"
        frames = []
        for t in range(1 if still else N):
            f = G.render(t)
            if phone:  # the prompt as large live text
                im = Image.fromarray(f)
                d = ImageDraw.Draw(im)
                p, i = font_path(True)
                font = ImageFont.truetype(p, 54, index=i)
                y = L["ground"] * G.ch + 140
                parts = [("ali", CYAN), ("@", WHITE), ("cairo", AMBER), (":~$", WHITE)]
                total = d.textlength("ali@cairo:~$ _", font=font)
                x = (G.W - total) / 2
                d.rectangle([x - 18, y - 50, x + total + 18, y + 50], fill=tuple(NAVY.astype(int)))
                for s_, c_ in parts:
                    d.text((x, y), s_, font=font, fill=tuple(c_.astype(int)), anchor="lm")
                    x += d.textlength(s_, font=font)
                if t < N // 2:
                    d.rectangle([x + 16, y - 30, x + 46, y + 30], fill=tuple(AMBER.astype(int)))
                f = np.asarray(im)
            # link labels
            lk = L["links"]
            im = Image.fromarray(f)
            d = ImageDraw.Draw(im)
            p, i = font_path(True)
            font = ImageFont.truetype(p, 38 if phone else 62, index=i)
            mid = G.cols // 2
            yc = (lk + G.rows) * G.ch // 2
            for xc, s_, c_ in [((1 + mid - 1) * G.cw // 2, "LinkedIn ↗", CYAN), ((mid + 1 + G.cols - 1) * G.cw // 2, "Portfolio ↗", AMBER)]:
                tw = d.textlength(s_, font=font)
                d.rectangle([xc - tw / 2 - 10, yc - (30 if phone else 46), xc + tw / 2 + 10, yc + (30 if phone else 46)], fill=tuple(NAVY.astype(int)))
                d.text((xc, yc), s_, font=font, fill=tuple(c_.astype(int)), anchor="mm")
            frames.append(np.asarray(im))
        for name, (a, b) in cuts.items():
            part = [f[a * G.ch:b * G.ch] for f in frames]
            if name == "links":
                half = G.W // 2
                save([p[:, :half] for p in part], f"{out}/{pre}-linkedin.webp", still)
                save([p[:, half:] for p in part], f"{out}/{pre}-portfolio.webp", still)
            else:
                save(part, f"{out}/{pre}-{name}.webp", still)
            if name == "star":
                x0, y0, x1, y1 = box
                save(part, f"{out}/{pre}-star-base.webp", still)
        if not still:
            import json
            x0, y0, x1, y1 = box
            top = cuts["star"][0] * G.ch
            with open(f"{out}/{pre}-star.json", "w") as fh:
                json.dump({"box": [x0, y0 - top, x1, y1 - top], "ms": MS, "frames": N}, fh)
        Image.fromarray(frames[0]).save(f"{out}/../preview-{pre}.png")
        if not still:
            Image.fromarray(frames[N // 2]).save(f"{out}/../preview-{pre}-mid.png")
        print(pre, frames[0].shape, "missing skills:", missing)


if __name__ == "__main__":
    main()
