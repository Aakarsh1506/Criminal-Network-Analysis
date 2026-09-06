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
  secure: IS_PROD, // requires HTTPS in production; fine over plain HTTP in dev
  maxAge: 12 * 60 * 60 * 1000, // 12h — keep roughly in sync with JWT_EXPIRES_IN
};

// New accounts never get created here — only checked. New officers are added
// with `npm run add-officer` (backend/scripts/addOfficer.js).
router.post("/login", async (req, res) => {
  const { username, password } = req.body || {};

  if (!username || !password) {
    return res.status(400).json({ error: "Username and password are required" });
  }

  try {
    const { rows } = await pool.query(
      `SELECT officer_id, username, password_hash, name, org_name, role, is_active
       FROM officers WHERE username = $1`,
      [username]
    );
    const officer = rows[0];

    // Same generic error whether the username doesn't exist or the password
    // is wrong — don't let the response reveal which one it was.
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

// Lets the frontend check "am I still logged in?" on page load/refresh.
router.get("/me", requireAuth, (req, res) => {
  const { officerId, username, name, orgName, role } = req.officer;
  res.json({ officerId, username, name, orgName, role });
});

export default router;