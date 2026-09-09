# Criminal Network Analysis

React/Vite frontend with an API backed by PostgreSQL and Neo4j — available as either an **Express** backend or a **FastAPI** backend (same routes, same databases, pick one). Officer accounts are cookie/JWT authenticated, and an admin panel is used to provision new officer accounts.

![Node](https://img.shields.io/badge/node-%3E%3D22.12-brightgreen)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB)
![Backend](https://img.shields.io/badge/backend-Express%20%7C%20FastAPI-black)
![Database](https://img.shields.io/badge/databases-PostgreSQL%20%7C%20Neo4j-4479A1)

---

## 📁 Project structure

```
Criminal Network Analysis/
├── express-backend/
│   ├── middleware/     # Auth guards (requireAuth, requireAdmin)
│   ├── neo4j/          # Neo4j scripts and queries
│   ├── routes/         # Express route handlers
│   ├── scripts/        # CLI utilities (e.g. add-officer)
│   ├── services/       # Business logic, incl. Groq integration
│   ├── sql/            # Reference SQL for hand-managed setup
│   ├── uploads/        # Uploaded PDFs on disk (gitignored)
│   ├── utils/          # Shared backend helpers
│   ├── .env            # Local environment variables (gitignored)
│   ├── .env.example    # Template for required env vars
│   ├── db.js           # PostgreSQL connection
│   ├── neo4jDriver.js  # Neo4j driver setup
│   └── server.js       # Express app entry point
│
├── backend/
│   ├── middleware/, routes/, services/, sql/, utils/  # Python equivalents of the above
│   ├── neo4j/           # Same Neo4j scripts, shared reference with express-backend/
│   ├── uploads/         # Uploaded PDFs on disk (gitignored)
│   ├── tests/           # pytest suite, incl. fixtures asserting parity with Express
│   ├── .env             # Local environment variables (gitignored) — separate from express-backend/.env
│   ├── .env.example     # Template for required env vars
│   ├── db.py            # PostgreSQL connection
│   ├── neo4j_driver.py  # Neo4j driver setup
│   ├── app.py           # FastAPI app factory
│   └── server.py        # FastAPI entry point (`python -m backend.server`)
│
├── frontend/
│   ├── public/          # Static assets (images, etc.)
│   ├── src/
│   │   ├── api/          # API client functions
│   │   ├── components/   # Reusable React components
│   │   └── pages/        # Route-level page components
│   ├── index.html
│   └── vite.config.js
│
├── node_modules/        # Installed dependencies (gitignored)
├── .env                 # Root-level environment variables (gitignored)
├── .gitignore
├── .oxlintrc.json
├── package-lock.json
├── package.json
└── README.md
```

- `frontend/`: React source (`src/`), static assets (`public/`), HTML entry point, and Vite configuration. Builds output to `frontend/dist/`.
- `express-backend/`: Express server, routes, middleware, services, utilities, database connections, and Neo4j scripts (`neo4j/`).
- `backend/`: FastAPI equivalent of the above, same API routes and database schemas. See [`backend/README.md`](backend/README.md) for its own setup/run/verify instructions.
- Shared npm dependencies, scripts, and lint configuration remain at the repository root. Run all commands below from the root.

---

## 🚀 Run locally

Use **Node.js 22.12 or newer**. Install dependencies with:

```bash
npm install
```

Create `express-backend/.env` using `express-backend/.env.example` if you do not already have it, then configure your PostgreSQL and Neo4j connections (see below for the full list of variables).

Run the frontend and backend in separate terminals:

```bash
npm run server   # starts the Express API
npm run dev      # starts the Vite dev server
```

Open **http://localhost:3000**.

### Running the FastAPI backend instead

Same frontend, same port, same databases — only the backend terminal command changes. Requires **Python 3.11+**.

1. Create and activate a virtual environment for it, then install dependencies:
   ```bash
   python3 -m venv backend/.venv
   source backend/.venv/bin/activate   # Windows: backend\.venv\Scripts\activate
   python -m pip install -r backend/requirements.txt
   ```
2. Create `backend/.env` using `backend/.env.example` if you do not already have it, then configure it — this is a **separate file** from `express-backend/.env`, even if you're pointing both at the same databases.
3. With the virtual environment still active, start the API:
   ```bash
   npm run server:fastapi   # starts the FastAPI API (python3 -m backend.server)
   npm run dev               # starts the Vite dev server, same as above
   ```

Open **http://localhost:3000** — same URL either way. See [`backend/README.md`](backend/README.md) for the full setup/run/verify reference, including the `add-officer` CLI equivalent (`npm run add-officer:fastapi`).

---

## 🔐 Authentication & accounts

Every API route except `/api/auth/login` and `/api/health` requires a valid session cookie (`requireAuth`). There are two kinds of accounts:

### Officer accounts
Stored in the `officers` table, password hashed with bcrypt. Created either:
- **Through the admin panel** (`/admin`, see below) — the normal path for a real org.
- **Via the CLI script**, useful for bootstrapping the very first account on a fresh deployment:
  ```bash
  npm run add-officer -- --username jdoe --password "SomeStrongPass!" --name "Jane Doe" --org "Delhi Police"
  ```

An officer's session is scoped to their `officer_id` everywhere it matters — pinned criminal, working list, and uploaded documents are all private to that officer (see below).

### Admin account
A single hardcoded account, checked against `ADMIN_USERNAME` / `ADMIN_PASSWORD` in your backend's `.env` (`express-backend/.env` or `backend/.env`, depending which backend you're running) — **not** a row in the `officers` table. Logging in with these credentials on the normal login page redirects to `/admin` instead of `/dashboard`.

From `/admin` you can:
- Create new officer accounts (username, password, name, DOB, org).
- View all existing officers and deactivate one (soft-delete via `is_active`, not a hard delete — keeps history intact).

> ⚠️ This is a stopgap for one deployment/demo. It's a single shared password with no rotation and no audit trail. Before a real multi-org deployment, this should become a proper `role = 'admin'` row in `officers` (bcrypt-hashed like everyone else), ideally with a separate "platform" tier above it that provisions each org's first admin — see project notes for the fuller plan.

---

## 🗂️ Per-officer data

Three things are scoped to the logged-in officer's `officer_id`, each backed by its own self-creating table (no manual migration needed — they're created with `CREATE TABLE IF NOT EXISTS` the first time the backend boots):

| Feature | Table | Notes |
|---|---|---|
| Pinned criminal (Dashboard) | `officer_pinned_criminal` | One row per officer, replaced on re-pin |
| Working list (Dashboard / Criminal List) | `officer_working_list` | Many rows per officer |
| Uploaded documents (Upload page) | `officer_documents` | Files stored on disk in `express-backend/uploads/` (or `backend/uploads/` for FastAPI), metadata + ownership in Postgres |

None of this is shared across officers — each of these used to be `localStorage`-based (or in-memory, for documents) and was visible to *whoever was using the browser*, not the logged-in officer. All three now go through authenticated, officer-scoped API routes instead.

---

## 🤖 Groq AI summaries

1. Create an API key at [console.groq.com/keys](https://console.groq.com/keys).
2. Add `GROQ_API_KEY=your_key` to your backend's `.env` (`express-backend/.env` or `backend/.env`). Keep existing database settings.
3. Restart the backend (`npm run server` or `npm run server:fastapi`).
4. Open a profile and click **Explain this network** below its graph.

The optional `GROQ_MODEL` setting defaults to `openai/gpt-oss-20b`. The Express backend calls the [Groq Chat Completions API](https://console.groq.com/docs/api-reference) using Node's built-in `fetch`; the FastAPI backend uses `httpx`. Neither needs an additional SDK.

> ⚠️ Never place the key in frontend code or a `VITE_` variable. Backend `.env` files are ignored by Git.

**`POST /api/criminals/:id/explain`**
- Requires a valid officer/admin session, same as the rest of the API.
- Reads records from the databases and sends the profile ID/name/status, up to 50 cases, and 25 graph overlap rows to Groq.
- Returns `{ explanation }`.
- Photos and demographic fields are excluded.
- Generation happens only on a button click.
- The response explains shared attributes, **not** proven personal associations or guilt.
- Empty overlap results may mean Neo4j was unavailable. Summaries require source verification.

**Limits & safety:**
- Requests have a 30-second Groq timeout and a process-wide limit of three concurrent summaries.
- Missing keys, provider failures, and usage limits produce actionable UI errors.

---

## ⚙️ Environment variables (`express-backend/.env.example`)

The FastAPI backend (`backend/.env.example`) uses the same variable names — copy whichever backend's example file you're running to a real `.env` in that same folder. **Each backend reads its own `.env`; they don't share one.**

```bash
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=your_password_here
PGDATABASE=criminal_network
PORT=5050

NEO4J_URI=neo4j+s://your-instance-id.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_aura_password_here

# Groq AI summaries (server only)
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-20b

# Auth
# Generate a real secret with: node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"
JWT_SECRET=replace_with_a_long_random_string
JWT_EXPIRES_IN=12h
COOKIE_NAME=cna_token
# Set to your deployed frontend URL in production (dev works out of the box via the Vite proxy)
FRONTEND_ORIGIN=http://localhost:3000
NODE_ENV=development

# Admin panel login — a single hardcoded account, not stored in the
# officers table. Change these before any real deployment; there's no
# UI to change them yet, only this file.
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_this_admin_password
```

**Deploying frontend/backend on different domains?** Set `NODE_ENV=production` so cookies get `secure: true`, and make sure `sameSite` is set to `"none"` in `express-backend/routes/auth.js`'s `COOKIE_OPTIONS` for the cross-site cookie to survive — `"lax"` (the local-dev default) gets silently dropped cross-domain. Also point `FRONTEND_ORIGIN` at your exact deployed frontend URL; CORS needs it to match exactly.

**Deploying with a managed Postgres provider?** Most give you a single `DATABASE_URL` connection string requiring SSL rather than discrete `PGHOST`/`PGUSER`/etc. — `express-backend/db.js` (or `backend/db.py`) can be extended to prefer `DATABASE_URL` (with SSL enabled, e.g. `ssl: { rejectUnauthorized: false }` in Node) when it's present, falling back to the discrete vars for local dev.

**Deploying Neo4j by raw IP instead of a domain?** Public CAs won't issue certificates for bare IPs, so you'll be stuck with a self-signed certificate. Node's TLS stack may tolerate that as-is, but Python's `ssl` module won't — `backend`'s driver needs its URI scheme rewritten from `neo4j+s://`/`bolt+s://` to `neo4j+ssc://`/`bolt+ssc://` to skip certificate verification. Prefer a real domain + CA-signed cert (or Neo4j Aura, which provides one automatically) wherever possible instead.

---

## ✅ Checks

```bash
npm run build
npm run lint
node --test express-backend/services/groq.test.js
```

For the FastAPI backend, see [`backend/README.md`](backend/README.md#verify) for its `pytest`/`ruff` equivalents.

---

## FastAPI alternative

The Python backend is in [`backend/`](backend/README.md). It preserves the existing API routes and frontend proxy port. Follow its setup instructions, activate `backend/.venv`, then run `npm run server:fastapi` from the repository root.