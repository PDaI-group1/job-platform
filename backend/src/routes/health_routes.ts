import { Router } from "express";
import type { db_client } from "../db.ts";

export function create_health_router(db: db_client): Router {
  const router = Router();

  // OK only when the database answers, so a deploy can use it as a readiness check.
  router.get("/health", async (_req, res) => {
    try {
      await db.query("SELECT 1");
      res.json({ status: "ok" });
    } catch (error) {
      console.error(
        "Health check failed:",
        error instanceof Error ? error.message : error,
      );
      res.status(503).json({ status: "error", database: "unreachable" });
    }
  });

  return router;
}
