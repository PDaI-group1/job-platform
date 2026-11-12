BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS jobs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source TEXT NOT NULL,
    source_job_id TEXT NOT NULL,
    url TEXT NOT NULL,

    title TEXT NOT NULL,
    company_name TEXT,
    location TEXT,
    remote_type TEXT,
    employment_type TEXT,
    description TEXT,
    skills TEXT[] NOT NULL DEFAULT '{}',
    language TEXT,

    salary_min NUMERIC(10, 2),
    salary_max NUMERIC(10, 2),
    salary_currency CHAR(3) NOT NULL DEFAULT 'EUR',
    salary_period TEXT,

    published_at TIMESTAMPTZ,
    deadline_at TIMESTAMPTZ,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    content_hash TEXT,
    raw_data JSONB,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT jobs_source_job_uniq UNIQUE (source, source_job_id),
    CONSTRAINT jobs_remote_type_chk CHECK (remote_type IS NULL OR remote_type IN ('onsite', 'hybrid', 'remote')),
    CONSTRAINT jobs_employment_type_chk CHECK (
        employment_type IS NULL
        OR employment_type IN ('full_time', 'part_time', 'internship', 'temporary', 'contract')
    ),
    CONSTRAINT jobs_salary_period_chk CHECK (salary_period IS NULL OR salary_period IN ('hour', 'month', 'year')),
    CONSTRAINT jobs_salary_range_chk CHECK (
        salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max
    )
);

CREATE INDEX IF NOT EXISTS jobs_published_at_idx ON jobs (published_at DESC);
CREATE INDEX IF NOT EXISTS jobs_company_name_idx ON jobs (company_name);
CREATE INDEX IF NOT EXISTS jobs_location_idx ON jobs (location);
CREATE INDEX IF NOT EXISTS jobs_skills_gin_idx ON jobs USING GIN (skills);
CREATE INDEX IF NOT EXISTS jobs_active_idx ON jobs (is_active) WHERE is_active;

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS jobs_set_updated_at ON jobs;
CREATE TRIGGER jobs_set_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
