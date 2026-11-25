import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Same .env as `npm run dev`. In CI the variables come from the environment instead.
// Variables that are already set are not overwritten.
const env_file = fileURLToPath(new URL("../../.env", import.meta.url));
if (existsSync(env_file)) {
  process.loadEnvFile(env_file);
}
