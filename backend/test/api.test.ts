// HTTP tests that do not need a running database.
import request from "supertest";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { create_app } from "../src/app.ts";
import { create_pool, type db_client } from "../src/db.ts";

const frontend_origin = "http://localhost:5173";

// Validation must reject bad input before any query is sent.
const no_db = {
  query: () => {
    throw new Error("the database must not be called");
  },
} as unknown as db_client;

const app = create_app({ db: no_db, cors_origins: [frontend_origin] });

beforeEach(() => {
  // Keep the expected server-side error logs out of the test output.
  vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("request validation", () => {
  it.each([
    ["/jobs?page=0", "page"],
    ["/jobs?page_size=1000", "page_size"],
    ["/jobs?employment_type=all", "employment_type"],
    ["/jobs?is_active=yes", "is_active"],
    ["/jobs/abc", "id"],
    ["/jobs/99999999999999999999", "id"],
  ])("GET %s -> 400 for %s", async (url, parameter) => {
    const res = await request(app).get(url);

    expect(res.status).toBe(400);
    expect(res.body).toEqual({
      error: {
        code: "invalid_parameter",
        message: expect.any(String),
        details: { parameter },
      },
    });
  });

  it("returns 400 for a malformed URL", async () => {
    const res = await request(app).get("/jobs/%E0%A4%A");
    expect(res.status).toBe(400);
    expect(res.body.error.code).toBe("bad_request");
  });

  it("returns a JSON 404 for an unknown route", async () => {
    const res = await request(app).get("/nope");
    expect(res.status).toBe(404);
    expect(res.body.error.code).toBe("not_found");
  });
});

describe("CORS", () => {
  it("allows the configured frontend origin", async () => {
    const res = await request(app)
      .options("/jobs")
      .set("Origin", frontend_origin)
      .set("Access-Control-Request-Method", "GET");

    expect(res.status).toBe(204);
    expect(res.headers["access-control-allow-origin"]).toBe(frontend_origin);
  });

  it("does not allow other origins", async () => {
    const res = await request(app).get("/jobs/abc").set("Origin", "http://example.com");
    expect(res.headers["access-control-allow-origin"]).toBeUndefined();
  });
});

describe("database errors", () => {
  it("hides unexpected errors behind a generic 500", async () => {
    const failing_db = {
      query: async () => {
        throw new Error('column "secret_column" does not exist');
      },
    } as unknown as db_client;
    const failing_app = create_app({ db: failing_db, cors_origins: [] });

    const res = await request(failing_app).get("/jobs");

    expect(res.status).toBe(500);
    expect(res.body).toEqual({
      error: { code: "internal_error", message: "Internal server error" },
    });
    expect(JSON.stringify(res.body)).not.toContain("secret_column");
  });

  describe("when the database is unreachable", () => {
    // Nothing listens on port 1, so every connection is refused.
    const pool = create_pool("postgresql://user:password@127.0.0.1:1/none");
    const down_app = create_app({ db: pool, cors_origins: [] });

    afterAll(() => pool.end());

    it("GET /health -> 503", async () => {
      const res = await request(down_app).get("/health");
      expect(res.status).toBe(503);
      expect(res.body).toEqual({ status: "error", database: "unreachable" });
    });

    it.each(["/jobs", "/jobs/1"])("GET %s -> 503", async (url) => {
      const res = await request(down_app).get(url);
      expect(res.status).toBe(503);
      expect(res.body.error.code).toBe("service_unavailable");
    });
  });
});
