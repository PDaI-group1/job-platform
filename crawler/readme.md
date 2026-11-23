# Crawler

Collects job postings from public Finnish job sites, normalizes them into one format and saves them into the _jobs_ table.

Sources at the 12.11.2026: _Jobly_

## Quick Start
Requires Python 3.11+ and Docker Desktop. All commands run from the repository root
1. Copy .env.example to .env
2. docker compose up -d db
3. python -m venv .venv
4. venv\Scripts\activat
5. pip install -r crawler/requirements-dev.txt

## Modes
 
| Mode | Requests | What happens | Use for |
|---|---|---|---|
| listing | 1 per 20 jobs | New jobs inserted **without description**; known jobs only marked as seen | Quick discovery |
| incremental | listing + 1 per new job | Full data for new jobs; known jobs marked as seen | Regular runs |
| full | listing + 1 per job | Every job re-parsed; changed jobs updated | After changing parsing or normalization rules |
 
Running any mode twice never creates duplicates, because _(source, source_job_id)_ is unique and saving is an upsert.
Data from a listing page never overwrites data that came from a job's own page.

## Options
 
```
python -m crawler run <source> [options]
 
  --mode {listing,incremental,full}  see above, incremental by default
  --limit N               stop after N jobs
  --start-page N          first listing page, 1-based
  --max-pages N           stop after N listing pages
  --delay SECONDS         pause between requests, overrides the source config
  --batch-size N          jobs per database transaction, 50 by default
  --dry-run               do not write to the database
  --output FILE           also write normalized jobs as JSON Lines
  --dump-html DIR         save every downloaded page
  --deactivate-missing    mark jobs that are no longer listed as inactive
  --fail-fast             stop at the first parse / validation error
  --no-robots             ignore robots.txt
  --config FILE           alternative source YAML
  --database-url URL      instead of .env.DATABASE_URL
  --stats-json FILE       write run statistics as JSON
 
python -m crawler sources                                  list sources
python -m crawler parse jobly page.html --kind detail      run a parser on a saved page
python -m crawler parse jobly page.html --kind listing --normalized
python -m crawler --log-level DEBUG run jobly ...          verbose logging
```

_Ctrl+C_ is safe: jobs collected so far are saved before exiting.

## Try it on Jobly

Every command below says roughly how long it takes.
 
**1. Dry run - 5 jobs into a file, nothing saved to the database** _~1 min_
 
```
python -m crawler run jobly --limit 5 --dry-run --output out/jobs.jsonl
```
 
Check _title, company_name, salary_*, _employment_type_, _deadline_at__ against the job on jobly.fi.
 
**2. Listing only - 2 pages, 40 jobs, no descriptions** _~20 s_
 
```
python -m crawler run jobly --mode listing --max-pages 2 --dry-run --output out/listing.jsonl
```
 
**3. Save one page into the database** _~3.5 min: 1 listing + 20 job pages_
 
```
python -m crawler run jobly --max-pages 1
```
 
The last log line shows _inserted=20_.
 
**4. Run it again - no duplicates** _~10 s: job pages of known jobs are not opened again_
 
```
python -m crawler run jobly --max-pages 1
```
 
Expected: _inserted=0, unchanged=20,_ _details_skipped_known=20_.
 
**5. Look at the data**
 
```
"SELECT source_job_id, left(title, 35) AS title, company_name, employment_type, salary_min, salary_max, salary_period
 FROM jobs WHERE source = 'jobly' ORDER BY id LIMIT 20;" |
```
 
**6. Another part of the listing, with statistics** _~1 min_
 
```
python -m crawler run jobly --start-page 10 --limit 5 --dry-run --stats-json out/stats.json
Get-Content out\stats.json
```

## Job board feeds (Greenhouse, Lever, Teamtailor)

Greenhouse and Lever publish a JSON API, Teamtailor an RSS feed. One request per employer returns all its jobs
with descriptions, so there are no detail pages and every mode makes the same requests.
Employers are listed in _config/sources/<board>.yml_; the list and the terms of use are in _docs/job-sources.md_.

**1. Dry run - all 15 employers into a file** _~1 min_

```
python -m crawler run feeds --dry-run --output out/feeds.jsonl
```

The log shows every employer: Oura: 95 jobs, 5 kept (Finland, no open applications).

**2. One board, one employer**

```
python -m crawler run greenhouse --employer oura --dry-run --output out/oura.jsonl
```

**3. Save to the database, then run again - no duplicates**

```
python -m crawler run feeds
python -m crawler run feeds        # inserted=0, unchanged=...
```

**4. Debug a parser on a saved feed**

```
python -m crawler run lever --employer alifsemi --dry-run --dump-html out/raw
python -m crawler parse lever out\raw\lever\feed\<file>.json --kind listing --normalized
```

What happens to every feed:
- **Fallback host:** Greenhouse and Lever accounts live in a US or an EU region. The US host is tried first,
  then the EU one (Lever answers an empty list on the wrong region, Greenhouse 404).
- **Filters**: only jobs in Finland are kept (any location, office or country of the job matches); "open application" postings are skipped.
- **If one employer fails, the rest continue.** The error is shown in the summary; _--deactivate-missing_
  is then skipped, so jobs of the failed employer are not marked inactive.
- **Mapping:** everything goes through the same normalizer as Jobly. Specials: Greenhouse descriptions are
  HTML entities, Lever dates are Unix milliseconds, Lever salaries in other currencies than EUR
  stay only in _raw_data_, Teamtailor remoteStatus none/hybrid/fully -> onsite/hybrid/remote.

## How crawler works
 
```
listing page -> Raw job listing data -> detail page -> Raw job detailed data merged -> normalized data -> PostgreSQL / JSON
```
 
1. **Source** (_sources/name/_) knows the site: URLs, pagination, which HTML holds what.
   It only extracts text and never interprets it.
2. **Normalizer** (_normalize/_) turns _RawJob_ into a validated _JobRecord_. All interpretation rules live here,
   shared by every source, so a salary or a date is understood the same way everywhere.
3. **Pipeline** (_core/pipeline.py_) runs it: modes, batching, statistics. One broken posting is logged
   and skipped and never stops the run.