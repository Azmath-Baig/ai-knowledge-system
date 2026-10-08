"""Tunable settings in one place.

Thresholds were chosen from the evaluation set (``python -m knowledge_system.evaluate -v``):
every correctly answered question scored >= 0.196, while out-of-scope questions
that pass the unknown-word check scored <= 0.140. MIN_SCORE sits in that gap.
The set is small and was also used for tuning, so treat its numbers as optimistic.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("KB_DATA_DIR", PROJECT_ROOT / "data"))

# Below this cosine similarity, the best match is treated as "not found".
MIN_SCORE = 0.18
# At or above this (with no unknown words), the answer is labelled high confidence.
CONFIDENT_SCORE = 0.30
# Decline when at least this fraction of the question's content words are
# absent from the knowledge base (e.g. "paternity leave" -> 1 of 2 unknown).
MAX_UNKNOWN_RATIO = 0.5
# Another section is also cited if it scores within this fraction of the best.
RELATED_SCORE_RATIO = 0.8

TOP_K = 3
MAX_ANSWER_SENTENCES = 2

FALLBACK_CONTACT = "HR (or the IT Service Desk for IT issues)"
