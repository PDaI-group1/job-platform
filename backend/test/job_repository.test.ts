import { describe, expect, it } from "vitest";
import {
  build_job_filters,
  build_job_order,
  escape_like,
} from "../src/jobs/job_repository.ts";

describe("build_job_filters", () => {
  it("returns no WHERE clause without filters", () => {
    expect(build_job_filters({})).toEqual({ where: "", values: [] });
  });

  it("numbers placeholders in order and keeps user input out of the SQL", () => {
    const { where, values } = build_job_filters({
      q: "dev'; DROP TABLE jobs; --",
      location: "Oulu",
      employment_type: "full_time",
      remote_type: "hybrid",
      is_active: true,
    });

    expect(where).toBe(
      "WHERE (title ILIKE $1 OR description ILIKE $1" +
        " OR company_name ILIKE $1 OR location ILIKE $1)" +
        " AND location ILIKE $2 AND employment_type = $3" +
        " AND remote_type = $4 AND is_active = $5",
    );
    expect(where).not.toContain("DROP");
    expect(values).toEqual([
      "%dev'; DROP TABLE jobs; --%",
      "%Oulu%",
      "full_time",
      "hybrid",
      true,
    ]);
  });

  it("escapes wildcards in location", () => {
    expect(build_job_filters({ location: "100%" }).values).toEqual(["%100\\%%"]);
  });

  it("keeps is_active=false as a filter", () => {
    expect(build_job_filters({ is_active: false })).toEqual({
      where: "WHERE is_active = $1",
      values: [false],
    });
  });
});

describe("build_job_order", () => {
  it("orders newest first by default, with a stable id tie-breaker", () => {
    expect(build_job_order("newest")).toBe("published_at DESC NULLS LAST, id DESC");
  });

  it("orders by company name A–Z, then newest first", () => {
    expect(build_job_order("company_name")).toBe(
      "lower(company_name) ASC NULLS LAST, published_at DESC NULLS LAST, id DESC",
    );
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
