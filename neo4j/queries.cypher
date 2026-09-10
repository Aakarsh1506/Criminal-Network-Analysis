// =====================================================
// CHEATCODE - NEO4J ANALYSIS QUERIES
// =====================================================


// =====================================================
// QUERY 1: VIEW COMPLETE GRAPH
// =====================================================

MATCH (n)-[r]->(m)
RETURN n, r, m;


// =====================================================
// QUERY 2: PEOPLE CONNECTED THROUGH SAME LOCATION
// =====================================================

MATCH (p1:Person)-[:INVOLVED_IN]->(c1:Case)-[:OCCURRED_AT]->(l:Location)
MATCH (p2:Person)-[:INVOLVED_IN]->(c2:Case)-[:OCCURRED_AT]->(l)

WHERE p1.person_id < p2.person_id

RETURN DISTINCT
    p1.person_id AS Person1ID,
    p1.name AS Person1,
    p2.person_id AS Person2ID,
    p2.name AS Person2,
    l.city AS SharedLocation;


// =====================================================
// QUERY 3: SAME LOCATION + SAME CRIME TYPE
// =====================================================

MATCH (p1:Person)-[:INVOLVED_IN]->(c1:Case)
MATCH (p2:Person)-[:INVOLVED_IN]->(c2:Case)

MATCH (c1)-[:OCCURRED_AT]->(l:Location)
MATCH (c2)-[:OCCURRED_AT]->(l)

MATCH (c1)-[:OF_TYPE]->(crime:CrimeType)
MATCH (c2)-[:OF_TYPE]->(crime)

WHERE p1.person_id < p2.person_id

RETURN DISTINCT
    p1.person_id AS Person1ID,
    p1.name AS Person1,
    p2.person_id AS Person2ID,
    p2.name AS Person2,
    l.city AS SharedLocation,
    crime.crime_name AS SharedCrimeType;


// =====================================================
// QUERY 4: PEOPLE INVOLVED IN MULTIPLE CASES
// =====================================================

MATCH (p:Person)-[:INVOLVED_IN]->(c:Case)

WITH p, count(c) AS NumberOfCases

WHERE NumberOfCases > 1

RETURN
    p.person_id AS PersonID,
    p.name AS Person,
    NumberOfCases

ORDER BY NumberOfCases DESC;


// =====================================================
// QUERY 5: PEOPLE CONNECTED THROUGH SAME CRIME TYPE
// =====================================================

MATCH (p1:Person)-[:INVOLVED_IN]->(:Case)-[:OF_TYPE]->(crime:CrimeType)
MATCH (p2:Person)-[:INVOLVED_IN]->(:Case)-[:OF_TYPE]->(crime)

WHERE p1.person_id < p2.person_id

RETURN DISTINCT
    p1.person_id AS Person1ID,
    p1.name AS Person1,
    p2.person_id AS Person2ID,
    p2.name AS Person2,
    crime.crime_name AS SharedCrimeType;


// =====================================================
// QUERY 6: CONNECTION STRENGTH
// Shared crime types + shared locations
// =====================================================

MATCH (p1:Person)
MATCH (p2:Person)

WHERE p1.person_id < p2.person_id

OPTIONAL MATCH
    (p1)-[:INVOLVED_IN]->(:Case)-[:OF_TYPE]->(crime:CrimeType)
    <-[:OF_TYPE]-(:Case)<-[:INVOLVED_IN]-(p2)

WITH p1, p2,
     count(DISTINCT crime) AS SharedCrimeTypes

OPTIONAL MATCH
    (p1)-[:INVOLVED_IN]->(:Case)-[:OCCURRED_AT]->(loc:Location)
    <-[:OCCURRED_AT]-(:Case)<-[:INVOLVED_IN]-(p2)

WITH p1,
     p2,
     SharedCrimeTypes,
     count(DISTINCT loc) AS SharedLocations

WITH p1,
     p2,
     SharedCrimeTypes,
     SharedLocations,
     SharedCrimeTypes + SharedLocations AS ConnectionStrength

WHERE ConnectionStrength > 0

RETURN
    p1.person_id AS Person1ID,
    p1.name AS Person1,
    p2.person_id AS Person2ID,
    p2.name AS Person2,
    SharedCrimeTypes,
    SharedLocations,
    ConnectionStrength

ORDER BY ConnectionStrength DESC;


// =====================================================
// QUERY 7: TOP CONNECTED PEOPLE
// =====================================================

MATCH (p:Person)

OPTIONAL MATCH (p)-[r]-()

WITH p, count(r) AS TotalConnections

RETURN
    p.person_id AS PersonID,
    p.name AS Person,
    TotalConnections

