# FastAPI backend

`backend` is the Python/FastAPI version of the API. It exposes the same `/api/...` routes as the Express backend and uses the existing PostgreSQL schema, Neo4j graph, JWT cookie, and PDF filenames. The frontend can use it through its existing proxy on port 5050.

## Run

Run these commands from the repository root with Python 3.11 or newer (verified on Python 3.13):

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
```

Keep your existing `backend/.env`. If it does not exist, copy `backend/.env.example` to `backend/.env` and configure the PostgreSQL, Neo4j, and JWT settings. Environment variables override values in that file. The configuration path is relative to `backend`, independent of the launch directory.

Stop any other backend using port 5050, then start FastAPI from the repository root:

```bash
python -m backend.server
```

With the virtual environment activated, `npm run server:fastapi` does the same thing.

For automatic reload during development:

```bash
python -m uvicorn backend.server:app --reload --port 5050
```

Start the frontend in another terminal with `npm run dev`. The API health endpoint is `http://localhost:5050/api/health`; interactive API documentation is at `http://localhost:5050/docs`.

`python -m backend.server` reads `PORT` from the environment/configuration (default 5050). If you use the Uvicorn CLI, pass its port explicitly. Production HTTPS cookies retain the existing `NODE_ENV=production` switch. Keep the same `JWT_SECRET` and `COOKIE_NAME` when switching servers to preserve signed-in sessions.

## Database and files

The API reads the existing `persons`, `cases`, `locations`, and `crime_types` tables. Startup creates the officers, workspace, and document metadata tables if missing; it does not seed or replace criminal records. Reference SQL is in `sql/`. Database connections and the HTTP client are opened and closed with the app's [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/).

If database initialization is unavailable, the server logs the failure and starts in the same degraded mode as the original backend. `/api/health` is a liveness check, not a database-readiness check. Database-dependent requests return the existing error responses.

Uploaded files are stored in `backend/uploads/`, using their stored UUID filenames. This directory must contain the files referenced by `officer_documents` when switching from the other backend. Existing files in this folder are retained. Uploads use multipart field `file` plus a source category and enforce the 20 MB limit. See the extraction section below for the supported formats and processing flow. File listing, download, and deletion remain scoped to the officer ID from the signed cookie.

## API compatibility

| Area | Endpoints |
| --- | --- |
| Authentication | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| Criminal records | `GET /api/criminals`, `GET /api/criminals/{id}` |
| Graph and AI | `GET /api/criminals/{id}/network`, `POST /api/criminals/{id}/explain` |
| Dashboard | `GET /api/crime-types`, `GET /api/stats` |
| Workspace | `GET /api/workspace`, `PUT/DELETE /api/workspace/pin`, `POST /api/workspace/list`, `DELETE /api/workspace/list/{personId}` |
| Officer administration | `GET/POST /api/officers`, `PATCH /api/officers/{id}/deactivate` |
| Documents | `GET/POST /api/documents`, `GET /api/documents/{id}/file`, `DELETE /api/documents/{id}` |
| Health | `GET /api/health` |

The migration preserves camelCase payload fields and `{ "error": "..." }` failures. Invalid request bodies return 400 rather than FastAPI's default 422. Existing bcrypt password hashes and HS256 JWT cookies remain valid. The admin-only officer API always creates the `officer` role, regardless of client-supplied role fields.

The network query retains the four-hop limit and 1,000-path cap. Crime-type nodes are endpoints, so traversal cannot expand through them into other cases. Native Neo4j node and relationship IDs and original edge directions are retained.

Groq remains optional, configured with `GROQ_API_KEY` and `GROQ_MODEL`. The provider timeout is 30 seconds and at most three explanations run concurrently per server worker. Provider errors are sanitized, and source record limits and prompts are preserved.

## Add an officer

From the repository root, with the virtual environment active:

```bash
python -m backend.scripts.add_officer --username jdoe --name "Jane Doe" --org "Delhi Police" --dob 1990-05-14
```

