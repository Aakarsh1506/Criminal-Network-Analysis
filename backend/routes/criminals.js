import { Router } from "express";
import { pool } from "../db.js";
import { initialsAvatar, colorForId } from "../utils/avatar.js";
import { coordinatesForCity } from "../utils/mapCoordinates.js";

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

// Known associates, drawn from an optional `associations` table (see
// database/associations.sql). Returns [] gracefully if that table doesn't
// exist yet — the DB dump you gave me doesn't include one.
async function fetchAssociates(id) {
  try {
    const { rows } = await pool.query(
      `SELECT a.relation_type,
              p.person_id AS other_id, p.name AS other_name,
              p.alias AS other_alias, p.photo AS other_photo
       FROM associations a
       JOIN persons p
         ON p.person_id = (CASE WHEN a.person_id_a = $1 THEN a.person_id_b ELSE a.person_id_a END)
       WHERE a.person_id_a = $1 OR a.person_id_b = $1`,
      [id]
    );
    return rows.map((r) => ({
      criminal: {
        id: r.other_id,
        name: r.other_name,
        alias: r.other_alias,
        photo: r.other_photo || initialsAvatar(r.other_name, colorForId(r.other_id)),
      },
      type: r.relation_type,
    }));
  } catch (err) {
    if (err.code === "42P01") return []; // associations table not created yet
    throw err;
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

    if (q || tags.length) {
      results = results.filter((c) => {
        const nameMatch = q && (c.name.toLowerCase().includes(q) || (c.alias || "").toLowerCase().includes(q));
        const tagMatch = tags.length > 0 && c.crimeTags.some((tag) => tags.includes(tag.toLowerCase()));
        const queryAsTagMatch = q && c.crimeTags.some((tag) => tag.toLowerCase().includes(q));
        return nameMatch || tagMatch || queryAsTagMatch;
      });
    } else {
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
    const { rows } = await pool.query(personsQuery("WHERE p.person_id = $1", [id]));
    if (rows.length === 0) return res.status(404).json({ error: "Not found" });

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

    res.json({ criminal, relations });
  } catch (err) {
    console.error(`GET /api/criminals/${id} failed`, err);
    res.status(500).json({ error: "Failed to load criminal" });
  }
});

export default router;