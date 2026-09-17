"""Clean statistical NER spans before they become review candidates.

Small NER models label form fields, dates, amounts and bullets as names ("Age",
"September 2026", "INR 3,20,000", "• Sameer Khan"). These rules only trim or discard
source spans and correct a kind from an explicit name suffix; they never invent text.
"""

import json
import re
from pathlib import Path

LOCATION_NAMES = json.loads(
    (Path(__file__).resolve().parents[1] / "data/location_names.json").read_text()
)
KNOWN_LOCATIONS = {" ".join(name.split()).casefold() for name in LOCATION_NAMES}

# Words that label a form field or describe a record; never a name at a span edge.
FORM_WORDS = frozenset("""
page pages age aged years yrs old address mobile phone tel telephone email date dated time
hrs hours registration registered district alias name status remarks summary conclusion
details statement nature subject observation observations note notes information records
record report reports section annexure document documents file approximately approx about
available business persons person referred preliminary communication financial transactions
transaction tower towers locations location complaint complainant accused suspect witness
victim action taken certification verified prepared analyst investigating investigation
officer inspector sub-inspector constable cctv cdr fir number references organisation
organization footage place scene nationality occupation informant copy rank signature particulars contents
occurrence offence offences inquest diary entry reference case type item reasons delay thumb
impression despatch dispatch charge father father's husband husband's resident aged u/s p.s ps
s/o d/o w/o r/o pi api psi si asi hc pc dsp acp sp dcp ssp sho ips hon'ble honble shri smt mr mrs
ms
""".split())
# Statutes and sections are legal references, never people, places or organizations.
LEGAL_WORDS = frozenset("""
act acts section sections sec sanhita adhiniyam penal procedure bns bnss bsa ipc crpc ndps pmla
uapa pocso mcoca
""".split())
# Courts and the State as a party are institutional references, not network entities.
COURT_WORDS = frozenset("""
state sessions session court courts magistrate judicial tribunal bench judge government govt
class high supreme metropolitan additional addl special chief
""".split())
WEEKDAYS = frozenset("monday tuesday wednesday thursday friday saturday sunday".split())
FUNCTION_WORDS = frozenset("""
the a an of on at in near from to and or with by for between during since until after before
this that these those his her their its same another other said some several via per no
""".split())
DATE_WORDS = frozenset("""
january february march april may june july august september october november december
jan feb mar apr jun jul aug sep sept oct nov dec
""".split())
CURRENCY_WORDS = frozenset("inr rs usd eur gbp aed rupees rupee lakh lakhs crore crores ₹".split())
EDGE_WORDS = FORM_WORDS | FUNCTION_WORDS | DATE_WORDS | CURRENCY_WORDS | WEEKDAYS | LEGAL_WORDS

ORG_TAILS = frozenset("""
ltd limited pvt llp inc corp corporation company companies bank traders exports imports
agency enterprises industries logistics finserv solutions services railways bureau
department ministry branch cell squad trust foundation society associates holdings group
""".split())
LOCATION_TAILS = frozenset("""
road rd marg nagar market colony chowk bazaar bazar lane street highway layout village taluka
tehsil complex port sector city park gardens apartments apartment residency enclave vihar bagh
heights estate plaza chawl wadi peth gali
""".split())
# Generic nouns that are part of names ("Delhi Police") but never a name alone.
GENERIC_WORDS = ORG_TAILS | LOCATION_TAILS | COURT_WORDS | {
    "police", "station", "office", "unit", "team", "private", "headquarters", "hq"}
# Words that start real names ("Indian Railways", "First Choice Traders") but not alone.
SOLO_WORDS = frozenset("first indian foreign foreigner unknown accused complainant".split())
ABBREVIATIONS = frozenset("ltd pvt inc co corp bros jr sr st rd".split())

TOKEN = re.compile(r"[^\s/•·|]+")
EDGE_PUNCTUATION = ",;:()[]{}\"'-–—*•·"

