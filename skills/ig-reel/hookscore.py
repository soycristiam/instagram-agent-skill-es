#!/usr/bin/env python3
"""
hookscore.py - score the first line of a Reel on the five things strong hooks
have in common, and rank a batch of them against each other.

What this is:  five local heuristics, computed on your machine from the text
alone. They measure properties that hooks which hold attention tend to share -
a length you can say in under three seconds, a concrete marker, something at stake,
the payload at the front rather than the back, and a viewer to aim it at.

What this is NOT:  a view predictor. It was tested against 74 real short-form
hooks, transcribed from the first three seconds of the top eight and bottom
eight performers on five channels. Separating a real hook from a deliberately
bad one it does well: AUC 0.83, and 9 of 10 written-to-be-bad hooks scored
below the real median. Separating a good creator's hits from that same
creator's misses it barely does at all: AUC 0.56, where 0.50 is a coin flip.

So use it for what it measured well. It catches greetings, preambles, hooks
with nothing concrete in them and hooks that take five seconds to say. It will
not tell you which of two decent hooks will travel, and nothing that reads text
can, because that is decided by your face, your edit, your audio and who
Instagram shows it to. Trust the retention graph over this script.

Each check returns 0 to 100. Higher is better.

Usage
  python3 hookscore.py hooks.txt              # one hook per line, ranked
  python3 hookscore.py --hook "I lost $18,000 on one missing contract."
  pbpaste | python3 hookscore.py -
  python3 hookscore.py hooks.txt --json
"""

import argparse
import json
import re
import statistics
import sys

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

# ---------------------------------------------------------------------------
# Spanish (rioplatense) adaptation. English vocabulary is kept so English hooks
# still score; Spanish is added alongside it. Tokenising is Unicode-aware so
# "automatización" and "dólares" are single words.
# ---------------------------------------------------------------------------

WORD_RE = re.compile(r"[\w$%'’€-]+")
NUMBER_RE = re.compile(
    r"(?:US\$|USD|U\$S|\$|€|ARS|MXN)\s?\d[\d.,]*"              # money, whole
    r"|\b\d[\d.,]*\s?"                                        # a figure, with or
    r"(?:%|k\b|x\b|hrs?\b|hours?\b|mins?\b|minutes?\b"        # without a unit
    r"|days?\b|weeks?\b|months?\b|years?\b"
    r"|hs\b|horas?\b|minutos?\b|segundos?\b|d[ií]as?\b|semanas?\b"
    r"|mes\b|meses\b|años?\b|d[óo]lares\b|pesos\b|euros\b|lucas\b|palos\b"
    r"|clientes?\b|ventas?\b|pedidos?\b|mensajes?\b|leads?\b)?",
    re.IGNORECASE)
PROPER_RE = re.compile(r"(?<!^)\b[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]{2,}\w*\b")
HASHTAG_RE = re.compile(r"(?:^|\s)#\w+")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF☀-➿]")

# Spoken hooks say their numbers out loud. "Zero dollars" and "twenty grand"
# are as concrete as "$0" and "$20,000", and counting only digits missed them.
# "one" and "first" are deliberately absent: they are filler far more often
# than they are a quantity. Same for "uno", "una", "primero".
SPOKEN_NUMBERS = {
    "zero", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "fifteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million",
    "billion", "dozen", "half", "twice", "triple",
    # es
    "cero", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "quince", "veinte", "treinta", "cuarenta",
    "cincuenta", "sesenta", "setenta", "ochenta", "noventa", "cien", "ciento",
    "cientos", "mil", "miles", "millón", "millon", "millones", "docena",
    "mitad", "doble", "triple",
}
MONEY_WORDS = {
    "dollars", "dollar", "bucks", "grand", "percent", "cents",
    "millionaire", "billionaire", "revenue", "profit", "salary", "rent",
    # es
    "dólares", "dolares", "dólar", "dolar", "pesos", "euros", "lucas", "palos",
    "centavos", "porciento", "facturación", "facturacion", "ganancia",
    "ganancias", "sueldo", "alquiler", "plata", "guita", "usd",
}

