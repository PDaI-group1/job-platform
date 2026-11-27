import { useEffect, useState } from "react";
import JobList from "../components/job_list";
import type { job } from "../types/job";

type jobs_response = {
  data: job[];
  pagination: {
    total: number;
  };
};

function JobsPage() {
  const [search_query, set_search_query] = useState("");
  const [location_filter, set_location_filter] = useState("");
  const [employment_filter, set_employment_filter] = useState("all");
  const [remote_filter, set_remote_filter] = useState("all");
  const [sort_order, set_sort_order] = useState("newest");
  const [jobs, set_jobs] = useState<job[]>([]);
  const [total, set_total] = useState(0);
  const [loading, set_loading] = useState(true);
  const [error, set_error] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load_jobs() {
      set_loading(true);
      set_error(null);

      const api_base_url = import.meta.env.VITE_API_BASE_URL?.trim();
      if (!api_base_url) {
        set_error("Set VITE_API_BASE_URL to connect to the jobs API.");
        set_loading(false);
        return;
      }

      try {
        const jobs_url = new URL(`${api_base_url.replace(/\/+$/, "")}/jobs`);
        const query = search_query.trim();
        if (query) jobs_url.searchParams.set("q", query);
        const location = location_filter.trim();
        if (location) jobs_url.searchParams.set("location", location);
        if (employment_filter !== "all") {
          jobs_url.searchParams.set("employment_type", employment_filter);
        }
        if (remote_filter !== "all") {
          jobs_url.searchParams.set("remote_type", remote_filter);
        }
        jobs_url.searchParams.set("sort", sort_order);

        const response = await fetch(jobs_url, { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Unable to load jobs (HTTP ${response.status}).`);
        }

        const result = (await response.json()) as jobs_response;
        set_jobs(result.data);
        set_total(result.pagination.total);
      } catch (request_error) {
        if (!controller.signal.aborted) {
          set_error(
            request_error instanceof Error
              ? request_error.message
              : "Unable to load jobs.",
          );
        }
      } finally {
        if (!controller.signal.aborted) set_loading(false);
      }
    }

    void load_jobs();
    return () => controller.abort();
  }, [employment_filter, location_filter, remote_filter, search_query, sort_order]);

  return (
    <main className="dashboard">
      <header className="page_header">
        <div>
          <h1>Job Board</h1>
          <p>Discover job opportunities in one place.</p>
        </div>

        <span className="total_count">
          {loading
            ? "Loading jobs..."
            : error
              ? "Jobs unavailable"
              : `${total} jobs found`}
        </span>
      </header>

      <section className="jobs_section">
        <div className="section_header">
          <div>
            <h2>Available positions</h2>
            <p>
              {loading
                ? "Loading results..."
                : error
                  ? "Unable to load results"
                  : `${total} results found`}
            </p>
          </div>
        </div>

        <div className="filters">
          <input
            type="text"
            placeholder="Search job titles or descriptions..."
            aria-label="Search job titles and descriptions"
            value={search_query}
            onChange={(event) => set_search_query(event.target.value)}
          />

          <input
            type="text"
            placeholder="Filter by location..."
            aria-label="Filter by location"
            value={location_filter}
            onChange={(event) => set_location_filter(event.target.value)}
          />

          <select
            aria-label="Filter by employment type"
            value={employment_filter}
            onChange={(event) => set_employment_filter(event.target.value)}
          >
            <option value="all">All employment types</option>
            <option value="full_time">Full time</option>
            <option value="part_time">Part time</option>
            <option value="internship">Internship</option>
            <option value="temporary">Temporary</option>
            <option value="contract">Contract</option>
          </select>

          <select
            aria-label="Filter by remote type"
            value={remote_filter}
            onChange={(event) => set_remote_filter(event.target.value)}
          >
            <option value="all">All work arrangements</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">On-site</option>
          </select>

          <select
            aria-label="Sort jobs"
            value={sort_order}
            onChange={(event) => set_sort_order(event.target.value)}
          >
            <option value="newest">Newest first</option>
            <option value="company_name">Company name (A–Z)</option>
          </select>
        </div>

        {loading ? (
          <p className="empty_state" role="status">
            Loading jobs...
          </p>
        ) : error ? (
          <p className="empty_state" role="alert">
            {error}
          </p>
        ) : (
          <JobList jobs={jobs} />
        )}
      </section>
    </main>
  );
}

export default JobsPage;