# A suffix word cannot also be a name word ("Police Station Bandra Police Station").
_NAME = r"(?:(?!(?:Police|Station|Private|Limited|Pvt|Ltd)\b)[A-Z][A-Za-z0-9&'.\-]*)"
_GAP = r"(?:[ \t]*\n[ \t]*|[ \t]+)"
# Capitalized names ending in an explicit organization or place suffix.
ORG_NAMES = re.compile(
    rf"(?<![\w.])(?:{_NAME}{_GAP}){{0,4}}{_NAME}{_GAP}"
    r"(?:Pvt\.?[ \t]*Ltd\.?|Private[ \t]+Limited|Limited|Ltd\.?|LLP|Inc\.?|Corporation|Bank"
    r"|Traders|Exports|Agency|Enterprises|Industries|Logistics|Finserv|Railways|Bureau"
    r"|Police[ \t]+Station|Branch)"
    # "Police Station:" after a name on the previous line is a field label, not a name.
    r"(?:[ \t]+of[ \t]+[A-Z][A-Za-z]+)?(?![\w-])(?![ \t]*:)"
)
_PLACE_NAME = r"(?:[A-Z][A-Za-z0-9&'.\-]*)"
LOCATION_PLACES = re.compile(
    rf"(?<![\w.])(?:{_PLACE_NAME}[ \t]+){{0,3}}{_PLACE_NAME}[ \t]+"
    r"(?:Road|Marg|Nagar|Market|Colony|Chowk|Bazaar|Lane|Street|Highway|Layout|Park|Gardens"
    r"|Apartments|Residency|Enclave|Vihar|Bagh|Heights|Estate|Plaza|Chawl|Wadi|Peth|Gali)(?![\w-])"
)
GAZETTEER = re.compile(
    r"(?<![\w-])(?:" + "|".join(
        r"[\s-]+".join(re.escape(part) for part in re.split(r"[\s-]+", name))
        for name in sorted(LOCATION_NAMES, key=len, reverse=True)
    ) + r")(?![\w-])",
    re.I,
)


def _key(token):
    return token.strip(EDGE_PUNCTUATION + ".").casefold()


def _is_edge_noise(token, dated=True):
    key = _key(token)
    return (
        not any(char.isalpha() for char in key)  # bullets, numbers, times, amounts
        or key in EDGE_WORDS - (set() if dated else DATE_WORDS)
        or re.fullmatch(r"\d+(?:st|nd|rd|th|hrs)", key) is not None
        or (token.strip(EDGE_PUNCTUATION + ".").isupper() and re.fullmatch(r"[ivx]+", key) is not None)
        or key.replace(".", "") in LEGAL_WORDS  # "B.N.S.S", "I.P.C"
    )


def _lines(text, start, end):
    """Split a span at hard line breaks, keeping soft wraps inside wrapped names."""
    pieces, piece_start = [], start
    for match in re.finditer(r"\n|:(?=\s)", text[start:end]):
        newline = start + match.start()
        before = TOKEN.findall(text[piece_start:newline])
        after = TOKEN.findall(text[newline + 1:end])
        ended = before and before[-1][-1] in ".,;:!?" and _key(before[-1]) not in ABBREVIATIONS
        # "PI Sandeep Pawar Rank: Police" is two fields; a colon always ends a value.
        if (match[0] == ":" or not before or not after or ended or _is_edge_noise(before[-1])
                or _is_edge_noise(after[0]) or text[newline + 1:end].startswith("\n")):
            pieces.append((piece_start, newline))
            piece_start = newline + 1
    pieces.append((piece_start, end))
    return pieces


def _trim(text, start, end):
    tokens = [(start + m.start(), start + m.end()) for m in TOKEN.finditer(text[start:end])]
    # Month names are dates only beside a number ("April Fernandes" is a person).
    dated = any(char.isdigit() for char in text[start:end])
    while tokens and _is_edge_noise(text[slice(*tokens[0])], dated):
        tokens.pop(0)
    while tokens and _is_edge_noise(text[slice(*tokens[-1])], dated):
        tokens.pop()
    if not tokens:
        return None
    start, end = tokens[0][0], tokens[-1][1]
    while start < end and text[start] in EDGE_PUNCTUATION:
        start += 1
    while start < end and (
        text[end - 1] in EDGE_PUNCTUATION
        or (text[end - 1] == "." and _key(text[slice(*tokens[-1])]) not in ABBREVIATIONS)
    ):
        end -= 1
    return (start, end) if start < end else None


