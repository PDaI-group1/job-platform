import re
from collections import Counter
from collections.abc import Iterable
from functools import lru_cache

from crawler.config import LanguageRules, NegationRules

_STRUCTURED_EMPLOYMENT = {
    "full_time": "full_time", "fulltime": "full_time",
    "part_time": "part_time", "parttime": "part_time",
    "intern": "internship", "internship": "internship",
    "temporary": "temporary", "seasonal": "temporary",
    "contractor": "contract", "contract": "contract", "per_diem": "temporary",
}
_STRUCTURED_REMOTE = {"telecommute": "remote", "remote": "remote", "hybrid": "hybrid", "onsite": "onsite", "on_site": "onsite"}


@lru_cache(maxsize=256)
def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


def _negated(text: str, start: int, end: int, negation: NegationRules) -> bool:
    if not negation.words:
        return False
    before = text[max(0, start - negation.window_chars): start].lower()
    after = text[end: end + negation.after_window_chars].lower()
    return any(re.search(rf"\b{re.escape(w)}\b", window) for w in negation.words for window in (before, after))


def match_rules(text: str, rules: dict[str, list[str]], negation: NegationRules) -> str | None:
    for key, patterns in rules.items():
        for pattern in patterns:
            for m in _compile(pattern).finditer(text):
                if not _negated(text, m.start(), m.end(), negation):
                    return key
    return None


def classify(
    texts: Iterable[str | None],
    rules: dict[str, list[str]],
    negation: NegationRules,
    structured: dict[str, str] | None = None,
) -> str | None:
    for text in texts:
        if not text:
            continue
        if structured:
            token = re.sub(r"[\s-]+", "_", text.strip().lower())
            if token in structured:
                return structured[token]
        if (key := match_rules(text, rules, negation)) is not None:
            return key
    return None


def classify_employment(texts: Iterable[str | None], rules: dict[str, list[str]], negation: NegationRules) -> str | None:
    return classify(texts, rules, negation, _STRUCTURED_EMPLOYMENT)


def classify_remote(texts: Iterable[str | None], rules: dict[str, list[str]], negation: NegationRules) -> str | None:
    return classify(texts, rules, negation, _STRUCTURED_REMOTE)


def detect_language(text: str | None, rules: LanguageRules, hint: str | None = None) -> str | None:
    if hint:
        code = hint.strip().lower()[:2]
        if code in rules.stopwords:
            return code
    if not text:
        return None
    words = re.findall(r"[a-zåäö]+", text.lower())
    counts = Counter(words)
    scores = {lang: sum(counts[w] for w in stop) for lang, stop in rules.stopwords.items()}
    lang, best = max(scores.items(), key=lambda kv: kv[1])
    if best < rules.min_hits:
        return None
    if sum(1 for s in scores.values() if s == best) > 1:
        return None
    return lang
