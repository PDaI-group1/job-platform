import { useMemo, useState } from "react";
import { mock_jobs } from "./data/mock_jobs";
import JobList from "./components/job_list";
import "./App.css";

function App() {
  const [search_query, set_search_query] = useState("");
  const [employment_filter, set_employment_filter] = useState("all");

  const filtered_jobs = useMemo(() => {
    return mock_jobs.filter((job) => {
      const query = search_query.toLowerCase();

      const matches_search =
        job.title.toLowerCase().includes(query) ||
        (job.company_name?.toLowerCase().includes(query) ?? false) ||
        (job.location?.toLowerCase().includes(query) ?? false);

      const matches_employment =
        employment_filter === "all" ||
        job.employment_type === employment_filter;

      return matches_search && matches_employment;
    });
  }, [search_query, employment_filter]);

  const active_jobs = mock_jobs.filter((job) => job.is_active).length;

  return (
    <main className="dashboard">
      <header className="page_header">
        <div>
          <h1>Job Board</h1>
          <p>Discover job opportunities in one place.</p>
        </div>

        <span className="total_count">{mock_jobs.length} jobs collected</span>
      </header>

      <section className="stats_grid">
        <div className="stat_card">
          <span>Total jobs</span>
          <strong>{mock_jobs.length}</strong>
        </div>

        <div className="stat_card">
          <span>Active jobs</span>
          <strong>{active_jobs}</strong>
        </div>

        <div className="stat_card">
          <span>Companies</span>
          <strong>
            {
              new Set(mock_jobs.map((job) => job.company_name).filter(Boolean))
                .size
            }
          </strong>
        </div>
      </section>

      <section className="jobs_section">
        <div className="section_header">
          <div>
            <h2>Available positions</h2>
            <p>{filtered_jobs.length} results found</p>
          </div>
        </div>

        <div className="filters">
          <input
            type="text"
            placeholder="Search jobs, companies, locations..."
            value={search_query}
            onChange={(event) => set_search_query(event.target.value)}
          />

          <select
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
        </div>

        <JobList jobs={filtered_jobs} />
      </section>
    </main>
  );
}

export default App;
