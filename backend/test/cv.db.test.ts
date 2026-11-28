// CV flow against a real PostgreSQL with migrations 001 and 002, plus a
// simulated worker (test/helpers/worker.ts, SQL from docs/cv-processing.md).
// These tests write and delete rows in `cvs`, so they need a separate test
// database: TEST_DATABASE_URL locally, the throwaway CI database in CI.
import { readFileSync } from "node:fs";
import pg from "pg";
import request from "supertest";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { create_app } from "../src/app.ts";
import { create_pool } from "../src/db.ts";
import { hash_access_token } from "../src/cvs/cv_token.ts";
import { cv_failed_message } from "../src/routes/cv_routes.ts";
import { fictional_cv_lines, make_pdf } from "./helpers/pdf.ts";
import { claim_cv, reset_stuck, save_failure, save_profile } from "./helpers/worker.ts";

const database_url =
  process.env.TEST_DATABASE_URL ?? (process.env.CI ? process.env.DATABASE_URL : undefined);

// A real profile produced by matching/cv_extract.py for a made-up CV.
const sample_profile = Object.values(
  JSON.parse(
    readFileSync(new URL("../../matching/cv_test_results.json", import.meta.url), "utf8"),
  ) as Record<string, unknown>,
)[0];

const pdf_type = { filename: "Maija_Esimerkki_CV.pdf", contentType: "application/pdf" };

