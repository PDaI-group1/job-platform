# Job Sources - ATS Direct Feeds

Finnish employers whose public ATS job boards are crawled directly via documented feeds.
Each entry was verified: the feed returns live job data, and robots.txt was checked.

Last verified: 2026-11-12

---

## Platform terms of use

| Platform | Feed type | Terms |
|---|---|---|
| Greenhouse | JSON - `https://boards-api.greenhouse.io/v1/boards/{token}/jobs` | Job board data is public; GET endpoints need no authentication. Only submitting applications needs a key. [Greenhouse Job Board API docs](https://developers.greenhouse.io/job-board.html) |
| Lever | JSON - `https://api.lever.co/v0/postings/{slug}?mode=json` | Postings API is for building job sites; the docs state published jobs may be scraped by third parties. [Lever Postings API](https://github.com/lever/postings-api) |
| Teamtailor | RSS - `{career-site-url}/jobs.rss` | Teamtailor provides a jobs RSS feed so the data can be shared to other channels. [Teamtailor RSS feed guide](https://support.teamtailor.com/en/articles/11171756-rss-feed-how-to-guide) |

---

## Verified sources

| Company | Sector | ATS | Token / slug | Feed URL | Live jobs | Finland jobs | Verified |
|---|---|---|---|---|---|---|---|
| Wolt | Food tech | Greenhouse | `wolt` | https://boards-api.greenhouse.io/v1/boards/wolt/jobs | 50 | 3 | 2026-11-12 |
| Smartly.io | AdTech | Greenhouse | `smartlyio` | https://boards-api.greenhouse.io/v1/boards/smartlyio/jobs | 68 | 18 | 2026-11-12 |
| Solita | Consulting | Greenhouse | `solita` | https://boards-api.greenhouse.io/v1/boards/solita/jobs | 63 | 16 | 2026-11-12 |
| RELEX Solutions | Supply chain | Greenhouse | `relex` | https://boards-api.greenhouse.io/v1/boards/relex/jobs | 38 | 7 | 2026-11-12 |
| Supermetrics | SaaS | Greenhouse | `supermetricsoy` | https://boards-api.greenhouse.io/v1/boards/supermetricsoy/jobs | 9 | 4 | 2026-11-12 |
| Oura | Health tech | Greenhouse | `oura` | https://boards-api.greenhouse.io/v1/boards/oura/jobs | 95 | 5 | 2026-11-12 |
| Alif Semiconductor | Hardware / R&D | Lever | `alifsemi` | https://api.lever.co/v0/postings/alifsemi?mode=json | 11 | 6 | 2026-11-12 |
| The Upright Project | Impact tech | Lever | `uprightproject` | https://api.lever.co/v0/postings/uprightproject?mode=json | 3 | 2 | 2026-11-12 |
| Futurice | Consulting | Teamtailor | - | https://careers.futurice.com/jobs.rss | 9 | 6 | 2026-11-12 |
| Visma Finland | Software / SaaS | Teamtailor | - | https://vismafinland.teamtailor.com/jobs.rss | 3 | 3 | 2026-11-12 |
| Huawei Finland R&D | R&D | Teamtailor | - | https://huaweifinlandrnd.teamtailor.com/jobs.rss | 15 | 15 | 2026-11-12 |
| Codento | Consulting | Teamtailor | - | https://codento.teamtailor.com/jobs.rss | 10 | 2 | 2026-11-12 |
| Vincit | Consulting | Teamtailor | - | https://vincitoyj.teamtailor.com/jobs.rss | 6 | 5 | 2026-11-12 |
| Siili Solutions | Consulting / AI | Teamtailor | - | https://siili.teamtailor.com/jobs.rss | 6 | 5 | 2026-11-12 |
| Eficode | DevOps / consulting | Teamtailor | - | https://career.eficode.com/jobs.rss | 8 | 1 | 2026-11-12 |

---

## Greenhouse sources

### Wolt
- **Careers page**: https://careers.wolt.com
- **Board token**: `wolt`
- **Feed URL**: `https://boards-api.greenhouse.io/v1/boards/wolt/jobs`
- **Finnish locations**: Helsinki
- **Sector**: Food tech / delivery
- **Live jobs at verification**: 50 (3 in Helsinki)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: `Allow: /` - no disallow rules.
- **Notes**: 3 Helsinki roles are Engineering Manager positions. Filter `location.name` for Finnish roles.

### Smartly.io
- **Careers page**: https://www.smartly.io/careers
- **Board token**: `smartlyio`
- **Feed URL**: `https://boards-api.greenhouse.io/v1/boards/smartlyio/jobs`
- **Finnish locations**: Helsinki
- **Sector**: AdTech
- **Live jobs at verification**: 68 (18 in Helsinki)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: careers paths not disallowed.
- **Notes**: Helsinki is a major engineering hub alongside Berlin. Apply `location.name` filter for Finnish roles.

### Solita
- **Careers page**: https://www.solita.fi/en/open-positions/
- **Board token**: `solita`
- **Feed URL**: `https://boards-api.greenhouse.io/v1/boards/solita/jobs`
- **Finnish locations**: Helsinki, Lahti, Oulu, Tampere, Turku
- **Sector**: Consulting
- **Live jobs at verification**: 63 (16 in Finland)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: careers paths not disallowed.
- **Notes**: Solita uses a custom-domain careers experience on solita.fi but the underlying data comes from the `solita` Greenhouse board. Broad Finnish coverage across five cities.

### RELEX Solutions
- **Careers page**: https://www.relexsolutions.com/careers/
- **Board token**: `relex`
- **Feed URL**: `https://boards-api.greenhouse.io/v1/boards/relex/jobs`
- **Finnish locations**: Helsinki
- **Sector**: Supply chain software
- **Live jobs at verification**: 38 (7 in Helsinki)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: only `/wp-admin/` disallowed.
- **Notes**: Global company (US, UK, EU offices); filter `location.name` for Helsinki roles.

### Supermetrics
- **Careers page**: https://supermetrics.com/careers
- **Board token**: `supermetricsoy`
- **Feed URL**: `https://boards-api.greenhouse.io/v1/boards/supermetricsoy/jobs`
- **Finnish locations**: Helsinki
- **Sector**: SaaS / marketing analytics
- **Live jobs at verification**: 9 (4 in Helsinki)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: careers paths not disallowed.
- **Notes**: Supermetrics uses a custom-domain careers page that proxies Greenhouse; the board token is `supermetricsoy`.

### Oura
- **Careers page**: https://ouraring.com/careers
- **Board token**: `oura`
- **Feed URL**: `https://boards-api.greenhouse.io/v1/boards/oura/jobs`
- **Finnish locations**: Helsinki, Oulu
- **Sector**: Health tech / wearables
- **Live jobs at verification**: 95 (5 in Finland)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: only e-commerce paths disallowed (`/cart`, `/checkout`, `/my-account`, `/orders`).
- **Notes**: Large feed with strong IT focus - ML engineers, biosignal scientists, software designers, antenna engineers. Helsinki and Oulu offices both hiring. Filter `location.name` for Finnish roles.

---

## Lever sources

### Alif Semiconductor
- **Careers page**: https://www.alifsemi.com/company/careers/
- **Slug**: `alifsemi`
- **Feed URL**: `https://api.lever.co/v0/postings/alifsemi?mode=json`
- **Finnish locations**: Oulu
- **Sector**: Hardware / semiconductor R&D
- **Live jobs at verification**: 11 (6 in Oulu)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: only `/wp-admin/` disallowed.
- **Notes**: Oulu Technology Park R&D site. Remaining roles are in Pleasanton CA, Bangalore, and Singapore - filter `categories.location` for Oulu.

### The Upright Project
- **Careers page**: https://www.uprightproject.com/careers
- **Slug**: `uprightproject`
- **Feed URL**: `https://api.lever.co/v0/postings/uprightproject?mode=json`
- **Finnish locations**: Helsinki
- **Sector**: Impact tech / AI
- **Live jobs at verification**: 3 (2 real roles in Helsinki; 1 open application excluded)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: all paths allowed.
- **Notes**: Small feed; all roles are Helsinki-based hybrid.

---

## Teamtailor sources

Teamtailor's documented public feed is `/jobs.rss` on the company career site. All Teamtailor robots.txt files follow the same pattern: `/jobs/internal/` is disallowed; public jobs are accessible. `Content-Signal: ai-train=no` is present on all Teamtailor sites - this is a request to exclude content from AI training datasets, not a prohibition on job aggregation.

### Futurice
- **Career site**: https://careers.futurice.com
- **Feed URL**: `https://careers.futurice.com/jobs.rss`
- **Finnish locations**: Helsinki, Tampere
- **Sector**: Consulting / technology
- **Live jobs at verification**: 9 (6 in Finland)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: `/jobs/internal/` disallowed, public jobs accessible.
- **Notes**: Also has London-based roles; filter by location for Finnish postings.

### Visma Finland
- **Career site**: https://vismafinland.teamtailor.com
- **Feed URL**: `https://vismafinland.teamtailor.com/jobs.rss`
- **Finnish locations**: Helsinki, Lappeenranta, Turku
- **Sector**: Software / SaaS
- **Live jobs at verification**: 3 (all in Finland)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: `/jobs/internal/` disallowed, public jobs accessible.
- **Notes**: Visma Finland is the Finnish arm of Visma Group. All current roles are in Finland.

### Huawei Finland R&D
- **Career site**: https://huaweifinlandrnd.teamtailor.com
- **Feed URL**: `https://huaweifinlandrnd.teamtailor.com/jobs.rss`
- **Finnish locations**: Helsinki, Tampere
- **Sector**: R&D / telecoms
- **Live jobs at verification**: 15 (all in Finland)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: `/jobs/internal/` disallowed, public jobs accessible.
- **Notes**: Dedicated R&D centre board, separate from the main Huawei Finland commercial entity (`huaweifinland.teamtailor.com`). All roles are research positions in Helsinki and Tampere.

### Codento
- **Career site**: https://codento.teamtailor.com
- **Feed URL**: `https://codento.teamtailor.com/jobs.rss`
- **Finnish locations**: Helsinki
- **Sector**: Consulting / cloud
- **Live jobs at verification**: 10 (2 real roles in Finland; open application excluded)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: `/jobs/internal/` disallowed, public jobs accessible.
- **Notes**: Google Cloud-focused consultancy.

### Vincit
- **Career site**: https://vincitoyj.teamtailor.com
- **Feed URL**: `https://vincitoyj.teamtailor.com/jobs.rss`
- **Finnish locations**: Helsinki, Jyväskylä, Kuopio, Oulu, Tampere, Turku
- **Sector**: Consulting / digital services
- **Live jobs at verification**: 6 (5 real roles in Finland; 1 open application excluded)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: `/jobs/internal/` disallowed, public jobs accessible.
- **Notes**: Broad Finnish city coverage. Roles require right to work in Finland. AI and SAP consulting focus in current listings.

### Siili Solutions
- **Career site**: https://siili.teamtailor.com
- **Feed URL**: `https://siili.teamtailor.com/jobs.rss`
- **Finnish locations**: Helsinki, Joensuu, Jyväskylä, Kuopio, Oulu, Seinäjoki, Tampere
- **Sector**: Consulting / AI
- **Live jobs at verification**: 6 (5 real roles in Finland; 1 open application excluded)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: `/jobs/internal/` disallowed, public jobs accessible.
- **Notes**: Strong AI focus - current listings are almost entirely AI/data roles. Wide Finnish city coverage.

### Eficode
- **Career site**: https://career.eficode.com
- **Feed URL**: `https://career.eficode.com/jobs.rss`
- **Finnish locations**: Helsinki, Tampere
- **Sector**: DevOps / consulting
- **Live jobs at verification**: 8 (1 in Finland)
- **Verified**: 2026-11-12
- **Terms**: robots.txt checked: `/jobs/internal/` disallowed, public jobs accessible.
- **Notes**: Operates across 10 countries; most roles are non-Finnish at any given time. Filter by location - Finnish roles appear regularly for DevOps, AI, and Atlassian consulting positions.

---

## Excluded candidates

| Company | Reason |
|---|---|
| Reaktor | Custom careers platform on reaktor.com - no Greenhouse/Lever/Teamtailor feed |
| Gofore | Custom WordPress careers integration - no Greenhouse/Lever/Teamtailor feed |
| Aiven | board token `aiven36`: HTTP 404 on US host; EU host DNS not found |
| Sievo | ATS not identifiable from public pages - no accessible feed found |
| Nokia | Uses Oracle HCM - no public feed |
| Nordea | Uses SAP SuccessFactors (career5.successfactors.eu, company ID `nordeabank`) - no public feed |
| OP Financial Group | Uses SAP SuccessFactors (career2.successfactors.eu) via op-careers.fi - no public feed |
| Supercell | Custom proprietary ATS on supercell.com - no Greenhouse/Lever/Teamtailor feed |
| ICEYE | ATS not identifiable from public pages - no accessible feed found |
| Swappie | Teamtailor (careers.swappie.com) but no Finnish jobs in feed at verification |
| Varjo | Uses WHR (WorkHere Resources) - not in scope |
| Polar | Custom recruitment portal (polar.rekrytointi.com) - not in scope |
| Suunto | Uses CatsOne (suunto.catsone.com) - not in scope |

---

## Candidates for later (#15)

| Company | ATS | Feed URL | Notes |
|---|---|---|---|
| Hoxhunt | Ashby | https://api.ashbyhq.com/posting-api/job-board/hoxhunt | Helsinki-based cybersecurity training. Ashby is an approved source; feed not yet verified. |

---

## Rules for the crawler
- Read only the feeds listed here. Don't scrape employer websites, LinkedIn, Glassdoor or job aggregators.
- At most one request per source per crawl, and only a few crawls per day.
- Always store and show the link to the original posting and the employer's name.
- Skip "open application" postings; they aren't real jobs.
- If an employer asks us to stop, remove the source.

---

## First source for the crawler (#11)
Start with Greenhouse: one JSON request per board, no key, and the fields map directly to our data model. Oura covers Helsinki and Oulu; Wolt has the most Helsinki tech roles. Teamtailor (RSS/XML) is a good second source for #15.

---

## Mapping notes
- `source`: `greenhouse`, `lever` or `teamtailor` (matches docs/data-model.md).
- `source_job_id`: Greenhouse `id`, Lever `id`, Teamtailor: the numeric ID in the job URL.
- `description`: Greenhouse `content` (with `?content=true`) is HTML-escaped. Unescape it, then strip HTML to plain text. Lever timestamps are Unix milliseconds.
- Filter to jobs located in Finland before inserting; most boards also list jobs abroad.
- Greenhouse and Lever each have an EU host (`boards-api.eu.greenhouse.io`, `api.eu.lever.co`). Try the US host first, then EU.

---

## How to verify
```
powershell -ExecutionPolicy Bypass -File scripts\check-sources.ps1
```
Prints status, total jobs and Finland jobs per source. Don't commit `source-check.csv`.
