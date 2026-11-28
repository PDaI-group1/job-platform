import cors from "cors";
import express, { type Express } from "express";
import type { db_client } from "./db.ts";
import { cv_token_header } from "./cvs/cv_token.ts";
import { error_handler, not_found_handler } from "./errors.ts";
import { create_cv_router } from "./routes/cv_routes.ts";
import { create_health_router } from "./routes/health_routes.ts";
import { create_job_router } from "./routes/job_routes.ts";
import { create_stats_router } from "./routes/stats_routes.ts";

export type app_options = {
  db: db_client;
  cors_origins: string[];
  // POST /cvs; off unless CV_UPLOAD_ENABLED=true.
  cv_upload_enabled?: boolean;
};

// Builds the app without starting the server, so tests can call it directly.
export function create_app({
  db,
  cors_origins,
  cv_upload_enabled = false,
}: app_options): Express {
  const app = express();

  app.disable("x-powered-by");
  app.use(
    cors({
      origin: cors_origins,
      methods: ["GET", "POST", "DELETE"],
      allowedHeaders: ["Content-Type", cv_token_header],
    }),
  );

  app.use(create_health_router(db));
  app.use(create_job_router(db));
  app.use(create_stats_router(db));
  app.use(create_cv_router({ db, upload_enabled: cv_upload_enabled }));

  app.use(not_found_handler);
  app.use(error_handler);

  return app;
}
