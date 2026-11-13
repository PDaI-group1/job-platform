import { create_app } from "./app.ts";
import { load_config, type app_config } from "./config.ts";
import { create_pool } from "./db.ts";

let config: app_config;
try {
  config = load_config();
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
}

const pool = create_pool(config.database_url);
const app = create_app({ db: pool, cors_origins: config.cors_origins });

const server = app.listen(config.port, (error) => {
  if (error) {
    console.error(`Cannot start the API on port ${config.port}:`, error.message);
    process.exit(1);
  }
  console.log(`API listening on http://localhost:${config.port}`);
});

function shutdown(signal: string) {
  console.log(`${signal} received, shutting down`);
  server.close(() => {
    pool.end().finally(() => process.exit(0));
  });
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
