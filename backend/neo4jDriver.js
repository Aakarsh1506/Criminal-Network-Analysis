// Central Neo4j driver/session helper for the Criminal Network Analysis API.
// Reads connection details from environment variables (see backend/.env.example).

import neo4j from "neo4j-driver";
import dotenv from "dotenv";

dotenv.config();

const driver = neo4j.driver(
  process.env.NEO4J_URI,
  neo4j.auth.basic(process.env.NEO4J_USER, process.env.NEO4J_PASSWORD)
);

// Run a single Cypher query and return plain JS records.
// Opens and closes a session per call — fine for this app's query volume.
export async function runCypher(query, params = {}) {
  const session = driver.session();
  try {
    const result = await session.run(query, params);
    return result.records.map((record) => record.toObject());
  } finally {
    await session.close();
  }
}

export default driver;