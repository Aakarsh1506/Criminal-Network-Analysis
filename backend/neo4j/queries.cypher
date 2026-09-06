// =====================================================
// CRIMINAL NETWORK ANALYSIS QUERIES
// =====================================================

// 1. VIEW COMPLETE GRAPH
MATCH (n)-[r]->(m)
RETURN n, r, m;

// 2. FIND PEOPLE CONNECTED THROUGH THE SAME LOCATION

MATCH (p1:Person)-[:INVOLVED_IN]->(:Case)-[:OCCURRED_AT]->(l:Location)
      <-[:OCCURRED_AT]-(:Case)<-[:INVOLVED_IN]-(p2:Person)

WHERE p1.person_id < p2.person_id

RETURN p1.name AS Person1,
       p2.name AS Person2,
       l.city AS SharedLocation
ORDER BY l.city;


// 3. FIND PEOPLE WITH SAME LOCATION + SAME CRIME TYPE

MATCH (p1:Person)-[:INVOLVED_IN]->(c1:Case)
      -[:OCCURRED_AT]->(l:Location)

MATCH (p2:Person)-[:INVOLVED_IN]->(c2:Case)
      -[:OCCURRED_AT]->(l)

MATCH (c1)-[:OF_TYPE]->(crime:CrimeType)
MATCH (c2)-[:OF_TYPE]->(crime)

WHERE p1.person_id < p2.person_id

RETURN DISTINCT
       p1.name AS Person1,
       p2.name AS Person2,
       l.city AS SharedLocation,
       crime.crime_name AS SharedCrimeType
ORDER BY SharedLocation, SharedCrimeType;

// 4. FIND PEOPLE INVOLVED IN MULTIPLE CASES

MATCH (p:Person)-[:INVOLVED_IN]->(c:Case)

WITH p, count(c) AS NumberOfCases

WHERE NumberOfCases > 1

RETURN p.person_id AS PersonID,
       p.name AS PersonName,
       NumberOfCases
ORDER BY NumberOfCases DESC;

// 5. FIND PEOPLE CONNECTED THROUGH THE SAME CRIME TYPE

MATCH (p1:Person)-[:INVOLVED_IN]->(:Case)-[:OF_TYPE]->(crime:CrimeType)
      <-[:OF_TYPE]-(:Case)<-[:INVOLVED_IN]-(p2:Person)

WHERE p1.person_id < p2.person_id

RETURN DISTINCT
       p1.name AS Person1,
       p2.name AS Person2,
       crime.crime_name AS SharedCrimeType
ORDER BY SharedCrimeType, Person1, Person2;

// 6. CONNECTION STRENGTH BASED ON SHARED PATTERNS

MATCH (p1:Person)-[:INVOLVED_IN]->(c1:Case)
MATCH (p2:Person)-[:INVOLVED_IN]->(c2:Case)

WHERE p1.person_id < p2.person_id

OPTIONAL MATCH (c1)-[:OF_TYPE]->(crime:CrimeType)<-[:OF_TYPE]-(c2)
OPTIONAL MATCH (c1)-[:OCCURRED_AT]->(loc:Location)<-[:OCCURRED_AT]-(c2)

WITH p1, p2,
     count(DISTINCT crime) AS SharedCrimeTypes,
     count(DISTINCT loc) AS SharedLocations

WITH p1, p2,
     SharedCrimeTypes,
     SharedLocations,
     SharedCrimeTypes + SharedLocations AS ConnectionStrength

WHERE ConnectionStrength > 0

RETURN
    p1.name AS Person1,
    p2.name AS Person2,
    SharedCrimeTypes,
    SharedLocations,
    ConnectionStrength

ORDER BY ConnectionStrength DESC, Person1, Person2;

// 7. TOP CONNECTED PEOPLE BASED ON SHARED PATTERNS

MATCH (p1:Person)-[:INVOLVED_IN]->(c1:Case)
MATCH (p2:Person)-[:INVOLVED_IN]->(c2:Case)

WHERE p1.person_id < p2.person_id

OPTIONAL MATCH (c1)-[:OF_TYPE]->(crime:CrimeType)<-[:OF_TYPE]-(c2)
OPTIONAL MATCH (c1)-[:OCCURRED_AT]->(loc:Location)<-[:OCCURRED_AT]-(c2)

WITH p1, p2,
     count(DISTINCT crime) AS SharedCrimeTypes,
     count(DISTINCT loc) AS SharedLocations

WITH p1, p2,
     SharedCrimeTypes + SharedLocations AS ConnectionStrength

WHERE ConnectionStrength > 0

UNWIND [
    {person: p1, score: ConnectionStrength},
    {person: p2, score: ConnectionStrength}
] AS x

WITH x.person AS person,
     sum(x.score) AS TotalConnectionScore,
     count(*) AS ConnectedPeopleCount

RETURN
    person.person_id AS PersonID,
    person.name AS PersonName,
    ConnectedPeopleCount,
    TotalConnectionScore

ORDER BY TotalConnectionScore DESC
LIMIT 10;

// 8. SHORTEST CONNECTION PATH BETWEEN TWO PEOPLE

MATCH (p1:Person {person_id: "P001"})
MATCH (p2:Person {person_id: "P011"})

MATCH path = shortestPath(
    (p1)-[*..6]-(p2)
)

RETURN path;

// 9. FIND PEOPLE CONNECTED TO A SELECTED PERSON

MATCH (selected:Person {person_id: "P001"})
MATCH (selected)-[:INVOLVED_IN]->(c1:Case)

MATCH (other:Person)-[:INVOLVED_IN]->(c2:Case)

WHERE other.person_id <> selected.person_id

OPTIONAL MATCH (c1)-[:OF_TYPE]->(crime:CrimeType)<-[:OF_TYPE]-(c2)
OPTIONAL MATCH (c1)-[:OCCURRED_AT]->(loc:Location)<-[:OCCURRED_AT]-(c2)

WITH selected, other,
     count(DISTINCT crime) AS SharedCrimeTypes,
     count(DISTINCT loc) AS SharedLocations

WHERE SharedCrimeTypes > 0 OR SharedLocations > 0

RETURN DISTINCT
       selected.name AS SelectedPerson,
       other.person_id AS ConnectedPersonID,
       other.name AS ConnectedPerson,
       SharedCrimeTypes,
       SharedLocations,
       SharedCrimeTypes + SharedLocations AS ConnectionStrength

ORDER BY ConnectionStrength DESC;