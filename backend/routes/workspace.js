import { Router } from "express";
import { pool } from "../db.js";

const router = Router();

// Self-creating, same convention as the officers table in addOfficer.js —
// no manual migration step needed.
// person_id is VARCHAR to match persons.person_id (e.g. "P001").
async function ensureWorkspaceTables() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS officer_pinned_criminal (
      officer_id  INTEGER PRIMARY KEY REFERENCES officers(officer_id) ON DELETE CASCADE,
      person_id   VARCHAR(20) NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
      pinned_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    );
  `);
  await pool.query(`
    CREATE TABLE IF NOT EXISTS officer_working_list (
      officer_id  INTEGER NOT NULL REFERENCES officers(officer_id) ON DELETE CASCADE,
      person_id   VARCHAR(20) NOT NULL REFERENCES persons(person_id) ON DELETE CASCADE,
      added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (officer_id, person_id)
    );
  `);
}
ensureWorkspaceTables().catch((err) => console.error("Failed to ensure workspace tables", err));

// Joins against persons/cases/crime_types instead of storing a name+tags
// snapshot, so the list always reflects current data (unlike the old
// localStorage snapshot, which could go stale).
const LIST_ITEMS_SQL = `
  SELECT p.person_id, p.name,
         array_remove(array_agg(DISTINCT ct.crime_name), NULL) AS crime_tags
  FROM officer_working_list w
  JOIN persons p ON p.person_id = w.person_id
  LEFT JOIN cases c ON c.person_id = p.person_id
  LEFT JOIN crime_types ct ON ct.crime_id = c.crime_id
  WHERE w.officer_id = $1
  GROUP BY p.person_id, w.added_at
  ORDER BY w.added_at ASC
`;

// GET /api/workspace — this officer's pinned criminal + working list
router.get("/", async (req, res) => {
  try {
    const officerId = req.officer.officerId;
    const [{ rows: pinnedRows }, { rows: listRows }] = await Promise.all([
      pool.query(`SELECT person_id FROM officer_pinned_criminal WHERE officer_id = $1`, [officerId]),
      pool.query(LIST_ITEMS_SQL, [officerId]),
    ]);

    res.json({
      pinnedId: pinnedRows[0]?.person_id ?? null,
      workingList: listRows.map((r) => ({
        id: r.person_id,
        name: r.name,
        crimeTags: r.crime_tags ? r.crime_tags.filter(Boolean) : [],
      })),
    });
  } catch (err) {
    console.error("GET /api/workspace failed", err);
    res.status(500).json({ error: "Failed to load workspace" });
  }
});

// PUT /api/workspace/pin { personId } — pin replaces whatever this officer had pinned
router.put("/pin", async (req, res) => {
  const { personId } = req.body || {};
  if (!personId) return res.status(400).json({ error: "personId is required" });

  try {
    await pool.query(
      `INSERT INTO officer_pinned_criminal (officer_id, person_id, pinned_at)
       VALUES ($1, $2, now())
       ON CONFLICT (officer_id) DO UPDATE SET person_id = EXCLUDED.person_id, pinned_at = now()`,
      [req.officer.officerId, personId]
    );
    res.json({ pinnedId: personId });
  } catch (err) {
    console.error("PUT /api/workspace/pin failed", err);
    res.status(500).json({ error: "Failed to pin criminal" });
  }
});

// DELETE /api/workspace/pin — unpin for this officer
router.delete("/pin", async (req, res) => {
  try {
    await pool.query(`DELETE FROM officer_pinned_criminal WHERE officer_id = $1`, [req.officer.officerId]);
    res.json({ pinnedId: null });
  } catch (err) {
    console.error("DELETE /api/workspace/pin failed", err);
    res.status(500).json({ error: "Failed to unpin criminal" });
  }
});

// POST /api/workspace/list { personId } — add to this officer's working list
router.post("/list", async (req, res) => {
  const { personId } = req.body || {};
  if (!personId) return res.status(400).json({ error: "personId is required" });

  try {
    await pool.query(
      `INSERT INTO officer_working_list (officer_id, person_id)
       VALUES ($1, $2)
       ON CONFLICT (officer_id, person_id) DO NOTHING`,
      [req.officer.officerId, personId]
    );
    res.status(201).json({ ok: true });
  } catch (err) {
    console.error("POST /api/workspace/list failed", err);
    res.status(500).json({ error: "Failed to add to list" });
  }
});

// DELETE /api/workspace/list/:personId — remove from this officer's working list
router.delete("/list/:personId", async (req, res) => {
  try {
    await pool.query(
      `DELETE FROM officer_working_list WHERE officer_id = $1 AND person_id = $2`,
      [req.officer.officerId, req.params.personId]
    );
    res.json({ ok: true });
  } catch (err) {
    console.error("DELETE /api/workspace/list failed", err);
    res.status(500).json({ error: "Failed to remove from list" });
  }
});

export default router;