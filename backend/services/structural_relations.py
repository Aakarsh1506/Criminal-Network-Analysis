"""Relationships an FIR states through its layout or in fixed phrasing, found without a model.

Only explicit structure is used: a single case header, labelled fields, role headings with
listed entries, and short fixed phrases ("X called Y", "X, resident of L", "X was seen at L").
Proximity alone never creates an edge. Every edge cites a contiguous source span and is
validated exactly like model output before it is kept.
"""

import re

from .extraction import Extraction, Relationship, validate_extraction

ROLE_HEADINGS = (
    ("SUSPECT_IN", re.compile(r"\b(?:accused|suspects?|suspected)\b", re.I)),
    ("WITNESS_IN", re.compile(r"\bwitness(?:es)?\b", re.I)),
)
ROLE_FIELD = re.compile(
    r"^[ \t]*(?:[-*•][ \t]*)?(Accused|Suspect|Witness)(?:[ \t]+name)?[ \t]*:[ \t]*(?=\S)", re.I | re.M)
ITEM = re.compile(r"[ \t]*(?:\d{1,2}[.)]|[•*-]|\(?[a-z]\))[ \t]+", re.I)
FIELD = re.compile(r"[ \t]*(?:[-*•][ \t]*)?([A-Za-z][\w ./'’&-]{0,40}?)[ \t]*:[ \t]*")
ADDRESS_LABEL = re.compile(r"(?:(?:permanent|present|residential)[ \t]+)?(?:address|residence)$", re.I)
ROLE_LABEL = (r"(?:Name[ \t]+of[ \t]+(?:the[ \t]+)?)?(?:Accused|Suspects?|Suspected[ \t]+persons?|Witness(?:es)?)"
              r"(?:[ \t]+(?:name|persons?|details))?")
OCCURRENCE_LABEL = (r"(?:Place|Scene|Location)[ \t]+of[ \t]+(?:occurrence|offen[cs]e|incident|crime)"
                    r"(?:[ \t]+with[ \t]+address)?")
OFFICER_LABEL = (r"(?:Name[ \t]+of[ \t]+)?(?:Investigating[ \t]+Officer|Officer[ \t]+in[ \t]+charge|I\.?O\.?"
                 r"|S\.?H\.?O\.?)(?:[ \t]+name)?")
RESIDENCE = re.compile(r"\b(?:resident of|residing (?:at|in)|resides (?:at|in)|lives (?:at|in)|r/o)\b", re.I)
NEGATION = re.compile(r"\b(?:not|no longer|formerly|previously|earlier|never|nor)\b|n't\b", re.I)
_ = r"\s+"
CONTACT = r"(?:called|phoned|contacted|messaged|texted|telephoned|spoke" + _ + r"(?:to|with))"
# Up to six ordinary words between a verb and its place ("seen entering an office near L").
_FILLER = r"(?:(?!(?:not|never|no)\b)[\w'’-]+" + _ + r"){0,6}?"
SIGHTING = (r"(?:(?:was|were)" + _ + r"(?:reportedly" + _ + r")?(?:last" + _ + r")?"
            r"(?:seen|sighted|spotted|reported)|visited)" + _ + _FILLER
            + r"(?:near|at|in|around|outside)" + _ + r"(?:the" + _ + r")?")
PAIR_SIGHTING = (_ + r"and" + _ + "{other}" + _ + r"(?:had" + _ + r")?(?:previously" + _ + r")?"
                 r"(?:been|were)" + _ + r"(?:seen|spotted|sighted)" + _ + r"together" + _ + _FILLER
                 + r"(?:near|at|in|around|outside)" + _ + r"(?:the" + _ + r")?")
CALLS_BETWEEN = r"(?:calls?|messages?|communications?)" + _ + r"between" + _
CRIME_FIELD = re.compile(
    r"^[ \t]*(?:Nature[ \t]+of[ \t]+(?:complaint|offen[cs]e|case)|Type[ \t]+of[ \t]+(?:offen[cs]e|crime)"
    r"|Crime(?:[ \t]+type)?|Offen[cs]es?(?:[ \t]+committed)?)\b[ \t]*:?[ \t]*([^\n]+)", re.I | re.M)
EMPLOYMENT = (r"(?:,?" + _ + r"(?:an?" + _ + r")?(?:employee|staff member|accountant|manager|clerk|cashier"
              r"|driver|agent|supervisor)" + _ + r"(?:of|at|with)|" + _ + r"(?:works|worked|is employed"
              r"|was employed|is working|was working)" + _ + r"(?:at|for|with|by))" + _ + r"(?:the" + _ + r")?")


