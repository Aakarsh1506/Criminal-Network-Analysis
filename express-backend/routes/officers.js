import { Router } from "express";
import bcrypt from "bcrypt";
import { pool } from "../db.js";

const router = Router();

// GET /api/officers — list accounts for the admin panel table
router.get("/", async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT officer_id, username, name, dob, org_name, role, is_active, created_at
       FROM officers ORDER BY created_at DESC`
    );
    res.json(rows);
  } catch (err) {
    console.error("GET /api/officers failed", err);
    res.status(500).json({ error: "Failed to load officers" });
  }
});

// POST /api/officers — create a new officer account.
// Role is always "officer" here — the only "admin" account is the
// hardcoded one in .env, this endpoint can't mint more of them.
router.post("/", async (req, res) => {
  const { username, password, name, dob, orgName } = req.body || {};

  const missing = ["username", "password", "name", "orgName"].filter((k) => !req.body?.[k]);
  if (missing.length) {
    return res.status(400).json({ error: `Missing required field(s): ${missing.join(", ")}` });
  }
  if (password.length < 8) {
    return res.status(400).json({ error: "Password must be at least 8 characters" });
  }

  try {
    const passwordHash = await bcrypt.hash(password, 12);
    const { rows } = await pool.query(
      `INSERT INTO officers (username, password_hash, name, dob, org_name, role)
       VALUES ($1, $2, $3, $4, $5, 'officer')
       RETURNING officer_id, username, name, dob, org_name, role, is_active, created_at`,
      [username, passwordHash, name, dob || null, orgName]
    );
    res.status(201).json(rows[0]);
  } catch (err) {
    if (err.code === "23505") {
      return res.status(409).json({ error: `Username "${username}" already exists` });
    }
    console.error("POST /api/officers failed", err);
    res.status(500).json({ error: "Failed to create officer" });
  }
});

// PATCH /api/officers/:id/deactivate — soft-delete (is_active = false)
// instead of removing the row, so history/audit trail is preserved.
router.patch("/:id/deactivate", async (req, res) => {
  try {
    const { rows } = await pool.query(
      `UPDATE officers SET is_active = FALSE WHERE officer_id = $1
       RETURNING officer_id, username, is_active`,
      [req.params.id]
    );
    if (!rows[0]) return res.status(404).json({ error: "Officer not found" });
    res.json(rows[0]);
  } catch (err) {
    console.error("PATCH /api/officers/:id/deactivate failed", err);
    res.status(500).json({ error: "Failed to deactivate officer" });
  }
});

export default router;