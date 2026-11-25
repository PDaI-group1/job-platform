"""
Match every CV in cv_test_results.json against every ad in test_results.json
and save results to matching/match_results.json.

Requires both result files to exist. Run the test runners first if needed:
    python -m matching.run_tests       # produces test_results.json
    python -m matching.run_cv_tests    # produces cv_test_results.json

Usage:
    python -m matching.run_match_tests
"""

import json
from pathlib import Path

from matching.cv_schemas import CVProfile
from matching.match import match_cv_to_job
from matching.schemas import JobRequirements

CV_RESULTS = Path("matching/cv_test_results.json")
AD_RESULTS = Path("matching/test_results.json")
MATCH_RESULTS = Path("matching/match_results.json")


def load_cv_profiles(path: Path) -> dict[str, CVProfile]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {name: CVProfile.model_validate(profile) for name, profile in data.items()}


def load_job_requirements(path: Path) -> dict[str, JobRequirements]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {name: JobRequirements.model_validate(req) for name, req in data.items()}


def main() -> None:
    for path in (CV_RESULTS, AD_RESULTS):
        if not path.exists():
            print(f"Missing: {path}. Run the relevant test runner first.")
            return

    print("Loading profiles and requirements...", flush=True)
    profiles = load_cv_profiles(CV_RESULTS)
    requirements = load_job_requirements(AD_RESULTS)

    cv_names = sorted(profiles)
    ad_names = sorted(requirements)
    total = len(cv_names) * len(ad_names)
    print(f"{len(cv_names)} CVs x {len(ad_names)} ads = {total} pairs", flush=True)

    pairs = []
    done = 0
    for cv_name in cv_names:
        for ad_name in ad_names:
            result = match_cv_to_job(profiles[cv_name], requirements[ad_name])
            pairs.append({
                "cv": cv_name,
                "ad": ad_name,
                "score": result.score,
                "must_have": result.model_dump()["must_have"],
                "nice_to_have": result.model_dump()["nice_to_have"],
                "languages": result.model_dump()["languages"],
            })
            done += 1
            if done % 10 == 0 or done == total:
                print(f"  {done}/{total}", flush=True)

    MATCH_RESULTS.write_text(json.dumps({"pairs": pairs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done. Results saved to {MATCH_RESULTS}")

    # Print score table
    print()
    header = f"{'CV':<40}" + "".join(f"{ad[:6]:>8}" for ad in ad_names)
    print(header)
    for cv_name in cv_names:
        row = f"{cv_name:<40}"
        for ad_name in ad_names:
            score = next(p["score"] for p in pairs if p["cv"] == cv_name and p["ad"] == ad_name)
            row += f"{score:>8}"
        print(row)


if __name__ == "__main__":
    main()
