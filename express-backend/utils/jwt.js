// Small wrapper around jsonwebtoken so the secret/expiry are read from env
// in exactly one place.

import jwt from "jsonwebtoken";
import dotenv from "dotenv";
import { fileURLToPath } from "node:url";

dotenv.config({ path: fileURLToPath(new URL("../.env", import.meta.url)) });

const SECRET = process.env.JWT_SECRET;
const EXPIRES_IN = process.env.JWT_EXPIRES_IN || "12h";

if (!SECRET) {
  // Fail loudly at boot rather than silently signing tokens with `undefined`.
  throw new Error("JWT_SECRET is not set — add it to backend/.env");
}

// payload should be the small, non-secret set of claims we want on every
// request: officer id, username, org, role. Never put the password hash here.
export function signOfficerToken(payload) {
  return jwt.sign(payload, SECRET, { expiresIn: EXPIRES_IN });
}

export function verifyOfficerToken(token) {
  return jwt.verify(token, SECRET); // throws if invalid/expired
}