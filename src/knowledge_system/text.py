"""Text processing shared by indexing and querying.

The same ``tokenize`` function is used for documents and questions, so both
sides of the comparison see identical vocabulary.
"""

from __future__ import annotations

import re

import snowballstemmer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Words that appear in questions or document titles but say nothing about the
# topic. Without these, "What is the company's maternity policy?" matched the
# "Expenses Policy" document purely on the word "policy".
DOMAIN_STOP_WORDS = {
    "policy", "policies", "company", "nalits", "employee", "employees", "staff",
    "tell", "know", "want", "need", "does", "rule", "rules", "happen", "happens",
    # Conversational filler. sklearn's list targets formal text, so without
    # these "...and like if I..." counted "like" as an unknown topic word.
    "like", "just", "really", "actually", "basically", "ok", "okay", "hi", "hello",
    "thanks", "thank", "pls", "plz", "hey",
    # Fragments left after splitting contractions ("don't" -> "don").
    "don", "doesn", "didn", "isn", "aren", "won", "ve", "ll", "re",
}
STOP_WORDS = ENGLISH_STOP_WORDS | DOMAIN_STOP_WORDS

_TOKEN = re.compile(r"[a-z0-9]+")
_STEMMER = snowballstemmer.stemmer("english")
_POSSESSIVE = re.compile(r"'s\b")

# Informal term -> words the policy documents actually use.
# TF-IDF only matches literal words, so "WFH" would otherwise miss "Remote
# Working". This small, reviewable table is a deliberate stop-gap; embeddings
# would handle vocabulary mismatch more generally (see README).
SYNONYMS: dict[str, str] = {
    "wfh": "work from home remote working",
    "work from home": "remote working",
    "home working": "remote working",
    "pto": "annual leave",
    "vacation": "annual leave holiday",
    "days off": "annual leave",
    "time off": "annual leave",
    "reimburse": "expenses claim",
    "reimbursed": "expenses claim",
    "reimbursement": "expenses claim",
    "refund": "expenses claim",
    "computer": "laptop",
    "pc": "laptop",
    "broken": "problem report",
    "sick": "sickness absence unwell",
    "ill": "sickness absence unwell",
    "promoted": "promotion",
    "appraisal": "performance review",
    "course": "training learning",
    "resign": "notice period",
    "quit": "notice period",
    "login": "password account access",
    "lose": "lost",
    "overseas": "working abroad another country",
    "locked out": "password account access",
}
_SYNONYM_PATTERNS = [
    (re.compile(rf"\b{re.escape(term)}\b"), expansion) for term, expansion in SYNONYMS.items()
]


def _stem(token: str) -> str:
    """Reduce a word to its stem so 'carry', 'carrying' and 'carried' match.

    Snowball (Porter2) is a small, pure-Python, rule-based stemmer. Simple
    plural-stripping was tried first but missed '-ing'/'-ed' forms, which
    caused false "unknown word" refusals (e.g. "carry over holiday").
    """
    return _STEMMER.stemWord(token)


def normalise(text: str) -> str:
    """Lower-case, unify apostrophes and collapse whitespace."""
    return " ".join(text.lower().replace("’", "'").split())


def content_words(text: str) -> list[tuple[str, str]]:
    """Return ``(word, stem)`` pairs for the content words in ``text``.

    Keeping the original word lets messages say "maternity" rather than "matern".
    """
    text = _POSSESSIVE.sub("", normalise(text))  # "company's" -> "company"
    return [(w, _stem(w)) for w in _TOKEN.findall(text) if w not in STOP_WORDS and len(w) > 1]


def tokenize(text: str) -> list[str]:
    """Split text into lower-case, stemmed content words (stop words removed)."""
    return [stem for _, stem in content_words(text)]


def expand_query(question: str) -> str:
    """Append document vocabulary for any informal terms found in the question.

    The original words are kept, so expansion can only add matches, never remove them.
    """
    q = normalise(question)
    additions = [expansion for pattern, expansion in _SYNONYM_PATTERNS if pattern.search(q)]
    return " ".join([q, *additions])


def synonym_tokens() -> set[str]:
    """Tokens of the informal terms we know how to translate (e.g. 'wfh')."""
    return {t for term in SYNONYMS for t in tokenize(term)}