def _name_pattern(entity):
    words = entity.name.split()
    return r"(?<![\w-])" + r"\s+".join(re.escape(word) for word in words) + r"(?![\w-])"


def _mentions(entity, text, start=0, end=None):
    end = len(text) if end is None else end
    return [(start + m.start(), start + m.end())
            for m in re.finditer(_name_pattern(entity), text[start:end], re.I)]


def _lines(text, start, end):
    """Complete source lines covering [start, end), bounded by the evidence limit."""
    left = text.rfind("\n", 0, start) + 1
    right = text.find("\n", end)
    right = len(text) if right < 0 else right
    return (left, right) if right - left <= 2000 else None


# Sentences also end at blank lines, list entries and "Label: value" form lines.
_BREAK = r"\n[ \t]*\n|\n(?=[ \t]*(?:\d{1,2}[.)]|[•*-])[ \t])|\n(?=[ \t]*[A-Za-z][\w ./'’&-]{0,40}:)"
SENTENCE_START = re.compile(r"[.!?;](?=\s)|(?m:^[ \t]*[A-Za-z][\w ./'’&-]{0,40}:[^\n]*\n)|" + _BREAK)
SENTENCE_END = re.compile(r"[.!?;](?=\s|$)|" + _BREAK)


def _sentence(text, start, end):
    """The sentence (or list entry) containing a phrase, across PDF line wraps."""
    left = max((m.end() for m in SENTENCE_START.finditer(text, 0, start)), default=0)
    stop = SENTENCE_END.search(text, end)
    right = stop.end() if stop and stop[0] in ".!?" else stop.start() if stop else len(text)
    while left < start and text[left].isspace():
        left += 1
    return (left, right) if right - left <= 2000 else _lines(text, start, end)


def _starts_with(entities, text, position):
    """Entities named exactly at a position (an item or clause start)."""
    return [e for e in entities if re.match(_name_pattern(e), text[position:], re.I)]


def _edge(subject, predicate, target, text, span):
    if span is None or not text[span[0]:span[1]].strip():
        return None
    return Relationship(subject=subject.ref, predicate=predicate, object=target.ref,
                        evidence=text[span[0]:span[1]].strip())


def _line_offsets(text):
    offset = 0
    for line in text.split("\n"):
        yield offset, offset + len(line), line
        offset += len(line) + 1


def role_edges(text, people, case):
    edges = []
    lines = list(_line_offsets(text))
    for index, (start, end, line) in enumerate(lines):
        roles = [role for role, pattern in ROLE_HEADINGS if pattern.search(line)]
        # A heading names a role, no person, and is not a narrative sentence.
        # Headings are short labels or end with ":" ("Nature of complaint: Suspected fraud …" is not).
        if (len(roles) != 1 or (len(line.strip()) > 60 and not line.rstrip().endswith(":"))
                or line.rstrip().endswith(".")
                or any(_mentions(p, text, start, end) for p in people)
                or (ITEM.match(line) and len(line.strip()) > 60)):
            continue
        in_record, first = False, True
        for item_start, item_end, item in lines[index + 1:]:
            if not item.strip():
                in_record = False
                continue
            marker = ITEM.match(item)
            field = FIELD.match(item)
            # Table layouts print a label, then its value on the next line ("Accused" / "Rohan …").
            if marker or first or (field and field[1].casefold() == "name"):
                first = False
                offset = marker.end() if marker else field.end() if field and field[1].casefold() == "name" else 0
                content = item_start + offset + len(item[offset:]) - len(item[offset:].lstrip())
                # "1. Rohan Mehta, ...; Sameer Qureshi, ..." lists two people in one entry.
                starts = [content] + [item_start + m.end() for m in re.finditer(r";\s*", item)]
                named = [p for position in starts for p in _starts_with(people, text, position)]
                if not named:
                    break  # "1. Brief facts of the information" starts the next section.
                span = _lines(text, start, item_end)
                edges.extend(_edge(p, roles[0], case, text, span) for p in named)
                in_record = bool(field and not marker)
            elif not (in_record and field) and not item[:1].islower():
                break
    for match in ROLE_FIELD.finditer(text):
        role = "WITNESS_IN" if match[1].lower() == "witness" else "SUSPECT_IN"
        for person in _starts_with(people, text, match.end()):
            edges.append(_edge(person, role, case, text, _lines(text, match.start(), match.end())))
    return edges


def field_values(text, label):
    """(label start, value start, value end) for "Label: value" or a label line above its value."""
    pattern = re.compile(
        rf"^[ \t]*(?:[-*•][ \t]*)?(?:{label})[ \t]*(?::[ \t]*(?=\S)|:?[ \t]*\n(?:[ \t]*\n)*[ \t]*(?=\S))",
        re.I | re.M)
    for match in pattern.finditer(text):
        end = text.find("\n", match.end())
        yield match.start(), match.end(), len(text) if end < 0 else end


