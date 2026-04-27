"""Utilities for converting skill dicts to pgvector-compatible float lists.

The skill vocabulary (skill_name → vector index) is now backed by the
`skill_vocabulary` table in Supabase so it survives process restarts.
The in-memory cache is still used within a single process for speed.
"""

from typing import Dict, List, Optional

# --- in-process cache (loaded lazily from DB on first use) ---
_skill_vocabulary: Dict[str, int] = {}
_vocab_loaded: bool = False


# ---------------------------------------------------------------------------
# Low-level helpers (used by agent/nodes/persist.py too)
# ---------------------------------------------------------------------------

def get_or_create_skill_index(skill_name: str, max_dimensions: int = 200) -> int:
    global _skill_vocabulary
    if skill_name not in _skill_vocabulary:
        if len(_skill_vocabulary) >= max_dimensions:
            raise ValueError(f"Max skill vocabulary ({max_dimensions}) reached")
        _skill_vocabulary[skill_name] = len(_skill_vocabulary)
    return _skill_vocabulary[skill_name]


def load_vocabulary_from_skills(skills: Dict[str, int], max_dimensions: int = 200):
    for skill_name in skills:
        get_or_create_skill_index(skill_name, max_dimensions)


def skills_to_vector(skills: Dict[str, int], max_dimensions: int = 200) -> List[float]:
    load_vocabulary_from_skills(skills, max_dimensions)
    vec = [0.0] * max_dimensions
    for name, score in skills.items():
        if name in _skill_vocabulary:
            idx = _skill_vocabulary[name]
            if idx < max_dimensions:
                vec[idx] = float(score) / 100.0
    return vec


def vector_to_skills(
    vector: List[float],
    vocabulary: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    vocab = vocabulary if vocabulary is not None else _skill_vocabulary
    rev = {idx: name for name, idx in vocab.items()}
    return {rev[i]: int(v * 100) for i, v in enumerate(vector) if i in rev and v > 0}


def merge_skill_vectors(old: Dict[str, int], new: Dict[str, int]) -> Dict[str, int]:
    merged = old.copy()
    for name, score in new.items():
        merged[name] = max(merged.get(name, 0), score)
    return merged


def build_vocabulary_from_db(skill_jsons: List[Dict[str, int]], max_dimensions: int = 200):
    """Rebuild in-memory vocab from a list of skill dicts (used during initialisation)."""
    global _skill_vocabulary
    all_skills: set[str] = set()
    for s in skill_jsons:
        if s:
            all_skills.update(s.keys())
    for name in sorted(all_skills):
        if len(_skill_vocabulary) < max_dimensions:
            _skill_vocabulary.setdefault(name, len(_skill_vocabulary))


# ---------------------------------------------------------------------------
# DB-backed vocabulary (called by DatabaseManager.initialize_vocabulary)
# ---------------------------------------------------------------------------

def load_vocabulary_from_supabase(client, max_dimensions: int = 200):
    """Fetch skill_vocabulary rows from Supabase and populate in-memory cache."""
    global _skill_vocabulary, _vocab_loaded
    try:
        resp = client.table("skill_vocabulary").select("skill_name, idx").execute()
        for row in resp.data or []:
            name = row["skill_name"]
            idx = row["idx"]
            if idx < max_dimensions:
                _skill_vocabulary[name] = idx
        _vocab_loaded = True
    except Exception:
        pass  # table may not exist yet; fall back to in-memory behaviour
