// Guards a route with the JWT stored in the httpOnly cookie set by
// POST /api/auth/login. On success, attaches the decoded claims to
// req.officer for downstream handlers to use (e.g. scoping by org).

import { verifyOfficerToken } from "../utils/jwt.js";

const COOKIE_NAME = process.env.COOKIE_NAME || "cna_token";

export function requireAuth(req, res, next) {
  const token = req.cookies?.[COOKIE_NAME];

  if (!token) {
    return res.status(401).json({ error: "Not authenticated" });
  }

  try {
    req.officer = verifyOfficerToken(token);
    next();
  } catch {
    // Covers both an invalid signature and an expired token.
    res.clearCookie(COOKIE_NAME);
    return res.status(401).json({ error: "Session expired, please log in again" });
  }
}