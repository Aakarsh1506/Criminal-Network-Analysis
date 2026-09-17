"""Select complete source sentences for relationship analysis, without inferring edges."""

import re
from functools import lru_cache

from .crime_terms import CRIME_MENTION
from .extraction import RELATION_RULES, evidence_names_entity

# Cues select text to review, never assert a relationship. Keep negations intact.
RELATIONSHIP_CUES = re.compile(
    r"\b(?:contact(?:ed|s|ing)?|call(?:ed|s|ing)?|phon(?:ed|ing)|communicat\w*|"
    r"spoke|speaking|met|meet(?:ing|s)?|mention(?:ed|s)?|nam(?:ed|es)|list(?:ed|s)|"
    r"witness\w*|suspect\w*|accused|complainant|fir|case|"
    r"resid\w*|liv(?:e|es|ed|ing)|address|last\s+seen|seen|sighted|visit\w*|"
    r"occur\w*|incident|crime|offen[cs]e|own(?:s|ed|er|ership)?|belongs?\s+to|"
    r"employ\w*|work(?:s|ed|ing)?\s+(?:at|for)|transfer\w*|paid|received|sent)\b"
    r"|संपर्क|कॉल|गवाह|संदिग्ध|आरोपी|निवासी|देखा|उल्लेख|मालिक|घटना",
    re.I,
)
PRONOUN = re.compile(r"\b(?:he|she|they|his|her|their|him|them|the\s+(?:suspect|accused|witness))\b|वह|उसने", re.I)


@lru_cache(maxsize=1)
def sentence_pipeline():
    import spacy

    pipeline = spacy.blank("en")
    pipeline.add_pipe("sentencizer", config={"punct_chars": [".", "!", "?", "।"]})
    return pipeline


def sentence_spans(text):
    return [(s.start_char, s.end_char) for s in sentence_pipeline()(text).sents if s.text.strip()]


def entity_context(text, entity, spans):
    # Names and types alone cannot disambiguate a person from a place. Include the
    # original sentence, without asking the model to rewrite the candidate name.
    for start, end in spans:
        if evidence_names_entity(text[start:end], entity.name, entity.identifier):
            return text[start:end].strip()
    return entity.evidence


def relationship_batches(text, entities, output_budget=None, *, max_sentences=None):
    """Group whole cue sentences; retain antecedents and a single FIR header."""
    spans = sentence_spans(text)
    selected = []
    seen = set()
    for index, (start, end) in enumerate(spans):
        sentence = text[start:end]
        if not (RELATIONSHIP_CUES.search(sentence) or CRIME_MENTION.search(sentence)):
            continue
        if index and PRONOUN.search(sentence):
            start = spans[index - 1][0]
        passage = text[start:end].strip()
        if passage in seen:
            continue
        seen.add(passage)
        # Overlapping pronoun context must not create duplicate input sentences.
        if selected and start < selected[-1][1]:
            selected[-1] = (selected[-1][0], max(end, selected[-1][1]))
        else:
            selected.append((start, end))

    target_size = min(3500, max(1400, output_budget * 2)) if output_budget else 3500
    sentence_limit = max(2, min(8, output_budget // 256)) if output_budget else 8
    if max_sentences is not None:
        sentence_limit = max_sentences
    entities = [e for e in entities if e.kind != "PhoneNumber"]
    cases = [e for e in entities if e.kind == "Case"]
    case_context = cases[0].evidence if len(cases) == 1 else None
    groups, group, size = [], [], 0
    for start, end in selected:
        if group and (size + end - start > target_size or len(group) >= sentence_limit):
            groups.append(group)
            group, size = [], 0
        group.append((start, end))
        size += end - start
    if group:
        groups.append(group)

    for group in groups:
        pieces, last = [], None
        for start, end in group:
            if last is not None:
                between = text[last:start]
                pieces.append(between if not between.strip() else "\n[OMITTED SOURCE]\n")
            pieces.append(text[start:end])
            last = end
        passage = "".join(pieces)
        if case_context and not evidence_names_entity(passage, cases[0].name, cases[0].identifier):
            passage = case_context + "\n[OMITTED SOURCE]\n" + passage
        catalog = [e.model_copy(update={"attributes": [], "evidence":
                   e.evidence if e.evidence in passage else e.name}) for e in entities
                   if evidence_names_entity(passage, e.name, e.identifier)]
        if any(a.ref != b.ref and a.kind in subjects and b.kind in objects
               for subjects, objects in RELATION_RULES.values() for a in catalog for b in catalog):
            yield passage, catalog