ORDER BY TotalConnections DESC;


// =====================================================
// QUERY 8: SHORTEST PATH BETWEEN P001 AND P011
// =====================================================

MATCH (p1:Person {person_id: "P001"})
MATCH (p2:Person {person_id: "P011"})

MATCH path = shortestPath(
    (p1)-[*..6]-(p2)
)

RETURN path;


// =====================================================
// QUERY 9: CONNECTIONS TO A SELECTED PERSON
// Example: P001
// =====================================================

MATCH (p:Person {person_id: "P001"})-[r]-(connected)

RETURN
    p,
    r,
    connected;


// =====================================================
// QUERY 10: VIEW SYNTHETIC / DIRECT RELATIONSHIPS
// =====================================================

MATCH (p1:Person)-[r]-(p2:Person)

WHERE type(r) IN [
    "SEEN_WITH",
    "MET_WITH",
    "CO_INVOLVED_WITH",
    "CONTACTED"
]

RETURN DISTINCT
    p1,
    r,
    p2;


// =====================================================
// QUERY 11: PEOPLE ASSOCIATED WITH VEHICLES
// =====================================================

MATCH (p:Person)-[r:ASSOCIATED_WITH_VEHICLE]->(v:Vehicle)

RETURN
    p,
    r,
    v;


// =====================================================
// QUERY 12: PEOPLE ASSOCIATED WITH SAME VEHICLE
// =====================================================

MATCH (p1:Person)-[:ASSOCIATED_WITH_VEHICLE]->(v:Vehicle)
      <-[:ASSOCIATED_WITH_VEHICLE]-(p2:Person)

WHERE p1.person_id < p2.person_id

RETURN
    p1.person_id AS Person1ID,
    p1.name AS Person1,
    p2.person_id AS Person2ID,
    p2.name AS Person2,
    v.registration AS SharedVehicle;


// =====================================================
// QUERY 13: MENTIONED ENTITIES IN CASES
// =====================================================

MATCH (entity)-[r:MENTIONED_IN]->(c:Case)

WHERE entity:Person
   OR entity:Organization
   OR entity:Vehicle

RETURN
    labels(entity) AS EntityType,
    entity,
    r,
    c;


// =====================================================
// QUERY 14: PERSON -> ORGANIZATION EMPLOYMENT
// =====================================================

MATCH (p:Person)-[r:EMPLOYED_BY]->(o:Organization)

RETURN
    p,
    r,
    o;


// =====================================================
// QUERY 15: VEHICLE OWNERSHIP
// Person or Organization -> Vehicle
// =====================================================

MATCH (owner)-[r:OWNS]->(v:Vehicle)

WHERE owner:Person
   OR owner:Organization

RETURN
    owner,
    r,
    v;


// =====================================================
// QUERY 16: CONTACTED RELATIONSHIPS
// =====================================================

MATCH (p1:Person)-[r:CONTACTED]->(p2:Person)

RETURN
    p1.person_id AS FromPersonID,
    p1.name AS FromPerson,
    p2.person_id AS ToPersonID,
    p2.name AS ToPerson,
    r.source AS Source,
    r.review_status AS ReviewStatus;


// =====================================================
// QUERY 17: EVIDENCE AND SOURCE DOCUMENT
// =====================================================

MATCH (e:Evidence)-[r:FROM_DOCUMENT]->(d:Document)

RETURN
    e,
    r,
    d;


// =====================================================
// QUERY 18: STRICT MULTI-FACTOR CONNECTION ANALYSIS
// Creates / updates POTENTIAL_LINK relationships
//
// Weak contextual signals:
// Same crime type       = +1
// Same location         = +1
// Activity within 30d   = +1
//
// Strong signals:
// Same exact case       = +6
// Same vehicle          = +4
// Seen together         = +5
// Met together          = +5
// Co-involved           = +6
// Contacted             = +5
//
// IMPORTANT:
// POTENTIAL_LINK is created ONLY when at least
// one strong signal exists.
// =====================================================

MATCH (p1:Person)
MATCH (p2:Person)

WHERE p1.person_id < p2.person_id

WITH p1, p2,

EXISTS {
    MATCH (p1)-[:INVOLVED_IN]->(c:Case)
          <-[:INVOLVED_IN]-(p2)
} AS sameCase,

EXISTS {
    MATCH (p1)-[:INVOLVED_IN]->(:Case)-[:OF_TYPE]->(crime:CrimeType)
          <-[:OF_TYPE]-(:Case)<-[:INVOLVED_IN]-(p2)
} AS sameCrime,

EXISTS {
    MATCH (p1)-[:INVOLVED_IN]->(:Case)-[:OCCURRED_AT]->(loc:Location)
          <-[:OCCURRED_AT]-(:Case)<-[:INVOLVED_IN]-(p2)
} AS sameLocation,

