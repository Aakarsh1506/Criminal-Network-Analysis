-- Officer accounts for the login system.
-- Accounts are created through the admin API or scripts/add_officer.py.
-- App startup and the CLI both create this table if it is missing.

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
