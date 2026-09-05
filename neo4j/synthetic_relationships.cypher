// =====================================================
// SYNTHETIC DEMO RELATIONSHIPS
// For prototype/testing purposes only
// =====================================================

// -----------------------------------------------------
// 1. CO-INVOLVED IN SAME CASE
// -----------------------------------------------------

MATCH (p1:Person {person_id: "P001"})
MATCH (p2:Person {person_id: "P007"})
MERGE (p1)-[r:CO_INVOLVED_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.reason = "Involved together in the same criminal incident",
    r.confidence = 0.95;

MATCH (p1:Person {person_id: "P003"})
MATCH (p2:Person {person_id: "P011"})
MERGE (p1)-[r:CO_INVOLVED_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.reason = "Associated with the same case activity",
    r.confidence = 0.92;

MATCH (p1:Person {person_id: "P014"})
MATCH (p2:Person {person_id: "P021"})
MERGE (p1)-[r:CO_INVOLVED_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.reason = "Both linked to the same incident",
    r.confidence = 0.90;


// -----------------------------------------------------
// 2. SEEN TOGETHER
// -----------------------------------------------------

MATCH (p1:Person {person_id: "P002"})
MATCH (p2:Person {person_id: "P009"})
MERGE (p1)-[r:SEEN_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.reason = "Reported together near a case location",
    r.confidence = 0.84;

MATCH (p1:Person {person_id: "P006"})
MATCH (p2:Person {person_id: "P018"})
MERGE (p1)-[r:SEEN_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.reason = "Seen together during investigation timeline",
    r.confidence = 0.81;

MATCH (p1:Person {person_id: "P020"})
MATCH (p2:Person {person_id: "P027"})
MERGE (p1)-[r:SEEN_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.reason = "Observed at the same place and time",
    r.confidence = 0.88;


// -----------------------------------------------------
// 3. SHARED VEHICLE
// -----------------------------------------------------

MATCH (p1:Person {person_id: "P004"})
MATCH (p2:Person {person_id: "P012"})
MERGE (p1)-[r:SHARED_VEHICLE_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.vehicle = "MH01AB4821",
    r.reason = "Both linked to the same vehicle",
    r.confidence = 0.93;

MATCH (p1:Person {person_id: "P008"})
MATCH (p2:Person {person_id: "P017"})
MERGE (p1)-[r:SHARED_VEHICLE_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.vehicle = "DL03CP7412",
    r.reason = "Same vehicle referenced in investigation records",
    r.confidence = 0.89;

MATCH (p1:Person {person_id: "P025"})
MATCH (p2:Person {person_id: "P031"})
MERGE (p1)-[r:SHARED_VEHICLE_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.vehicle = "GJ05KL2219",
    r.reason = "Both associated with the same vehicle",
    r.confidence = 0.91;


// -----------------------------------------------------
// 4. REPEATED ASSOCIATION / MEETING
// -----------------------------------------------------

MATCH (p1:Person {person_id: "P005"})
MATCH (p2:Person {person_id: "P013"})
MERGE (p1)-[r:MET_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.reason = "Reported meeting during the investigation period",
    r.confidence = 0.87;

MATCH (p1:Person {person_id: "P013"})
MATCH (p2:Person {person_id: "P022"})
MERGE (p1)-[r:MET_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.reason = "Possible meeting identified in case context",
    r.confidence = 0.80;

MATCH (p1:Person {person_id: "P005"})
MATCH (p2:Person {person_id: "P022"})
MERGE (p1)-[r:SEEN_WITH]->(p2)
SET r.source = "synthetic_demo",
    r.reason = "Observed together at a common location",
    r.confidence = 0.83;


// -----------------------------------------------------
// 5. VIEW ALL SYNTHETIC RELATIONSHIPS
// -----------------------------------------------------

MATCH (p1:Person)-[r]->(p2:Person)
WHERE r.source = "synthetic_demo"
RETURN p1, r, p2;


// =====================================================
// VEHICLE NODES
// =====================================================

MERGE (v1:Vehicle {
    vehicle_id: "V001"
})
SET v1.registration = "MH01AB4821",
    v1.type = "SUV",
    v1.source = "synthetic_demo";

MERGE (v2:Vehicle {
    vehicle_id: "V002"
})
SET v2.registration = "DL03CP7412",
    v2.type = "Sedan",
    v2.source = "synthetic_demo";

MERGE (v3:Vehicle {
    vehicle_id: "V003"
})
SET v3.registration = "GJ05KL2219",
    v3.type = "Hatchback",
    v3.source = "synthetic_demo";


// P004 and P012 linked to same vehicle
MATCH (p1:Person {person_id: "P004"})
MATCH (p2:Person {person_id: "P012"})
MATCH (v:Vehicle {vehicle_id: "V001"})

MERGE (p1)-[:ASSOCIATED_WITH_VEHICLE {
    source: "synthetic_demo"
}]->(v)

MERGE (p2)-[:ASSOCIATED_WITH_VEHICLE {
    source: "synthetic_demo"
}]->(v);


// P008 and P017 linked to same vehicle
MATCH (p1:Person {person_id: "P008"})
MATCH (p2:Person {person_id: "P017"})
MATCH (v:Vehicle {vehicle_id: "V002"})

MERGE (p1)-[:ASSOCIATED_WITH_VEHICLE {
    source: "synthetic_demo"
}]->(v)

MERGE (p2)-[:ASSOCIATED_WITH_VEHICLE {
    source: "synthetic_demo"
}]->(v);


// P025 and P031 linked to same vehicle
MATCH (p1:Person {person_id: "P025"})
MATCH (p2:Person {person_id: "P031"})
MATCH (v:Vehicle {vehicle_id: "V003"})

MERGE (p1)-[:ASSOCIATED_WITH_VEHICLE {
    source: "synthetic_demo"
}]->(v)

MERGE (p2)-[:ASSOCIATED_WITH_VEHICLE {
    source: "synthetic_demo"
}]->(v);