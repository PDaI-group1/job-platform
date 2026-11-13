export type app_config = {
  database_url: string;
  port: number;
  cors_origins: string[];
};

const default_port = 3000;
// Vite dev server
const default_cors_origin = "http://localhost:5173";

export function load_config(env: NodeJS.ProcessEnv = process.env): app_config {
  const database_url = env.DATABASE_URL?.trim();
  if (!database_url) {
    throw new Error(
      "DATABASE_URL is not set. Copy .env.example to .env in the repository root.",
    );
  }

  return {
    database_url,
    port: parse_port(env.PORT),
    cors_origins: parse_origins(env.CORS_ORIGIN ?? default_cors_origin),
  };
}

function parse_port(value: string | undefined): number {
  if (value === undefined || value.trim() === "") return default_port;

  const port = Number(value);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`PORT must be an integer between 1 and 65535, got "${value}".`);
  }
  return port;
}

// CORS_ORIGIN is a comma-separated list, e.g. "http://localhost:5173,https://example.com"
function parse_origins(value: string): string[] {
  return value
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
}
