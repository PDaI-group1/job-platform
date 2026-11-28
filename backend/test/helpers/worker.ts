// Stands in for matching/worker.py in tests. The SQL is copied from
// docs/cv-processing.md, so these tests check that the API side works with the
// worker contract. Keep both in sync.
import type pg from "pg";

export type claimed_cv = { id: number; attempts: number; text: string };

type queryable = Pick<pg.Pool, "query"> | Pick<pg.PoolClient, "query">;

export async function claim_cv(db: queryable): Promise<claimed_cv | null> {
  const result = await db.query<claimed_cv>(
    `UPDATE cvs
     SET profile_status = 'processing',
         attempts = attempts + 1,
         processing_started_at = now()
     WHERE id = (
         SELECT id FROM cvs
         WHERE profile_status = 'pending'
         ORDER BY created_at
         LIMIT 1
         FOR UPDATE SKIP LOCKED
     )
     RETURNING id, attempts, text`,
  );
  return result.rows[0] ?? null;
}

// Returns the number of updated rows: 0 means the result was dropped.
export async function save_profile(
  db: queryable,
  claim: claimed_cv,
  profile: unknown,
  model: string,
): Promise<number> {
  const result = await db.query(
    `UPDATE cvs
     SET profile_status = 'done',
         profile = $3,
         profile_model = $4,
         profile_error = NULL,
         profile_updated_at = now()
     WHERE id = $1 AND profile_status = 'processing' AND attempts = $2`,
    [claim.id, claim.attempts, JSON.stringify(profile), model],
  );
  return result.rowCount ?? 0;
}

export async function save_failure(
  db: queryable,
  claim: claimed_cv,
  reason: string,
  model: string,
): Promise<number> {
  const result = await db.query(
    `UPDATE cvs
     SET profile_status = 'failed',
         profile = NULL,
         profile_model = $4,
         profile_error = $3,
         profile_updated_at = now()
     WHERE id = $1 AND profile_status = 'processing' AND attempts = $2`,
    [claim.id, claim.attempts, reason, model],
  );
  return result.rowCount ?? 0;
}

// Stuck-processing recovery, as in the example in the contract (timeout 0 here).
export async function reset_stuck(db: queryable, max_attempts = 3): Promise<number> {
  const result = await db.query(
    `UPDATE cvs
     SET profile_status = CASE WHEN attempts < $1 THEN 'pending' ELSE 'failed' END,
         profile_error  = CASE WHEN attempts < $1 THEN profile_error ELSE 'timed out' END,
         profile_updated_at = CASE WHEN attempts < $1 THEN profile_updated_at ELSE now() END
     WHERE profile_status = 'processing'
       AND processing_started_at <= now()`,
    [max_attempts],
  );
  return result.rowCount ?? 0;
}
