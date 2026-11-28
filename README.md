# Finnish Student Job Platform

A web platform for students and graduates in Finland that aggregates job postings from multiple sources, uses AI to match CVs against job ads, and lets applicants track their applications and rate employers' hiring processes.

## Features

> Coming soon.

## Project structure

```
job-platform/
├── frontend/       Web app
├── backend/        REST API server
├── ai-service/     CV parsing and job match scoring (Python)
├── scrapers/       Crawlers for Finnish job boards
└── docs/           Architecture, API reference, guides
```

## Getting started

### Database
Requires Docker Desktop

Run: docker compose up -d db

On the first start of an empty volume the container applies all files in _migrations/_ in
filename order and, if _SEED_DB=true_, loads example data from _seeds/_.

Connect URI: **postgresql://jobplatform-admin:jobplatform-password@localhost:5432/jobplatform-db**

Connect via Docker: **docker compose exec db psql -U jobplatform-admin -d jobplatform-db**

If port 5432 is already taken by a local PostgreSQL, set _POSTGRES_PORT=5433_ in _.env_ and use the same port in _DATABASE_URL_.

### Backend API
Requires Node.js 24+ and the database running. Copy _.env.example_ to _.env_ in the repository root first.

```
cd backend
npm install
npm run dev
```

The API runs on **http://localhost:3000**; check it with **http://localhost:3000/health**.
Endpoints are described in [docs/api.md](docs/api.md).

| Command | What it does |
|---|---|
| npm run dev | Start the API and restart on file changes |
| npm run build | Compile to _dist/_ |
| npm start | Run the compiled API from _dist/_ |
| npm run typecheck | TypeScript check without output |
| npm run lint | Oxlint |
| npm test | Unit and API tests; tests that need the database run only when _DATABASE_URL_ is set |

The CV tests write to the database, so they run only against a separate test database
(_TEST_DATABASE_URL_, whose name must contain "test") or in CI. One-time setup with Docker:

```
docker compose exec db psql -U jobplatform-admin -d postgres -c "CREATE DATABASE jobplatform_test"
docker compose exec db psql -U jobplatform-admin -d jobplatform_test -f /migrations/001_create_jobs.sql
docker compose exec db psql -U jobplatform-admin -d jobplatform_test -f /seeds/001_jobs_seed.sql
docker compose exec db psql -U jobplatform-admin -d jobplatform_test -f /migrations/002_cvs.sql
```

Then set _TEST_DATABASE_URL_ in _.env_ (see _.env.example_).

New migrations are applied automatically only to an empty volume. To add _002_cvs.sql_ to an
existing local database without losing data:
_docker compose exec db psql -U jobplatform-admin -d jobplatform-db -f /migrations/002_cvs.sql_

CV upload (_POST /cvs_) is off unless _CV_UPLOAD_ENABLED=true_.

On Windows, if every test file fails with _Cannot read properties of undefined (reading 'config')_,
the terminal opened the folder with a lowercase drive letter (_d:\\..._). Vitest then loads itself twice.
Run the tests from PowerShell or after _cd D:\\Workfield\\job-platform\\backend_ with an uppercase letter.
