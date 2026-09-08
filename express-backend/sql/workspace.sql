-- Per-officer "currently working on" state.
-- Replaces the old localStorage-based pin/list, which was shared by whoever
-- was using the browser rather than scoped to the logged-in officer.
-- This file is here for reference / manual setup; workspace.js also
-- creates these tables itself on first run (CREATE TABLE IF NOT EXISTS),
-- same convention as officers.sql.
--
-- person_id is VARCHAR to match persons.person_id (e.g. "P001").

CREATE TABLE IF NOT EXISTS officer_pinned_criminal (
  officer_id  INTEGER PRIMARY KEY REFERENCES officers(officer_id) ON DELETE CASCADE,
  person_id   VARCHAR(20) NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
  pinned_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS officer_working_list (
  officer_id  INTEGER NOT NULL REFERENCES officers(officer_id) ON DELETE CASCADE,
  person_id   VARCHAR(20) NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
  added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (officer_id, person_id)
);