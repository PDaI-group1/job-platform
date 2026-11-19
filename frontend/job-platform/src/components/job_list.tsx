import { Link } from "react-router-dom";
import type { job } from "../types/job";

type job_list_props = {
  jobs: job[];
};

export default function job_list({ jobs }: job_list_props) {
  if (jobs.length === 0) {
    return <div className="empty_state">No jobs found.</div>;
  }

  return (
    <div className="job_list">
      {jobs.map((job) => (
        <Link className="job_card" to={`/jobs/${job.id}`} key={job.id}>
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
              <span>{job.location ?? "Location unknown"}</span>
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
            <strong>
              {job.salary_min !== null || job.salary_max !== null
                ? `${job.salary_min ?? "?"} - ${job.salary_max ?? "?"} ${job.salary_currency}`
                : "Salary not specified"}
            </strong>

            <span>{job.source}</span>
          </div>
        </Link>
      ))}
    </div>
  );
}
