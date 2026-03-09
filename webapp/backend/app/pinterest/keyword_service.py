from __future__ import annotations

import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
KEYWORDS_FILE = BASE_DIR / "workspace" / "pinterest" / "keywords.json"

_keywords_cache: dict | None = None
_used_keywords: set[str] = set()


def load_keywords() -> dict:
    global _keywords_cache
    if _keywords_cache is not None:
        return _keywords_cache
    if KEYWORDS_FILE.exists():
        _keywords_cache = json.loads(KEYWORDS_FILE.read_text(encoding="utf-8"))
    else:
        _keywords_cache = {}
    return _keywords_cache


def select_keywords(
    category_names: list[str],
    count: int = 5,
    exclude: set[str] | None = None,
) -> list[str]:
    global _used_keywords
    kw_db = load_keywords()
    exclude = exclude or set()

    pool: list[str] = []
    for cat in category_names:
        pool.extend(kw_db.get(cat, []))

    # Also add from long_tail if present
    if "long_tail" in kw_db:
        pool.extend(kw_db["long_tail"])

    # Filter out already-used and explicitly excluded
    available = [k for k in pool if k not in _used_keywords and k not in exclude]

    # If we've exhausted the pool, reset rotation
    if len(available) < count:
        _used_keywords.clear()
        available = [k for k in pool if k not in exclude]

    selected = random.sample(available, min(count, len(available)))
    _used_keywords.update(selected)
    return selected


def get_all_keywords() -> dict:
    return load_keywords()
