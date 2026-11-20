#!/usr/bin/env python3
"""
caption.py - lint an Instagram caption and show exactly what the feed shows
before the "... more".

Instagram gives a caption about 125 characters in the feed and hides the rest
behind a tap. Almost every caption that fails, fails there: the hook is in
sentence three, or the first line is a greeting, or the whole thing opens on a
hashtag. This prints the visible window as a box so you can read it the way a
scrolling stranger does, then checks the eight things that are worth checking.

The 125-character cut is an approximation. The real number moves with the
device, the font size and where your line breaks fall, which is exactly why
you want a margin rather than a caption engineered to end at 125. Change it
with --truncate if you want to test a tighter one.

Usage
  python3 caption.py caption.txt
  python3 caption.py caption.txt --keywords "proposal software,client contract"
  pbpaste | python3 caption.py -
  python3 caption.py caption.txt --json
"""

import argparse
import json
import re
import sys
import textwrap

# Windows consoles default to cp1252 and choke on the first emoji or accent.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def _read_input(path):
    """Read a text file, or stdin when path is "-". Accepts UTF-8 with or
    without BOM, UTF-16 (what Windows PowerShell 5.1 writes with `>`) and, as
    a last resort, Windows ANSI, so a file saved on Windows never crashes."""
    if path == "-":
        return sys.stdin.read().lstrip("\ufeff")
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252")

LIMIT = 2200             # Instagram's hard caption limit.
TRUNCATE = 125           # Roughly where the feed cuts to "... more".
HASHTAG_LIMIT = 5        # Instagram's cap per post or reel since 18 Dec 2025,
                         # down from 30. Announced by the @Creators account:
                         # "using fewer (up to 5) more targeted hashtags,
                         # rather than many generic ones, can improve both your
                         # content's performance and people's experience".

HASHTAG_RE = re.compile(r"(?:^|\s)(#\w+)")
MENTION_RE = re.compile(r"(?:^|\s)(@[A-Za-z0-9_.]+)")
LINK_RE = re.compile(r"https?://\S+|\bwww\.\S+|\b[a-z0-9-]+\.(?:com|co|io|net|org|ai|app|ar|mx|es|agency)/\S*",
                     re.IGNORECASE)
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF☀-➿←-⇿️]")
CONCRETE_RE = re.compile(r"(?:US\$|USD|\$|€)\s?\d|\b\d[\d,.]*\b|(?<!^)\b[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]{2,}\w*\b",
                         re.MULTILINE)

# ---------------------------------------------------------------------------
# Spanish (rioplatense) adaptation: every ask has its English pattern and its
# Spanish one, voseo and tú. The keyword ask requires the keyword in CAPITALS
# ("comentá GUÍA"), scoped with (?-i:) so the case-insensitive flag does
# not make "comentá abajo" count as a keyword.
# ---------------------------------------------------------------------------
ASKS = [
    (re.compile(r"(?i)\bcomment (?:the word |\")?[A-Z0-9]{2,}\b"
                r"|\b(?:coment[áa](?:me|nos)?|escrib[íi](?:me)?|dej[áa](?:me)? (?:un comentario con|la palabra)"
                r"|pon[ée](?:me)?|mand[áa](?:me)?)\s+(?:la palabra\s+|\"|“|«)?(?-i:[A-ZÁÉÍÓÚÑ0-9]{2,})\b"
                r"|\b(?-i:[A-ZÁÉÍÓÚÑ]{3,}) en (?:los )?comentarios\b"),
     "comment a keyword"),
    (re.compile(r"(?i)\b(?:dm|message) me\b"
                r"|\b(?:escrib[íi]me|escr[íi]beme|mand[áa]me|m[áa]ndame|envi[áa]me|env[íi]ame|habl[áa]me|h[áa]blame)\b"
                r"|\bme (?:mand[áa]s|escrib[íi]s|escribes|mandas) (?:un )?(?:mensaje|dm|md|privado|whatsapp)\b"
                r"|\b(?:por|al|un) (?:dm|md|privado|interno|directo)\b|\bpor whatsapp\b|\bmandame un whatsapp\b"),
     "DM me"),
    (re.compile(r"(?i)\bsave (?:this|it)\b"
                r"|\bguard[áa](?:lo|te|telo|la)?\b|\bgu[áa]rda(?:lo|telo|la)?\b|\bguardar (?:este|esto)\b"),
     "save this"),
    (re.compile(r"(?i)\bshare (?:this|it)\b"
                r"|\bcompart[íi](?:lo|la|selo)?\b|\bcomparte(?:lo|la)?\b|\bcomp[áa]rte(?:lo|la|selo)\b"
                r"|\b(?:mand[áa]|m[áa]nda|pas[áa]|p[áa]sa)(?:se|le)?(?:lo|la|selo) a\b|\betiquet[áa]\b|\betiqueta a\b"),
     "share this"),
    (re.compile(r"(?i)\bfollow (?:me|for)\b"
                r"|\bsegu[íi](?:me|nos|r la cuenta)\b|\bs[íi]gue(?:me|nos)\b|\bsigueme\b|\bsegu[íi] a @\w+"),
     "follow"),
    (re.compile(r"(?i)\blink in (?:my )?bio\b"
                r"|\b(?:link|enlace) en (?:la |mi )?bio\b|\ben (?:la|mi) bio\b|\blink en (?:el )?perfil\b"),
     "link in bio"),
    (re.compile(r"(?i)\b(?:swipe|tap) (?:through|left|right|for|to)\b"
                r"|\bdesliz[áa]\b|\bdesliza\b|\bpas[áa] (?:a la siguiente|las im[áa]genes|el carrusel)\b|\btoc[áa] (?:acá|aquí|el link|la imagen)\b"),
     "swipe or tap"),
    (re.compile(r"(?i)\btell me\b|\bwhat would you\b|\bwhich one\b"
                r"|\bcont[áa]me\b|\bcu[ée]ntame\b|\bdec[íi]me\b|\bdime\b|\brespond[ée]me\b"
                r"|\b¿?(?:vos )?qu[ée] (?:har[íi]as|eleg[íi]s|elegirías|pens[áa]s|opin[áa]s)\b|\b¿?cu[áa]l (?:eleg[íi]s|elegir[íi]as|es tu|te pas[óo]|prefer[íi]s)\b|\b¿?te pas[óo]\b"),
     "answer a question"),
    (re.compile(r"(?i)\bbook a call\b"
                r"|\bagend[áa](?:lo|te)?\b|\bagenda (?:una|tu|un)\b|\breserv[áa](?:te|lo)?\b|\breserva tu\b|\bsac[áa] (?:un )?turno\b"),
     "book a call"),
]

