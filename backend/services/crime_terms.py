"""Source-worded crime candidates, not conclusions about offences or guilt."""

import re

CRIME_TERMS = (
    "financial fraud", "bank fraud", "insurance fraud", "credit card fraud",
    "identity theft", "cyber fraud", "online fraud", "fraud", "theft", "robbery",
    "armed robbery", "burglary", "forgery", "cheating", "extortion", "blackmail",
    "criminal conspiracy", "criminal breach of trust", "money laundering",
    "embezzlement", "bribery", "corruption", "kidnapping", "abduction",
    "attempted murder", "attempt to murder", "murder", "homicide", "assault",
    "sexual assault", "rape", "domestic violence", "human trafficking",
    "drug trafficking", "narcotics trafficking", "smuggling", "cybercrime",
    "cyber crime", "cyberstalking", "stalking", "arson", "vandalism",
    "चोरी", "धोखाधड़ी", "हत्या", "अपहरण", "तस्करी",
)
CRIME_MENTION = re.compile(
    r"(?<!\w)(?:" + "|".join(
        r"\s+".join(re.escape(word) for word in term.split())
        for term in sorted(CRIME_TERMS, key=len, reverse=True)
    ) + r")(?!\w)", re.I,
)


def is_explicit_crime_field(evidence, name):
    """Limit the legacy case-column fallback to an actual labelled crime field."""
    fields = re.finditer(
        r"^[ \t]*(?:[-*][ \t]*)?(?:Crime(?: type| committed)?|Offen[cs]e(?: committed)?)"
        r"[ \t]*:[ \t]*(?P<value>[^\n]+)", evidence, re.I | re.M,
    )
    normalized_name = " ".join(name.split()).casefold()
    return any(normalized_name == " ".join(m["value"].split()).casefold() for m in fields)
