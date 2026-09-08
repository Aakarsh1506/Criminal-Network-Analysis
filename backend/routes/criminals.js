import { Router } from "express";
import { pool } from "../db.js";
import { runCypher } from "../neo4jDriver.js";
import { initialsAvatar, colorForId } from "../utils/avatar.js";
import { coordinatesForCity } from "../utils/mapCoordinates.js";

import { explainNetwork, AIError } from "../services/groq.js";
import { fetchNetwork } from "../services/network.js";

const router = Router();

function personsQuery(whereClause = "", params = []) {
  return {
    text: `
      SELECT p.*,
             array_remove(array_agg(DISTINCT ct.crime_name), NULL) AS crime_tags
      FROM persons p
      LEFT JOIN cases c ON c.person_id = p.person_id
      LEFT JOIN crime_types ct ON ct.crime_id = c.crime_id
      ${whereClause}
      GROUP BY p.person_id
    `,
    values: params,
  };
}

const CASES_SQL = `
  SELECT c.case_id, c.case_month, c.case_status, l.city, l.state, ct.crime_name
  FROM cases c
  LEFT JOIN crime_types ct ON ct.crime_id = c.crime_id
  LEFT JOIN locations l ON l.location_id = c.location_id
  WHERE c.person_id = $1
  ORDER BY c.case_month DESC
`;

// Shapes one `persons` row (+ aggregated crime tags) into the object shape
// the frontend expects — mirrors the old mock in src/data/criminals.js.
function mapPerson(row) {
  return {
    id: row.person_id,
    name: row.name,
    alias: row.alias,
    dob: row.dob ? new Date(row.dob).toISOString().slice(0, 10) : null,
    age: row.age,
    heightCm: row.height_cm,
    location: { city: row.city, state: row.state, ...coordinatesForCity(row.city) },
    lastSeen: row.last_seen
      ? `${row.city} — ${new Date(row.last_seen).toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        })}`
      : row.city,
    familyKnown: row.family_known,
    recordStatus: row.record_status,
    crimeTags: row.crime_tags ? row.crime_tags.filter(Boolean) : [],
    photo: row.photo || initialsAvatar(row.name, colorForId(row.person_id)),
  };
}

// Known associates, computed from the Neo4j graph instead of an explicit
// Postgres associations table. Two people are "related" if they share a
// case's location or crime type. Falls back to [] on any Neo4j error so
// the profile page still renders if the graph DB is unreachable.
async function fetchAssociates(id) {
  try {
    const records = await runCypher(
      `
      MATCH (p1:Person {person_id: $id})-[:INVOLVED_IN]->(c1:Case)
      MATCH (p2:Person)-[:INVOLVED_IN]->(c2:Case)
      WHERE p1 <> p2
      OPTIONAL MATCH (c1)-[:OCCURRED_AT]->(l:Location)<-[:OCCURRED_AT]-(c2)
      OPTIONAL MATCH (c1)-[:OF_TYPE]->(crime:CrimeType)<-[:OF_TYPE]-(c2)
      WITH p2, l, crime
      WHERE l IS NOT NULL OR crime IS NOT NULL
      RETURN DISTINCT
        p2.person_id AS other_id,
        p2.name AS other_name,
        p2.alias AS other_alias,
        p2.city AS other_city,
        p2.state AS other_state,
        l.city AS shared_location,
        crime.crime_name AS shared_crime
      LIMIT 25
      `,
      { id }
    );

    return records.map((r) => ({
      criminal: {
        id: r.other_id,
        name: r.other_name,
        alias: r.other_alias,
        location: { city: r.other_city, state: r.other_state },
        photo: initialsAvatar(r.other_name, colorForId(r.other_id)),
      },
      type: r.shared_crime
        ? `Shared Crime: ${r.shared_crime}`
        : `Shared Location: ${r.shared_location}`,
    }));
  } catch (err) {
    console.error(`Neo4j lookup failed for ${id}`, err);
    return [];
  }
}

// GET /api/criminals?q=&tags=fraud,robbery
router.get("/", async (req, res) => {
  try {
    const { rows } = await pool.query(personsQuery());
    let results = rows.map(mapPerson);

    const q = (req.query.q || "").toLowerCase().trim();
    const tags = (req.query.tags || "")
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);
    const wantsAll = req.query.all === "true";

    if (q || tags.length) {
      results = results.filter((c) => {
        const nameMatch = q && (c.name.toLowerCase().includes(q) || (c.alias || "").toLowerCase().includes(q));
        const tagMatch = tags.length > 0 && c.crimeTags.some((tag) => tags.includes(tag.toLowerCase()));
        const queryAsTagMatch = q && c.crimeTags.some((tag) => tag.toLowerCase().includes(q));
        return nameMatch || tagMatch || queryAsTagMatch;
      });
    } else if (!wantsAll) {
      results = []; // matches old UI behaviour: no query/tags => no results shown
    }

    res.json(results);
  } catch (err) {
    console.error("GET /api/criminals failed", err);
    res.status(500).json({ error: "Failed to load criminals" });
  }
});

// GET /api/criminals/:id — profile + case history + known associates
router.get("/:id", async (req, res) => {
  const { id } = req.params;
  try {
    const profile = await loadProfile(id);
    if (!profile) return res.status(404).json({ error: "Not found" });
    res.json(profile);
  } catch (err) {
    console.error(`GET /api/criminals/${id} failed`, err);
    res.status(500).json({ error: "Failed to load criminal" });
  }
});

// GET /api/criminals/:id/network — recorded relationships within two hops
router.get("/:id/network", async (req, res) => {
  const { id } = req.params;
  try {
    const network = await fetchNetwork(id, runCypher);
    if (!network) return res.status(404).json({ error: "Network not found for this person" });
    res.json(network);
  } catch (err) {
    console.error(`GET /api/criminals/${id}/network failed`, err);
    res.status(500).json({ error: "Failed to load criminal network" });
  }
});

async function loadProfile(id) {
    const { rows } = await pool.query(personsQuery("WHERE p.person_id = $1", [id]));
    if (rows.length === 0) return null;

    const criminal = mapPerson(rows[0]);
    const [{ rows: caseRows }, relations] = await Promise.all([
      pool.query(CASES_SQL, [id]),
      fetchAssociates(id),
    ]);

    criminal.cases = caseRows.map((c) => ({
      caseId: c.case_id,
      crime: c.crime_name,
      location: c.city ? `${c.city}, ${c.state}` : null,
      status: c.case_status,
      month: c.case_month ? new Date(c.case_month).toISOString().slice(0, 10) : null,
    }));

    return { criminal, relations };
}

let activeExplanations = 0;
router.post("/:id/explain", async (req, res) => {
  if (!process.env.GROQ_API_KEY?.trim()) {
    return res.status(503).json({ error: "AI is not configured. Add GROQ_API_KEY to backend/.env and restart the server." });
  }
  if (activeExplanations >= 3) {
    return res.status(429).json({ error: "AI is busy. Please try again shortly." });
  }
  activeExplanations++;
  try {
    const profile = await loadProfile(req.params.id);
    if (!profile) return res.status(404).json({ error: "Profile not found." });
    const explanation = await explainNetwork(profile);
    res.json({ explanation });
  } catch (err) {
    res.status(err instanceof AIError ? err.status : 500).json({
      error: err instanceof AIError ? err.message : "Unable to load records for the AI summary. Please try again.",
    });
  } finally {
    activeExplanations--;
  }
});

export default router;
