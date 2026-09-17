
from pathlib import Path

import spacy

nlp = spacy.load(Path(__file__).resolve().parent / "output/model-best")

tests = [
    "The CCTV footage showed Imran Sheikh outside DM Trading Services in Mumbai.",
    "Location Surveillance Records mentioned Rohan Mehta near Vashi Sector 17.",
    "Investigators collected Call Detail Records from Sameer Khan.",
    "Metro Logistics Pvt Ltd operates a warehouse in Navi Mumbai.",
    "Police searched Turbhe Warehouse No. 4 after receiving information.",
    "The investigation report showed that Dev Malhotra contacted KS Electronics.",
    "The Case File mentioned R K Sharma and Nova Components in Pune."
]

for text in tests:
    doc = nlp(text)
    print("\nTEXT:", text)
    print([(ent.text, ent.label_) for ent in doc.ents])