The script prompts for a password. `--password` and `--role` are also supported for compatibility with the old CLI; the default role is `officer`.

## Verify

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
python -m ruff check backend
python -m ruff format --check backend
```

Tests use temporary upload directories and isolated database/provider fixtures. They cover route parity against the Express snapshot, existing JWT/bcrypt compatibility, permissions, profiles, workspace isolation, native Neo4j paths, uploads, and AI failures/concurrency. They do not require database credentials or make Groq requests. The dependency versions in `requirements.txt` and `requirements-dev.txt` are pinned to the tested environment; the `.in` files record the supported dependency ranges.

## Document extraction and database import

The Upload page accepts seven source categories: FIR/police reports, CDRs, financial records,
surveillance reports, social media intelligence, criminal history, and intelligence reports.
Supported file formats are PDF, PNG/JPEG/TIFF, UTF-8 TXT/CSV/JSON, and DOCX. CSV and JSON are
read as text for extraction; this is not a raw SQL importer or a transaction anomaly detector.

Scanned PDFs and images use local Tesseract OCR. Digital PDFs and Word/text files use their
embedded text. The default hybrid mode extracts entity candidates locally with spaCy and
regex, then sends relevant passages and entity references to Groq for relationships only.
Set `EXTRACTION_MODE=groq` to use the original full AI entity and relationship extraction.
Groq cites numbered source-line ranges; the server copies the original text into each evidence field. The server validates names, source quotes, references, allowed predicates, and directions.
This checks structural validity and quoted evidence; it does not independently verify whether
an allegation or model interpretation is true. Results are staged for review. Entity records and graph relationships are saved only after
the uploading officer confirms the exact draft, and remain unverified source assertions. Witnesses and mentioned people retain their specific case roles.

Install Python dependencies with `python -m pip install -r backend/requirements.txt`.
Install the Tesseract executable separately (`brew install tesseract` on macOS, or your
platform's Tesseract package). English OCR is the default. For other languages, install their
Tesseract trained data and set `OCR_LANGUAGE` (for example `eng+hin`).

Configure `GROQ_API_KEY` in `backend/.env`. Optional settings:

```dotenv
GROQ_EXTRACTION_MODEL=openai/gpt-oss-20b
EXTRACTION_MODE=hybrid
SPACY_MODEL=en_core_web_sm
OCR_LANGUAGE=eng
```

The Python requirements include spaCy and its English `en_core_web_sm` model. After pulling
this change, reinstall `backend/requirements.txt` in your backend virtual environment and
restart FastAPI. Model loading happens locally on the first extraction and is cached.
Missing model installations produce a setup error; they do not silently switch to Groq.

Hybrid extraction uses spaCy for people, organizations and places, plus regex for Indian
mobile numbers, vehicle registrations and FIR IDs. Explicit `Name:`, `Suspect:`, `Witness:`,
`Company:`, `Crime type:` and similar fields supplement NER. Consecutive labeled fields
for age, phone/mobile, alias, ISO DOB, city and state immediately after a named-person
record become attributes. Unlabeled or distant attributes are not inferred. Phone numbers
also remain separate candidates; the app does not infer ownership from proximity.
When saving, exact age wording such as `34 years` becomes numeric age `34`. Ranges,
approximations, unknown values and out-of-range ages remain source text (`age_text` in
the extracted entity properties), with no guessed numeric age. The reviewed attribute
and original evidence are retained.
Explicit `Address:`, `Location:`, `Residence:`, `City:`, `Area:`, `Locality:` and `Last seen:`
fields are location candidates and take precedence over statistical NER spans. The local
phrase list in `backend/data/location_names.json` protects known place names such as
Bandra Kurla Complex and Khar West from being classified as people. Add exact place-name
variants to that JSON list and restart to extend it. These rules improve known cases;
the general English NER model can still misclassify unfamiliar names.

Groq receives bounded passages surrounding entity mentions, with nearby context and
explicit markers where text was omitted. It cannot add entities, and relationships retain
the existing predicate, direction, evidence and review checks. Entity candidates with no
relationships still appear for review. The existing rate-limit backoff applies. Logs report
local entity counts, passage counts and Groq input/output token usage, without source text
unless debug responses are enabled.

Location entities keep their first detected source sentence in `evidence`, rather than just
the place name. It is visible under **Source evidence** in review, retained in the staged
extraction, and saved with the extracted entity after confirmation. Groq receives this
sentence as location context along with numbered source passages. If a batch boundary cuts
the saved sentence, a separate bounded passage preserves it. For OCR blocks without useful
sentence boundaries, evidence falls back to a source line or a maximum 2,000-character
source window around the mention. Later mentions remain available in relevant passages;
each accepted relationship has its own source evidence.

`RESIDES_IN` links a person to an explicitly stated residence; `SEEN_AT` records an explicit
sighting. `OCCURRED_AT` continues to link a case to an incident location. Mere co-occurrence
does not create any of these links. Restart FastAPI to apply the expanded SQL predicate
constraint before confirming new extractions. Existing saved records are not re-extracted.

This reduces generated entity JSON and can omit unrelated source text; token savings vary
with the document and retries. It does not eliminate Groq rate limits. The English model can
miss names or misclassify entities, and distant references or relationships across batches
may be missed. Review the results against the document. Use `EXTRACTION_MODE=groq` and
restart if you need the original extraction behavior. Custom languages require a compatible
installed spaCy model; the regex rules remain focused on Indian identifiers.

The local pipeline follows spaCy's [model loading](https://spacy.io/usage/models) and
[entity recognition](https://spacy.io/usage/linguistic-features#named-entities) interfaces.

Run the **FastAPI** backend with `python -m backend.server` from the repository root and your
virtual environment activated. The repository's `npm run server` still launches the old
Express backend, which does not implement this pipeline. Restart FastAPI after updating.

Startup applies `sql/ingestion.sql` to the existing database from the supplied dump. It adds
organizations, vehicles, extraction evidence tables, document job fields, and the `case_people`
view. It allows `cases.person_id` and `locations.state` to be null so imports do not invent a
primary suspect or an unknown state. Existing rows remain intact. Persons, cases, locations,
and crime types are inserted into the original tables; phone entities and all extracted
properties also live in `extracted_entities`. Each source relationship lives in
`extracted_relationships` and Neo4j. The Neo4j account must be able to create uniqueness
constraints as well as write nodes and edges.

Supported graph predicates are `MENTIONED_IN`, `WITNESS_IN`, `SUSPECT_IN`, `OCCURRED_AT`,
`OF_TYPE`, `EMPLOYED_BY`, `OWNS`, `CONTACTED`, `RESIDES_IN`, and `SEEN_AT`, with the requested subject/object types.
Unidentified phone owners are not turned into people or inferred `CONTACTED` edges.

Uploads return immediately with status `queued`. A persistent, single-job-per-worker queue
extracts text, calls Groq, and stops at `awaiting_review`. After confirmation it commits
PostgreSQL entity records and a graph payload in one transaction,
and then writes Neo4j in a transaction after confirmation. `complete` means both saves succeeded. A `sync_failed`
job keeps its PostgreSQL data and retries only Neo4j. Graph replay uses stable relationship
IDs to avoid duplicates. Jobs interrupted by shutdown are requeued; crash-abandoned leases
become available after 20 minutes. PostgreSQL and Neo4j are eventually consistent, not one
shared distributed transaction.

The review page requires a Yes/No choice for each entity and relationship before saving.
Rejecting an entity also excludes relationships connected to it. Rejected items and their
reasons remain in the document's review history, but are not saved as entity or graph records.
Use **Remove document** on the review page or document details to permanently delete an
unconfirmed stored, failed, or awaiting-review document after confirmation. Processing
documents and confirmed extraction sources remain protected from removal.

The page shows status, source text, entities, relationships, and supporting quotes. Use
**Process document** to retry extraction, or **Retry Neo4j sync** after fixing graph access.
A failed extraction retry keeps OCR text but calls Groq again. Existing stored PDFs can also
be processed. Files used as extraction evidence are retained and cannot be deleted by the
ordinary document deletion endpoint.

Limits: 20 MB per file, 30 PDF pages/image frames, 60,000 extracted characters, and a ten-minute
job timeout. Long text is split into overlapping chunks. Repeated uploads remain separate
source documents. Explicit identifiers can link existing records; names alone never merge
people across documents. This does not include fuzzy identity matching or editing extracted fields.

API additions:

- `GET /api/documents/source-types`: categories and accepted file extensions.
- `POST /api/documents`: multipart `file` and `sourceType` (defaults to `fir`).
- `GET /api/documents/{id}`: owner-scoped status, extracted text, and extraction JSON.
- `POST /api/documents/{id}/process`: retry a failed/sync-failed/stored document.
- `POST /api/documents/{id}/confirm`: approve the exact staged `extraction` JSON and queue saving.

Extraction tests mock Groq and Neo4j provider calls. OCR tests run real Tesseract when installed.
The optional PostgreSQL tests create and remove isolated databases; run them only against a
test instance with a user allowed to create databases:

```bash
CNA_TEST_PGHOST=/path/to/test/socket CNA_TEST_PGPORT=55439 \
  python -m pytest backend/tests/test_ingestion_postgres.py -q
