
import json
from pathlib import Path

import spacy
from spacy.tokens import DocBin

BASE = Path(__file__).parent

def convert(src, dst):
    nlp = spacy.blank("en")
    db = DocBin()
    period_fixes = 0
    with open(src, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            item = json.loads(line)
            doc = nlp.make_doc(item["text"])
            spans = []
            for start, end, label in item["entities"]:
                sp = doc.char_span(start, end, label=label, alignment_mode="strict")
                # Include only the trailing period in abbreviations such as "Ltd.".
                # All other annotation boundaries still undergo strict validation.
                if sp is None and item["text"][end:end + 1] == ".":
                    sp = doc.char_span(start, end + 1, label=label, alignment_mode="strict")
                    if sp is not None:
                        period_fixes += 1
                if sp is None:
                    raise ValueError(
                        f"Bad span line {line_no}: {start}-{end} "
                        f"{item['text'][start:end]!r}"
                    )
                spans.append(sp)
            doc.ents = spans
            db.add(doc)
    db.to_disk(dst)
    print(f"Saved {dst} ({period_fixes} abbreviation-period spans aligned)")

if __name__ == "__main__":
    convert(BASE/"train.jsonl", BASE/"train.spacy")
    convert(BASE/"dev.jsonl", BASE/"dev.spacy")
