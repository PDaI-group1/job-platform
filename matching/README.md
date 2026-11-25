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
  "must_have_skills": [["Python"], ["Terraform", "Bicep"], ["CI/CD"]],
  "nice_to_have_skills": [["Java", "Kotlin"]],
  "seniority": "senior",
  "required_languages": [
    {"code": "fi", "requirement": "required"},
    {"code": "en", "requirement": "advantage"}
  ]
}
```

Each skill entry is a list of acceptable alternatives for one requirement.
`seniority` is one of `junior / mid / senior / lead / intern`, or `null` if not stated.

## Test results

Tested on 10 real Finnish job ads from Greenhouse, Lever, and Teamtailor ATS feeds.

| Ad | Source | Seniority | Must-have | Nice-to-have | Languages |
|----|--------|-----------|-----------|--------------|-----------|
| 001 AI Architect | Greenhouse | senior | 8 | 2 | fi (required), en (required) |
| 002 Cloud Engineer AWS/Azure | Greenhouse | senior | 4 | 1 | fi (required), en (required) |
| 003 AI Full-Stack Developer | Greenhouse | senior | 2 | 4 | en (required), fi (advantage) |
| 004 Principal Engineer Platform | Greenhouse | senior | 0 | 1 | — |
| 005 Senior ML Biosignal Scientist | Greenhouse | senior | 3 | 1 | — |
| 006 Internal Communications (trainee) | Greenhouse | intern | 0 | 2 | — |
| 007 Engineering Manager Chat | Greenhouse | senior | 4 | 3 | — |
| 008 Senior Design Verification Engineer | Lever | senior | 9 | 1 | — |
| 009 Member of Technical Staff Data Science | Lever | senior | 2 | 1 | — |
| 010 Senior Cloud DevOps Engineer | Teamtailor | senior | 3 | 2 | en (required), fi (advantage) |

**10/10 ads processed successfully.**

> Must-have and nice-to-have counts are requirements (groups of alternatives), not individual skill names. Lower counts than the previous schema are expected — e.g. `[NumPy, SciPy, pandas, scikit-learn]` counts as one requirement.

### Observations

- **Seniority looked correct on inspection** (not measured against labels). `intern` is now a valid value — the trainee ad maps to it.
- **Finnish ads work correctly** — the prompt asks for English skill names, so Finnish ads produce normalised labels suitable for cross-ad matching.
- **Language detection is conservative** — only languages explicitly stated in the ad are returned. Languages are ISO 639-1 codes with a `required` / `advantage` distinction.
- **Skill granularity reflects the source ad** — a detailed ML role lists many tool-level skills; an engineering manager role lists high-level competencies. Both are correct extractions.
- **Skill-free ads score 0** — ad 004 (Principal Engineer Platform) requires seniority and experience rather than named tools, so `must_have_skills` is empty and all CVs score 0 against it. This is correct behaviour.

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

> **Note:** The 79/86 figure is not representative. The skills list (`matching/data/skills_list.txt`) was expanded by reviewing the same CVs used for testing, so the number overstates real-world coverage.

---

## Matching

### Entry point

```python
from matching.match import match_cv_to_job

result = match_cv_to_job(profile, requirements)
# profile: CVProfile from build_cv_profile()
# requirements: JobRequirements from extract_requirements()
```

### Output schema

```json
{
  "score": 85,
  "must_have": [
    {"skill": ["Python"],              "status": "matched", "matched_by": "Python",  "score": 1.0},
    {"skill": ["Terraform", "Bicep"],  "status": "partial", "matched_by": "Ansible", "score": 0.61},
    {"skill": ["COBOL"],               "status": "missing", "matched_by": null,       "score": 0.12}
  ],
  "nice_to_have": [
    {"skill": ["Java", "Kotlin"], "status": "matched", "matched_by": "Java", "score": 1.0}
  ],
  "languages": [
    {"code": "fi", "requirement": "required",  "cv_level": "native"},
    {"code": "en", "requirement": "advantage", "cv_level": "fluent"}
  ]
}
```

`score` is 0–100, based on skills only (languages are reported separately and do not affect the score).

Scoring: must-haves 80 %, nice-to-haves 20 %. If there are no nice-to-haves, score is based on must-haves alone. `matched` = 1 point, `partial` = 0.5, `missing` = 0.

Matching tries exact case-insensitive comparison first (CV label, then raw). Embeddings (`all-MiniLM-L6-v2`) are used only for skills that did not match exactly. A requirement is satisfied if **any** of its alternatives matches. Thresholds: `matched` ≥ 0.75, `partial` ≥ 0.50 — untuned until the evaluation set (#22) is ready.

### Run the full matrix

Matches all CVs in `cv_test_results.json` against all ads in `test_results.json` (5 × 10 = 50 pairs):

```bash
python -m matching.run_match_tests
```

Saves results to `matching/match_results.json` and prints a score table.
