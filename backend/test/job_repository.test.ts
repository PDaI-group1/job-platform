import { describe, expect, it } from "vitest";
import { build_job_filters, escape_like } from "../src/jobs/job_repository.ts";

describe("build_job_filters", () => {
  it("returns no WHERE clause without filters", () => {
    expect(build_job_filters({})).toEqual({ where: "", values: [] });
  });

  it("numbers placeholders in order and keeps user input out of the SQL", () => {
    const { where, values } = build_job_filters({
      q: "dev'; DROP TABLE jobs; --",
      employment_type: "full_time",
      remote_type: "hybrid",
      is_active: true,
    });

    expect(where).toBe(
      "WHERE (title ILIKE $1 OR company_name ILIKE $1 OR location ILIKE $1)" +
        " AND employment_type = $2 AND remote_type = $3 AND is_active = $4",
    );
    expect(where).not.toContain("DROP");
    expect(values).toEqual(["%dev'; DROP TABLE jobs; --%", "full_time", "hybrid", true]);
  });

  it("keeps is_active=false as a filter", () => {
    expect(build_job_filters({ is_active: false })).toEqual({
      where: "WHERE is_active = $1",
      values: [false],
    });
  });
});

describe("escape_like", () => {
  it("escapes LIKE wildcards and the escape character", () => {
    expect(escape_like("50%_off\\")).toBe("50\\%\\_off\\\\");
  });

  it("leaves normal text unchanged", () => {
    expect(escape_like("Ohjelmistokehittäjä")).toBe("Ohjelmistokehittäjä");
  });
});
