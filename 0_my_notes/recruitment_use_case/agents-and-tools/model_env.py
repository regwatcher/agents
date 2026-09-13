"""Defaults from environment (model, research sizing)."""

import os

DEFAULT_MODEL = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")


def target_candidate_count() -> int:
    """How many candidates the researcher should aim for (``RECRUITMENT_TARGET_CANDIDATES``, default 10)."""
    raw = os.getenv("RECRUITMENT_TARGET_CANDIDATES", "10").strip()
    try:
        n = int(raw)
    except ValueError:
        return 10
    return max(1, min(n, 50))
