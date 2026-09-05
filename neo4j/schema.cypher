CREATE CONSTRAINT person_id_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.person_id IS UNIQUE;

CREATE CONSTRAINT case_id_unique IF NOT EXISTS
FOR (c:Case)
REQUIRE c.case_id IS UNIQUE;

CREATE CONSTRAINT crime_id_unique IF NOT EXISTS
FOR (c:CrimeType)
REQUIRE c.crime_id IS UNIQUE;

CREATE CONSTRAINT location_id_unique IF NOT EXISTS
FOR (l:Location)
REQUIRE l.location_id IS UNIQUE;