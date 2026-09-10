import { Router } from "express";
import { pool } from "../db.js";

const router = Router();

// GET /api/stats — dashboard summary numbers, computed straight from the DB
router.get("/", async (req, res) => {
  try {
    const [{ rows: totalRows }, { rows: tagRows }, { rows: cityRows }, { rows: caseRows }] = await Promise.all([
      pool.query("SELECT COUNT(*)::int AS count FROM persons"),
      pool.query(`
        SELECT ct.crime_name, COUNT(DISTINCT c.person_id)::int AS count
        FROM cases c JOIN crime_types ct ON ct.crime_id = c.crime_id
        GROUP BY ct.crime_name ORDER BY count DESC
      `),
      pool.query("SELECT city, COUNT(*)::int AS count FROM persons GROUP BY city ORDER BY count DESC"),
      pool.query("SELECT COUNT(*)::int AS count FROM cases"),
    ]);

    let tracedConnections = 0;
    try {
      const { rows } = await pool.query("SELECT COUNT(*)::int AS count FROM associations");
      tracedConnections = rows[0].count;
    } catch (err) {
      if (err.code !== "42P01") throw err; // ignore "table doesn't exist yet"
    }

    res.json({
      totalCriminals: totalRows[0].count,
      totalCases: caseRows[0].count,
      tracedConnections,
      tagCounts: tagRows.map((r) => [r.crime_name, r.count]),
      cityCounts: cityRows.map((r) => [r.city, r.count]),
    });
  } catch (err) {
    console.error("GET /api/stats failed", err);
    res.status(500).json({ error: "Failed to load stats" });
  }
});

export default router;