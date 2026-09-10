// =====================================================
// EVIDENCE & EXTENDED RELATIONSHIP SCHEMA
// =====================================================


// =====================================================
// 1. CONSTRAINTS
// =====================================================

CREATE CONSTRAINT document_id_unique IF NOT EXISTS
FOR (d:Document)
REQUIRE d.document_id IS UNIQUE;

CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS
FOR (e:Evidence)
REQUIRE e.evidence_id IS UNIQUE;

CREATE CONSTRAINT organization_id_unique IF NOT EXISTS
FOR (o:Organization)
REQUIRE o.organization_id IS UNIQUE;


// =====================================================
// 2. SAMPLE DOCUMENT
// =====================================================

MERGE (d:Document {document_id: "DOC001"})
SET d.document_type = "FIR",
    d.title = "Sample FIR",
    d.source = "synthetic_demo";


// =====================================================
// 3. SAMPLE EVIDENCE
// =====================================================

MERGE (e:Evidence {evidence_id: "E001"})
SET e.evidence_type = "text_excerpt",
    e.text = "P001 was reported contacting P007.",
    e.source = "synthetic_demo";


// Evidence came from Document
MATCH (e:Evidence {evidence_id: "E001"})
MATCH (d:Document {document_id: "DOC001"})
MERGE (e)-[:FROM_DOCUMENT]->(d);


// =====================================================
// 4. SAMPLE ORGANIZATION
// =====================================================

MERGE (o:Organization {organization_id: "ORG001"})
SET o.name = "ABC Logistics",
    o.source = "synthetic_demo";


// =====================================================
// 5. MENTIONED_IN
// Person / Organization / Vehicle -> Case
// =====================================================

// Person mentioned in case
MATCH (p:Person {person_id: "P001"})
MATCH (c:Case {case_id: "C001"})
MERGE (p)-[r:MENTIONED_IN]->(c)
SET r.source = "synthetic_demo",
    r.review_status = "pending";


// Organization mentioned in case
MATCH (o:Organization {organization_id: "ORG001"})
MATCH (c:Case {case_id: "C001"})
MERGE (o)-[r:MENTIONED_IN]->(c)
SET r.source = "synthetic_demo",
    r.review_status = "pending";


// Vehicle mentioned in case
MATCH (v:Vehicle {vehicle_id: "V001"})
MATCH (c:Case {case_id: "C001"})
MERGE (v)-[r:MENTIONED_IN]->(c)
SET r.source = "synthetic_demo",
    r.review_status = "pending";


// =====================================================
// 6. EMPLOYED_BY
// Person -> Organization
// =====================================================

MATCH (p:Person {person_id: "P001"})
MATCH (o:Organization {organization_id: "ORG001"})
MERGE (p)-[r:EMPLOYED_BY]->(o)
SET r.source = "synthetic_demo",
    r.review_status = "pending";


// =====================================================
// 7. OWNS
// Person / Organization -> Vehicle
// =====================================================

// Person owns vehicle
MATCH (p:Person {person_id: "P001"})
MATCH (v:Vehicle {vehicle_id: "V001"})
MERGE (p)-[r:OWNS]->(v)
SET r.source = "synthetic_demo",
    r.review_status = "pending";


// Organization owns vehicle
MATCH (o:Organization {organization_id: "ORG001"})
MATCH (v:Vehicle {vehicle_id: "V001"})
MERGE (o)-[r:OWNS]->(v)
SET r.source = "synthetic_demo",
    r.review_status = "pending";


// =====================================================
// 8. CONTACTED
// Person -> Person
// =====================================================

MATCH (p1:Person {person_id: "P001"})
MATCH (p2:Person {person_id: "P007"})

MERGE (p1)-[r:CONTACTED]->(p2)

SET r.source = "verified_demo",
    r.review_status = "approved";