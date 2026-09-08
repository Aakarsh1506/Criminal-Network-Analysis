import { Router } from "express";
import multer from "multer";
import path from "node:path";
import fs from "node:fs";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { pool } from "../db.js";

const router = Router();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const UPLOAD_DIR = path.join(__dirname, "..", "uploads");
fs.mkdirSync(UPLOAD_DIR, { recursive: true });

// Self-creating, same convention as workspace.js / officers.
async function ensureDocumentsTable() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS officer_documents (
      document_id   SERIAL PRIMARY KEY,
      officer_id    INTEGER NOT NULL REFERENCES officers(officer_id) ON DELETE CASCADE,
      original_name VARCHAR(255) NOT NULL,
      stored_name   VARCHAR(255) NOT NULL,
      mime_type     VARCHAR(100) NOT NULL,
      size_bytes    INTEGER NOT NULL,
      uploaded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    );
  `);
}
ensureDocumentsTable().catch((err) => console.error("Failed to ensure documents table", err));

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, UPLOAD_DIR),
  // Randomized filename on disk — original_name (kept in the DB) is what's shown to the user.
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname) || "";
    cb(null, `${crypto.randomUUID()}${ext}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 20 * 1024 * 1024 }, // 20MB
  fileFilter: (req, file, cb) => {
    if (file.mimetype !== "application/pdf") {
      return cb(new Error("Only PDF files are allowed"));
    }
    cb(null, true);
  },
});

function mapDoc(row) {
  return {
    id: row.document_id,
    name: row.original_name,
    type: row.mime_type,
    size: row.size_bytes,
    uploadedAt: row.uploaded_at,
  };
}

// GET /api/documents — this officer's uploaded documents only
router.get("/", async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT * FROM officer_documents WHERE officer_id = $1 ORDER BY uploaded_at DESC`,
      [req.officer.officerId]
    );
    res.json(rows.map(mapDoc));
  } catch (err) {
    console.error("GET /api/documents failed", err);
    res.status(500).json({ error: "Failed to load documents" });
  }
});

// POST /api/documents — upload a new document, owned by this officer
router.post("/", (req, res) => {
  upload.single("file")(req, res, async (err) => {
    if (err) {
      return res.status(400).json({ error: err.message || "Upload failed" });
    }
    if (!req.file) {
      return res.status(400).json({ error: "No file provided" });
    }
    try {
      const { rows } = await pool.query(
        `INSERT INTO officer_documents (officer_id, original_name, stored_name, mime_type, size_bytes)
         VALUES ($1, $2, $3, $4, $5)
         RETURNING *`,
        [req.officer.officerId, req.file.originalname, req.file.filename, req.file.mimetype, req.file.size]
      );
      res.status(201).json(mapDoc(rows[0]));
    } catch (dbErr) {
      console.error("POST /api/documents failed", dbErr);
      fs.unlink(req.file.path, () => {});
      res.status(500).json({ error: "Failed to save document" });
    }
  });
});

// GET /api/documents/:id/file — stream the actual PDF.
// Ownership is checked in the SQL itself (officer_id = req.officer.officerId),
// so one officer can never fetch another's file even by guessing an id.
router.get("/:id/file", async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT stored_name, mime_type, original_name FROM officer_documents
       WHERE document_id = $1 AND officer_id = $2`,
      [req.params.id, req.officer.officerId]
    );
    const doc = rows[0];
    if (!doc) return res.status(404).json({ error: "Document not found" });

    const filePath = path.join(UPLOAD_DIR, doc.stored_name);
    res.setHeader("Content-Type", doc.mime_type);
    res.setHeader("Content-Disposition", `inline; filename="${doc.original_name}"`);
    res.sendFile(filePath);
  } catch (err) {
    console.error("GET /api/documents/:id/file failed", err);
    res.status(500).json({ error: "Failed to load document" });
  }
});

// DELETE /api/documents/:id — remove a document (only its owner can)
router.delete("/:id", async (req, res) => {
  try {
    const { rows } = await pool.query(
      `DELETE FROM officer_documents WHERE document_id = $1 AND officer_id = $2
       RETURNING stored_name`,
      [req.params.id, req.officer.officerId]
    );
    const doc = rows[0];
    if (!doc) return res.status(404).json({ error: "Document not found" });
    fs.unlink(path.join(UPLOAD_DIR, doc.stored_name), () => {});
    res.json({ ok: true });
  } catch (err) {
    console.error("DELETE /api/documents/:id failed", err);
    res.status(500).json({ error: "Failed to delete document" });
  }
});

export default router;