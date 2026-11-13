import type { db_client } from "../db.ts";
import type { job } from "../types/job.ts";
import type { job_list_filters, job_list_params } from "./job_query.ts";

// Public fields from docs/data-model.md, in the documented order.
// content_hash and raw_data are internal to the crawler and never returned.
// TIMESTAMPTZ columns come back as Date objects and are serialized by
// res.json() as ISO 8601 strings in UTC, which is what the job type describes.
const job_columns = [
  "id",
  "title",
  "company_name",
  "location",
  "remote_type",
  "description",
  "url",
  "source",
  "published_at",
  "scraped_at",
  "source_job_id",
  "employment_type",
  "skills",
  "language",
  "salary_min",
  "salary_max",
  "salary_currency",
  "salary_period",
  "deadline_at",
  "is_active",
  "created_at",
  "updated_at",
].join(", ");

// Newest first. Jobs without a publish date go last; id keeps the order stable
// between pages when dates are equal.
const default_order = "published_at DESC NULLS LAST, id DESC";

export type job_list_result = {
  jobs: job[];
  total: number;
};

export type sql_where = {
  where: string;
  values: unknown[];
};

// User input only goes into values ($1, $2, ...), never into the SQL text.
export function build_job_filters(filters: job_list_filters): sql_where {
  const conditions: string[] = [];
  const values: unknown[] = [];

  const add = (to_sql: (placeholder: string) => string, value: unknown) => {
    values.push(value);
    conditions.push(to_sql(`$${values.length}`));
  };

  if (filters.q !== undefined) {
    // Same fields the mock-data search in the frontend looked at.
    add(
      (p) => `(title ILIKE ${p} OR company_name ILIKE ${p} OR location ILIKE ${p})`,
      `%${escape_like(filters.q)}%`,
    );
  }
  if (filters.employment_type !== undefined) {
    add((p) => `employment_type = ${p}`, filters.employment_type);
  }
  if (filters.remote_type !== undefined) {
    add((p) => `remote_type = ${p}`, filters.remote_type);
  }
  if (filters.is_active !== undefined) {
    add((p) => `is_active = ${p}`, filters.is_active);
  }

  return {
    where: conditions.length > 0 ? `WHERE ${conditions.join(" AND ")}` : "",
    values,
  };
}

// Makes %, _ and \ in the search text match literally in LIKE / ILIKE.
export function escape_like(value: string): string {
  return value.replace(/[\\%_]/g, (char) => `\\${char}`);
}

export async function list_jobs(
  db: db_client,
  { page, page_size, filters }: job_list_params,
): Promise<job_list_result> {
  const offset = (page - 1) * page_size;
  const { where, values } = build_job_filters(filters);
  const limit_placeholder = `$${values.length + 1}`;
  const offset_placeholder = `$${values.length + 2}`;

  const [count_result, rows_result] = await Promise.all([
    db.query<{ total: number }>(
      `SELECT count(*)::int AS total FROM jobs ${where}`,
      values,
    ),
    db.query<job>(
      `SELECT ${job_columns} FROM jobs ${where} ` +
        `ORDER BY ${default_order} LIMIT ${limit_placeholder} OFFSET ${offset_placeholder}`,
      [...values, page_size, offset],
    ),
  ]);

  return { jobs: rows_result.rows, total: count_result.rows[0]?.total ?? 0 };
}

export async function find_job_by_id(
  db: db_client,
  id: string,
): Promise<job | null> {
  const result = await db.query<job>(
    `SELECT ${job_columns} FROM jobs WHERE id = $1`,
    [id],
  );
  return result.rows[0] ?? null;
}
