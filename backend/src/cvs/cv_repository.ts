import type { db_client } from "../db.ts";

export const cv_statuses = ["pending", "processing", "done", "failed"] as const;
export type cv_status = (typeof cv_statuses)[number];

export type created_cv = {
  id: number;
  text_length: number;
  created_at: Date;
};

export type cv_row = {
  id: number;
  profile_status: cv_status;
  profile: unknown;
  text_length: number;
  created_at: Date;
  updated_at: Date;
};

// The API only creates CVs, reads their status and deletes them.
// Everything about processing (profile, model, error, attempts) is written by
// the worker, see docs/cv-processing.md.
export async function insert_cv(
  db: db_client,
  text: string,
  access_token_hash: string,
): Promise<created_cv> {
  const result = await db.query<created_cv>(
    `INSERT INTO cvs (text, access_token_hash)
     VALUES ($1, $2)
     RETURNING id, char_length(text)::int AS text_length, created_at`,
    [text, access_token_hash],
  );
  return result.rows[0]!;
}

// Only the owner (matching token hash) gets the row; for anyone else the CV
// does not exist. profile_model and profile_error stay internal.
export async function find_cv(
  db: db_client,
  id: string,
  access_token_hash: string,
): Promise<cv_row | null> {
  const result = await db.query<cv_row>(
    `SELECT id, profile_status, profile, char_length(text)::int AS text_length,
            created_at, updated_at
     FROM cvs
     WHERE id = $1 AND access_token_hash = $2`,
    [id, access_token_hash],
  );
  return result.rows[0] ?? null;
}

// Deletes the row completely, also while the worker is processing it: the worker
// then finds nothing to update and drops its result.
export async function delete_cv(
  db: db_client,
  id: string,
  access_token_hash: string,
): Promise<boolean> {
  const result = await db.query(
    "DELETE FROM cvs WHERE id = $1 AND access_token_hash = $2",
    [id, access_token_hash],
  );
  return (result.rowCount ?? 0) > 0;
}
