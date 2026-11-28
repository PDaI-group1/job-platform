// Temporary owner check for CVs until user accounts (#23).
// Proposal, not agreed yet: docs/decisions/cv-temporary-access-token.md.
import { createHash, randomBytes } from "node:crypto";
import type { Request } from "express";
import { api_error } from "../errors.ts";

export const cv_token_header = "X-CV-Token";

// 32 random bytes, base64url: 43 characters.
const token_pattern = /^[A-Za-z0-9_-]{43}$/;

export function create_access_token(): string {
  return randomBytes(32).toString("base64url");
}

export function hash_access_token(token: string): string {
  return createHash("sha256").update(token).digest("hex");
}

// Returns the hash of the token sent by the client, or 401 when it is missing
// or malformed. A wrong but well-formed token is answered with 404 by the
// routes, so nobody can find out which CV ids exist.
export function read_access_token_hash(req: Request): string {
  const token = req.get(cv_token_header)?.trim();
  if (!token || !token_pattern.test(token)) {
    throw new api_error(401, "unauthorized", `Missing or invalid ${cv_token_header} header.`);
  }
  return hash_access_token(token);
}