```

Implementation references: [Groq JSON output mode](https://console.groq.com/docs/structured-outputs),
[pypdfium2 resource/thread handling](https://pypdfium2-team.github.io/pypdfium2/python_api.html), and
[pytesseract setup](https://pypi.org/project/pytesseract/).

### Review before saving

New uploads open `/documents/{id}/review`. The page shows a scrollable dossier for each entity,
all extracted attributes, identifiers, source evidence, incoming/outgoing relationships, and a
complete relationship list. **Review later** leaves the draft untouched. **Confirm and save**
authorizes saving the displayed extraction to the entity tables and Neo4j.

The original file, OCR text, and draft JSON stay in the officer's document staging record so
review can resume after a refresh. No persons/cases/organizations/vehicles, extraction entity
or relationship rows, or graph nodes/edges are created before confirmation. Confirmation is
owner-scoped and checks JSON equality with the staged snapshot; stale or modified snapshots
are rejected. `confirmed_at` and `confirmed_by` record approval. Retries of an approved import
reuse that exact extraction. Previously completed imports are retained.

During review, **Reject relationship** excludes an individual suggestion; **Undo rejection**
restores it before confirmation. Controls in the entity dossiers and complete relationship
list share the same selections. Pending choices last for the current page; **Confirm and
save** records them. Entities remain in the draft even if all their relationships are rejected.
The confirmation API accepts `rejected_relationship_indices`, a list of distinct zero-based
indices into the original `extraction.relationships`. The server atomically checks ownership
and equality with that original draft, then moves selected relationships to
`excluded_relationships` with the reason `Rejected by reviewer during confirmation.`
The document's confirmation identity/time records the decision. Rejections remain in the
review history but never enter `extracted_relationships` or the Neo4j graph payload.
This applies to drafts awaiting review, not links already saved from completed documents.

The configured GPT-OSS models use Groq strict JSON schema output. Temporary rate limits use
bounded retries respecting `Retry-After`; evidence is still validated against the source.

### Debug Groq responses

Set `GROQ_DEBUG_RESPONSES=true` in `backend/.env` and restart FastAPI. Each extraction
attempt prints the HTTP response body to the backend console, followed by the generated
JSON or `error.failed_generation` when Groq rejects it. Output is captured before validation,
so failed attempts are visible too. API keys are redacted; request headers are never printed.
Full responses can contain source document data. Set the flag to `false` when finished.