# Words that put something on the line. A hook with none of these is a
# statement; a hook with one is a reason to keep watching.
STAKES = {
    "stop", "never", "wrong", "mistake", "mistakes", "lost", "lose", "losing",
    "cost", "costs", "broke", "broken", "failed", "failure", "fail", "nobody",
    "no", "not", "don't", "dont", "doesn't", "didn't", "can't", "won't",
    "quit", "quitting", "fired", "deleted", "delete", "killed", "kills", "kill",
    "replaced", "replaces", "cut", "beat", "free", "paid", "charged", "hired",
    "saved", "first",
    "banned", "illegal", "worst", "hate", "hated", "wasted", "waste", "scam",
    "lie", "lied", "lying", "truth", "secret", "hidden", "stole", "stolen",
    "before", "until", "instead", "but", "except", "unless", "problem",
    "risk", "danger", "warning", "regret", "wish", "should", "shouldn't",
    "still", "already", "only", "without", "versus", "vs", "actually",
    # es: pérdida, costo, negación, tensión
    "dejá", "deja", "dejen", "basta", "nunca", "jamás", "jamas", "mal",
    "error", "errores", "equivocado", "equivocada", "equivocás", "equivocas",
    "perdí", "perdi", "perder", "perdiendo", "perdió", "perdio", "perdés",
    "perdes", "perdiste", "perdimos", "pierde", "pierden", "pierdo", "perdido",
    "perdida", "perdidas", "perdidos",
    "costó", "costo", "cuesta", "cuestan", "costaron", "costando", "caro", "cara",
    "roto", "rota", "rompió", "rompio", "rompe", "fallé", "falle", "falló",
    "fallo", "falla", "fallan", "fracaso", "fracasó", "fracaso", "fracasan",
    "nadie", "ni", "ningún", "ningun", "ninguna", "ninguno", "nada",
    "renuncié", "renuncie", "despidieron", "despedí", "echaron", "borré",
    "borre", "borrá", "borra", "mató", "mata", "matan", "reemplazó",
    "reemplaza", "reemplazan", "reemplacé", "cortá", "corta", "corté",
    "gratis", "pagué", "pague", "pagó", "pago", "pagan", "pagando", "cobré",
    "cobre", "cobró", "cobra", "cobran", "cobrás", "contraté", "contrate",
    "ahorré", "ahorre", "ahorra", "ahorran", "ahorrás", "primero", "primer",
    "primera", "último", "ultimo", "última",
    "prohibido", "ilegal", "peor", "odio", "odié", "odie", "desperdicié",
    "desperdicio", "tiré", "tire", "tirás", "quemé", "queme", "quemás",
    "quemando", "estafa", "estafaron", "mentira", "mintió", "mintieron",
    "verdad", "secreto", "oculto", "escondido", "robó", "robaron", "roban",
    "antes", "hasta", "vez", "pero", "salvo", "excepto", "problema",
    "problemas", "riesgo", "peligro", "cuidado", "ojo", "arrepiento",
    "arrepentí", "ojalá", "ojala", "debería", "deberías", "deberia",
    "deberias", "todavía", "todavia", "ya", "solo", "sólo", "sin", "versus",
    "vs", "realmente", "realidad", "tarde", "demasiado", "trampa", "culpa",
    "cuello", "botella", "frenó", "frena", "frenando", "trabado", "trabada",
    "atascado", "estancado", "estancada", "espera", "esperando", "esperó",
    "respondió", "respondí", "respondés", "contestó", "contestás",
    "cancelado", "canceló", "cancelaron", "devolución", "devolvió", "reembolso",
}

# Openers that spend the first second saying nothing.
WEAK_OPENERS = [
    "so", "ok", "okay", "hey", "hi", "hello", "guys", "yo", "alright",
    "welcome", "today", "basically", "honestly", "look", "listen", "um",
    "just", "let", "lets", "let's", "i wanted", "i want", "one of",
    "have you", "did you", "do you", "are you", "in this", "in today",
    "the thing", "a lot", "there is", "there are", "this is", "it is",
    "as a", "when it", "if you've", "you know",
    # es
    "bueno", "buenas", "buen", "hola", "holis", "holaa", "gente", "che",
    "dale", "hoy", "básicamente", "basicamente", "sinceramente",
    "honestamente", "la verdad", "mirá", "mira", "miren", "escuchá",
    "escucha", "escuchen", "eh", "este", "o sea", "bien", "okey", "entonces",
    "quería", "queria", "quiero", "les quiero", "te quiero", "hoy les",
    "hoy te", "hoy vengo", "hoy quiero", "hoy vamos", "uno de", "una de",
    "alguna vez", "sabías", "sabias", "sabían", "te pasó", "les pasó",
    "en este", "en el", "el tema", "la cosa", "un montón", "hay un",
    "hay una", "esto es", "es un", "es una", "como", "cuando se", "si alguna",
    "ya sabés", "ya sabes", "viste que", "bienvenidos", "bienvenidas",
    "qué tal", "que tal", "cómo están", "como estan", "cómo andan",
    "como andan", "les cuento", "te cuento", "vengo a", "vamos a",
    "en el video", "en este video", "antes de empezar", "primero que nada",
]

