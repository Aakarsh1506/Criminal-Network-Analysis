# Criminal Network Analysis — Presentation Script

A spoken walkthrough of the project: the problem, a feature demo, the technical implementation,
what makes it different, and its limitations. Speaker lines are in plain text; **[DEMO]** marks
what to show on screen. Timings assume a 15–20 minute presentation.

---

## 1. Opening — the problem (1 minute)

Police investigations produce information scattered across First Information Reports, call
detail records, bank statements, surveillance notes and intelligence inputs. The connections
that matter — the same suspect in three FIRs, a phone number shared by two people, a residence
that is also a crime scene — are buried in PDFs and scanned pages.

Reading every document and drawing those links by hand is slow, and it is easy to miss a
pattern or, worse, to assert a link the documents never state.

**Criminal Network Analysis** turns investigation documents into a reviewed, evidence-backed
network of people, cases, places, organisations, vehicles and phone numbers, and gives officers
an AI investigator that answers questions about that network with citations.

Three principles run through the whole system:

1. **Every fact cites its source.** Each entity and relationship carries the exact text it came from.
2. **Nothing is saved without an officer's review.** AI proposes; the officer decides.
3. **It can run entirely on a local machine.** Sensitive police data never has to leave the laptop.

---

## 2. Architecture at a glance (1.5 minutes)

```
 Browser (React 19 + Vite, English / Hindi)
        │  /api via Vite proxy, JWT session cookie
        ▼
 FastAPI backend (Python 3.13)
   ├── PostgreSQL ── officers, persons, cases, locations, documents, extracted evidence,
   │                 full-text + vector search chunks, job queue
   ├── Neo4j ─────── the relationship graph (people ↔ cases ↔ places ↔ organisations …)
   ├── spaCy ─────── local named-entity recognition (custom crime/FIR model)
   ├── Tesseract ─── local OCR for scanned PDFs and images
   └── Ollama ────── local LLM (qwen3) for relationships and answers,
                     local embeddings (embeddinggemma) for document search
                     (Groq cloud models are an optional alternative)
```

- **Frontend:** React 19, React Router, Vite; Cytoscape.js for the interactive network graph; an
  SVG map of India for connected locations; a built-in English/Hindi translation layer.
- **Backend:** FastAPI with an async PostgreSQL pool (psycopg) and the Neo4j async driver. A
  background worker processes the document queue inside the same server.
- **Two databases, two jobs:** PostgreSQL is the system of record — accounts, source documents,
  extracted evidence, and search indexes. Neo4j stores the relationship graph for fast multi-hop
  traversal.
- **AI is pluggable:** `EXTRACTION_PROVIDER=ollama` runs everything locally; `groq` uses hosted models.

---

## 3. Feature walkthrough (6–7 minutes)

### 3.1 Secure login and accounts

**[DEMO]** Log in as an officer.

Officers sign in with bcrypt-hashed passwords; the session is a signed JWT in an HTTP-only
cookie. Every API route except login and health requires it. An admin account creates and
deactivates officer accounts from the `/admin` panel. Each officer's uploads, pinned suspect and
working list are private to that officer.

### 3.2 Dashboard

**[DEMO]** Open the dashboard.

The dashboard shows the officer's pinned person and working list, record counts, a crime
frequency breakdown, the cities being tracked on a map of India, and a network preview for the
pinned person. It is the officer's daily starting point.

### 3.3 Search

**[DEMO]** Search by name, then filter by a crime type.

The search page matches people by name, alias or crime type, and filters by crime-type tags derived
from their cases. Results can be added to the officer's working list or opened as a profile. In the AI
Investigator, the person finder also tolerates typos using Unicode normalisation and edit
distance, so "Rohan Meta" still finds "Rohan Mehta".

### 3.4 Criminal profile — the dossier

**[DEMO]** Open Rohan Mehta's profile.

The profile is laid out like a case dossier:

- **Identity details** — alias, date of birth, age, height, status, family, last seen.
- **Case history and crimes** — every case the person is linked to, with their role.
- **Activity timeline** — source-backed entries, each with the quoted evidence and the document it
  came from. Nothing on the timeline is generated.
- **Connected locations** — residences, sightings and incident locations plotted on the India map.
- **Detailed record** — an optional AI synthesis of everything retrieved about the person, where
  every sentence must list the source it came from, grouped into identity, cases, locations,
  connections and source details.

### 3.5 The network graph

**[DEMO]** Explore the graph; click a node, then a line.

