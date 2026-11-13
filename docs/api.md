# Job list API

REST API that serves job postings from PostgreSQL. Code lives in _backend/_.

Base URL locally: **http://localhost:3000**. All responses are JSON in _snake_case_.
A job object has exactly the fields described in [data-model.md](data-model.md).

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service status; OK only when the database is reachable |
| GET | `/jobs` | Paginated list of jobs, newest first, with search and filters |
| GET | `/jobs/:id` | One job by internal _id_ |

### GET /health

| Status | Body |
|---|---|
| 200 | `{"status": "ok"}` |
| 503 | `{"status": "error", "database": "unreachable"}` |

### GET /jobs

All query parameters are optional and combine with AND. Unknown parameters are ignored.
Empty values (e.g. `q=`) are treated as not set. Each parameter may appear only once.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer 1–100000 | `1` | Page number, 1-based |
| `page_size` | integer 1–100 | `20` | Jobs per page |
| `q` | string, max 200 chars | — | Case-insensitive substring search in `title`, `company_name` and `location` |
| `employment_type` | enum | — | `full_time`, `part_time`, `internship`, `temporary`, `contract` |
| `remote_type` | enum | — | `onsite`, `hybrid`, `remote` |
| `is_active` | `true` \| `false` | — | Without it both active and inactive jobs are returned |

**Order:** `published_at` descending, jobs without `published_at` last, then `id` descending.

**Response 200:**

```json
{
  "data": [
    { "id": 3, "title": "Ohjelmistokehittäjä, harjoittelu", "...": "all job fields" }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 8,
    "total_pages": 1
  }
}
```

`total` is the number of jobs matching the filters. A page past the end returns `"data": []` with status 200.

Example: `GET /jobs?q=developer&employment_type=full_time&page=1&page_size=20`

### GET /jobs/:id

| Status | When |
|---|---|
| 200 | The job object (not wrapped), see the example in [data-model.md](data-model.md#example-record) |
| 400 | `id` is not a positive integer |
| 404 | No job with this `id` |

Inactive jobs are returned too, with `"is_active": false`.

## Value formats

- `id`, `salary_min`, `salary_max` are JSON numbers.
- Timestamps are ISO 8601 strings in UTC with milliseconds, e.g. `"2026-11-09T08:30:00.000Z"`.
- `skills` is always an array, possibly empty. Any other field except `id`, `title`, `url`, `source`, `scraped_at` may be `null`.
- `content_hash` and `raw_data` are never returned.

## Errors

Every error except `/health` uses the same body:

```json
{
  "error": {
    "code": "invalid_parameter",
    "message": "page_size must be an integer between 1 and 100",
    "details": { "parameter": "page_size" }
  }
}
```

| Status | `code` | When |
|---|---|---|
| 400 | `invalid_parameter` | A query parameter or `id` is invalid; `details.parameter` names it |
| 400 | `bad_request` | The request itself is malformed, e.g. broken URL encoding |
| 404 | `not_found` | Unknown job `id` or unknown route |
| 503 | `service_unavailable` | The database is down, unreachable or misconfigured |
| 500 | `internal_error` | Any other error; details are only in the server log |

## CORS

Only origins listed in `CORS_ORIGIN` may call the API from a browser. Allowed method: `GET`.

## Configuration

Read from environment variables; locally from _.env_ in the repository root (see _.env.example_).

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | yes | — | PostgreSQL connection string |
| `PORT` | no | `3000` | Port the API listens on |
| `CORS_ORIGIN` | no | `http://localhost:5173` | Comma-separated list of allowed frontend origins |