# Imperatives that earn the front position.
IMPERATIVES = {
    "stop", "steal", "copy", "delete", "try", "watch", "read", "save",
    "use", "build", "make", "write", "send", "take", "start", "quit",
    "never", "always", "don't", "dont", "do", "put", "run", "check",
    # es (voseo + tú)
    "dejá", "deja", "basta", "robá", "roba", "copiá", "copia", "borrá",
    "borra", "probá", "prueba", "leé", "lee", "guardá", "guarda", "usá",
    "usa", "armá", "arma", "hacé", "hace", "escribí", "escribe", "mandá",
    "manda", "tomá", "toma", "empezá", "empieza", "arrancá", "arranca",
    "renunciá", "renuncia", "nunca", "siempre", "no", "poné", "pon", "corré",
    "corre", "fijate", "fíjate", "chequeá", "chequea", "revisá", "revisa",
    "anotá", "anota", "frená", "frena", "pará", "para", "olvidate",
    "olvídate", "acordate", "acuérdate", "imaginá", "imagina", "pensá",
    "piensa", "comentá", "comenta", "contestá", "contesta", "respondé",
    "responde", "cobrá", "cobra", "vendé", "vende", "automatizá",
    "automatiza", "sacá", "saca", "cortá", "corta", "calculá", "calcula",
    "medí", "mide", "preguntale", "pregúntale", "decile", "dile", "mostrale",
    "cerrá", "cierra", "abrí", "abre", "contá", "cuenta", "sumá", "suma",
    "restá", "resta", "conectá", "conecta", "cambiá", "cambia",
}

# Second person in Spanish. Explicit pronouns, the most common voseo verb
# forms, the voseo/tú imperatives above, and a verb-ending heuristic (-ás /
# -és is voseo present: "tenés", "cobrás") with the nouns and adverbs that
# share the ending excluded.
SECOND_PERSON_RE = re.compile(
    r"\b(?:you|your|you're|youre|yourself"
    r"|vos|te|tu|tus|tuyo|tuya|tuyos|tuyas|tú|ti|contigo|usted|ustedes|les|os"
    r"|sos|tenés|tenes|querés|queres|podés|podes|sabés|sabes|hacés|haces"
    r"|estás|estas|vas|necesitás|necesitas|pensás|piensas|creés|crees|ves"
    r"|decís|dices|vendés|vendes|cobrás|cobras|perdés|pierdes|gastás|gastas"
    r"|pagás|pagas|usás|usas|mandás|mandas|respondés|respondes|tardás|tardas"
    r"|contestás|contestas|laburás|laburas|trabajás|trabajas|seguís|sigues"
    r"|vivís|vives|tenías|tenias|podías|podias|querías|querias|sabías|sabias"
    r"|hiciste|perdiste|pagaste|cobraste|gastaste|mandaste|respondiste"
    r"|vendiste|tardaste|contrataste|dejaste|armaste|probaste)\b",
    re.IGNORECASE)
