# Job posting data model

This document defines the shared structure of a job posting. Scrapers produce it, the database stores it, the API returns it and the frontend renders it.

## Conventions

- **Naming:** _snake_case_ everywhere — in the database, in scraper output and in API JSON.
- **Timestamps:** ISO 8601 with timezone, in UTC (e.g. _2026-11-09T08:30:00Z_). Stored as _TIMESTAMPTZ_.
- **Enums:** lowercase _snake_case strings_ (e.g. _full_time_, _internship_).
- **Missing values:** _null_. Missing lists are _[]_.
- **Ids:** _id_ is our internal id, assigned by the database. The id on the original site is _source_job_id_.

## Core fields

| Field | Type (JSON) | Type (PostgreSQL) | Required | Description |
|---|---|---|---|---|
| `id` | integer | `BIGINT` identity | yes | Internal id, assigned by the database. Scrapers do not send it. |
| `title` | string | `TEXT` | yes | Job title as shown on the source. |
| `company_name` | string \| null | `TEXT` | no | Employer name as shown on the source. |
| `location` | string \| null | `TEXT` | no | Location as free text, e.g. `"Oulu"`, `"Helsinki, Espoo"`. |
| `remote_type` | enum \| null | `TEXT` + CHECK | no | `onsite`, `hybrid` or `remote`. `null` if the posting does not say. |
| `description` | string \| null | `TEXT` | no | Full job description, plain text (HTML stripped). |
| `url` | string | `TEXT` | yes | Link to the original posting. |
| `source` | string | `TEXT` | yes | Source site id: `duunitori`, `oikotie`, `tyomarkkinatori`, … |
| `published_at` | string (datetime) \| null | `TIMESTAMPTZ` | no | When the job was published on the source. |
| `scraped_at` | string (datetime) | `TIMESTAMPTZ` | yes | When our scraper collected (last saw) the posting. |

## Extended fields

| Field | Type (JSON) | Description |
|---|---|---|
| `source_job_id` | string | Id of the posting on the source site. `(source, source_job_id)` is unique — used for upserts. |
| `employment_type` | enum \| null | `full_time`, `part_time`, `internship`, `temporary`, `contract`. |
| `skills` | string[] | Normalized skill tags, lowercase, e.g. `["python", "sql"]`. |
| `language` | string \| null | Language of the posting: `fi`, `en`, `sv`. |
| `salary_min` / `salary_max` | number \| null | Salary range. Often missing in Finnish postings. |
| `salary_currency` | string | ISO 4217, default `EUR`. |
| `salary_period` | enum \| null | `hour`, `month`, `year`. |
| `deadline_at` | string (datetime) \| null | Application deadline. |
| `is_active` | boolean | `false` when the posting disappeared from the source. |
| `created_at` / `updated_at` | string (datetime) | Set by the database. |

Internal fields _content_hash_ and _raw_data_ are used only by scrapers and **are not returned by the API**.

## Example record

As returned by the API:

```json
{
  "id": 1,
  "title": "Junior Python Developer",
  "company_name": "Pohjoistech Oy",
  "location": "Oulu",
  "remote_type": "hybrid",
  "description": "Join our backend team building data pipelines for industrial IoT. Python, SQL and Docker experience is a plus.",
  "url": "https://example.com/jobs/seed-001",
  "source": "duunitori",
  "published_at": "2026-11-09T08:30:00Z",
  "scraped_at": "2026-11-11T06:00:00Z",
  "source_job_id": "seed-001",
  "employment_type": "full_time",
  "skills": ["python", "sql", "docker", "git"],
  "language": "en",
  "salary_min": 3200,
  "salary_max": 3800,
  "salary_currency": "EUR",
  "salary_period": "month",
  "deadline_at": "2026-12-02T21:59:59Z",
  "is_active": true,
  "created_at": "2026-11-11T06:00:00Z",
  "updated_at": "2026-11-11T06:00:00Z"
}
```

## Who uses what

- **Scrapers** produce every field except `id`, `created_at`, `updated_at` (set by the database) and write with
  `INSERT ... ON CONFLICT (source, source_job_id) DO UPDATE`.
- **API** returns the core and extended fields, without `content_hash` and `raw_data`.
- **Frontend** can rely on `id`, `title`, `url`, `source` and `scraped_at` always being present; everything else may be `null`.


## Approval

- [ ] Alicja
- [ ] Alex
- [ ] Kirill