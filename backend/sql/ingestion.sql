-- Extend the supplied schema without replacing its records.
-- A case can mention several people, or have no identified person yet.
ALTER TABLE cases ALTER COLUMN person_id DROP NOT NULL;

CREATE TABLE IF NOT EXISTS organizations (
  organization_id VARCHAR(20) PRIMARY KEY,
  name VARCHAR(100) NOT NULL
);
CREATE TABLE IF NOT EXISTS vehicles (
  vehicle_id VARCHAR(20) PRIMARY KEY,
  registration VARCHAR(100),
  name VARCHAR(100) NOT NULL
);

ALTER TABLE officer_documents ADD COLUMN IF NOT EXISTS source_type TEXT;
ALTER TABLE officer_documents ADD COLUMN IF NOT EXISTS processing_status TEXT NOT NULL DEFAULT 'stored';
ALTER TABLE officer_documents ADD COLUMN IF NOT EXISTS processing_error TEXT;
ALTER TABLE officer_documents ADD COLUMN IF NOT EXISTS processing_progress JSONB;
ALTER TABLE officer_documents ADD COLUMN IF NOT EXISTS extracted_text TEXT;
ALTER TABLE officer_documents ADD COLUMN IF NOT EXISTS extraction JSONB;
ALTER TABLE officer_documents ADD COLUMN IF NOT EXISTS graph_payload JSONB;
ALTER TABLE officer_documents ADD COLUMN IF NOT EXISTS lease_until TIMESTAMPTZ;

-- Keep every extracted entity and assertion linked to its source document.
CREATE TABLE IF NOT EXISTS extracted_entities (
  entity_id VARCHAR(20) PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES officer_documents(document_id),
  kind TEXT NOT NULL,
  canonical_id TEXT NOT NULL,
  name TEXT NOT NULL,
  properties JSONB NOT NULL,
  evidence TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS extracted_entities_document_idx ON extracted_entities(document_id);
CREATE TABLE IF NOT EXISTS extracted_relationships (
  relationship_id VARCHAR(20) PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES officer_documents(document_id),
  subject_id VARCHAR(20) NOT NULL REFERENCES extracted_entities(entity_id),
  predicate TEXT NOT NULL CHECK (predicate IN
    ('MENTIONED_IN','WITNESS_IN','SUSPECT_IN','OCCURRED_AT','OF_TYPE','EMPLOYED_BY','OWNS','CONTACTED')),
  object_id VARCHAR(20) NOT NULL REFERENCES extracted_entities(entity_id),
  evidence TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS extracted_relationships_document_idx ON extracted_relationships(document_id);
-- Extend existing installations as well as new databases with explicit person/location roles.
ALTER TABLE extracted_relationships DROP CONSTRAINT IF EXISTS extracted_relationships_predicate_check;
ALTER TABLE extracted_relationships ADD CONSTRAINT extracted_relationships_predicate_check
  CHECK (predicate IN ('MENTIONED_IN','WITNESS_IN','SUSPECT_IN','OCCURRED_AT','OF_TYPE',
    'EMPLOYED_BY','OWNS','CONTACTED','RESIDES_IN','SEEN_AT'));
CREATE INDEX IF NOT EXISTS documents_processing_idx ON officer_documents(processing_status);
-- Do not invent a state when a report only names a city.
ALTER TABLE locations ALTER COLUMN state DROP NOT NULL;

-- Expose both legacy case links and the newly extracted, role-specific links.
CREATE OR REPLACE VIEW case_people AS
SELECT case_id, person_id, 'INVOLVED_IN'::text AS role FROM cases WHERE person_id IS NOT NULL
UNION
SELECT target.canonical_id::varchar(20), subject.canonical_id::varchar(20), r.predicate
FROM extracted_relationships r
JOIN extracted_entities subject ON subject.entity_id=r.subject_id AND subject.kind='Person'
JOIN extracted_entities target ON target.entity_id=r.object_id AND target.kind='Case'
WHERE r.predicate IN ('MENTIONED_IN','WITNESS_IN','SUSPECT_IN');

-- Confirmation applies to the exact staged extraction, before canonical/graph writes.
ALTER TABLE officer_documents ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;
ALTER TABLE officer_documents ADD COLUMN IF NOT EXISTS confirmed_by INTEGER REFERENCES officers(officer_id);
