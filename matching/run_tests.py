"""
Run extraction on all ads in matching/test_ads/ and save results to matching/test_results.json.
Skips ads that already have a result saved. Safe to re-run after failures.

Usage:
    python -m matching.run_tests
    python -m matching.run_tests --delay 15
"""
import argparse
import json
import time
from pathlib import Path

from matching.extract import extract_requirements

RESULTS_FILE = Path("matching/test_results.json")
ADS_DIR = Path("matching/test_ads")


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
    ads = sorted(ADS_DIR.glob("*.txt"))
    pending = [ad for ad in ads if ad.name not in results]

    if not pending:
        print("All ads already processed.")
        return

    print(f"{len(pending)} ads to process, {len(results)} already done.")
    for i, ad in enumerate(pending):
        print(f"[{len(results)+1}/{len(ads)}] {ad.name}", flush=True)
        text = ad.read_text(encoding="utf-8")
        result = extract_requirements(text)
        results[ad.name] = result.model_dump()
        save_results(results)
        print(f"  seniority={result.seniority} must={len(result.must_have_skills)} "
              f"nice={len(result.nice_to_have_skills)} lang={result.required_languages}", flush=True)
        if i < len(pending) - 1:
            time.sleep(args.delay)

    print(f"Done. {len(results)}/{len(ads)} results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
