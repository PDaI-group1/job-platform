BEGIN;

-- CVs uploaded by users (#18). The API stores the text extracted from the PDF;
-- the matching worker (matching/worker.py) builds the profile from it.
-- The PDF file and its name are never stored. Contract: docs/cv-processing.md.
CREATE TABLE IF NOT EXISTS cvs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Temporary owner check until user accounts (#23): SHA-256 (hex) of the
    -- access token returned once by POST /cvs. The token itself is not stored.
    access_token_hash TEXT NOT NULL,

    -- Extracted plain text: LF line breaks, NFC, at most 30 000 characters
    -- (the same limit as matching/cv_extract.py).
    text TEXT NOT NULL,

    -- Written by the worker.
    profile_status TEXT NOT NULL DEFAULT 'pending',
    profile JSONB,
    profile_model TEXT,
    profile_error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    processing_started_at TIMESTAMPTZ,
    profile_updated_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT cvs_text_length_chk CHECK (char_length(text) BETWEEN 1 AND 30000),
    CONSTRAINT cvs_profile_status_chk CHECK (
        profile_status IN ('pending', 'processing', 'done', 'failed')
    ),
    CONSTRAINT cvs_profile_done_chk CHECK (profile_status <> 'done' OR profile IS NOT NULL),
    CONSTRAINT cvs_attempts_chk CHECK (attempts >= 0)
);

-- The worker picks the oldest pending CV and looks for stuck processing ones.
CREATE INDEX IF NOT EXISTS cvs_queue_idx ON cvs (created_at)
    WHERE profile_status IN ('pending', 'processing');

-- set_updated_at() is defined in 001_create_jobs.sql.
DROP TRIGGER IF EXISTS cvs_set_updated_at ON cvs;
CREATE TRIGGER cvs_set_updated_at
    BEFORE UPDATE ON cvs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
