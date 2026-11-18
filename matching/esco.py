"""
Normalise raw skill strings to ESCO preferred labels using sentence embeddings.

Uses a curated subset of ESCO IT skills bundled in matching/data/esco_it_skills.txt.
To use the full ESCO dataset, download skills_en.csv from
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

_DEFAULT_SKILLS_FILE = Path(__file__).parent / "data" / "esco_it_skills.txt"
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
    esco_path: Path | None = None,
    threshold: float = _SIMILARITY_THRESHOLD,
) -> list[str]:
    """Map raw skill strings to the closest ESCO preferred label.

    Skills with no match above the similarity threshold are dropped.

    Args:
        skills: Raw skill strings extracted from a CV.
        esco_path: Optional path to a custom skills file (see load_skills).
        threshold: Minimum cosine similarity to accept a match (0–1).

    Returns:
        Deduplicated list of ESCO preferred labels.
    """
    if not skills:
        return []

    esco_labels = load_skills(esco_path)
    model = _get_model()

    skill_vecs = model.encode(skills, convert_to_tensor=True, show_progress_bar=False)
    esco_vecs = model.encode(esco_labels, convert_to_tensor=True, show_progress_bar=False)

    similarities = cos_sim(skill_vecs, esco_vecs).numpy()

    seen: dict[str, None] = {}
    for i, raw in enumerate(skills):
        best_idx = int(np.argmax(similarities[i]))
        if similarities[i][best_idx] >= threshold:
            label = esco_labels[best_idx]
            seen.setdefault(label, None)

    return list(seen)
