# Multi-Entity Crime/FIR NER Dataset

Synthetic dataset for training a custom spaCy NER pipeline on crime/FIR-style text.
The training script initializes a new NER pipeline with pretrained word vectors; it does not continue the existing NER weights.

## Labels
- PERSON — people
- ORG — named organisations/companies
- GPE — cities/states/countries
- LOC — named geographic areas/roads/localities
- FAC — named facilities/warehouses/depots

## Hard negatives
The dataset repeatedly includes the following as **unlabelled non-entities**
so the model learns not to call them ORG:
- CCTV footage / CCTV records
- Location Surveillance Record(s)
- FIR / FIR record
- Call Detail Records / CDR records
- bank records / financial records
- investigation report / police report
- case file
- evidence log
- surveillance records
- forensic report
- arrest memo / seizure memo
- station diary entry

## Size
- Total examples: 2221
- Training examples: 1821
- Validation examples: 400

## Train

```bash
cd spacy_crime_multientity_ner_package
bash train_model.sh
```

Then test:

```bash
../backend/.venv/bin/python test_model.py
```

## Important design note
Do not label generic document types as ORG. If you later need to extract them,
use a separate label such as DOCUMENT_TYPE instead of ORG.

Likewise, a police station can be modelled with a dedicated POLICE_STATION or FAC
label if that distinction matters to your application.

## Backend integration

The script prefers `backend/.venv` to match the application spaCy version (3.8.x). It
validates the data, explicitly enables static `en_core_web_lg` vectors, trains on CPU,
and writes `output/model-best`, `output/model-last`, and `evaluation.json`. The converter
includes the trailing abbreviation period when required for strict token alignment
(45 training spans, 11 development spans); other invalid spans still fail. JSONL source
annotations are preserved. Generated model binaries and DocBins are ignored by Git.

After inspecting evaluation results and independent examples, set `SPACY_MODEL` in
`backend/.env` to the absolute path of this package's `output/model-best` directory.
Keep `EXTRACTION_MODE=hybrid`, and restart FastAPI. Relationship extraction remains in
batches and is not trained by this package. A saved `.env` change affects new server
processes, not an already-running model cached in memory.

This dataset has five labels: PERSON, ORG, GPE, LOC, FAC. FIR numbers, phones, vehicle
registrations, and crime terms continue to use the application's other extractors.
Validation scores on this synthetic split do not measure real-FIR generalization.
