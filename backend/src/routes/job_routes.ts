import { Router } from "express";
import type { db_client } from "../db.ts";
import { not_found } from "../errors.ts";
import { parse_job_id, parse_job_list_params } from "../jobs/job_query.ts";
import { find_job_by_id, list_jobs } from "../jobs/job_repository.ts";

export function create_job_router(db: db_client): Router {
  const router = Router();

  // Express 5 forwards errors from async handlers to error_handler.
  router.get("/jobs", async (req, res) => {
    const params = parse_job_list_params(req.query);
    const { jobs, total } = await list_jobs(db, params);

    res.json({
      data: jobs,
      pagination: {
        page: params.page,
        page_size: params.page_size,
        total,
        total_pages: Math.ceil(total / params.page_size),
      },
    });
  });

  router.get("/jobs/:id", async (req, res) => {
    const id = parse_job_id(req.params.id);
    const job = await find_job_by_id(db, id);
    if (!job) {
      throw not_found(`Job ${id} not found`);
    }
    res.json(job);
  });

  return router;
}