EXISTS {
    MATCH (p1)-[:INVOLVED_IN]->(c1:Case)
    MATCH (p2)-[:INVOLVED_IN]->(c2:Case)

    WHERE abs(
        duration.inDays(
            c1.case_month,
            c2.case_month
        ).days
    ) <= 30
} AS closeTime,

EXISTS {
    MATCH (p1)-[:ASSOCIATED_WITH_VEHICLE]->(v:Vehicle)
          <-[:ASSOCIATED_WITH_VEHICLE]-(p2)
} AS sameVehicle,

EXISTS {
    MATCH (p1)-[:SEEN_WITH]-(p2)
} AS seenTogether,

EXISTS {
    MATCH (p1)-[:MET_WITH]-(p2)
} AS metTogether,

EXISTS {
    MATCH (p1)-[:CO_INVOLVED_WITH]-(p2)
} AS coInvolved,

EXISTS {
    MATCH (p1)-[:CONTACTED]-(p2)
} AS contacted


WITH
    p1,
    p2,
    sameCase,
    sameCrime,
    sameLocation,
    closeTime,
    sameVehicle,
    seenTogether,
    metTogether,
    coInvolved,
    contacted,

    CASE WHEN sameCrime THEN 1 ELSE 0 END +
    CASE WHEN sameLocation THEN 1 ELSE 0 END +
    CASE WHEN closeTime THEN 1 ELSE 0 END +
    CASE WHEN sameCase THEN 6 ELSE 0 END +
    CASE WHEN sameVehicle THEN 4 ELSE 0 END +
    CASE WHEN seenTogether THEN 5 ELSE 0 END +
    CASE WHEN metTogether THEN 5 ELSE 0 END +
    CASE WHEN coInvolved THEN 6 ELSE 0 END +
    CASE WHEN contacted THEN 5 ELSE 0 END
    AS connectionScore


WHERE
    sameCase = true
    OR sameVehicle = true
    OR seenTogether = true
    OR metTogether = true
    OR coInvolved = true
    OR contacted = true


WITH
    p1,
    p2,
    connectionScore,

    [
        x IN [
            CASE
                WHEN sameCase
                THEN "Involved in same case"
            END,

            CASE
                WHEN sameVehicle
                THEN "Associated with same vehicle"
            END,

            CASE
                WHEN seenTogether
                THEN "Seen together"
            END,

            CASE
                WHEN metTogether
                THEN "Reported meeting"
            END,

            CASE
                WHEN coInvolved
                THEN "Co-involved in incident"
            END,

            CASE
                WHEN contacted
                THEN "Confirmed contact"
            END,

            CASE
                WHEN sameCrime
                THEN "Same crime type"
            END,

            CASE
                WHEN sameLocation
                THEN "Same location"
            END,

            CASE
                WHEN closeTime
                THEN "Activity within 30 days"
            END
        ]

        WHERE x IS NOT NULL

    ] AS reasons


MERGE (p1)-[r:POTENTIAL_LINK]->(p2)

SET
    r.score = connectionScore,
    r.reasons = reasons,
    r.generated_by = "rule_based_analysis",
    r.updated_at = datetime()


RETURN
    p1.person_id AS Person1ID,
    p1.name AS Person1,
    p2.person_id AS Person2ID,
    p2.name AS Person2,
    connectionScore,
    reasons

ORDER BY connectionScore DESC;


// =====================================================
// QUERY 19: VIEW ALL POTENTIAL LINKS
// =====================================================

MATCH (p1:Person)-[r:POTENTIAL_LINK]->(p2:Person)

RETURN
    p1,
    r,
    p2

ORDER BY r.score DESC;


// =====================================================
// QUERY 20: VIEW STRONG POTENTIAL LINKS
// Score >= 5
// =====================================================

MATCH (p1:Person)-[r:POTENTIAL_LINK]->(p2:Person)

WHERE r.score >= 5

RETURN
    p1,
    r,
    p2

ORDER BY r.score DESC;


// =====================================================
// QUERY 21: POTENTIAL LINK DETAILS
// Useful for backend / frontend
// =====================================================

MATCH (p1:Person)-[r:POTENTIAL_LINK]->(p2:Person)

RETURN
    p1.person_id AS Person1ID,
    p1.name AS Person1,
    p2.person_id AS Person2ID,
    p2.name AS Person2,
    r.score AS ConnectionScore,
    r.reasons AS Reasons,
    r.generated_by AS GeneratedBy,
    r.updated_at AS UpdatedAt

ORDER BY ConnectionScore DESC;