# Criminal Network Analysis

React/Vite frontend with an Express API backed by PostgreSQL and Neo4j.

![Node](https://img.shields.io/badge/node-%3E%3D22.12-brightgreen)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB)
![Backend](https://img.shields.io/badge/backend-Express-black)
![Database](https://img.shields.io/badge/databases-PostgreSQL%20%7C%20Neo4j-4479A1)

---

## 📁 Project structure

```
Criminal Network Analysis/
├── backend/
│   ├── neo4j/              # Neo4j scripts and queries
│   ├── routes/              # Express route handlers
│   ├── services/             # Business logic, incl. Groq integration
│   ├── utils/                # Shared backend helpers
│   ├── .env                  # Local environment variables (gitignored)
│   ├── .env.example           # Template for required env vars
│   ├── db.js                  # PostgreSQL connection
│   ├── neo4jDriver.js          # Neo4j driver setup
│   └── server.js                # Express app entry point
│
├── frontend/
│   ├── public/
│   │   └── images/            # Static image assets
│   └── src/
│       ├── api/                # API client functions
│       ├── components/          # Reusable React components
│       ├── pages/                # Route-level page components
│       ├── utils/                 # Shared frontend helpers
│       ├── App.css
│       ├── App.jsx
│       ├── index.css
│       └── main.jsx
│   ├── index.html
│   └── vite.config.js
│
├── node_modules/               # Installed dependencies (gitignored)
├── .env                          # Root-level environment variables (gitignored)
├── .gitignore
├── .oxlintrc.json
├── package-lock.json
├── package.json
└── README.md
```

- `frontend/`: React source (`src/`), static assets (`public/`), HTML entry point, and Vite configuration. Builds output to `frontend/dist/`.
- `backend/`: Express server, routes, services, utilities, database connections, and Neo4j scripts (`neo4j/`).
- Shared npm dependencies, scripts, and lint configuration remain at the repository root. Run all commands below from the root.

---

## 🚀 Run locally

Use **Node.js 22.12 or newer**. Install dependencies with:

```bash
npm install
```

Create `backend/.env` using `backend/.env.example` if you do not already have it, then configure your PostgreSQL and Neo4j connections.

Run the frontend and backend in separate terminals:

```bash
npm run server   # starts the Express API
npm run dev      # starts the Vite dev server
```

Open **http://localhost:3000**.

---

## 🤖 Groq AI summaries

1. Create an API key at [console.groq.com/keys](https://console.groq.com/keys).
2. Add `GROQ_API_KEY=your_key` to `backend/.env`. Keep existing database settings.
3. Restart `npm run server`.
4. Open a profile and click **Explain this network** below its graph.

The optional `GROQ_MODEL` setting defaults to `openai/gpt-oss-20b`. The backend calls the [Groq Chat Completions API](https://console.groq.com/docs/api-reference) using Node's built-in `fetch`; no additional SDK is required.

> ⚠️ Never place the key in frontend code or a `VITE_` variable. `backend/.env` is ignored by Git.

**`POST /api/criminals/:id/explain`**
- Reads records from the databases and sends the profile ID/name/status, up to 50 cases, and 25 graph overlap rows to Groq.
- Returns `{ explanation }`.
- Photos and demographic fields are excluded.
- Generation happens only on a button click.
- The response explains shared attributes, **not** proven personal associations or guilt.
- Empty overlap results may mean Neo4j was unavailable. Summaries require source verification.

**Limits & safety:**
- Requests have a 30-second Groq timeout and a process-wide limit of three concurrent summaries.
- Missing keys, provider failures, and usage limits produce actionable UI errors.
- The existing API has **no authentication** — deploy behind access control and per-user rate limits before exposing records and paid AI calls publicly.

---

## ✅ Checks

```bash
npm run build
npm run lint
node --test backend/services/groq.test.js
```