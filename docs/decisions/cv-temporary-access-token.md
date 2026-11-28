# CV access before user accounts: temporary token

- **Status:** Proposed — needs the team's agreement before CV upload is switched on
- **Date:** 2026-11-28
- **Related:** #18 Upload a CV, #23 Simple user accounts, #26 Let users delete their data

## Context

A CV may only be read and deleted by the person who uploaded it. User accounts (#23) are planned
for week 4 and do not exist yet, so there is no owner to check against. Until this is decided,
`POST /cvs` stays off (`CV_UPLOAD_ENABLED=false`), so no real CVs can be uploaded.

## Proposal

1. `POST /cvs` creates a random access token (32 bytes, base64url) and returns it **once** in the
   response. The database keeps only its SHA-256 hash (`cvs.access_token_hash`).
2. The frontend keeps the token (e.g. `localStorage`) and sends it as the `X-CV-Token` header to
   `GET /cvs/:id` and `DELETE /cvs/:id`.
3. Missing or malformed header → `401`. Wrong token or unknown id → `404`, so nobody can probe
   which CV ids exist.
4. A lost token means the CV cannot be opened or deleted from the UI anymore. Acceptable for the
   demo period; such CVs can be removed by the team on request.
5. With #23 a migration adds `cvs.user_id`; new CVs belong to the logged-in user and the token is
   removed.

## Alternatives

- **Wait for #23:** no CV upload until week 4; the frontend and the worker cannot be tested end
  to end before then.
- **Anonymous session cookie:** similar security, but needs cookie and CORS-with-credentials
  setup now and would be replaced by #23 anyway.

## Open questions

- Header name (`X-CV-Token`) and storing the token in `localStorage` — fine for the frontend?
- Is one CV per upload enough, or should a user see a list of their CVs before #23?
