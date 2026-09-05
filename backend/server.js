import express from "express";
import cors from "cors";
import criminalsRouter from "./routes/criminals.js";
import crimeTypesRouter from "./routes/crimeTypes.js";
import statsRouter from "./routes/stats.js";

const app = express();
const PORT = process.env.PORT || 5050;

app.use(cors());
app.use(express.json());

app.use("/api/criminals", criminalsRouter);
app.use("/api/crime-types", crimeTypesRouter);
app.use("/api/stats", statsRouter);

app.get("/api/health", (req, res) => res.json({ ok: true }));

app.listen(PORT, () => {
  console.log(`Criminal Network Analysis API listening on port ${PORT}`);
});