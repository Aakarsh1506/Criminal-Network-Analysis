# FastAPI backend

`backend1` is the Python/FastAPI version of the API. It exposes the same `/api/...` routes as the Express backend and uses the existing PostgreSQL schema, Neo4j graph, JWT cookie, and PDF filenames. The frontend can use it through its existing proxy on port 5050.

## Run

Run these commands from the repository root with Python 3.11 or newer (verified on Python 3.13):

```bash
python3 -m venv backend1/.venv
source backend1/.venv/bin/activate
python -m pip install -r backend1/requirements.txt
```

Keep your existing `backend1/.env`. If it does not exist, copy `backend1/.env.example` to `backend1/.env` and configure the PostgreSQL, Neo4j, and JWT settings. Environment variables override values in that file. The configuration path is relative to `backend1`, independent of the launch directory.

Stop any other backend using port 5050, then start FastAPI from the repository root:

```bash
python -m backend1.server
```

With the virtual environment activated, `npm run server:fastapi` does the same thing. `npm run server` still starts the separate Express backend in `backend/`.

For automatic reload during development:

```bash
python -m uvicorn backend1.server:app --reload --port 5050
```

Start the frontend in another terminal with `npm run dev`. The API health endpoint is `http://localhost:5050/api/health`; interactive API documentation is at `http://localhost:5050/docs`.

`python -m backend1.server` reads `PORT` from the environment/configuration (default 5050). If you use the Uvicorn CLI, pass its port explicitly. Production HTTPS cookies retain the existing `NODE_ENV=production` switch. Keep the same `JWT_SECRET` and `COOKIE_NAME` when switching servers to preserve signed-in sessions.

## Database and files

The API reads the existing `persons`, `cases`, `locations`, and `crime_types` tables. Startup creates the officers, workspace, and document metadata tables if missing; it does not seed or replace criminal records. Reference SQL is in `sql/`. Database connections and the HTTP client are opened and closed with the app's [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/).

If database initialization is unavailable, the server logs the failure and starts in the same degraded mode as the original backend. `/api/health` is a liveness check, not a database-readiness check. Database-dependent requests return the existing error responses.

PDFs remain in `backend1/uploads/`, using their stored UUID filenames. This directory must contain the files referenced by `officer_documents` when switching from the other backend. Existing files in this folder are retained. Uploads use multipart field `file`, accept `application/pdf`, and enforce the original 20 MB limit. File listing, download, and deletion remain scoped to the officer ID from the signed cookie.

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
python -m backend1.scripts.add_officer --username jdoe --name "Jane Doe" --org "Delhi Police" --dob 1990-05-14
```

The script prompts for a password. `--password` and `--role` are also supported for compatibility with the old CLI; the default role is `officer`.

## Verify

```bash
python -m pip install -r backend1/requirements-dev.txt
python -m pytest backend1/tests -q
python -m ruff check backend1
python -m ruff format --check backend1
```

Tests use temporary upload directories and isolated database/provider fixtures. They cover route parity against the Express snapshot, existing JWT/bcrypt compatibility, permissions, profiles, workspace isolation, native Neo4j paths, uploads, and AI failures/concurrency. They do not require database credentials or make Groq requests. The dependency versions in `requirements.txt` and `requirements-dev.txt` are pinned to the tested environment; the `.in` files record the supported dependency ranges.
