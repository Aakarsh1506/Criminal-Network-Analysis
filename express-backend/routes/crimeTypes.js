import { Router } from "express";
import { pool } from "../db.js";

const router = Router();

// GET /api/crime-types — replaces the mock's hardcoded `presetTags`
router.get("/", async (req, res) => {
  try {
    const { rows } = await pool.query("SELECT crime_name FROM crime_types ORDER BY crime_name");
    res.json(rows.map((r) => r.crime_name));
  } catch (err) {
    console.error("GET /api/crime-types failed", err);
    res.status(500).json({ error: "Failed to load crime types" });
  }
});

export default router;