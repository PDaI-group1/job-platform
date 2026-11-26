# matching/

LLM-based extraction of structured requirements from job ads and CV skills profiles.

## Setup

```bash
pip install -r matching/requirements.txt
```

Add your Gemini API key to `.env`:

```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

`GEMINI_MODEL` is optional — defaults to `gemini-3.5-flash-lite`.

## Tests

```bash
python -m pytest matching/tests/
```

No API key or embedding model required.

---

## Job ad extraction

### Usage

```bash
python -m matching.extract matching/test_ads/001_greenhouse_ai_architect.txt
```

### Run the full test suite

```bash
python -m matching.run_tests
```

Saves results incrementally to `matching/test_results.json` — safe to re-run after failures or quota exhaustion. Free tier limits: 20 requests/day, 5 requests/minute. The test runner adds a 13-second delay between requests and retries up to 3 times on network errors or server overload.

### Output schema

```json
{
  "must_have_skills": ["Python", "Terraform", "CI/CD"],
  "nice_to_have_skills": ["Java"],
  "seniority": "senior",
  "required_languages": ["Finnish", "English"]
}
```

`seniority` is one of `junior / mid / senior / lead`, or `null` if not stated.

## Test results

Tested on 10 real Finnish job ads from Greenhouse, Lever, and Teamtailor ATS feeds.

| Ad | Source | Seniority | Must-have | Nice-to-have | Languages |
|----|--------|-----------|-----------|--------------|-----------|
| 001 AI Architect | Greenhouse | senior | 11 | 2 | Finnish, English |
| 002 Cloud Engineer AWS/Azure | Greenhouse | senior | 6 | 2 | Finnish, English |
| 003 AI Full-Stack Developer | Greenhouse | senior | 4 | 4 | — |
| 004 Principal Engineer Platform | Greenhouse | lead | 5 | 4 | — |
| 005 Senior ML Biosignal Scientist | Greenhouse | senior | 13 | 3 | — |
| 006 Internal Communications (trainee) | Greenhouse | junior | 2 | 2 | — |
| 007 Engineering Manager Chat | Greenhouse | lead | 3 | 4 | — |
| 008 Senior Design Verification Engineer | Lever | senior | 11 | 1 | — |
| 009 Member of Technical Staff Data Science | Lever | senior | 14 | 3 | — |
| 010 Senior Cloud DevOps Engineer | Teamtailor | senior | 4 | 1 | English |

**10/10 ads processed successfully.**

### Observations

- **Seniority looked correct on inspection** (not measured against labels); the trainee ad was mapped to junior because the schema has no intern option.
- **Finnish ads work correctly** — skills are extracted in the language of the ad without translation.
- **Language detection is conservative** — only languages explicitly stated in the ad are returned. Ads that imply English without stating it return an empty list.
- **Language output is not normalised** — ad 001 returns `["Finnish", "English"]`, ad 002 returns `["Suomi", "Englanti"]`. Downstream code should normalise to ISO 639-1 codes (`fi`, `en`).
- **Skill granularity reflects the source ad** — a detailed ML role lists 13 tool-level skills; an engineering manager role lists 3 high-level competencies. Both are correct extractions.
- **Finnish-language skills are extracted as they are** — ad 002 skills are full Finnish sentences rather than short labels. A normalisation step would be needed for consistent cross-ad matching.

---

## CV extraction

### Entry point for the worker

```python
from matching.cv_extract import build_cv_profile

profile = build_cv_profile(cv_text)   # str, max 30 000 characters
data = profile.model_dump(mode="json")  # ready for JSONB storage
```

`build_cv_profile` validates input, redacts emails and phone numbers, calls Gemini, and fills `skill_matches` via embedding-based normalisation. It raises `ValueError` for empty or oversized input.

### Run manually

```bash
python -m matching.cv_extract matching/test_cvs/001_junior_developer_fi.txt
```

### Run the full test suite

```bash
python -m matching.run_cv_tests
```

Saves results incrementally to `matching/cv_test_results.json`.

### Output schema

```json
{
  "skills": ["Python", "React", "Docker"],
  "skill_matches": [
    {"raw": "Python",    "label": "Python",  "score": 1.0},
    {"raw": "React",     "label": "React",   "score": 1.0},
    {"raw": "FreeRTOS",  "label": null,      "score": 0.34}
  ],
  "experience": [
    {"title": "Senior Software Engineer", "years": 3.0},
    {"title": "Intern",                   "years": 0.25}
  ],
  "education": ["M.Sc. in Computer Science"],
  "languages": [
    {"code": "fi", "level": "native"},
    {"code": "en", "level": "fluent"},
    {"code": "sv", "level": "basic"}
  ]
}
```

`label` is the matched label from `matching/data/skills_list.txt`; `null` means no match above the 0.75 cosine similarity threshold — the raw skill is kept so no information is lost.

`level` is one of `native / fluent / good / basic`, or `null` if not stated in the CV.

### Skill matching results

Tested on 5 fictional CVs covering junior dev, senior data scientist, DevOps, full-stack, and embedded engineer profiles.

**Before expanding the skills list:** 45/86 skills matched (100 entries, all matches exact at score 1.0; unmatched scored 0.25–0.59, one AWS variant at 0.74).

**After adding tools from the test CVs:** 79/86 matched.

> **Note:** The 79/86 figure is not representative. The skills list (`matching/data/skills_list.txt`) was expanded by reviewing the same CVs used for testing, so the number overstates real-world coverage. Fuzzy/partial matching is deferred to issue #20.