VOSEO_ENDING_RE = re.compile(r"\b[a-záéíóúñü]{3,}(?:ás|és)\b", re.IGNORECASE)
NOT_VOSEO = {
    "además", "jamás", "quizás", "atrás", "detrás", "demás", "inglés",
    "francés", "después", "través", "interés", "estrés", "revés", "cortés",
    "portugués", "holandés", "japonés", "danés", "irlandés", "escocés",
    "burgués", "marqués", "ciprés", "montés", "compás", "finlandés",
    "entremés", "arnés", "pavés", "andrés", "tomás", "inés", "moisés",
    "nicolás", "barrabás", "ananás", "ajedrez",
}
# First person: pronouns, the common irregular preterites, and -é/-í
# preterite endings ("perdí", "pagué") minus words that share the ending.
# The -é/-í check runs after the second-person check because "escribí" is
# both "I wrote" and "write!" in voseo; the imperative set wins that tie.
FIRST_PERSON_RE = re.compile(
    r"\b(?:i|my|me|we|our"
    r"|yo|mi|mis|mío|mía|míos|mías|nosotros|nosotras|nos|nuestro|nuestra"
    r"|nuestros|nuestras|conmigo|hice|tuve|fui|estuve|pude|puse|dije|vi|di"
    r"|supe|quise|vine|traje|hago|tengo|estoy|puedo|quiero|sé|voy|soy|cobro"
    r"|pierdo|gasto|pago|vendo|trabajo|laburo|facturo|automatizo)\b",
    re.IGNORECASE)
FIRST_PERSON_VERB_RE = re.compile(r"\b[a-záéíóúñü]{3,}(?:é|í)\b", re.IGNORECASE)
NOT_FIRST_PERSON = {
    "qué", "porqué", "café", "así", "ahí", "aquí", "allí", "sí", "bebé",
    "josé", "maní", "pié", "té", "comité", "chalé", "carné", "puré", "canapé",
    "cabaré", "ballet", "corsé", "parqué", "bidé", "cliché", "rosé", "soufflé",
    "colibrí", "israelí", "iraní", "marroquí", "paquistaní", "rubí", "jabalí",
    "alhelí", "frenesí", "esquí", "taxi", "safari", "wifi", "mí", "tahití",
    "haití", "bisturí", "berbiquí", "zahorí", "maniquí", "ahí", "hindú",
}

DEALBREAKERS = [
    (re.compile(r"(?i)^\s*¿?(?:stop scrolling|don'?t scroll"
                r"|dej[áa] de scrollear|dejen de scrollear|par[áa] de scrollear"
                r"|no sigas scrolleando|no scrollees|no pases de largo"
                r"|esper[áa][,.]? no (?:sigas|scrollees|pases))"),
     "Opens with \"stop scrolling\". Asking for attention proves you have not earned it."),
    (re.compile(r"(?i)\b(?:in (?:this|today'?s) (?:video|reel)|i'?m going to show you|i'?ll show you how"
                r"|en (?:este|el) (?:video|reel|posteo)(?: de hoy)?"
                r"|hoy (?:les|te|os) (?:quiero|voy a|vengo a|quería) (?:hablar|contar|mostrar|enseñar|explicar)"
                r"|(?:te|les|os) voy a (?:mostrar|enseñar|contar|explicar) (?:cómo|como|por qué|porque|qué|que)"
                r"|hoy vengo a (?:contar|hablar|mostrar)(?:les|te)?"
                r"|hoy (?:vamos a|les voy a|te voy a) (?:hablar|ver|contar))\b"),
     "Video preamble. Delete it and open on the payoff."),
    (re.compile(r"(?i)^\s*¡?(?:hey |hi |what'?s up |welcome "
                r"|hola\b|holis\b|holaa+\b|buenas\b|buen d[ií]a\b|buenos d[ií]as\b"
                r"|buenas tardes\b|buenas noches\b|qu[ée] tal\b|c[óo]mo (?:est[áa]n|andan)\b"
                r"|bienvenid[oa]s?\b|hey gente\b|che gente\b|gente\b)"),
     "Greeting. Nobody came to the feed to be greeted."),
    (HASHTAG_RE,
     "Hashtag in the hook. Hashtags belong at the bottom of the caption, if anywhere."),
    (EMOJI_RE,
     "Emoji in the hook. On-screen text at hook size has room for words or for an emoji, not both."),
]


def clamp(n):
    return max(0.0, min(100.0, n))


def words(text):
    # "$18,000" is one word when it is spoken, so it is one word here too.
    # Spanish writes thousands with a dot ("2.000"), so that collapses as well.
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)
    text = re.sub(r"(?<=\d)\.(?=\d{3}\b)", "", text)
    return WORD_RE.findall(text)


