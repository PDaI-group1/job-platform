"""
Run CV extraction + ESCO normalisation on all CVs in matching/test_cvs/ and save results
to matching/cv_test_results.json. Skips CVs that already have a result saved.
Safe to re-run after failures.

Usage:
    python -m matching.run_cv_tests
    python -m matching.run_cv_tests --delay 15
"""
import argparse
import json
import time
from pathlib import Path

from matching.cv_extract import extract_cv_profile
from matching.esco import normalise_skills

RESULTS_FILE = Path("matching/cv_test_results.json")
CVS_DIR = Path("matching/test_cvs")


def load_results() -> dict:
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    return {}


def save_results(results: dict) -> None:
    RESULTS_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=13.0, help="seconds between requests")
    args = parser.parse_args()

    results = load_results()
    cvs = sorted(CVS_DIR.glob("*.txt"))
    pending = [cv for cv in cvs if cv.name not in results]

    if not pending:
        print("All CVs already processed.")
        return

    print(f"{len(pending)} CVs to process, {len(results)} already done.")
    for i, cv in enumerate(pending):
        print(f"[{len(results)+1}/{len(cvs)}] {cv.name}", flush=True)
        text = cv.read_text(encoding="utf-8")

        profile = extract_cv_profile(text)

        print(f"  Normalising {len(profile.skills)} skills with ESCO...", flush=True)
        profile.skills_esco = normalise_skills(profile.skills)

        results[cv.name] = profile.model_dump()
        save_results(results)
        print(
            f"  skills={len(profile.skills)} esco={len(profile.skills_esco)} "
            f"exp={len(profile.experience)} lang={profile.languages}",
            flush=True,
        )
        if i < len(pending) - 1:
            time.sleep(args.delay)

    print(f"Done. {len(results)}/{len(cvs)} results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
