// Run this locally whenever you need to add a new officer account.
// There is no signup page and no API route that creates accounts — this
// script is the only way in, and it only works if you have the DB
// credentials in backend/.env.
//
// Usage:
//   npm run add-officer -- --username jdoe --password "S0meStrongPass!" \
//     --name "Jane Doe" --org "Delhi Police" --dob 1990-05-14 --role officer
//
// --dob and --role are optional (role defaults to "officer").

import bcrypt from "bcrypt";
import { pool } from "../db.js";

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const next = argv[i + 1];
      args[key] = next && !next.startsWith("--") ? next : true;
      if (args[key] !== true) i += 1;
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const { username, password, name, org, dob, role = "officer" } = args;

  const missing = ["username", "password", "name", "org"].filter((k) => !args[k]);
  if (missing.length) {
    console.error(`Missing required argument(s): ${missing.join(", ")}`);
    console.error(
      'Example: npm run add-officer -- --username jdoe --password "S0meStrongPass!" --name "Jane Doe" --org "Delhi Police"'
    );
    process.exit(1);
  }

  if (password.length < 8) {
    console.error("Password must be at least 8 characters.");
    process.exit(1);
  }

  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS officers (
        officer_id    SERIAL PRIMARY KEY,
        username      VARCHAR(64) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name          VARCHAR(120) NOT NULL,
        dob           DATE,
        org_name      VARCHAR(120) NOT NULL,
        role          VARCHAR(32) NOT NULL DEFAULT 'officer',
        is_active     BOOLEAN NOT NULL DEFAULT TRUE,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
      );
    `);

    const passwordHash = await bcrypt.hash(password, 12);

    const { rows } = await pool.query(
      `INSERT INTO officers (username, password_hash, name, dob, org_name, role)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING officer_id, username, name, org_name, role`,
      [username, passwordHash, name, dob || null, org, role]
    );

    console.log("Officer account created:");
    console.table(rows);
  } catch (err) {
    if (err.code === "23505") {
      console.error(`Username "${username}" already exists — pick a different one.`);
    } else {
      console.error("Failed to create officer:", err.message);
    }
    process.exit(1);
  } finally {
    await pool.end();
  }
}

main();