import { invalid_parameter } from "../errors.ts";
import type { employment_type, remote_type } from "../types/job.ts";

export const default_page_size = 20;
export const max_page_size = 100;
// Keeps OFFSET within a sane range; nobody pages this far.
export const max_page = 100_000;
export const max_search_length = 200;
export const max_location_length = 100;

// newest: published_at, newest first (default); company: company name A–Z.
export const job_sorts = ["newest", "company"] as const;
export type job_sort = (typeof job_sorts)[number];
export const default_sort: job_sort = "newest";

// Same values as the CHECK constraints in migrations/001_create_jobs.sql.
export const employment_types: readonly employment_type[] = [
  "full_time",
  "part_time",
  "internship",
  "temporary",
  "contract",
];
export const remote_types: readonly remote_type[] = ["onsite", "hybrid", "remote"];

export type job_list_filters = {
  q?: string;
  location?: string;
  employment_type?: employment_type;
  remote_type?: remote_type;
  is_active?: boolean;
};

export type job_list_params = {
  page: number;
  page_size: number;
  sort: job_sort;
  filters: job_list_filters;
};

type query_values = Record<string, unknown>;

// Unknown parameters are ignored; known ones are validated strictly.
export function parse_job_list_params(query: query_values): job_list_params {
  return {
    page: parse_int_param(query, "page", { min: 1, max: max_page, fallback: 1 }),
    page_size: parse_int_param(query, "page_size", {
      min: 1,
      max: max_page_size,
      fallback: default_page_size,
    }),
    sort: parse_enum_param(query, "sort", job_sorts) ?? default_sort,
    filters: {
      q: parse_text_param(query, "q", max_search_length),
      location: parse_text_param(query, "location", max_location_length),
      employment_type: parse_enum_param(query, "employment_type", employment_types),
      remote_type: parse_enum_param(query, "remote_type", remote_types),
      is_active: parse_bool_param(query, "is_active"),
    },
  };
}

// Ids are BIGINT in the database. The value stays a string so it is passed to
// PostgreSQL as is, without going through a JS number.
const max_bigint = 9223372036854775807n;

export function parse_job_id(value: string): string {
  if (!/^[1-9]\d{0,18}$/.test(value) || BigInt(value) > max_bigint) {
    throw invalid_parameter("id", "id must be a positive integer");
  }
  return value;
}

// Returns undefined when the parameter is missing or empty.
function read_single(query: query_values, name: string): string | undefined {
  const value = query[name];
  if (value === undefined) return undefined;
  if (Array.isArray(value)) {
    throw invalid_parameter(name, `${name} must be specified only once`);
  }
  if (typeof value !== "string") {
    throw invalid_parameter(name, `${name} must be a string`);
  }
  const trimmed = value.trim();
  return trimmed === "" ? undefined : trimmed;
}

function parse_text_param(
  query: query_values,
  name: string,
  max_length: number,
): string | undefined {
  const value = read_single(query, name);
  if (value !== undefined && value.length > max_length) {
    throw invalid_parameter(name, `${name} must be at most ${max_length} characters`);
  }
  return value;
}

function parse_enum_param<T extends string>(
  query: query_values,
  name: string,
  allowed: readonly T[],
): T | undefined {
  const value = read_single(query, name);
  if (value === undefined) return undefined;
  if (!allowed.includes(value as T)) {
    throw invalid_parameter(name, `${name} must be one of: ${allowed.join(", ")}`);
  }
  return value as T;
}

function parse_bool_param(query: query_values, name: string): boolean | undefined {
  const value = read_single(query, name);
  if (value === undefined) return undefined;
  if (value === "true") return true;
  if (value === "false") return false;
  throw invalid_parameter(name, `${name} must be true or false`);
}

function parse_int_param(
  query: query_values,
  name: string,
  { min, max, fallback }: { min: number; max: number; fallback: number },
): number {
  const raw = read_single(query, name);
  if (raw === undefined) return fallback;

  const value = /^\d+$/.test(raw) ? Number(raw) : NaN;
  if (!Number.isSafeInteger(value) || value < min || value > max) {
    throw invalid_parameter(
      name,
      `${name} must be an integer between ${min} and ${max}`,
    );
  }
  return value;
}