def primary_case(text, entities):
    """The document's own FIR: its only case, or the only one printed under an "FIR No." label."""
    cases = [e for e in entities if e.kind == "Case"]
    if len(cases) == 1:
        return cases[0]
    labelled = [case for case in cases if any(
        re.search(r"FIR[ \t]*No\.?[\s:#]*$", text[max(0, start - 40):start], re.I)
        for start, _ in _mentions(case, text)[:1])]
    return labelled[0] if len(labelled) == 1 else None


def residence_edges(text, people, places):
    edges = []
    lines = list(_line_offsets(text))
    # A labelled record: "Name: X" followed by its own fields, including "Address: L".
    for index, (start, _end, line) in enumerate(lines):
        field = FIELD.match(line)
        if not field or field[1].casefold() != "name":
            continue
        named = _starts_with(people, text, start + field.end())
        for field_start, field_end, next_line in lines[index + 1:]:
            label = FIELD.match(next_line)
            if not label or label[1].casefold() == "name":
                break
            if ADDRESS_LABEL.fullmatch(label[1].strip()):
                value = (field_start + label.end(), field_end)
                span = _lines(text, start, field_end)
                edges.extend(_edge(p, "RESIDES_IN", place, text, span) for p in named
                             for place in places if _mentions(place, text, *value))
    # A clause naming one person: "Rohan Mehta, age 29, resident of 42 Cedar Park, Nandipur".
    for start, end, line in lines:
        for clause in re.finditer(r"[^;]+", line):
            clause_start, clause_end = start + clause.start(), start + clause.end()
            cue = RESIDENCE.search(text, clause_start, clause_end)
            named = [p for p in people if _mentions(p, text, clause_start, clause_end)]
            if cue is None or len(named) != 1 or NEGATION.search(text, clause_start, cue.start()):
                continue
            if _mentions(named[0], text, cue.end(), clause_end):
                continue
            # Cite only this clause, not the next person's address on the same line.
            span = (clause_start, clause_end)
            edges.extend(_edge(named[0], "RESIDES_IN", place, text, span) for place in places
                         if _mentions(place, text, cue.end(), clause_end))
    return edges


# "Imran Sheikh, an employee of X, was seen at L": one short aside, never a negation.
APPOSITIVE = r"(?:,(?![^,.;\n]*\b(?:not|never|no)\b)[^,.;\n]{1,80},)?"


def _names(entities, group):
    """One alternation for many names, and a lookup from matched text back to its entity."""
    lookup = {}
    for entity in entities:
        lookup.setdefault(" ".join(entity.name.split()).casefold(), entity)
    words = sorted((name.split() for name in lookup), key=lambda parts: -len(" ".join(parts)))
    alternation = "|".join(r"\s+".join(re.escape(word) for word in parts) for parts in words)
    return rf"(?<![\w-])(?P<{group}>{alternation})(?![\w-])", lookup


def phrase_edges(text, people, places, organizations):
    """Fixed "subject verb object" phrases with nothing in between, so negations cannot match."""
    edges = []
    if not people:
        return edges

    def found(match, group, lookup):
        return lookup[" ".join(match[group].split()).casefold()]

    person, person_lookup = _names(people, "a")
    other, _other = _names(people, "b")
    rules = [("CONTACTED", APPOSITIVE + _ + CONTACT + _, people),
             ("SEEN_AT", APPOSITIVE + _ + SIGHTING, places),
             ("EMPLOYED_BY", EMPLOYMENT, organizations)]
    for predicate, verb, objects in rules:
        if not objects:
            continue
        target, target_lookup = _names(objects, "b")
        for match in re.finditer(person + verb + target, text, re.I):
            subject, obj = found(match, "a", person_lookup), found(match, "b", target_lookup)
            if subject.ref != obj.ref:
                edges.append(_edge(subject, predicate, obj, text, _sentence(text, *match.span())))
    # "6 calls between Arjun Malhotra and Karan Mehta"
    for match in re.finditer(CALLS_BETWEEN + person + _ + r"and" + _ + other, text, re.I):
        first, second = found(match, "a", person_lookup), found(match, "b", person_lookup)
        if first.ref != second.ref:
            edges.append(_edge(first, "CONTACTED", second, text, _sentence(text, *match.span())))
    # "Arjun Malhotra and Sameer Khan had previously been seen together at a café in Powai"
    if places:
        place, place_lookup = _names(places, "c")
        for match in re.finditer(person + PAIR_SIGHTING.replace("{other}", other) + place, text, re.I):
            first, second = found(match, "a", person_lookup), found(match, "b", person_lookup)
            span = _sentence(text, *match.span())
            target = found(match, "c", place_lookup)
            edges += [_edge(first, "SEEN_AT", target, text, span), _edge(second, "SEEN_AT", target, text, span)]
    return edges