def second_person_hits(text):
    """Explicit second person, voseo forms, imperatives and -ás/-és endings."""
    hits = [m.group(0) for m in SECOND_PERSON_RE.finditer(text)]
    low = [w.lower().strip("'’¿¡") for w in words(text)]
    hits += [w for w in low if w in IMPERATIVES and w not in {"no", "nunca", "siempre", "never", "always", "don't", "dont", "do"}]
    hits += [w for w in low if VOSEO_ENDING_RE.fullmatch(w) and w not in NOT_VOSEO]
    return hits


def first_person_hits(text):
    """Explicit first person plus -é/-í preterites that are not imperatives."""
    hits = [m.group(0) for m in FIRST_PERSON_RE.finditer(text)]
    low = [w.lower().strip("'’¿¡") for w in words(text)]
    hits += [w for w in low
             if FIRST_PERSON_VERB_RE.fullmatch(w)
             and w not in NOT_FIRST_PERSON and w not in IMPERATIVES]
    return hits


def check_length(text):
    """A hook has to land before the thumb moves. Roughly two seconds."""
    w = words(text)
    n = len(w)
    secs = n / 2.75                      # ~165 words per minute, spoken
    chars = len(text.strip())
    if 5 <= n <= 12:
        score = 100.0
    elif n < 5:
        score = clamp(100 - (5 - n) * 20)
    else:
        score = clamp(100 - (n - 12) * 11)
    if chars > 60:                       # two lines of big on-screen text
        score -= 12
    return clamp(score), f"{n} words, {chars} chars, ~{secs:.1f}s spoken (want 5-12 words)"


def check_specificity(text):
    """One concrete thing beats three abstract ones."""
    nums = [n.strip() for n in NUMBER_RE.findall(text) if n.strip()]
    propers = set(PROPER_RE.findall(text))
    low = [w.lower().strip("'’¿¡") for w in words(text)]
    # A unit already counted inside a figure ("2.000 dólares") is not a second marker.
    covered = " ".join(n.lower() for n in nums)
    spoken = [w for w in low
              if (w in SPOKEN_NUMBERS or w in MONEY_WORDS) and w not in covered.split()]
    hits = len(nums) + len(propers) + len(spoken)
    score = 15.0 if hits == 0 else clamp(45 + hits * 30)
    found = ", ".join(nums[:2] + sorted(propers)[:2] + spoken[:2])
    return score, (f"{hits} concrete marker(s)" + (f": {found}" if found else
                   " - no number, no name, nothing checkable"))


def check_stakes(text):
    """Tension, cost, negation. Something the viewer might lose."""
    w = [x.lower().strip("'’¿¡") for x in words(text)]
    hits = [x for x in w if x in STAKES]
    markers = sorted(set(hits))
    if re.search(r"(?:US\$|USD|U\$S|\$|€)\s?\d", text):
        markers.append("a price")
    n = len(markers)
    score = {0: 20.0, 1: 70.0}.get(n, 100.0)
    detail = f"{n} tension marker(s)" + (f": {', '.join(markers[:4])}" if markers else
                                         " - nothing is at stake in this line")
    return clamp(score), detail


def check_frontload(text):
    """The interesting word cannot be in position nine."""
    w = words(text)
    if not w:
        return 0.0, "empty"
    low = [x.lower().strip("'’¿¡") for x in w]
    opener = " ".join(low[:2])
    penalty = 0
    hit_opener = None
    for weak in WEAK_OPENERS:
        # Whole-word match only: "hoy" must not fire on "hoyo", nor "este"
        # on "estefanía". The two-word openers match the whole two-word span.
        if low[0] == weak or opener == weak or opener.startswith(weak + " "):
            penalty, hit_opener = 30, weak
            break
    payload = None
    for i, token in enumerate(low):
        if (token in STAKES or token in SPOKEN_NUMBERS or token in MONEY_WORDS
                or NUMBER_RE.match(w[i]) or (i and PROPER_RE.match(w[i]))):
            payload = i
            break
    if payload is None:
        base = 30.0
        where = "no payload word anywhere in the line"
    elif payload <= 3:
        base = 100.0
        where = f"payload at word {payload + 1}"
    elif payload <= 6:
        base = 70.0
        where = f"payload at word {payload + 1}, could move forward"
    else:
        base = 40.0
        where = f"payload at word {payload + 1}, too late"
    detail = where + (f"; weak opener \"{hit_opener}\"" if hit_opener else "")
    return clamp(base - penalty), detail


