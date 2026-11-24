"""
Normalise raw skill strings to known labels using sentence embeddings.

Uses the curated IT skills list in matching/data/skills_list.txt.
To use the full ESCO dataset instead, download skills_en.csv from
https://esco.ec.europa.eu/en/use-esco/download and pass its path to normalise_skills().

The embedding model (all-MiniLM-L6-v2, ~80 MB) is downloaded on first use and cached
by sentence-transformers in ~/.cache/torch/sentence_transformers/.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

from matching.cv_schemas import SkillMatch

_DEFAULT_SKILLS_FILE = Path(__file__).parent / "data" / "skills_list.txt"
_MODEL_NAME = "all-MiniLM-L6-v2"
_SIMILARITY_THRESHOLD = 0.75


def load_skills(path: Path | None = None) -> list[str]:
    """Load ESCO skill labels from a text file or a full ESCO skills_en.csv.

    Args:
        path: Path to a .txt (one label per line) or ESCO skills_en.csv.
              Defaults to the bundled IT skills subset.

    Returns:
        List of skill preferred labels.
    """
    path = path or _DEFAULT_SKILLS_FILE
    if path.suffix == ".csv":
        with path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return [row["preferredLabel"].strip() for row in reader if row.get("preferredLabel")]
    else:
        lines = path.read_text(encoding="utf-8").splitlines()
        return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(_MODEL_NAME)


def normalise_skills(
    skills: list[str],
    skills_path: Path | None = None,
    threshold: float = _SIMILARITY_THRESHOLD,
) -> list[SkillMatch]:
    """Map raw skill strings to the closest label in the skills list.

    Every skill is returned. Skills with a match above the threshold get a
    label; others get label=None. No skill is ever dropped.

    Args:
        skills: Raw skill strings extracted from a CV.
        skills_path: Optional path to a custom skills file (see load_skills).
                     To use the full ESCO dataset, pass the path to skills_en.csv.
        threshold: Minimum cosine similarity to accept a match (0–1).

    Returns:
        One SkillMatch per unique raw skill, preserving input order.
    """
    if not skills:
        return []

    known_labels = load_skills(skills_path)
    model = _get_model()

    skill_vecs = model.encode(skills, convert_to_tensor=True, show_progress_bar=False)
    label_vecs = model.encode(known_labels, convert_to_tensor=True, show_progress_bar=False)

    similarities = cos_sim(skill_vecs, label_vecs).numpy()

    seen: dict[str, SkillMatch] = {}
    for i, raw in enumerate(skills):
        if raw in seen:
            continue
        best_idx = int(np.argmax(similarities[i]))
        score = round(float(similarities[i][best_idx]), 3)
        label = known_labels[best_idx] if score >= threshold else None
        seen[raw] = SkillMatch(raw=raw, label=label, score=score)

    return list(seen.values())
