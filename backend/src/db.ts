import pg from "pg";

// node-postgres returns BIGINT and NUMERIC as strings to avoid precision loss.
// Job ids and salaries fit safely into a JS number, and docs/data-model.md
// defines them as numbers in the API.
pg.types.setTypeParser(pg.types.builtins.INT8, (value) => Number(value));
pg.types.setTypeParser(pg.types.builtins.NUMERIC, (value) => Number(value));

// The routes only need query(), which also makes it easy to pass a test double.
export type db_client = Pick<pg.Pool, "query">;

export function create_pool(database_url: string): pg.Pool {
  const pool = new pg.Pool({
    connectionString: database_url,
    max: 10,
    // Fail fast so /health and the API answer 503 instead of hanging.
    connectionTimeoutMillis: 5000,
  });

  // An idle client can lose its connection (e.g. the database restarts).
  // Without this listener the error would crash the process.
  pool.on("error", (error) => {
    console.error("Unexpected error on an idle database client:", error.message);
  });

  return pool;
}
