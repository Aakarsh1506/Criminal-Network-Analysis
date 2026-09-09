-- Officer accounts for the login system.
-- There is no public signup route — rows are only ever inserted by an admin
-- running `python -m backend1.scripts.add_officer`. This
-- file is here for reference / manual setup; the CLI script also creates
-- the table itself on first run (CREATE TABLE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS officers (
  officer_id    SERIAL PRIMARY KEY,
  username      VARCHAR(64) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name          VARCHAR(120) NOT NULL,
  dob           DATE,
  org_name      VARCHAR(120) NOT NULL,
  role          VARCHAR(32) NOT NULL DEFAULT 'officer',
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);