FILLER_TAGS = {"#viral", "#fyp", "#explore", "#explorepage", "#foryou", "#foryoupage",
               "#trending", "#instagood", "#love", "#follow", "#like4like", "#reels",
               "#reelsinstagram", "#viralreels", "#instadaily",
               # es
               "#parati", "#paratí", "#explorar", "#emprendedor", "#emprendedores",
               "#emprender", "#emprendimiento", "#motivacion", "#motivación", "#exito",
               "#éxito", "#frases", "#siguemeytesigo", "#sigueme", "#seguime", "#like",
               "#likes", "#amor", "#viralvideos", "#tendencia", "#argentina", "#reel"}


def fold(s):
    """Lower-case and strip accents, so 'automatización' matches '#automatizacion'."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower())
                   if not unicodedata.combining(c))


def visible_window(text, cut):
    """What the feed shows. Instagram cuts mid-word, so this does too."""
    flat = text.strip()
    return flat if len(flat) <= cut else flat[:cut]


def render_box(window, truncated, out=sys.stdout, width=52):
    print("\n  WHAT THE FEED SHOWS", file=out)
    print("  +" + "-" * (width + 2) + "+", file=out)
    lines = []
    for raw in window.split("\n"):
        lines.extend(textwrap.wrap(raw, width) or [""])
    for line in lines[:8]:
        print(f"  | {line:<{width}} |", file=out)
    tail = "... more" if truncated else "(whole caption fits)"
    print("  +" + "-" * (width + 2 - len(tail) - 2) + f" {tail} " + "+", file=out)


def analyse(text, cut=TRUNCATE, keywords=None):
    text = text.rstrip()
    stripped = text.strip()
    chars = len(stripped)
    lines = [l for l in stripped.split("\n")]
    first_line = lines[0].strip() if lines else ""
    tags = HASHTAG_RE.findall(stripped)
    mentions = MENTION_RE.findall(stripped)
    links = LINK_RE.findall(stripped)
    emoji = EMOJI_RE.findall(stripped)
    window = visible_window(stripped, cut)
    truncated = chars > cut
    asks = [name for pattern, name in ASKS if pattern.search(stripped)]
    filler = [t for t in tags if t.lower() in FILLER_TAGS]
    keywords = [k.strip() for k in (keywords or []) if k.strip()]

    checks = []

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    add("LENGTH", "FAIL" if chars > LIMIT else "PASS",
        f"{chars} / {LIMIT} characters" + (f", {chars - LIMIT} over the limit"
                                           if chars > LIMIT else ""))

    if not first_line:
        add("FIRST LINE", "FAIL", "the caption opens on a blank line")
    elif first_line.startswith("#") or first_line.startswith("@"):
        add("FIRST LINE", "FAIL",
            "opens on a hashtag or a mention, which is the one position worth a sentence")
    elif len(first_line) > cut:
        add("FIRST LINE", "WARN",
            f"{len(first_line)} characters, so it gets cut at {cut} mid-thought. "
            "Fine if the cut is a cliffhanger, bad if it is a subordinate clause")
    else:
        add("FIRST LINE", "PASS", f"{len(first_line)} characters, lands whole")

    add("HOOK IS CONCRETE", "PASS" if CONCRETE_RE.search(window) else "WARN",
        f"{len(CONCRETE_RE.findall(window))} number(s) or name(s) in the visible window"
        + ("" if CONCRETE_RE.search(window) else " - nothing checkable before the tap"))

    if len(tags) > HASHTAG_LIMIT:
        add("HASHTAGS", "FAIL", f"{len(tags)} tags, over Instagram's cap of {HASHTAG_LIMIT}. "
                                "Tags past the fifth do not count and the block reads as old")
    elif len(tags) == HASHTAG_LIMIT and filler:
        add("HASHTAGS", "WARN", f"{len(tags)} tags, at the cap, and "
                                f"{len(filler)} of them generic. Spend the five on topics")
    elif filler:
        add("HASHTAGS", "WARN", f"{len(tags)} tags, {len(filler)} of them generic "
                                f"({', '.join(filler[:3])}). Those describe nothing")
    else:
        add("HASHTAGS", "PASS", f"{len(tags)} tag(s)" + (f": {' '.join(tags)}" if tags else ""))

    if not tags:
        add("TAG PLACEMENT", "PASS", "no tags to place")
    elif any(re.search(r"(?:^|\s)" + re.escape(t) + r"\b", window) for t in tags):
        add("TAG PLACEMENT", "WARN", "a hashtag is inside the visible window, "
                                     "spending feed space on a label")
    else:
        add("TAG PLACEMENT", "PASS", "tags are below the fold")

    add("LINKS", "WARN" if links else "PASS",
        f"{len(links)} link(s) in the caption, and captions are not clickable. "
        f"Move it to the bio or the DM" if links else "no dead links in the body")

    if len(asks) == 1:
        add("ONE ASK", "PASS", f"one call to action: {asks[0]}")
    elif not asks:
        add("ONE ASK", "WARN", "no call to action. Decide what this post is for")
    else:
        add("ONE ASK", "WARN", f"{len(asks)} asks ({', '.join(asks)}). "
                               "Two asks is the same as none")

    density = len(emoji) * 100 / max(chars, 1)
    add("EMOJI", "WARN" if density > 4 else "PASS",
        f"{len(emoji)} emoji, {density:.1f} per 100 characters"
        + (" - reads as decoration" if density > 4 else ""))

    if keywords:
        # Accent-insensitive: hashtags drop the accents ("#automatizacion"),
        # and so does half of the audience when they search.
        low = fold(stripped)
        found = [k for k in keywords if fold(k) in low]
        missing = [k for k in keywords if fold(k) not in low]
        in_window = [k for k in found if fold(k) in fold(window)]
        status = "PASS" if not missing else ("WARN" if found else "FAIL")
        add("SEARCH TERMS", status,
            f"{len(found)}/{len(keywords)} present"
            + (f", {len(in_window)} in the visible window" if found else "")
            + (f". Missing: {', '.join(missing)}" if missing else ""))

    fails = sum(1 for c in checks if c["status"] == "FAIL")
    warns = sum(1 for c in checks if c["status"] == "WARN")
    verdict = "FIX" if fails else ("REVIEW" if warns else "READY")

    return {
        "characters": chars, "limit": LIMIT, "truncate_at": cut,
        "visible": window, "truncated": truncated,
        "first_line_chars": len(first_line),
        "hashtags": tags, "mentions": mentions, "links": links,
        "emoji": len(emoji), "asks": asks,
        "checks": checks, "verdict": verdict,
    }


def render(a, out=sys.stdout):
    head = (f"CAPTION LINT  ·  {a['characters']} / {a['limit']} chars  ·  "
            f"{len(a['hashtags'])} hashtags  ·  {len(a['asks'])} ask(s)")
    print("\n" + head, file=out)
    print("=" * max(len(head), 62), file=out)
    render_box(a["visible"], a["truncated"], out=out)
    print("", file=out)
    for c in a["checks"]:
        print(f"  {c['status']:<5} {c['check']:<17} {c['detail']}", file=out)
    print("-" * max(len(head), 62), file=out)
    print(f"  VERDICT  {a['verdict']}\n", file=out)


def main():
    ap = argparse.ArgumentParser(description="Lint an Instagram caption.")
    ap.add_argument("input", nargs="?", default="-", help="caption file, or - for stdin")
    ap.add_argument("--truncate", type=int, default=TRUNCATE,
                    help=f"characters shown before '... more' (default {TRUNCATE})")
    ap.add_argument("--keywords", default="", help="comma-separated terms you want to be found for")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    raw = _read_input(args.input)
    a = analyse(raw, cut=args.truncate, keywords=args.keywords.split(","))
    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)
    sys.exit(0 if a["verdict"] == "READY" else 1)


if __name__ == "__main__":
    main()
