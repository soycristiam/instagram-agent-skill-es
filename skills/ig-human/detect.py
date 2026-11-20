#!/usr/bin/env python3
"""
detect.py - a five-check panel that scores how machine-written a draft looks.

What this is:  five local heuristics modelled on the signals public AI
detectors actually measure - sentence-length variation, concreteness, stock
vocabulary, typographic fingerprint, and voice. Every score is computed on
your machine from the text alone. Nothing is uploaded.

What this is NOT:  GPTZero, Originality, Copyleaks, Winston or Turnitin.
It does not call their APIs and it cannot promise their verdict. It catches
the things they all key on, which is why fixing them tends to move their
numbers too - but the only honest claim is the one on this line.

Each check returns a HUMAN score from 0 to 100. Higher is better.

Usage
  python3 detect.py draft.txt
  pbpaste | python3 detect.py -
  python3 detect.py draft.txt --json
  python3 detect.py before.txt after.txt      # compare two drafts
"""

import argparse
import json
import os
import re
import statistics
import sys
import unicodedata

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

HERE = os.path.dirname(os.path.abspath(__file__))
LEX = os.path.join(HERE, "slop.json")

# ---------------------------------------------------------------------------
# Spanish (rioplatense) adaptation. Tokenising is Unicode-aware. VOICE keeps
# the English contraction count and adds the Spanish equivalents of "a person
# wrote this": voseo forms and imperatives ("tenés", "fijate", "mirá"),
# second-person pronouns, first-person pronouns and -é/-í preterites, and the
# colloquial markers of the Río de la Plata ("che", "posta", "laburo").
# ---------------------------------------------------------------------------

SENT_RE = re.compile(r"(?:[^.!?\n]|(?<=\d)\.(?=\d))+[.!?]*")   # "2.000" is not a sentence end
WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)?")
CONTRACTIONS = re.compile(r"\b\w+'(?:s|t|re|ve|ll|d|m)\b", re.IGNORECASE)
PRONOUNS = re.compile(
    r"\b(?:i|me|my|mine|we|us|our|you|your"
    r"|yo|mi|mis|mío|mía|míos|mías|nosotros|nosotras|nos|nuestro|nuestra"
    r"|nuestros|nuestras|conmigo"
    r"|vos|te|tu|tus|tuyo|tuya|tuyos|tuyas|tú|ti|contigo|usted|ustedes|les|os)\b",
    re.IGNORECASE)
VOSEO = re.compile(
    r"\b(?:sos|tenés|querés|podés|sabés|hacés|estás|vas|necesitás|pensás|creés"
    r"|decís|vendés|cobrás|perdés|gastás|pagás|usás|mandás|respondés|tardás"
    r"|contestás|laburás|trabajás|seguís|vivís|fijate|mirá|dejá|probá|hacé"
    r"|hacelo|hacela|decime|mandame|mandá|escribime|escribí|comentá|guardá"
    r"|guardalo|compartí|compartilo|frená|pará|imaginá|anotá|leé|poné|sacá"
    r"|acordate|olvidate|pensá|contame|contá|agendá|agendalo|reservá|probalo"
    r"|chequeá|revisá|calculá|medí|preguntale|decile|mostrale|cerrá|abrí"
    r"|sumá|conectá|cambiá|automatizá|respondé|contestá|cobrá|vendé|armá|usá"
    r"|empezá|arrancá|tomá|borrá|copiá|robá|dale|andá|vení|fijense|fíjense)\b",
    re.IGNORECASE)
VOSEO_ENDING = re.compile(r"\b[a-záéíóúñü]{3,}(?:ás|és)\b", re.IGNORECASE)
NOT_VOSEO = {
    "además", "jamás", "quizás", "atrás", "detrás", "demás", "inglés",
    "francés", "después", "través", "interés", "estrés", "revés", "cortés",
    "portugués", "holandés", "japonés", "danés", "irlandés", "escocés",
    "burgués", "marqués", "ciprés", "montés", "compás", "finlandés",
    "entremés", "arnés", "andrés", "tomás", "inés", "moisés", "nicolás",
}
FIRST_PERSON_VERB = re.compile(r"\b[a-záéíóúñü]{3,}(?:é|í)\b", re.IGNORECASE)
NOT_FIRST_PERSON = {
    "qué", "porqué", "café", "así", "ahí", "aquí", "allí", "sí", "bebé",
    "josé", "maní", "té", "comité", "carné", "puré", "cliché", "colibrí",
    "israelí", "iraní", "marroquí", "rubí", "jabalí", "esquí", "mí",
    # voseo imperatives of -er/-ir verbs share the ending; they are 2nd person
    "hacé", "poné", "decí", "vení", "escribí", "compartí", "seguí", "leé",
    "medí", "respondé", "vendé", "abrí", "corré", "comé", "bebé", "creé",
}
COLLOQUIAL = re.compile(
    r"\b(?:che|bro|posta|re|laburo|laburar|laburás|guita|plata|quilombo"
    r"|bardo|boludo|boluda|flaco|flaca|loco|loca|dale|ojo|mirá|fijate"
    r"|tranqui|igual|onda|zafar|zafás|bancar|bancás|garpa|garpar|joya"
    r"|copado|copada|bajón|bajon|al toque|de una|ni ahí|ni ahi|un montón"
    r"|un monton|la verdad|en serio|literal|tal cual|obvio|nada|o sea"
    r"|viste|sabés qué|sabes que|te juro|capaz|ponele|digamos|más o menos)\b",
    re.IGNORECASE)