def check_address(text):
    """Aimed at one viewer, or floating in the air."""
    w = [x.lower().strip("'’¿¡") for x in words(text)]
    if w and w[0] in IMPERATIVES:
        return 90.0, f"imperative opener (\"{w[0]}\")"
    second = second_person_hits(text)
    if second:
        return 100.0, f"speaks to the viewer (\"{second[0]}\")"
    first = first_person_hits(text)
    if first:
        return 70.0, f"first person (\"{first[0]}\"), no viewer named"
    return 35.0, "third person, nobody in the room"


CHECKS = ["LENGTH", "SPECIFICITY", "STAKES", "FRONTLOAD", "ADDRESS"]


def run(text):
    results = {
        "LENGTH": check_length(text),
        "SPECIFICITY": check_specificity(text),
        "STAKES": check_stakes(text),
        "FRONTLOAD": check_frontload(text),
        "ADDRESS": check_address(text),
    }
    flags = [msg for pattern, msg in DEALBREAKERS if pattern.search(text)]
    scores = [results[c][0] for c in CHECKS]
    # The weakest property caps the hook, same logic as detect.py: one bad
    # property is enough for the thumb to keep moving.
    overall = statistics.mean(scores) * 0.6 + min(scores) * 0.4 - len(flags) * 15
    overall = clamp(overall)
    verdict = "STRONG" if overall >= 70 and min(scores) >= 55 and not flags else (
        "OK" if overall >= 50 else "WEAK")
    return results, overall, verdict, flags


def bar(score, width=24):
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


def render_one(text, results, overall, verdict, flags, out=sys.stdout):
    print("\nHOOK SCORE", file=out)
    print("=" * 62, file=out)
    print(f"  \"{text.strip()}\"\n", file=out)
    for name in CHECKS:
        score, detail = results[name]
        print(f"  {name:<13} {bar(score)} {score:5.1f}", file=out)
        print(f"  {'':<13} {detail}", file=out)
    print("-" * 62, file=out)
    print(f"  {'HOOK SCORE':<13} {bar(overall)} {overall:5.1f}   {verdict}", file=out)
    for f in flags:
        print(f"\n  DEALBREAKER  {f}", file=out)
    if verdict != "STRONG":
        weakest = min(CHECKS, key=lambda c: results[c][0])
        print(f"\n  Weakest property: {weakest}. Fix that one and re-run.", file=out)
    print("", file=out)


def render_table(rows, out=sys.stdout):
    print("\nHOOK RANKING\n" + "=" * 78, file=out)
    for i, r in enumerate(rows, 1):
        mark = "->" if i == 1 else "  "
        hook = r["hook"] if len(r["hook"]) <= 62 else r["hook"][:59] + "..."
        print(f"{mark} {r['score']:5.1f} {r['verdict']:<7} {hook}", file=out)
        print(f"        weakest: {r['weakest']} ({r['checks'][r['weakest']]['score']:.0f})", file=out)
        for f in r["flags"]:
            print(f"        dealbreaker: {f}", file=out)
    print("\nShoot the top one. If the top one is under 50, none of these are the hook.\n",
          file=out)


def main():
    ap = argparse.ArgumentParser(description="Score a Reel hook on five properties.")
    ap.add_argument("input", nargs="?", default="-", help="file with one hook per line, or -")
    ap.add_argument("--hook", help="score a single hook given on the command line")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.hook:
        lines = [args.hook]
    else:
        raw = _read_input(args.input)
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
    if not lines:
        print("nothing to score", file=sys.stderr)
        sys.exit(2)

    payload = []
    for line in lines:
        results, overall, verdict, flags = run(line)
        payload.append({
            "hook": line,
            "checks": {k: {"score": round(v[0], 1), "detail": v[1]} for k, v in results.items()},
            "weakest": min(CHECKS, key=lambda c: results[c][0]),
            "flags": flags,
            "score": round(overall, 1),
            "verdict": verdict,
        })

    if args.json:
        print(json.dumps(payload if len(payload) > 1 else payload[0], indent=2, ensure_ascii=False))
        return

    if len(payload) == 1:
        results, overall, verdict, flags = run(lines[0])
        render_one(lines[0], results, overall, verdict, flags)
    else:
        render_table(sorted(payload, key=lambda r: -r["score"]))

    sys.exit(0 if max(p["score"] for p in payload) >= 70 else 1)


if __name__ == "__main__":
    main()
