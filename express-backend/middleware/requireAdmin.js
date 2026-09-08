// Stacks on top of requireAuth — assumes req.officer is already set by it.
// Blocks every officer except the one hardcoded admin account.
export function requireAdmin(req, res, next) {
  if (req.officer?.role !== "admin") {
    return res.status(403).json({ error: "Admin access required" });
  }
  next();
}