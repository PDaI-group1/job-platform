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
