# Criminal Network Analysis

React/Vite frontend with an Express API backed by PostgreSQL and Neo4j.

## Run locally

Use Node.js 22.12 or newer. Install dependencies with `npm install`.
Create `backend/.env` using `backend/.env.example` if you do not already have it,
then configure your PostgreSQL and Neo4j connections.

Run `npm run server` and `npm run dev` in separate terminals. Open http://localhost:3000.

## Groq AI summaries

1. Create an API key at https://console.groq.com/keys.
2. Add `GROQ_API_KEY=your_key` to `backend/.env`. Keep existing database settings.
3. Restart `npm run server`.
4. Open a profile and click **Explain this network** below its graph.

The optional `GROQ_MODEL` setting defaults to `openai/gpt-oss-20b`.
The backend calls the [Groq Chat Completions API](https://console.groq.com/docs/api-reference)
using Node's built-in fetch; no additional SDK is required.
Never place the key in frontend code or a `VITE_` variable. `backend/.env` is ignored by Git.

`POST /api/criminals/:id/explain` reads records from the databases, sends the profile ID/name/status,
up to 50 cases and 25 graph overlap rows to Groq, and returns `{ explanation }`.
Photos and demographic fields are excluded. Generation happens only on a button click.
The response explains shared attributes, not proven personal associations or guilt.
Empty overlap results may mean Neo4j was unavailable. Summaries require source verification.

Requests have a 30-second Groq timeout and a process-wide limit of three concurrent summaries.
Missing keys, provider failures, and usage limits produce actionable UI errors.
The existing API has no authentication; deploy behind access control and per-user rate limits
before exposing records and paid AI calls publicly.

## Checks

- `npm run build`
- `npm run lint`
- `node --test backend/services/groq.test.js`
