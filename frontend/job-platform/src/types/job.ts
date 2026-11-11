export type remote_type = "onsite" | "hybrid" | "remote";

export type employment_type =
  | "full_time"
  | "part_time"
  | "internship"
  | "temporary"
  | "contract";

export type salary_period = "hour" | "month" | "year";

export type job = {
  id: number;
  title: string;
  company_name: string | null;
  location: string | null;
  remote_type: remote_type | null;
  description: string | null;
  url: string;
  source: string;
  published_at: string | null;
  scraped_at: string;

  source_job_id: string;
  employment_type: employment_type | null;
  skills: string[];
  language: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  salary_period: salary_period | null;
  deadline_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};
