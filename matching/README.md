# matching/

LLM-based extraction of structured requirements from job ads.

## Setup

```bash
pip install -r matching/requirements.txt
```

Add your Gemini API key to `.env`:

```
GEMINI_API_KEY=your_key_here
```

## Usage

### Extract requirements from a single job ad

```bash
python -m matching.extract matching/test_ads/001_greenhouse_ai_architect.txt
```

Override the model:

```bash
python -m matching.extract path/to/ad.txt --model gemini-3.8-flash
```

### Run the full test suite

```bash
python -m matching.run_tests
```

Saves results incrementally to `matching/test_results.json` — safe to re-run after failures or quota exhaustion.

## Output schema

```json
{
  "must_have_skills": ["Python", "Terraform", "CI/CD"],
  "nice_to_have_skills": ["Java"],
  "seniority": "senior",
  "required_languages": ["Finnish", "English"]
}
```

`seniority` is one of `junior / mid / senior / lead`, or `null` if not stated.

## Model

Default: `gemini-3.5-flash-lite`

Free tier limits: 20 requests/day, 5 requests/minute. The test runner adds a 13-second delay between requests and retries up to 3 times on network errors or server overload (503).

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

- **Seniority detection is accurate** across all ads, including lead/principal roles and a junior trainee.
- **Finnish ads work correctly** — skills are extracted in the language of the ad without translation.
- **Language detection is conservative** — only languages explicitly stated in the ad are returned. Ads that imply English without stating it return an empty list.
- **Language output is not normalised** — ad 001 returns `["Finnish", "English"]`, ad 002 returns `["Suomi", "Englanti"]`. Downstream code should normalise to ISO 639-1 codes (`fi`, `en`).
- **Skill granularity reflects the source ad** — a detailed ML role lists 13 tool-level skills; an engineering manager role lists 3 high-level competencies. Both are correct extractions.
- **Finnish-language skills are extracted as they are** — ad 002 skills are full Finnish sentences rather than short labels. A normalisation step would be needed for consistent cross-ad matching.
