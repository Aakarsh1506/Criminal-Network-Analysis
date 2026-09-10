import { Router } from "express";
import bcrypt from "bcrypt";
import { pool } from "../db.js";
import { signOfficerToken } from "../utils/jwt.js";
import { requireAuth } from "../middleware/requireAuth.js";

const router = Router();

const COOKIE_NAME = process.env.COOKIE_NAME || "cna_token";
const IS_PROD = process.env.NODE_ENV === "production";

const COOKIE_OPTIONS = {
  httpOnly: true,
  sameSite: "lax",
  secure: IS_PROD,
  maxAge: 12 * 60 * 60 * 1000,
};

// New officer accounts never get created here — only checked. They're added
// either via `npm run add-officer` or, now, via the admin panel (POST /api/officers).
router.post("/login", async (req, res) => {
  const { username, password } = req.body || {};

  if (!username || !password) {
    return res.status(400).json({ error: "Username and password are required" });
  }

  // Single hardcoded admin account, read from env — not a row in `officers`.
  // Checked first, and only ever matches on the exact env credentials.
  const ADMIN_USERNAME = process.env.ADMIN_USERNAME;
  const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD;
  if (ADMIN_USERNAME && ADMIN_PASSWORD && username === ADMIN_USERNAME && password === ADMIN_PASSWORD) {
    const adminProfile = {
      officerId: null,
      username: ADMIN_USERNAME,
      name: "Administrator",
      orgName: "System",
      role: "admin",
    };
    const token = signOfficerToken(adminProfile);
    res.cookie(COOKIE_NAME, token, COOKIE_OPTIONS);
    return res.json(adminProfile);
  }

  try {
    const { rows } = await pool.query(
      `SELECT officer_id, username, password_hash, name, org_name, role, is_active
       FROM officers WHERE username = $1`,
      [username]
    );
    const officer = rows[0];

    if (!officer || !officer.is_active) {
      return res.status(401).json({ error: "Invalid credentials" });
    }

    const passwordOk = await bcrypt.compare(password, officer.password_hash);
    if (!passwordOk) {
      return res.status(401).json({ error: "Invalid credentials" });
    }

    const token = signOfficerToken({
      officerId: officer.officer_id,
      username: officer.username,
      name: officer.name,
      orgName: officer.org_name,
      role: officer.role,
    });

    res.cookie(COOKIE_NAME, token, COOKIE_OPTIONS);
    res.json({
      officerId: officer.officer_id,
      username: officer.username,
      name: officer.name,
      orgName: officer.org_name,
      role: officer.role,
    });
  } catch (err) {
    console.error("Login error:", err);
    res.status(500).json({ error: "Login failed" });
  }
});

router.post("/logout", (req, res) => {
  res.clearCookie(COOKIE_NAME);
  res.json({ ok: true });
});

router.get("/me", requireAuth, (req, res) => {
  const { officerId, username, name, orgName, role } = req.officer;
  res.json({ officerId, username, name, orgName, role });
});

export default router;