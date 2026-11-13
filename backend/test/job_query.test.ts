import { describe, expect, it } from "vitest";
import { api_error } from "../src/errors.ts";
import {
  default_page_size,
  parse_job_id,
  parse_job_list_params,
} from "../src/jobs/job_query.ts";

// Checks that fn throws a 400 invalid_parameter error that names the parameter.
function expect_invalid(fn: () => unknown, parameter: string) {
  let thrown: unknown;
  try {
    fn();
  } catch (error) {
    thrown = error;
  }
  expect(thrown).toBeInstanceOf(api_error);
  const error = thrown as api_error;
  expect(error.status).toBe(400);
  expect(error.code).toBe("invalid_parameter");
  expect(error.details).toEqual({ parameter });
}

describe("parse_job_list_params", () => {
  it("uses defaults when nothing is given", () => {
    expect(parse_job_list_params({})).toEqual({
      page: 1,
      page_size: default_page_size,
      filters: {
        q: undefined,
        employment_type: undefined,
        remote_type: undefined,
        is_active: undefined,
      },
    });
  });

  it("parses every supported parameter", () => {
    const params = parse_job_list_params({
      page: "2",
      page_size: "50",
      q: "  react  ",
      employment_type: "internship",
      remote_type: "remote",
      is_active: "false",
    });

    expect(params).toEqual({
      page: 2,
      page_size: 50,
      filters: {
        q: "react",
        employment_type: "internship",
        remote_type: "remote",
        is_active: false,
      },
    });
  });

  it("treats empty values as not set", () => {
    const params = parse_job_list_params({ page: "", q: "   ", employment_type: "" });
    expect(params.page).toBe(1);
    expect(params.filters.q).toBeUndefined();
    expect(params.filters.employment_type).toBeUndefined();
  });

  it.each(["0", "-1", "1.5", "abc", "1e3", "100001"])("rejects page=%s", (page) => {
    expect_invalid(() => parse_job_list_params({ page }), "page");
  });

  it.each(["0", "101"])("rejects page_size=%s", (page_size) => {
    expect_invalid(() => parse_job_list_params({ page_size }), "page_size");
  });

  it("rejects a parameter given twice", () => {
    expect_invalid(() => parse_job_list_params({ page: ["1", "2"] }), "page");
  });

  it("rejects q longer than 200 characters", () => {
    expect(parse_job_list_params({ q: "a".repeat(200) }).filters.q).toHaveLength(200);
    expect_invalid(() => parse_job_list_params({ q: "a".repeat(201) }), "q");
  });

  it.each(["all", "FULL_TIME", "full-time"])("rejects employment_type=%s", (value) => {
    expect_invalid(() => parse_job_list_params({ employment_type: value }), "employment_type");
  });

  it("rejects an unknown remote_type", () => {
    expect_invalid(() => parse_job_list_params({ remote_type: "Remote" }), "remote_type");
  });

  it.each(["yes", "1", "TRUE"])("rejects is_active=%s", (value) => {
    expect_invalid(() => parse_job_list_params({ is_active: value }), "is_active");
  });

  it("ignores unknown parameters", () => {
    expect(parse_job_list_params({ sort: "title" }).page).toBe(1);
  });
});

describe("parse_job_id", () => {
  it.each(["1", "42", "9223372036854775807"])("accepts %s", (id) => {
    expect(parse_job_id(id)).toBe(id);
  });

  it.each(["0", "01", "-1", "1.5", "abc", "", "9223372036854775808"])(
    "rejects %s",
    (id) => {
      expect_invalid(() => parse_job_id(id), "id");
    },
  );
});
