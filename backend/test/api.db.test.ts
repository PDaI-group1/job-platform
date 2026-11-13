// HTTP tests against a real PostgreSQL with the migrations applied and at least one job
// (e.g. the seed data). They only read, so they are safe to run on a dev database.
// Skipped when DATABASE_URL is not set.
import type pg from "pg";
import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { create_app } from "../src/app.ts";
import { create_pool } from "../src/db.ts";
import type { job } from "../src/types/job.ts";

const database_url = process.env.DATABASE_URL;

// Fields from docs/data-model.md, without content_hash and raw_data.
const job_fields = [
  "id", "title", "company_name", "location", "remote_type", "description", "url",
  "source", "published_at", "scraped_at", "source_job_id", "employment_type", "skills",
  "language", "salary_min", "salary_max", "salary_currency", "salary_period",
  "deadline_at", "is_active", "created_at", "updated_at",
].sort();

describe.skipIf(!database_url)("API with database", () => {
  let pool: pg.Pool;
  let app: ReturnType<typeof create_app>;

  const count_jobs = async (where = "", values: unknown[] = []) => {
    const result = await pool.query<{ n: number }>(
      `SELECT count(*)::int AS n FROM jobs ${where}`,
      values,
    );
    return result.rows[0]!.n;
  };

  beforeAll(async () => {
    pool = create_pool(database_url!);
    app = create_app({ db: pool, cors_origins: [] });
    expect(await count_jobs(), "the jobs table is empty; load the seed data").toBeGreaterThan(0);
  });

  afterAll(() => pool.end());

  it("GET /health -> 200", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
  });

  it("GET /jobs returns the first page with pagination", async () => {
    const total = await count_jobs();
    const res = await request(app).get("/jobs");

    expect(res.status).toBe(200);
    expect(res.body.pagination).toEqual({
      page: 1,
      page_size: 20,
      total,
      total_pages: Math.ceil(total / 20),
    });
    expect(res.body.data).toHaveLength(Math.min(total, 20));
  });

  it("returns jobs newest first, without a date last, ties by id", async () => {
    const res = await request(app).get("/jobs?page_size=100");
    const jobs: job[] = res.body.data;

    for (let i = 1; i < jobs.length; i++) {
      const prev = jobs[i - 1]!;
      const cur = jobs[i]!;
      if (prev.published_at === null) {
        expect(cur.published_at, `job ${cur.id} with a date after one without`).toBeNull();
      } else if (cur.published_at !== null) {
        const diff = Date.parse(prev.published_at) - Date.parse(cur.published_at);
        expect(diff).toBeGreaterThanOrEqual(0);
        if (diff === 0) expect(prev.id).toBeGreaterThan(cur.id);
      }
    }
  });

  it("splits pages without gaps or overlaps", async () => {
    const all = await request(app).get("/jobs?page_size=4");
    const first = await request(app).get("/jobs?page=1&page_size=2");
    const second = await request(app).get("/jobs?page=2&page_size=2");

    const ids = (res: request.Response) => res.body.data.map((j: job) => j.id);
    expect([...ids(first), ...ids(second)]).toEqual(ids(all));
  });

  it("returns an empty page past the end", async () => {
    const res = await request(app).get("/jobs?page=100000");
    expect(res.status).toBe(200);
    expect(res.body.data).toEqual([]);
    expect(res.body.pagination.total).toBe(await count_jobs());
  });

  it("returns jobs in the data model shape with JSON numbers", async () => {
    const res = await request(app).get("/jobs?page_size=100");

    for (const job of res.body.data as job[]) {
      expect(Object.keys(job).sort()).toEqual(job_fields);
      expect(typeof job.id).toBe("number");
      expect(Array.isArray(job.skills)).toBe(true);
      for (const salary of [job.salary_min, job.salary_max]) {
        expect(salary === null || typeof salary === "number").toBe(true);
      }
      expect(Number.isNaN(Date.parse(job.scraped_at))).toBe(false);
    }
  });

  it("q searches title, company and location case-insensitively", async () => {
    const sample = (await request(app).get("/jobs?page_size=1")).body.data[0] as job;
    const q = sample.title.slice(0, 5).toUpperCase();

    const res = await request(app).get("/jobs").query({ q, page_size: 100 });

    expect(res.status).toBe(200);
    expect(res.body.data.map((j: job) => j.id)).toContain(sample.id);
    for (const job of res.body.data as job[]) {
      const text = [job.title, job.company_name, job.location].join(" ").toLowerCase();
      expect(text).toContain(q.toLowerCase());
    }
  });

  it("treats % in q literally", async () => {
    const res = await request(app).get("/jobs").query({ q: "%" });
    expect(res.body.pagination.total).toBe(
      await count_jobs(
        "WHERE title LIKE '%\\%%' OR company_name LIKE '%\\%%' OR location LIKE '%\\%%'",
      ),
    );
  });

  it("filters by employment_type and counts only matching jobs", async () => {
    const res = await request(app).get("/jobs?employment_type=full_time&page_size=100");

    expect(res.status).toBe(200);
    expect(res.body.pagination.total).toBe(
      await count_jobs("WHERE employment_type = $1", ["full_time"]),
    );
    for (const job of res.body.data as job[]) {
      expect(job.employment_type).toBe("full_time");
    }
  });

  it("filters by is_active", async () => {
    const res = await request(app).get("/jobs?is_active=false");
    expect(res.body.pagination.total).toBe(await count_jobs("WHERE NOT is_active"));
  });

  it("GET /jobs/:id returns the same job as the list", async () => {
    const listed = (await request(app).get("/jobs?page_size=1")).body.data[0] as job;
    const res = await request(app).get(`/jobs/${listed.id}`);

    expect(res.status).toBe(200);
    expect(res.body).toEqual(listed);
  });

  it("GET /jobs/:id -> 404 for a missing job", async () => {
    const max = await pool.query<{ id: number }>("SELECT coalesce(max(id), 0) AS id FROM jobs");
    const res = await request(app).get(`/jobs/${max.rows[0]!.id + 1}`);

    expect(res.status).toBe(404);
    expect(res.body.error.code).toBe("not_found");
  });
});