# Words a citation must contain before a model-suggested edge of that type is saved.
PREDICATE_CUES = {
    "WITNESS_IN": r"witness|eye-?witness|acquainted with (?:the )?facts|statement|गवाह",
    "SUSPECT_IN": r"accused|suspect|offender|culprit|arrested|abscond|आरोपी|संदिग्ध",
    "OCCURRED_AT": r"occur|incident|took place|happened|committed|scene|offen[cs]e|crime|place of|घटना",
    "RESIDES_IN": r"resid|\blives?\b|living|address|r/o|\bhouse|\bhome|stay|native of|निवासी",
    "SEEN_AT": r"\bseen\b|\bsaw\b|sight|spott|notic|observ|cctv|footage|visit|arriv|enter|present at"
               r"|found at|last reported|देखा",
    "CONTACTED": r"call|phon|contact|spoke|speak|talk|messag|text|chat|whatsapp|e-?mail|\bmet\b|meet"
                 r"|communicat|संपर्क|कॉल",
    "EMPLOYED_BY": r"employ|work|staff|job|posted|officer|manager|accountant|clerk|driver|agent|director"
                   r"|executive|guard|supervisor|cashier|operator|partner",
    "OWNS": r"\bown|belong|registered|property of|purchas|bought|मालिक",
}


def unsupported_predicate(relation):
    """A reason when the citation lacks any wording for the predicate, else None."""
    cue = PREDICATE_CUES.get(relation.predicate)
    if cue is None or re.search(cue, relation.evidence, re.I):
        return None
    return (f"The cited text does not state a {relation.predicate} relationship "
            "(no wording for this relationship type). Check the source before adding it.")


def structural_relationships(text, entities):
    people = [e for e in entities if e.kind == "Person"]
    places = [e for e in entities if e.kind == "Location"]
    organizations = [e for e in entities if e.kind == "Organization"]
    case = primary_case(text, entities)
    edges = residence_edges(text, people, places) + phrase_edges(text, people, places, organizations)
    # An officer's own station, printed with them: "Investigating Officer: SI Neha Kulkarni, X Police Station".
    for start, value, end in field_values(text, OFFICER_LABEL):
        named = [p for p in people if _mentions(p, text, value, end)]
        edges.extend(_edge(person, "EMPLOYED_BY", org, text, _lines(text, start, end))
                     for person in named[:1] for org in organizations if _mentions(org, text, value, end))
    # Another FIR referenced inside this one ("shares Rohan Mehta with FIR-SYN-2026-0198") is
    # not this document's case; edges attach only to the document's own FIR.
    if case is not None:
        edges += role_edges(text, people, case)
        for start, value, end in field_values(text, ROLE_LABEL):
            label = text[start:value].casefold()
            role = "WITNESS_IN" if "witness" in label else "SUSPECT_IN"
            starts = [value] + [value + m.end() for m in re.finditer(r";\s*", text[value:end])]
            edges.extend(_edge(p, role, case, text, _lines(text, start, end))
                         for position in starts for p in _starts_with(people, text, position))
        # Everything named in a single-FIR document is, by definition, mentioned in that FIR.
        for entity in entities:
            if entity.kind in {"Person", "Organization", "Vehicle"}:
                found = _mentions(entity, text)
                if found:
                    edges.append(_edge(entity, "MENTIONED_IN", case, text, _lines(text, *found[0])))
        crimes = [e for e in entities if e.kind == "CrimeType"]
        for match in CRIME_FIELD.finditer(text):
            edges.extend(_edge(case, "OF_TYPE", crime, text, _lines(text, *match.span()))
                         for crime in crimes if _mentions(crime, text, *match.span(1)))
        for start, value, end in field_values(text, OCCURRENCE_LABEL):
            edges.extend(_edge(case, "OCCURRED_AT", place, text, _lines(text, start, end))
                         for place in places if _mentions(place, text, value, end))
    unique = {}
    for edge in edges:
        if edge is not None:
            unique.setdefault((edge.subject, edge.predicate, edge.object), edge)
    # Validate against this document's own case only, so its header identifies the case for
    # every edge exactly as it does in a single-case document.
    result = Extraction(entities=[e.model_copy() for e in entities if e.kind != "Case" or e is case],
                        relationships=list(unique.values()))
    # Grounding checks are the same as for model output; anything unproven is dropped.
    return validate_extraction(result, text, exclude_invalid=True).relationships
