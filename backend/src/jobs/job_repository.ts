import type { db_client } from "../db.ts";
import type { job } from "../types/job.ts";
import type { job_list_filters, job_list_params, job_sort } from "./job_query.ts";

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

// ORDER BY for each sort value. Only these fixed strings ever reach the SQL.
// Every order ends with newest first and id, so it is stable between pages.
// newest: jobs without a publish date go last.
// company_name: case-insensitive A–Z, jobs without a company go last.
const job_orders: Record<job_sort, string> = {
  newest: "published_at DESC NULLS LAST, id DESC",
  company_name: "lower(company_name) ASC NULLS LAST, published_at DESC NULLS LAST, id DESC",
};

export function build_job_order(sort: job_sort): string {
  return job_orders[sort];
}

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
    // Title and description (#13) plus company and location, which the
    // frontend search box also promises ("Search jobs, companies, locations").
    add(
      (p) =>
        `(title ILIKE ${p} OR description ILIKE ${p}` +
        ` OR company_name ILIKE ${p} OR location ILIKE ${p})`,
      `%${escape_like(filters.q)}%`,
    );
  }
  if (filters.location !== undefined) {
    // location is free text, e.g. "Helsinki, Espoo", so match a part of it.
    add((p) => `location ILIKE ${p}`, `%${escape_like(filters.location)}%`);
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
  { page, page_size, sort, filters }: job_list_params,
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
        `ORDER BY ${build_job_order(sort)} LIMIT ${limit_placeholder} OFFSET ${offset_placeholder}`,
      [...values, page_size, offset],
    ),
  ]);

  return { jobs: rows_result.rows, total: count_result.rows[0]?.total ?? 0 };
}

export type job_stats = {
  total: number;
  active: number;
  companies: number;
};

// Totals for the whole catalog, independent of search and filters.
// Companies are counted case- and whitespace-insensitively; jobs without a
// company name are not counted as a company.
export async function get_job_stats(db: db_client): Promise<job_stats> {
  const result = await db.query<job_stats>(
    `SELECT
       count(*)::int AS total,
       count(*) FILTER (WHERE is_active)::int AS active,
       count(DISTINCT lower(btrim(company_name)))
         FILTER (WHERE btrim(company_name) <> '')::int AS companies
     FROM jobs`,
  );
  return result.rows[0] ?? { total: 0, active: 0, companies: 0 };
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
