"""Redraws only the "star of the day" window: one small piece per day, over the animated frame."""
import datetime
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageSequence

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
FONTS = [("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 0), ("/System/Library/Fonts/Menlo.ttc", 1)]
AMBER, CYAN, WHITE = (255, 170, 48), (46, 214, 232), (238, 240, 250)

PIECES = [
    r"""    .
   /|\
 --=*=--
   \|/
    '""",
    r"""      _..._
    .' (   '.
   :  o   .  :
    '.  ( .'
      '---'""",
    r"""        |\
        |.\
        |..\
   _____|___\__
   \::::::::::/
 ~~~~~~~~~~~~~~~~""",
    r"""    /\_/\
   ( o.o )
    > ^ <   .  *
   /     \___)""",
    r"""        *
       /_\
      /___\
     |  o  |
     |_____|
    /_/ ' \_\
       '''""",
    r"""    _______
   |  ___  |
   | | >_| |
   |_______|
  /:::::::::\
 '-----------'""",
    r"""      ( (
       ) )
    .______.
    |      |]
    \      /
     '----'""",
    r"""    \ | /
  '-.;;;.-'
 -==;;;;;==-
  .-';;;'-.
    / | \
 ~~~~~~~~~~~""",
    r"""      __
  ___/o )>
  \     /      ~
   '---'   ~
 ~~~~~~~~~~~~~~""",
    r"""    ><(((('>
          o
       o
  <'))))><
             ><('>""",
    r"""       /\
      /  \    /\
  /\ / /\ \  /  \
 /  \ /  \ \/ /\ \
/____\____\___\__\\""",
    r"""      .--.
   .-(    ).
  (___.__)__)
    ' ' ' '
   ' ' ' '""",
    r"""       _
      (_)
   .--|--.
      |
  \   |   /
   '._|_.'""",
    r"""    .---.
   ( @ @ )
    ) ~ (
   /|||||\
    ' ' '""",
    r"""   _     _
  (o\---/o)
   ( . . )
   _( T )_
  / /'-'\ \\""",
    r"""      \\|//
     \\|||//
        ||
        ||
   ~~~~~||~~~~~""",
    r"""   +--------+
  /        /|
 +--------+ |
 |  01    | +
 |    10  |/
 +--------+""",
    r"""    .-""-.
   / .--. \
  | ( () ) |
   \ '--' /
    '-..-'""",
    r"""  *    .      *
    .-----.
 --(  (o)  )--
    '-----'
  .     *    .""",
    r"""      ()
      /\
     /  \
    / ** \
   /______\
      ||""",
    r"""    ____
   / __ \__
  / /  \ o\
 | | () |  >
  \ \__/  /
 ==\_____/==""",
    r"""  ,___,
  (O,O)
  /)_)
 --"-"----
      *""",
    r"""   __
  |  |_______
  |  | _  _  |
  |__|_______|
   (_)    (_)""",
    r"""    /\    /\
   /  \/\/  \
  ( *      * )
   \   vv   /
    '------'""",
    r"""      .:.
    .:::::.
   :::::::::
    ':::::'
      ':'""",
    r"""  o--o--o
  |\ | /|
  o--O--o
  |/ | \|
  o--o--o""",
    r"""   .------.
   | A    |
   |  /\  |
   |  \/  |
   |    A |
   '------'""",
    r"""  _/\_
  >  <        .
  /_  _\    *
    \/   .""",
    r"""    [=====]
     \   /
      \ /
      / \
     / . \
    [=====]""",
    r"""   { }   { }
    \     /
     (o o)
   ==( + )==
     /' '\\""",
]


def font(size):
    for path, index in FONTS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size, index=index)
    raise SystemExit("no monospace font found")


def draw(prefix, day):
    with open(os.path.join(ASSETS, f"{prefix}-star.json")) as fh:
        meta = json.load(fh)
    x0, y0, x1, y1 = meta["box"]
    lines = PIECES[day % len(PIECES)].split("\n")
    cols = max(map(len, lines))
    size = int(min((x1 - x0 - 12) / (cols * .61), (y1 - y0 - 8) / (len(lines) * 1.08)))
    f = font(size)
    cw, lh = f.getlength("M"), size * 1.08
    left = x0 + (x1 - x0 - cw * cols) / 2
    top = y0 + (y1 - y0 - lh * len(lines)) / 2
    tint = [AMBER, CYAN, WHITE][day % 3]
    frames, durations, clock = [], [], 0
    with Image.open(os.path.join(ASSETS, f"{prefix}-star-base.webp")) as base:
        for frame in ImageSequence.Iterator(base):
            image = frame.convert("RGB")
            ms = frame.info.get("duration", meta["ms"])
            frames.append(image)
            durations.append(ms)
    # split merged frames so the piece can shimmer at the full frame rate
    full = []
    for image, ms in zip(frames, durations):
        full += [image] * max(1, round(ms / meta["ms"]))
    out = []
    for t, image in enumerate(full):
        image = image.copy()
        d = ImageDraw.Draw(image)
        for j, line in enumerate(lines):
            for i, ch in enumerate(line):
                if ch == " ":
                    continue
                k = .5 + .5 * math.sin(2 * math.pi * t / len(full) - (i + j * 2) * .45)
                colour = tuple(int(c * (.68 + .32 * k)) for c in tint)
                d.text((left + i * cw, top + j * lh), ch, font=f, fill=colour)
        out.append(image)
    out[0].save(os.path.join(ASSETS, f"{prefix}-star.webp"), save_all=True, append_images=out[1:],
                duration=meta["ms"], loop=0, lossless=True, quality=70, method=4)


if __name__ == "__main__":
    day = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.datetime.now(datetime.timezone.utc).date().toordinal()
    for prefix in ("desk", "phone"):
        draw(prefix, day)
    print("piece", day % len(PIECES) + 1, "of", len(PIECES))
