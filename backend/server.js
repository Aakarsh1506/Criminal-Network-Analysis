import express from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import authRouter from "./routes/auth.js";
import criminalsRouter from "./routes/criminals.js";
import crimeTypesRouter from "./routes/crimeTypes.js";
import statsRouter from "./routes/stats.js";
import workspaceRouter from "./routes/workspace.js";
import officersRouter from "./routes/officers.js";
import { requireAuth } from "./middleware/requireAuth.js";
import { requireAdmin } from "./middleware/requireAdmin.js";

const app = express();
const PORT = process.env.PORT || 5050;

app.use(
  cors({
    origin: process.env.FRONTEND_ORIGIN || "http://localhost:3000",
    credentials: true,
  })
);
app.use(express.json());
app.use(cookieParser());

app.use("/api/auth", authRouter);

app.use("/api/criminals", requireAuth, criminalsRouter);
app.use("/api/crime-types", requireAuth, crimeTypesRouter);
app.use("/api/stats", requireAuth, statsRouter);
app.use("/api/workspace", requireAuth, workspaceRouter);
app.use("/api/officers", requireAuth, requireAdmin, officersRouter);

app.get("/api/health", (req, res) => res.json({ ok: true }));

app.listen(PORT, () => {
  console.log(`Criminal Network Analysis API listening on port ${PORT}`);
});