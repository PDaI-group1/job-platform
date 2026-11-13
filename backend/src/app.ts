import cors from "cors";
import express, { type Express } from "express";
import type { db_client } from "./db.ts";
import { error_handler, not_found_handler } from "./errors.ts";
import { create_health_router } from "./routes/health_routes.ts";
import { create_job_router } from "./routes/job_routes.ts";

export type app_options = {
  db: db_client;
  cors_origins: string[];
};

// Builds the app without starting the server, so tests can call it directly.
export function create_app({ db, cors_origins }: app_options): Express {
  const app = express();

  app.disable("x-powered-by");
  app.use(cors({ origin: cors_origins, methods: ["GET"] }));

  app.use(create_health_router(db));
  app.use(create_job_router(db));

  app.use(not_found_handler);
  app.use(error_handler);

  return app;
}
