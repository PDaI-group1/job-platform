import type { job } from "../types/job";

type job_list_props = {
  jobs: job[];
};

const format_date = (date: string | null) => {
  if (!date) return "Unknown";

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(date));
};

const format_salary = (job: job) => {
  if (job.salary_min === null && job.salary_max === null) {
    return "Not specified";
  }

  const amount =
    job.salary_min === job.salary_max
      ? `${job.salary_min}`
      : `${job.salary_min ?? "?"} - ${job.salary_max ?? "?"}`;

  const period = job.salary_period ? ` / ${job.salary_period}` : "";

  return `${amount} ${job.salary_currency}${period}`;
};

export default function job_list({ jobs }: job_list_props) {
  if (jobs.length === 0) {
    return <div className="empty_state">No jobs found.</div>;
  }

  return (
    <div className="job_list">
      {jobs.map((job) => (
        <a
          className="job_card"
          href={job.url}
          target="_blank"
          rel="noreferrer"
          key={job.id}
        >
          <div className="job_main">
            <div className="job_heading">
              <h3>{job.title}</h3>
              <span className="job_status">
                {job.is_active ? "Active" : "Inactive"}
              </span>
            </div>

            <p className="job_company">
              {job.company_name ?? "Unknown company"}
            </p>

            <div className="job_details">
              <span>📍 {job.location ?? "Location unknown"}</span>
              <span>
                {job.employment_type?.replaceAll("_", " ") ?? "Not specified"}
              </span>
              <span>{job.remote_type ?? "Not specified"}</span>
            </div>

            <div className="job_tags">
              {job.skills.map((skill) => (
                <span className="skill_tag" key={skill}>
                  {skill}
                </span>
              ))}
            </div>
          </div>

          <div className="job_meta">
            <strong>{format_salary(job)}</strong>
            <span>Published: {format_date(job.published_at)}</span>
            <span>Source: {job.source}</span>
          </div>
        </a>
      ))}
    </div>
  );
}
