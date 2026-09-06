import express from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import authRouter from "./routes/auth.js";
import criminalsRouter from "./routes/criminals.js";
import crimeTypesRouter from "./routes/crimeTypes.js";
import statsRouter from "./routes/stats.js";
import { requireAuth } from "./middleware/requireAuth.js";

const app = express();
const PORT = process.env.PORT || 5050;

// credentials: true is what lets the httpOnly auth cookie travel on
// cross-origin requests in production. In dev the Vite proxy makes
// frontend and backend look same-origin to the browser, so this doesn't
// even come into play — but it's needed once they're deployed separately.
app.use(
  cors({
    origin: process.env.FRONTEND_ORIGIN || "http://localhost:3000",
    credentials: true,
  })
);
app.use(express.json());
app.use(cookieParser());

// Public — this is the only route that ever issues a session.
app.use("/api/auth", authRouter);

// Everything below requires a valid login cookie.
app.use("/api/criminals", requireAuth, criminalsRouter);
app.use("/api/crime-types", requireAuth, crimeTypesRouter);
app.use("/api/stats", requireAuth, statsRouter);

app.get("/api/health", (req, res) => res.json({ ok: true }));

app.listen(PORT, () => {
  console.log(`Criminal Network Analysis API listening on port ${PORT}`);
});