The graph starts from the selected person and follows connections up to four steps away (capped
at 1,000 paths, with a notice when it is truncated). Nodes are coloured and shaped by kind —
person, case, location, crime type, organisation, vehicle, phone. Several relationships between
the same two records are drawn as one line and listed separately when selected. Clicking a node
dims everything unrelated; clicking a relationship shows its evidence, source document and
review status, and an **AI insight** button explains the selected record.

### 3.6 Uploading documents

**[DEMO]** Upload an FIR PDF.

Officers choose one of seven source categories — FIRs and police reports, call detail records,
financial records, surveillance reports, social-media intelligence, criminal history, and
intelligence reports — and upload PDF, image (PNG/JPEG/TIFF), Word, text, CSV or JSON files up to
20 MB. Digital PDFs are read directly; scanned pages and images go through local OCR.

Processing runs in a background queue with a live progress bar ("Finding entities",
"Extracting relationships: batch 2 of 3") and can be cancelled.

### 3.7 Review before saving

**[DEMO]** Open the review screen.

Nothing reaches the database or graph until the officer confirms. For every entity and
relationship the review screen shows:

- the type and name, and the **exact source evidence**;
- **Keep / Reject** controls;
- relationships the system excluded, with a plain-language reason — for example,
  "The FIR lists this person with the role SUSPECT_IN; the AI suggested WITNESS_IN."

### 3.8 Identity review — no silent duplicates, no wrong merges

**[DEMO]** Confirm a document that names someone already on file.

If a person in the new document has the same name as an existing record, the system does not
guess. It shows an **identity check**: the existing record's age, recorded place, the FIRs they
already appear in, and the connections both share. The officer chooses "Use existing person" or
"Keep as a separate person". A person is merged automatically only when the name **and** a strong
identifier — phone number, date of birth or alias — match.

### 3.9 The AI Investigator

**[DEMO]** Open the AI Investigator, add two people, ask "Is Rohan Mehta connected to other
suspects across these FIRs?"

The investigator workspace merges the networks of several people into one graph. The officer
selects a node or relationship and asks questions in English or Hindi. Each answer has four parts:

1. **Recorded facts** — a direct answer citing records.
2. **Patterns in linked records (leads, not proof)** — computed by the server, for example
   "Sameer Qureshi appears with Rohan Mehta in 2 records: FIR-SYN-2026-0142, FIR-SYN-2026-0271" or
   "Cedar Park, where Rohan Mehta resides, is also the place of occurrence of FIR-SYN-2026-0198."
3. **Investigator insight** — what those patterns could mean, framed as possible leads.
4. **Suggested checks** — concrete next steps that name the record or document to examine.

Answers also draw on the original document text through retrieval, so they can cite passages
that never became graph links.

### 3.10 Removing a document

Deleting a source document removes its extracted evidence and any imported records that no other
document still uses, in PostgreSQL and in Neo4j. Shared records are kept.

### 3.11 English and Hindi

**[DEMO]** Toggle the language.

The interface is bilingual, and the investigator answers in the language of the question.

---

## 4. Technical deep-dive (5–6 minutes)

### 4.1 From file to text

- PDFs are read with PDFium; pages without a text layer are rendered and OCR'd with Tesseract.
  Word files are parsed from their XML; text, CSV and JSON are read as UTF-8.
- Limits protect the server: 30 pages, 60,000 characters, bounded image sizes.
- Line endings are normalised (PDFium returns Windows `\r\n`), because line-based rules and
  evidence citations depend on consistent lines.

### 4.2 Hybrid extraction — deterministic first, AI second

The core design decision: **use exact, explainable rules wherever the document structure allows,
and use the language model only where judgement is genuinely needed.**

**Stage 1 — Entity candidates (local, no AI).**

- **Regular expressions** for Indian identifiers: FIR numbers, 10-digit mobile numbers, vehicle
  registrations. "FIR No. FIR-SYN-2026-0142" and "FIR-SYN-2026-0142" resolve to the same case ID.
- **Labelled fields** — `Name:`, `Accused:`, `Address:`, `Crime type:` — plus contiguous person
  records, whose Age, Phone, Alias and DOB lines become attributes of that person only.
- **Statistical NER** with spaCy. The project includes a custom crime/FIR NER model trained on
  2,221 annotated examples with hard negatives such as "CCTV footage" and "call detail records".
