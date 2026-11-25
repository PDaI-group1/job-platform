import { Router } from "express";
import type { db_client } from "../db.ts";
import { get_job_stats } from "../jobs/job_repository.ts";

export function create_stats_router(db: db_client): Router {
  const router = Router();

  // Catalog totals for the dashboard cards (Total jobs, Active jobs, Companies).
  // The number of search results is pagination.total of GET /jobs.
  router.get("/stats", async (_req, res) => {
    res.json(await get_job_stats(db));
  });

  return router;
}
