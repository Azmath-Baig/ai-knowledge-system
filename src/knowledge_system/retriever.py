"""TF-IDF retrieval over knowledge-base sections.

Why TF-IDF rather than embeddings or an LLM:
- The corpus is ~35 short sections; lexical matching is accurate enough here.
- It is deterministic, fast, offline and needs no API key or model download.
- Cosine similarity is bounded in [0, 1], which makes the "I don't know"
  threshold easy to reason about and tune (see eval/).
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from .loader import Section
from .text import content_words, expand_query, synonym_tokens, tokenize


@dataclass(frozen=True)
class SearchResult:
    section: Section
    score: float  # cosine similarity in [0, 1]


def _index_text(section: Section) -> str:
    # Headings are a strong, author-written summary of a section, so they are
    # repeated to give them extra weight relative to body text.
    heading = f"{section.doc_title} {section.title}"
    return f"{heading} {heading} {section.text}"


class TfidfRetriever:
    """Rank sections by TF-IDF cosine similarity to a question."""

    def __init__(self, sections: list[Section]) -> None:
        if not sections:
            raise ValueError("Cannot build a retriever with no sections")
        self.sections = sections
        self.vectorizer = TfidfVectorizer(
            tokenizer=tokenize,  # same tokenizer for documents and questions
            token_pattern=None,  # silence sklearn: we supply our own tokenizer
            lowercase=False,  # tokenize() already lower-cases
            ngram_range=(1, 2),  # "annual leave" means more than "annual" + "leave"
            sublinear_tf=True,  # dampen repeated words in long sections
        )
        self.matrix = self.vectorizer.fit_transform(_index_text(s) for s in sections)
        self._known_stems = set(self.vectorizer.vocabulary_) | synonym_tokens()

    def search(self, question: str, top_k: int = 3) -> list[SearchResult]:
        """Return up to ``top_k`` sections with a non-zero score, best first."""
        query_vector = self.vectorizer.transform([expand_query(question)])
        scores = linear_kernel(query_vector, self.matrix).ravel()  # vectors are L2-normalised
        ranked = scores.argsort(kind="stable")[::-1][:top_k]
        return [
            SearchResult(self.sections[i], float(scores[i])) for i in ranked if scores[i] > 0
        ]

    def similarity(self, question: str, texts: list[str]) -> list[float]:
        """Score arbitrary texts (e.g. sentences) against a question in the same TF-IDF space."""
        if not texts:
            return []
        query_vector = self.vectorizer.transform([expand_query(question)])
        return linear_kernel(query_vector, self.vectorizer.transform(texts)).ravel().tolist()

    def content_words(self, question: str) -> list[str]:
        """Distinct content words in the question, one per stem ("day"/"days" count once)."""
        return list(self._words_by_stem(question).values())

    def unknown_words(self, question: str) -> list[str]:
        """Content words in the question that never appear in the knowledge base.

        A partial match is the dangerous case: "paternity leave" matches the
        word "leave" strongly, but the knowledge base says nothing about
        paternity. Surfacing the unknown word lets the answerer decline
        honestly instead of returning a confident but irrelevant section.
        """
        words = self._words_by_stem(question)
        return [word for stem, word in words.items() if stem not in self._known_stems]

    @staticmethod
    def _words_by_stem(question: str) -> dict[str, str]:
        words: dict[str, str] = {}
        for word, stem in content_words(question):
            words.setdefault(stem, word)
        return words