- **Span cleaning** (`entity_spans.py`): small NER models label dates, amounts, bullets and form
  labels as names. The cleaner removes "September 2026", "INR 3,20,000", "Age", "Page 1", statute
  references ("BNS 318(4)", "Bharatiya Nyaya Sanhita"), courts ("State Sessions Court"), ranks and
  embedded codes; splits spans at form-field line breaks; and never invents text.
- **Name suffix rules** correct types: "… Pvt. Ltd." and "… Police Station" are organisations;
  "… Road", "… Nagar", "… Enclave" are places.
- **Gazetteer** of Indian states, union territories and major cities, applied after NER so "Goa"
  cannot break up "Goa Marine Exports".
- **One type per name**: a name tagged differently across mentions takes the majority type.

Measured on four realistic test documents, the cleaning step raised entity precision from **0.43
to 0.95** and recall from **0.71 to 0.88** with the custom model.

**Stage 2 — Structural relationships (local, no AI).** (`structural_relations.py`)

FIRs state many relationships through their layout. These are extracted exactly:

| Source structure | Relationship |
|---|---|
| People listed under an "Accused" or "Witnesses" heading, or `Accused:` / `Witness:` fields | `SUSPECT_IN`, `WITNESS_IN` |
| `Address:` in a person's record, "resident of …" in that person's own clause | `RESIDES_IN` |
| `Place of occurrence:` | `OCCURRED_AT` |
| `Nature of complaint:` / `Offence:` | `OF_TYPE` |
| "X called Y", "calls between X and Y" | `CONTACTED` |
| "X was seen near L", "X visited L", "X and Y were seen together at L" | `SEEN_AT` |
| "X, an employee of O"; the investigating officer's station | `EMPLOYED_BY` |
| Every person, organisation and vehicle named in the FIR | `MENTIONED_IN` |

Both "Label: value" and table layouts (label on one line, value below) are handled. Phrases must be
adjacent, so "was **not** seen" and "did **not** call" never match. When an FIR mentions other FIR
numbers, relationships attach only to the document's own FIR — the one under the "FIR No." label.

**Stage 3 — Model-extracted relationships (Ollama or Groq).**

- Only sentences containing relationship cues are sent, in bounded batches, with the list of
  already-found entities. **The model cannot create entities** — it can only link supplied ones.
- The model returns **line numbers**, not quoted text. The server copies the exact source lines as
  evidence, so evidence can never be paraphrased or invented.
- For local models, the output is constrained by a **JSON grammar** generated per batch: subject and
  object must be valid entity references of the allowed types for each predicate, and each start
  line is paired with only its valid end lines.
- Every model relationship is then validated: allowed direction (for example Person → Case for
  `SUSPECT_IN`), no self-links, evidence must name both endpoints, and — added in this project —
  the citation must contain wording for the relationship type (a `WITNESS_IN` citation must
  mention a witness).
- If the FIR's own accused/witness listing gives a person a different role, the model's role is
  excluded for review.
- One correction attempt is allowed. Output size is capped so a small model cannot loop, repeating
  the same edge until its token limit.

On a representative FIR, saved relationships rose from **3 (several wrong) to 21–23 (all correct)**,
and extraction time fell from **280 seconds to 66 seconds**.

### 4.3 Saving: consistency across two databases

- Confirmation checks that the officer is approving the exact draft that was reviewed (JSON
  equality), so a stale or altered draft cannot be saved.
- Records are written to PostgreSQL in one transaction under an advisory lock, with stable IDs
  derived from the document and reference. The graph write is stored as a replayable payload and
  then applied to Neo4j. If Neo4j is unavailable, the document is marked `sync_failed` and only the
  graph step is retried — PostgreSQL data is never lost or duplicated.
- The job queue uses **leases**: a crashed worker's job becomes available again after 20 minutes;
  a shutdown returns in-flight jobs to the queue; officers can cancel at safe checkpoints.
- Import ownership is tracked, so removing a document deletes only records that no other document uses.

### 4.4 Identity resolution

- Phones match across formats (`+91 98765-43210` = `9876543210`); vehicles by normalised
  registration; locations only when the city (and state, when known) is unambiguous.
- People are never merged on name alone. Automatic reuse requires a matching phone, date of birth
  or alias; otherwise every same-name record is offered for officer review, ranked by shared
  connections from PostgreSQL and Neo4j.

### 4.5 Retrieval for the AI Investigator (RAG)

- Confirmed documents are split into overlapping chunks, indexed with PostgreSQL full-text search
  and — when available — local `embeddinggemma` vectors.
