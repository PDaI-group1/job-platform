# CV processing: API ↔ worker contract

How an uploaded CV (#18) gets its skills profile. The API (Node.js, `backend/`) stores the CV text;
the matching worker (Python, `matching/worker.py`, a separate process) builds the profile with
`matching.cv_extract.build_cv_profile`. They only talk through the `cvs` table
(`migrations/002_cvs.sql`).

> **Status: proposal.** Agreed: Option A (worker polls the database), statuses
> `pending` / `processing` / `done` / `failed`, `profile_model TEXT`, 30 000 character limit,
> PDF not stored, contacts redacted by the worker. Column names other than `profile_model` and
> the SQL below are proposals for Alicja to confirm.

## Table `cvs`

| Column | Written by | Meaning |
|---|---|---|
| `id` | DB | Internal id |
| `access_token_hash` | API | Temporary owner check until accounts (#23). The worker ignores it |
| `text` | API | Extracted CV text: NFC, LF line breaks, 1–30 000 characters (code points, like Python `len`) |
| `profile_status` | API (`pending`), worker (the rest) | `pending` → `processing` → `done` or `failed` |
| `profile` | worker | `build_cv_profile(text).model_dump(mode="json")`; required when `done` |
| `profile_model` | worker | Model actually used, e.g. `matching.llm.MODEL` |
| `profile_error` | worker | Short technical reason when `failed`. **Never CV text.** Not shown to users |
| `attempts` | worker | Incremented on every claim; also identifies the attempt (see below) |
| `processing_started_at` | worker | When the current attempt was claimed |
| `profile_updated_at` | worker | When `done` or `failed` was written |
| `created_at`, `updated_at` | DB | `updated_at` is set by a trigger |

The API never writes the processing columns, and the worker never inserts or deletes rows.

## Statuses

```
pending ──claim──▶ processing ──success──▶ done
   ▲                    │
   └──── stuck, retry ──┤
                        └──error──────────▶ failed
```

## Worker steps

### 1. Claim one CV

```sql
UPDATE cvs
SET profile_status = 'processing',
    attempts = attempts + 1,
    processing_started_at = now()
WHERE id = (
    SELECT id FROM cvs
    WHERE profile_status = 'pending'
    ORDER BY created_at
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING id, attempts, text;
```

`SKIP LOCKED` lets several workers run without taking the same CV. Keep the returned
`attempts` value: it is the id of this attempt.

### 2. Save the result

```sql
UPDATE cvs
SET profile_status = 'done',
    profile = $profile_json,
    profile_model = $model,
    profile_error = NULL,
    profile_updated_at = now()
WHERE id = $id AND profile_status = 'processing' AND attempts = $attempt;
```

### 3. Save a failure

```sql
UPDATE cvs
SET profile_status = 'failed',
    profile = NULL,
    profile_model = $model,
    profile_error = $short_reason,
    profile_updated_at = now()
WHERE id = $id AND profile_status = 'processing' AND attempts = $attempt;
```

`ValueError` from `build_cv_profile` (empty or too long text) is permanent: write `failed`
right away. Retries for temporary Gemini errors are up to the worker.

### Two cases the conditions above handle

1. **The CV is deleted while it is processed.** `DELETE /cvs/:id` removes the row at once.
   Steps 2 and 3 then update 0 rows, and the worker **drops the result**. It must not insert
   the row again.
2. **A stuck attempt was retried.** If the worker resets a stuck `processing` CV, the next
   claim increments `attempts`. A late result of the old attempt has the old `attempts` value,
   updates 0 rows and is dropped, so it cannot overwrite the new attempt's result.

In both cases "0 rows updated" is normal and is not an error.

### Stuck `processing` (owned by the worker)

Timeout, number of retries and the exact query are the worker's decision. Example:

```sql
UPDATE cvs
SET profile_status = CASE WHEN attempts < $max_attempts THEN 'pending' ELSE 'failed' END,
    profile_error  = CASE WHEN attempts < $max_attempts THEN profile_error ELSE 'timed out' END,
    profile_updated_at = CASE WHEN attempts < $max_attempts THEN profile_updated_at ELSE now() END
WHERE profile_status = 'processing'
  AND processing_started_at < now() - $timeout::interval;
```

## What the API shows

`GET /cvs/:id` (see [api.md](api.md#cvs)) returns `status`, `profile` only when `done`, and for
`failed` a fixed, user-friendly message instead of `profile_error`. `profile_model` is internal.

## Privacy

- The API stores only the extracted text and the processing result. The PDF file and its name
  are not stored. CV text is not written to logs or error responses.
- Before calling Gemini the worker removes email addresses and phone numbers
  (`matching/privacy.py`). Names and the rest of the text are sent to the Gemini API.
- Skill normalisation runs locally (sentence-transformers) and sends nothing out.
- Deleting a CV removes the row: text, profile, model and error. Text already sent to Gemini
  cannot be recalled from our side.

## Deployment (#8)

The worker is a separate long-running process next to the API, with the same `DATABASE_URL`
and with `GEMINI_API_KEY` / `GEMINI_MODEL`. Migrations `002_cvs` (API, #18) and
`003_job_requirements` (worker, #17) must be applied before both start.
