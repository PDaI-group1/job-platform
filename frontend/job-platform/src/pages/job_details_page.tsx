import { Link, useParams } from "react-router-dom";
import { mock_jobs } from "../data/mock_jobs";

function format_date(date: string | null) {
  if (!date) return "Not specified";

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(date));
}

function format_salary(job: (typeof mock_jobs)[number]) {
  if (job.salary_min === null && job.salary_max === null) {
    return "Not specified";
  }

  const range =
    job.salary_min === job.salary_max
      ? `${job.salary_min}`
      : `${job.salary_min ?? "?"} - ${job.salary_max ?? "?"}`;

  return `${range} ${job.salary_currency}${
    job.salary_period ? ` / ${job.salary_period}` : ""
  }`;
}

export default function job_details_page() {
  const { id } = useParams();

  const job = mock_jobs.find((item) => item.id === Number(id));

  if (!job) {
    return (
      <main className="details_container">
        <Link to="/jobs" className="back_link">
          Back to jobs
        </Link>

        <h2>Job not found</h2>
        <p>This job listing does not exist.</p>
      </main>
    );
  }

  return (
    <main className="details_container">
      <Link to="/jobs" className="back_link">
        Back to jobs
      </Link>

      <section className="details_header">
        <div>
          <span className="details_source">{job.source}</span>

          <h1>{job.title}</h1>

          <p className="details_company">
            {job.company_name ?? "Unknown company"}
          </p>
        </div>

        <span className={job.is_active ? "active_badge" : "inactive_badge"}>
          {job.is_active ? "Active" : "Inactive"}
        </span>
      </section>

      <a
        href={job.url}
        target="_blank"
        rel="noopener noreferrer"
        className="apply_button"
      >
        Apply on original website
      </a>

      <div className="details_grid">
        <section className="details_main">
          <div className="details_card">
            <h2>Job description</h2>

            <p className="description_text">
              {job.description ?? "No description available."}
            </p>
          </div>

          <div className="details_card">
            <h2>Required skills</h2>

            {job.skills.length > 0 ? (
              <div className="job_tags">
                {job.skills.map((skill) => (
                  <span className="skill_tag" key={skill}>
                    {skill}
                  </span>
                ))}
              </div>
            ) : (
              <p>Not specified</p>
            )}
          </div>
        </section>

        <aside className="details_sidebar">
          <div className="details_card">
            <h2>Job information</h2>

            <div className="info_item">
              <span>Location</span>
              <strong>{job.location ?? "Not specified"}</strong>
            </div>

            <div className="info_item">
              <span>Employment type</span>
              <strong>
                {job.employment_type?.replaceAll("_", " ") ?? "Not specified"}
              </strong>
            </div>

            <div className="info_item">
              <span>Remote type</span>
              <strong>{job.remote_type ?? "Not specified"}</strong>
            </div>

            <div className="info_item">
              <span>Salary</span>
              <strong>{format_salary(job)}</strong>
            </div>

            <div className="info_item">
              <span>Language</span>
              <strong>{job.language ?? "Not specified"}</strong>
            </div>

            <div className="info_item">
              <span>Published</span>
              <strong>{format_date(job.published_at)}</strong>
            </div>

            <div className="info_item">
              <span>Application deadline</span>
              <strong>{format_date(job.deadline_at)}</strong>
            </div>
          </div>

          <div className="details_card">
            <h2>Source information</h2>

            <div className="info_item">
              <span>Source</span>
              <strong>{job.source}</strong>
            </div>

            <div className="info_item">
              <span>Source job ID</span>
              <strong>{job.source_job_id}</strong>
            </div>

            <div className="info_item">
              <span>Last scraped</span>
              <strong>{format_date(job.scraped_at)}</strong>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
