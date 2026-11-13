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

On Windows, if every test file fails with _Cannot read properties of undefined (reading 'config')_,
the terminal opened the folder with a lowercase drive letter (_d:\\..._). Vitest then loads itself twice.
Run the tests from PowerShell or after _cd D:\\Workfield\\job-platform\\backend_ with an uppercase letter.