NUMBERS = re.compile(r"\b\d[\d,.]*%?\b|(?:US\$|USD|\$|€)\s?\d")
# Spanish writes weekdays and months in lowercase, so PROPER misses them, and
# spoken numbers ("diez minutos", "cinco reels") are as concrete as digits.
# "un/una/uno" are left out on purpose: they are articles far more often.
CONCRETE_ES = re.compile(
    r"\b(?:dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece"
    r"|catorce|quince|veinte|treinta|cuarenta|cincuenta|sesenta|setenta"
    r"|ochenta|noventa|cien|ciento|doscientos|trescientos|quinientos|mil"
    r"|millón|millones|media hora|lunes|martes|miércoles|miercoles|jueves"
    r"|viernes|sábado|sabado|domingo|enero|febrero|marzo|abril|mayo|junio"
    r"|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b",
    re.IGNORECASE)
PROPER = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]{2,}\w*\b", re.MULTILINE)


def informality_hits(text):
    """Contractions (en) plus voseo forms, imperatives and -ás/-és endings (es)."""
    n = len(CONTRACTIONS.findall(text)) + len(VOSEO.findall(text))
    seen = set(m.lower() for m in VOSEO.findall(text))
    for w in WORD_RE.findall(text):
        lw = w.lower()
        if lw in seen:
            continue
        if VOSEO_ENDING.fullmatch(lw) and lw not in NOT_VOSEO:
            n += 1
        elif FIRST_PERSON_VERB.fullmatch(lw) and lw not in NOT_FIRST_PERSON:
            n += 1
    return n


def clamp(n):
    return max(0.0, min(100.0, n))


def scale(value, human, machine):
    """Map value onto 0-100 where `human` -> 100 and `machine` -> 0."""
    if human == machine:
        return 50.0
    return clamp((value - machine) / (human - machine) * 100)


def sentences(text):
    return [s.strip() for s in SENT_RE.findall(text) if len(s.split()) > 2]


def words(text):
    return WORD_RE.findall(text)


def check_burstiness(text):
    """Humans vary sentence length hard. Models write even."""
    lens = [len(s.split()) for s in sentences(text)]
    if len(lens) < 4:
        return 50.0, "too short to judge"
    mean = statistics.mean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0
    score = scale(cv, human=0.70, machine=0.22)
    return score, f"variation {cv:.2f} across {len(lens)} sentences (want 0.55+)"


def check_specificity(text):
    """Numbers, names and concrete nouns. Slop is abstract."""
    w = words(text)
    if len(w) < 25:
        return 50.0, "too short to judge"
    per100 = 100 / len(w)
    hits = (len(NUMBERS.findall(text)) + len(set(PROPER.findall(text)))
            + len(CONCRETE_ES.findall(text)))
    density = hits * per100
    score = scale(density, human=6.0, machine=0.5)
    return score, f"{hits} concrete markers, {density:.1f} per 100 words (want 4+)"


def check_slop(text, lex):
    """Stock vocabulary density against the lexicon."""
    w = words(text)
    if not w:
        return 50.0, "empty"
    hits, found = 0, []
    for entry in lex["words"] + lex["phrases"]:
        pattern = re.compile(r"\b" + re.escape(entry["find"]).replace(r"\ ", r"\s+") + r"\b",
                             re.IGNORECASE)
        n = len(pattern.findall(text))
        if n:
            hits += n
            found.append(entry["find"])
    density = hits * 100 / len(w)
    score = scale(density, human=0.0, machine=4.0)
    detail = f"{hits} stock terms, {density:.1f} per 100 words"
    if found:
        detail += " (" + ", ".join(sorted(found)[:4]) + (", ..." if len(found) > 4 else "") + ")"
    return score, detail


def check_fingerprint(text):
    """Characters a phone keyboard does not produce."""
    invisible = sum(1 for c in text if unicodedata.category(c) == "Cf")
    em = text.count("—")
    curly = sum(text.count(c) for c in "‘’“”")
    ellip = text.count("…")
    nbsp = sum(text.count(c) for c in "   ")
    total = invisible * 4 + em * 2 + curly + ellip + nbsp
    per1k = total * 1000 / max(len(text), 1)
    score = scale(per1k, human=0.0, machine=12.0)
    detail = (f"{invisible} invisible, {em} em dash, {curly} curly quote, "
              f"{ellip} ellipsis, {nbsp} hard space")
    return score, detail