def kind_from_suffix(name, kind):
    """An explicit suffix outranks a statistical guess ("Apex Finserv" is not a person)."""
    keys = [_key(token) for token in TOKEN.findall(name)]
    if " ".join(keys) in KNOWN_LOCATIONS:
        return "Location"
    if keys[-2:] == ["police", "station"]:
        return "Organization"
    if keys[-1:] == ["station"] or keys[-1] in LOCATION_TAILS:
        return "Location"
    if keys[-1] in ORG_TAILS:
        return "Organization"
    return kind


def clean_span(text, start, end, kind):
    """Return zero or more trimmed (start, end, kind) spans for one NER prediction."""
    spans = []
    # A prediction inside a longer code ("ME-06" in "CAM-ME-06") is not a name.
    if (start and (text[start - 1].isalnum() or (text[start - 1] in "-/" and text[start - 2:start - 1].isalnum()))) \
            or (end < len(text) and (text[end].isalnum() or (text[end] in "-/" and text[end + 1:end + 2].isalnum()))):
        return spans
    for piece in _lines(text, start, end):
        # Check statutes before trimming, so "Bharatiya Nyaya Sanhita" leaves no fragment.
        if any(_key(token).replace(".", "") in LEGAL_WORDS for token in TOKEN.findall(text[slice(*piece)])):
            continue
        trimmed = _trim(text, *piece)
        if trimmed is None:
            continue
        name = text[slice(*trimmed)]
        keys = [_key(token) for token in TOKEN.findall(name)]
        letters = next((char for char in name if char.isalpha()), "")
        words = [key for key in keys if key not in FUNCTION_WORDS]
        if (
            len(name) > 100
            # Initials alone ("P.S", "U.D.") are not names; "S. Iyer" still is.
            or not any(re.search(r"[^\W\d_]{2}", key) for key in keys)
            # Latin-script names start with a capital; Devanagari has no case.
            or (letters.isascii() and letters.islower())
            # "Police Station" alone is generic; "Station Road" names a real street.
            or (all(key in GENERIC_WORDS for key in words)
                and not (len(words) > 1 and words[0] not in LOCATION_TAILS
                         and words[-1] in LOCATION_TAILS - {"city", "sector", "complex", "port"}))
            or (len(words) == 1 and words[0] in SOLO_WORDS)
            or any(key.replace(".", "") in LEGAL_WORDS for key in words)
            # "State of Maharashtra", "Pune Sessions Court": the place is kept on its own.
            or (any(key in COURT_WORDS for key in words)
                and all(key in GENERIC_WORDS or key in KNOWN_LOCATIONS for key in words))
        ):
            continue
        span_kind = kind_from_suffix(name, kind)
        if span_kind == "Person" and any(char.isdigit() for char in name):
            continue
        # A short capitalized acronym ("AI", "IO") is not a person or place; agencies such
        # as "CBI" or "SBI" remain organization candidates.
        if span_kind in {"Person", "Location"} and re.fullmatch(r"[A-Z]{1,3}", name) \
                and name.casefold() not in KNOWN_LOCATIONS:
            continue
        spans.append((*trimmed, span_kind))
    return spans


def rule_spans(text):
    """Deterministic name candidates: known places and suffix-marked names."""
    spans = []
    for match in GAZETTEER.finditer(text):
        # A single-word place must be capitalized ("Pune", not the word "pune").
        if " " in match[0].strip() or "-" in match[0] or match[0][0].isupper():
            spans.append((*match.span(), "Location"))
    for pattern, kind in ((ORG_NAMES, "Organization"), (LOCATION_PLACES, "Location")):
        for match in pattern.finditer(text):
            spans.extend(clean_span(text, *match.span(), kind))
    return spans