describe.skipIf(!database_url)("CV API with database and simulated worker", () => {
  let pool: pg.Pool;
  let app: ReturnType<typeof create_app>;

  const upload = async (lines = fictional_cv_lines) =>
    request(app).post("/cvs").attach("file", await make_pdf([lines.join("\n")]), pdf_type);

  const row = async (id: number) =>
    (await pool.query("SELECT * FROM cvs WHERE id = $1", [id])).rows[0] as
      | Record<string, unknown>
      | undefined;

  beforeAll(async () => {
    const db_name = new URL(database_url!).pathname.slice(1);
    if (!process.env.CI && !/test/i.test(db_name)) {
      throw new Error(`Refusing to run CV write tests on "${db_name}": use a separate test database.`);
    }
    pool = create_pool(database_url!);
    app = create_app({ db: pool, cors_origins: [], cv_upload_enabled: true });
  });

  // The simulated worker takes the oldest pending CV, so every test starts empty.
  beforeEach(async () => {
    await pool.query("DELETE FROM cvs");
  });

  afterAll(async () => {
    await pool?.query("DELETE FROM cvs");
    await pool?.end();
  });

  it("stores the extracted text as pending and returns a one-time token", async () => {
    const res = await upload();

    expect(res.status).toBe(201);
    expect(res.body).toEqual({
      id: expect.any(Number),
      access_token: expect.stringMatching(/^[A-Za-z0-9_-]{43}$/),
      status: "pending",
      text_length: expect.any(Number),
      created_at: expect.any(String),
    });

    const stored = (await row(res.body.id))!;
    expect(stored.profile_status).toBe("pending");
    // Every line is kept with its line break. Empty lines are not: in a PDF they
    // are only vertical space, not text.
    expect(stored.text).toBe(fictional_cv_lines.filter(Boolean).join("\n"));
    expect([...(stored.text as string)].length).toBe(res.body.text_length);
    // Only the hash of the token is stored; no file name, no PDF.
    expect(stored.access_token_hash).toBe(hash_access_token(res.body.access_token));
    expect(Object.keys(stored).sort()).toEqual(
      [
        "access_token_hash", "attempts", "created_at", "id", "processing_started_at",
        "profile", "profile_error", "profile_model", "profile_status", "profile_updated_at",
        "text", "updated_at",
      ].sort(),
    );
    expect(JSON.stringify(stored)).not.toContain("Maija_Esimerkki_CV");
  });

  it("shows pending → processing → done and returns the profile only when done", async () => {
    const { body: created } = await upload();
    const get = () => request(app).get(`/cvs/${created.id}`).set("X-CV-Token", created.access_token);

    const pending = await get();
    expect(pending.status).toBe(200);
    expect(pending.body).toMatchObject({ id: created.id, status: "pending", profile: null, error: null });

    const claim = (await claim_cv(pool))!;
    expect(claim).toMatchObject({ id: created.id, attempts: 1 });
    expect(claim.text).toContain("Ohjelmistokehittäjä / Software Developer, Jyväskylä");
    expect((await get()).body).toMatchObject({ status: "processing", profile: null });

    expect(await save_profile(pool, claim, sample_profile, "test-model")).toBe(1);

    const done = await get();
    expect(done.body).toMatchObject({ status: "done", error: null });
    expect(done.body.profile).toEqual(sample_profile);
    expect(done.body).not.toHaveProperty("profile_model");
    expect((await row(created.id))!.profile_model).toBe("test-model");
  });

  it("shows a user-friendly message for failed, not the worker's reason", async () => {
    const { body: created } = await upload();
    const claim = (await claim_cv(pool))!;
    expect(await save_failure(pool, claim, "APIError 503: model overloaded", "test-model")).toBe(1);

    const res = await request(app).get(`/cvs/${created.id}`).set("X-CV-Token", created.access_token);

    expect(res.body).toMatchObject({ status: "failed", profile: null, error: cv_failed_message });
    expect(JSON.stringify(res.body)).not.toContain("overloaded");
  });

  it("does not let another client read or delete the CV", async () => {
    const { body: mine } = await upload();
    const { body: other } = await upload();

    const read = await request(app).get(`/cvs/${mine.id}`).set("X-CV-Token", other.access_token);
    const del = await request(app).delete(`/cvs/${mine.id}`).set("X-CV-Token", other.access_token);

    expect(read.status).toBe(404);
    expect(del.status).toBe(404);
    expect(await row(mine.id)).toBeDefined();
  });

  it("deletes the CV completely", async () => {
    const { body: created } = await upload();
    const auth = { "X-CV-Token": created.access_token };

    expect((await request(app).delete(`/cvs/${created.id}`).set(auth)).status).toBe(204);
    expect(await row(created.id)).toBeUndefined();
    expect((await request(app).get(`/cvs/${created.id}`).set(auth)).status).toBe(404);
    expect((await request(app).delete(`/cvs/${created.id}`).set(auth)).status).toBe(404);
  });

  it("worker drops its result when the CV was deleted during processing", async () => {
    const { body: created } = await upload();
    const claim = (await claim_cv(pool))!;

    await request(app).delete(`/cvs/${created.id}`).set("X-CV-Token", created.access_token).expect(204);

    expect(await save_profile(pool, claim, sample_profile, "test-model")).toBe(0);
    expect(await row(created.id)).toBeUndefined();
  });

  it("a late result of a stuck attempt cannot overwrite the retry", async () => {
    const { body: created } = await upload();
    const first = (await claim_cv(pool))!;
    expect(await reset_stuck(pool)).toBe(1);
    const second = (await claim_cv(pool))!;
    expect(second).toMatchObject({ id: created.id, attempts: 2 });

    expect(await save_profile(pool, second, sample_profile, "model-of-retry")).toBe(1);
    expect(await save_failure(pool, first, "late timeout of attempt 1", "old-model")).toBe(0);

    const stored = (await row(created.id))!;
    expect(stored).toMatchObject({ profile_status: "done", profile_model: "model-of-retry", attempts: 2 });
  });

  it("two workers never claim the same CV (SKIP LOCKED)", async () => {
    await upload();
    await upload();
    const a = await pool.connect();
    const b = await pool.connect();
    try {
      await a.query("BEGIN");
      await b.query("BEGIN");
      const claim_a = await claim_cv(a);
      const claim_b = await claim_cv(b);
      expect(claim_a?.id).toBeDefined();
      expect(claim_b?.id).toBeDefined();
      expect(claim_a!.id).not.toBe(claim_b!.id);
    } finally {
      await a.query("ROLLBACK");
      await b.query("ROLLBACK");
      a.release();
      b.release();
    }
  });

  it("keeps the jobs API working next to the CV tables", async () => {
    const res = await request(app).get("/jobs?page_size=1");
    expect(res.status).toBe(200);
    expect(res.body.pagination.total).toBeGreaterThan(0);
  });
});