def check_voice(text, lex):
    """Contractions, person, and the shapes models default to."""
    w = words(text)
    if len(w) < 25:
        return 50.0, "too short to judge"
    per100 = 100 / len(w)
    # "contractions" keeps its name for the JSON consumers, but it is now the
    # informality count: English contractions plus Spanish voseo and
    # first-person verb forms. Colloquial markers count half each.
    contractions = (informality_hits(text) + 0.5 * len(COLLOQUIAL.findall(text))) * per100
    person = len(PRONOUNS.findall(text)) * per100
    tells = 0
    names = []
    for s in lex["structures"]:
        try:
            n = len(re.compile(s["regex"], re.MULTILINE).findall(text))
        except re.error:
            continue
        if n:
            tells += n
            names.append(s["id"])
    bullets = [len(b.split()) for b in re.findall(r"(?m)^\s*[-*•]\s+(.+)$", text)]
    uniform = (len(bullets) >= 3 and statistics.pstdev(bullets) < 1.6)
    score = (scale(contractions, human=3.0, machine=0.0) * 0.35
             + scale(person, human=8.0, machine=1.0) * 0.35
             + clamp(100 - tells * 22) * 0.30)
    if uniform:
        score -= 12
        names.append("uniform-bullets")
    detail = (f"{contractions:.1f} contractions/voseo, {person:.1f} personal pronouns "
              f"per 100 words, {tells} structural tell(s)")
    if names:
        detail += " [" + ", ".join(names[:4]) + "]"
    return clamp(score), detail


CHECKS = ["BURSTINESS", "SPECIFICITY", "SLOP DENSITY", "FINGERPRINT", "VOICE"]


def run(text, lex):
    results = {}
    results["BURSTINESS"] = check_burstiness(text)
    results["SPECIFICITY"] = check_specificity(text)
    results["SLOP DENSITY"] = check_slop(text, lex)
    results["FINGERPRINT"] = check_fingerprint(text)
    results["VOICE"] = check_voice(text, lex)
    scores = [results[c][0] for c in CHECKS]
    # The weakest check drags the verdict: a detector only needs one signal.
    overall = statistics.mean(scores) * 0.6 + min(scores) * 0.4
    verdict = "PASS" if overall >= 70 and min(scores) >= 55 else (
        "REVIEW" if overall >= 50 else "FLAGGED")
    return results, overall, verdict


def bar(score, width=24):
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


def render(results, overall, verdict, label=None, out=sys.stdout):
    title = "AI DETECTION PANEL" + (f"  -  {label}" if label else "")
    print("\n" + title, file=out)
    print("=" * max(len(title), 62), file=out)
    for name in CHECKS:
        score, detail = results[name]
        print(f"  {name:<13} {bar(score)} {score:5.1f}", file=out)
        print(f"  {'':<13} {detail}", file=out)
    print("-" * 62, file=out)
    print(f"  {'HUMAN SCORE':<13} {bar(overall)} {overall:5.1f}   {verdict}", file=out)
    if verdict != "PASS":
        weakest = min(CHECKS, key=lambda c: results[c][0])
        print(f"\n  Weakest signal: {weakest}. Fix that first.", file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(description="Score how machine-written a draft looks.")
    ap.add_argument("input", nargs="?", default="-", help="file, or - for stdin")
    ap.add_argument("compare", nargs="?", help="second file, to show before/after")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--lexicon", default=LEX)
    args = ap.parse_args()

    lex = json.load(open(args.lexicon, encoding="utf-8"))
    read = _read_input

    targets = [(args.input, read(args.input))]
    if args.compare:
        targets.append((args.compare, read(args.compare)))

    payload = []
    for name, text in targets:
        results, overall, verdict = run(text, lex)
        payload.append({
            "source": name,
            "checks": {k: {"score": round(v[0], 1), "detail": v[1]} for k, v in results.items()},
            "human_score": round(overall, 1),
            "verdict": verdict,
        })

    if args.json:
        print(json.dumps(payload if args.compare else payload[0], indent=2, ensure_ascii=False))
        return

    for (name, text), p in zip(targets, payload):
        results, overall, verdict = run(text, lex)
        render(results, overall, verdict, label=os.path.basename(name) if args.compare else None)
    if args.compare:
        a, b = payload
        delta = b["human_score"] - a["human_score"]
        print(f"  {a['human_score']:.1f} {a['verdict']}  ->  "
              f"{b['human_score']:.1f} {b['verdict']}   ({delta:+.1f})\n")

    sys.exit(0 if payload[-1]["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
