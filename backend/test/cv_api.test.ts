// CV endpoints without a database: validation, errors, access checks, CORS.
import request from "supertest";
import { afterAll, beforeEach, describe, expect, it, vi } from "vitest";
import { create_app } from "../src/app.ts";
import { create_pool, type db_client } from "../src/db.ts";
import { create_access_token } from "../src/cvs/cv_token.ts";
import { max_pdf_bytes } from "../src/routes/cv_routes.ts";
import {
  fictional_cv_lines,
  make_long_pdf,
  make_pdf,
  make_pdf_without_text,
} from "./helpers/pdf.ts";

const frontend_origin = "http://localhost:5173";

// Every rejected upload must be rejected before anything is written.
const no_db = {
  query: () => {
    throw new Error("the database must not be called");
  },
} as unknown as db_client;

const app = create_app({ db: no_db, cors_origins: [frontend_origin], cv_upload_enabled: true });
const pdf_type = { filename: "cv.pdf", contentType: "application/pdf" };

let console_error: ReturnType<typeof vi.spyOn>;
beforeEach(() => {
  console_error = vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("POST /cvs when upload is disabled", () => {
  it("answers 503 feature_disabled (the default)", async () => {
    const disabled = create_app({ db: no_db, cors_origins: [] });
    const res = await request(disabled)
      .post("/cvs")
      .attach("file", await make_pdf(["x"]), pdf_type);

    expect(res.status).toBe(503);
    expect(res.body.error.code).toBe("feature_disabled");
  });
});

describe("POST /cvs validation", () => {
  it("requires a file", async () => {
    const res = await request(app).post("/cvs");
    expect(res.status).toBe(400);
    expect(res.body.error).toMatchObject({ code: "invalid_parameter", details: { parameter: "file" } });
  });

  it("requires the field name \"file\"", async () => {
    const res = await request(app).post("/cvs").attach("cv", await make_pdf(["x"]), pdf_type);
    expect(res.status).toBe(400);
    expect(res.body.error.details).toEqual({ parameter: "file" });
  });

  it("accepts only one file and no other fields", async () => {
    const pdf = await make_pdf(["x"]);
    const two = await request(app).post("/cvs").attach("file", pdf, pdf_type).attach("file", pdf, pdf_type);
    const field = await request(app).post("/cvs").field("name", "x").attach("file", pdf, pdf_type);
    expect(two.status).toBe(400);
    expect(field.status).toBe(400);
  });

  it("rejects files over 5 MB with 413", async () => {
    const big = Buffer.concat([Buffer.from("%PDF-1.7\n"), Buffer.alloc(max_pdf_bytes)]);
    const res = await request(app).post("/cvs").attach("file", big, pdf_type);
    expect(res.status).toBe(413);
    expect(res.body.error).toMatchObject({ code: "file_too_large", details: { max_bytes: max_pdf_bytes } });
  });

  it("rejects a non-PDF even if it is called .pdf", async () => {
    const res = await request(app)
      .post("/cvs")
      .attach("file", Buffer.from("\u0089PNG\r\n\u001a\nimage"), pdf_type);
    expect(res.status).toBe(415);
    expect(res.body.error.code).toBe("unsupported_file_type");
  });

  it("rejects a broken PDF", async () => {
    const res = await request(app).post("/cvs").attach("file", Buffer.from("%PDF-1.7\nbroken"), pdf_type);
    expect(res.status).toBe(422);
    expect(res.body.error.code).toBe("invalid_pdf");
  });

  it("rejects a PDF without text before writing anything", async () => {
    const res = await request(app).post("/cvs").attach("file", await make_pdf_without_text(), pdf_type);
    expect(res.status).toBe(422);
    expect(res.body.error.code).toBe("cv_no_text");
  });

  it("rejects too long text and does not echo it", async () => {
    const res = await request(app).post("/cvs").attach("file", await make_long_pdf(32_000), pdf_type);
    expect(res.status).toBe(422);
    expect(res.body.error).toMatchObject({ code: "cv_text_too_long", details: { max_length: 30_000 } });
    expect(JSON.stringify(res.body)).not.toContain("Lorem ipsum");
  });
});

describe("CV text never reaches logs or error responses", () => {
  it("logs a database error without its detail (which can contain the row)", async () => {
    const cv_line = fictional_cv_lines[1]!;
    const failing_db = {
      query: async () => {
        throw Object.assign(new Error('new row for relation "cvs" violates check constraint'), {
          severity: "ERROR",
          code: "23514",
          constraint: "cvs_text_length_chk",
          detail: `Failing row contains (1, hash, ${cv_line}).`,
        });
      },
    } as unknown as db_client;
    const failing_app = create_app({ db: failing_db, cors_origins: [], cv_upload_enabled: true });

    const res = await request(failing_app)
      .post("/cvs")
      .attach("file", await make_pdf([fictional_cv_lines.join("\n")]), pdf_type);

    expect(res.status).toBe(500);
    expect(JSON.stringify(res.body)).not.toContain(cv_line);
    const logged = JSON.stringify(console_error.mock.calls);
    expect(logged).toContain("cvs_text_length_chk");
    expect(logged).not.toContain(cv_line);
  });
});

describe("GET and DELETE /cvs/:id access checks", () => {
  it.each(["get", "delete"] as const)("%s without X-CV-Token -> 401", async (method) => {
    const res = await request(app)[method]("/cvs/1");
    expect(res.status).toBe(401);
    expect(res.body.error.code).toBe("unauthorized");
  });

  it("rejects a malformed token with 401", async () => {
    const res = await request(app).get("/cvs/1").set("X-CV-Token", "short");
    expect(res.status).toBe(401);
  });

  it("validates the id", async () => {
    const res = await request(app).get("/cvs/abc").set("X-CV-Token", create_access_token());
    expect(res.status).toBe(400);
    expect(res.body.error.details).toEqual({ parameter: "id" });
  });
});

describe("CORS for the CV endpoints", () => {
  it("allows POST and DELETE with the X-CV-Token header from the frontend", async () => {
    const res = await request(app)
      .options("/cvs/1")
      .set("Origin", frontend_origin)
      .set("Access-Control-Request-Method", "DELETE")
      .set("Access-Control-Request-Headers", "x-cv-token");

    expect(res.status).toBe(204);
    expect(res.headers["access-control-allow-origin"]).toBe(frontend_origin);
    expect(res.headers["access-control-allow-methods"]).toContain("DELETE");
    expect(res.headers["access-control-allow-headers"]).toContain("X-CV-Token");
  });
});

describe("when the database is unreachable", () => {
  const pool = create_pool("postgresql://user:password@127.0.0.1:1/none");
  const down_app = create_app({ db: pool, cors_origins: [], cv_upload_enabled: true });
  afterAll(() => pool.end());

  it("GET /cvs/:id -> 503", async () => {
    const res = await request(down_app).get("/cvs/1").set("X-CV-Token", create_access_token());
    expect(res.status).toBe(503);
  });

  it("POST /cvs -> 503 after the text was extracted", async () => {
    const res = await request(down_app)
      .post("/cvs")
      .attach("file", await make_pdf([fictional_cv_lines.join("\n")]), pdf_type);
    expect(res.status).toBe(503);
  });
});
