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
| GET | `/stats` | Catalog totals for the dashboard cards |
| POST | `/cvs` | Upload a CV as PDF; the text is extracted and queued for profiling |
| GET | `/cvs/:id` | Processing status and, when done, the skills profile |
| DELETE | `/cvs/:id` | Delete a CV with its text and profile |

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

### GET /stats

Totals for the whole catalog. Search and filters do not affect them; the number of
search results is `pagination.total` of `GET /jobs`. Query parameters are ignored.

**Response 200:**

```json
{
  "total": 150,
  "active": 132,
  "companies": 24
}
```

| Field | Description |
|---|---|
| `total` | All jobs in the database, active and inactive |
| `active` | Jobs with `is_active = true` |
| `companies` | Distinct `company_name` values, ignoring case and surrounding spaces; jobs without a company are not counted |

Errors: `503` / `500` as for the other endpoints.

## CVs

Upload a CV (#18). The API extracts the text from the PDF and stores only the text; the PDF and
its file name are not kept. A separate worker builds the skills profile; how the two work
together is described in [cv-processing.md](cv-processing.md).

> **Upload is off by default** (`CV_UPLOAD_ENABLED=false`) until the temporary access token is
> agreed: [decisions/cv-temporary-access-token.md](decisions/cv-temporary-access-token.md).
> The 5 MB limit, the `X-CV-Token` header and the polling interval are proposals.

### POST /cvs

`multipart/form-data` with exactly one field, `file`: the PDF, at most 5 MB.

**Response 201:**

```json
{
  "id": 12,
  "access_token": "kQ3v…43 characters…",
  "status": "pending",
  "text_length": 1834,
  "created_at": "2026-11-28T10:15:00.000Z"
}
```

`access_token` is returned **only here**. Send it as the `X-CV-Token` header to read or delete
the CV. `text_length` is the number of characters of the extracted text.

The text keeps the PDF's line breaks (LF), Finnish and other letters as they are; empty lines
between paragraphs are not kept. A PDF is rejected before anything is stored when:

| Status | `code` | When |
|---|---|---|
| 400 | `invalid_parameter` | No file, more than one file, other form fields, or a field other than `file` |
| 413 | `file_too_large` | The file is larger than 5 MB (`details.max_bytes`) |
| 415 | `unsupported_file_type` | The file is not a PDF (checked by content, not by name) |
| 422 | `invalid_pdf` | The PDF is damaged or password-protected |
| 422 | `cv_no_text` | No text could be extracted, e.g. a scanned document |
| 422 | `cv_text_too_long` | More than 30 000 characters of text (`details.max_length`); the text is not cut |
| 503 | `feature_disabled` | Upload is switched off |

### GET /cvs/:id

Header `X-CV-Token: <access_token>`.

**Response 200:**

```json
{
  "id": 12,
  "status": "done",
  "profile": {
    "skills": ["JavaScript", "PostgreSQL"],
    "experience": [{ "title": "Junior-ohjelmistokehittäjä", "years": 1 }],
    "education": ["Tietojenkäsittelytieteen kandidaatti"],
    "languages": [{ "code": "fi", "level": "native" }],
    "skill_matches": [{ "raw": "JavaScript", "label": "JavaScript", "score": 1 }]
  },
  "error": null,
  "text_length": 1834,
  "created_at": "2026-11-28T10:15:00.000Z",
  "updated_at": "2026-11-28T10:15:09.000Z"
}
```

| `status` | `profile` | `error` |
|---|---|---|
| `pending` | `null` | `null` — waiting for the worker |
| `processing` | `null` | `null` — the worker is building the profile |
| `done` | the profile, see `CVProfile` in `matching/cv_schemas.py` | `null` |
| `failed` | `null` | a short message that can be shown to the user |

Poll while the status is `pending` or `processing` (proposal: every 3 seconds).

### DELETE /cvs/:id

Header `X-CV-Token: <access_token>`. **204** with no body. The text and the profile are removed
from the database, also while the worker is still processing the CV.

### Access errors (GET and DELETE)

| Status | `code` | When |
|---|---|---|
| 400 | `invalid_parameter` | `id` is not a positive integer |
| 401 | `unauthorized` | `X-CV-Token` is missing or malformed |
| 404 | `not_found` | No CV with this `id`, or the token does not belong to it |

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
| 401 | `unauthorized` | Missing or malformed `X-CV-Token` (CV endpoints) |
| 404 | `not_found` | Unknown job or CV `id`, or unknown route |
| 413, 415, 422 | see [POST /cvs](#post-cvs) | Rejected CV upload |
| 503 | `service_unavailable` | The database is down, unreachable or misconfigured |
| 503 | `feature_disabled` | CV upload is switched off |
| 500 | `internal_error` | Any other error; details are only in the server log |

Error responses and server logs never contain CV text.

## CORS

Only origins listed in `CORS_ORIGIN` may call the API from a browser. Allowed methods: `GET`,
`POST`, `DELETE`; allowed request headers: `Content-Type`, `X-CV-Token`.

## Configuration

Read from environment variables; locally from _.env_ in the repository root (see _.env.example_).

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | yes | — | PostgreSQL connection string |
| `PORT` | no | `3000` | Port the API listens on |
| `CORS_ORIGIN` | no | `http://localhost:5173` | Comma-separated list of allowed frontend origins |
| `CV_UPLOAD_ENABLED` | no | `false` | `true` turns on `POST /cvs` |