- A question runs both keyword and vector search, scoped to the officer's own documents and, when
  a person is selected, to documents that mention that person. Results are combined with
  **reciprocal rank fusion** and near-duplicate passages are removed.
- If embeddings are unavailable, search falls back to keywords rather than failing.

### 4.6 The investigator's answers

- The server computes graph patterns first — roles by case, people sharing records, records
  linking several people, residences or sightings that are also incident locations, and evidence
  gaps — and writes them as plain sentences. A small local model reasons far better from these than
  from raw graph JSON, and the patterns are shown to the officer verbatim so accuracy does not depend
  on the model.
- The answer is **schema-constrained JSON** (facts, insight, 2–4 checks) and rejected if incomplete.
- Conversation history is limited to six validated messages and is used only to resolve follow-up
  references, never as evidence. Source text is marked as data, not instructions, to resist prompt
  injection.
- Model "thinking" is disabled for this step: with the patterns precomputed it only consumed the
  token budget. Answers now arrive in about 20–40 seconds on a laptop instead of timing out.

### 4.7 Security and safety

- bcrypt passwords, signed JWT cookies, admin-only officer management, per-officer data scoping.
- Upload size and format limits, stored under random UUID filenames, with path checks on download.
- Provider errors are sanitised: raw model output and document text never appear in error messages.
- At most three concurrent AI requests per worker; rate-limit backoff for Groq; bounded timeouts.
- Prompts forbid inferring guilt, predicting criminality, ranking people by risk, or treating shared
  places or crime types as proof of association.

### 4.8 Quality assurance

- **434 automated backend tests**, including PostgreSQL integration tests against a disposable
  database, API parity fixtures, OCR, extraction guardrails (negations, other people's records,
  invented references, evidence crossing omitted text), identity resolution, retrieval and
  investigator formatting.
- Benchmarks for relationship extraction and entity accuracy, run against the local model.

---

## 5. What makes this project unique (2 minutes)

1. **Evidence-grounded by construction.** The model never writes evidence; it points to source lines
   and the server copies them. Every saved fact can be traced to a quote in a named document.
2. **Human-in-the-loop at the right points.** Extraction proposes, the officer reviews entities,
   relationships and identities, and only then is anything written.
3. **Deterministic where possible, AI where necessary.** FIR layouts, fields and fixed phrasing are
   extracted by exact rules; the language model handles narrative, under strict validation.
4. **Private and offline-capable.** spaCy, Tesseract, Ollama and local embeddings keep sensitive
   investigation data on the officer's machine; hosted models are optional.
5. **Built for Indian investigation records.** FIR layouts and table formats, BNS/BNSS and IPC
   references, Indian mobile numbers and vehicle registrations, lakh/crore amounts, Indian place
   names, and an English/Hindi interface.
6. **Conservative about identity and guilt.** No name-only merges; shared records are presented as
   "leads, not proof"; allegations stay allegations; negated statements never become links.
7. **Explainable outputs.** Excluded relationships come with reasons; investigator patterns list the
   records they rest on; every graph edge shows its evidence and review status.
8. **Resilient pipeline.** Leased job queue, cancellation, replayable graph sync, and fallbacks when
   embeddings or Neo4j are temporarily unavailable.

---

## 6. Limitations and future work (1 minute)

Being honest about limits is part of responsible use:

- **Small local models.** `qwen3:1.7b` is fast enough for a laptop but its insight text can be
  generic; a larger model (for example `qwen3:4b`) gives better answers at slower speed.
- **Training data.** The custom NER model is trained on synthetic data; accuracy on real FIRs needs a
  manually labelled real-world test set.
- **Rule coverage.** Structural rules cover common FIR layouts and phrasings; unusual layouts fall back
  to the model and its checks.
- **Multi-case documents.** A document with several labelled FIRs receives no automatic case links.
- **Review remains essential.** Structural checks confirm that evidence exists and fits the
  relationship type; they cannot confirm that an allegation is true.

Future work: a real annotated evaluation set, more source-type-specific parsers (CDR and bank
statement tables), timeline analysis of dates across documents, audit logs, and role-based admin
accounts in place of the single configured admin.

---

## 7. Closing (30 seconds)

Criminal Network Analysis takes the documents investigators already have and turns them into a
network they can trust: every link cited, every save reviewed, every pattern labelled as a lead —
and all of it able to run on the officer's own laptop.

Thank you. I'm happy to take questions or show any part of the pipeline in more detail.
