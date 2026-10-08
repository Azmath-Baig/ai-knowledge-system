"""Turn retrieval results into an answer with sources, or an honest refusal.

Answers are *extractive*: the answer text is copied verbatim from the best
matching section. The system therefore cannot state anything that is not in
the knowledge base, and every answer can be checked against its source.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from . import config
from .loader import Section, load_documents
from .retriever import SearchResult, TfidfRetriever

logger = logging.getLogger(__name__)

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class Status(str, Enum):
    ANSWERED = "answered"
    NOT_FOUND = "not_found"
    INVALID = "invalid"


@dataclass(frozen=True)
class Source:
    citation: str  # "Working Arrangements — Section 2: Remote Working"
    file: str  # "working_arrangements.md"
    section: str  # "2"
    score: float
    text: str  # full section text, so the user can read the context

    @classmethod
    def from_result(cls, result: SearchResult) -> "Source":
        s = result.section
        return cls(s.citation, s.doc_file, s.number, round(result.score, 3), s.text)


@dataclass(frozen=True)
class Answer:
    question: str
    status: Status
    text: str  # the answer, or an explanation of why there is none
    confidence: str | None = None  # "high" / "low" when answered
    sources: list[Source] = field(default_factory=list)  # what the answer is based on
    related: list[Source] = field(default_factory=list)  # closest matches when not found
    notes: list[str] = field(default_factory=list)  # caveats shown to the user

    @property
    def answered(self) -> bool:
        return self.status is Status.ANSWERED

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "status": self.status.value,
            "answer": self.text,
            "confidence": self.confidence,
            "sources": [s.__dict__ for s in self.sources],
            "related": [s.__dict__ for s in self.related],
            "notes": self.notes,
        }


class KnowledgeBase:
    """Load documents once, then answer questions against them."""

    def __init__(self, sections: list[Section]) -> None:
        self.sections = sections
        self.retriever = TfidfRetriever(sections)

    @classmethod
    def from_directory(cls, data_dir: str | Path = config.DATA_DIR) -> "KnowledgeBase":
        return cls(load_documents(data_dir))

    @property
    def documents(self) -> list[str]:
        return sorted({s.doc_title for s in self.sections})

    def ask(self, question: str) -> Answer:
        question = question.strip()
        answer = self._answer(question)
        top = answer.sources[0].score if answer.sources else None
        logger.info("status=%s top_score=%s question=%r", answer.status.value, top, question)
        return answer

    def _answer(self, question: str) -> Answer:
        if not question:
            return Answer(question, Status.INVALID, "Please enter a question.")

        words = self.retriever.content_words(question)
        if not words:
            return Answer(
                question,
                Status.INVALID,
                "Your question doesn't contain any specific words to search for. "
                "Try asking about a topic, e.g. 'How many days of annual leave do I get?'",
            )

        results = self.retriever.search(question, top_k=config.TOP_K)
        unknown = self.retriever.unknown_words(question)

        if not results or results[0].score < config.MIN_SCORE:
            return self._not_found(question, results, "No section matched your question closely enough.")

        if len(unknown) / len(words) >= config.MAX_UNKNOWN_RATIO:
            return self._not_found(
                question, results, f"The knowledge base doesn't mention {_quote_list(unknown)}."
            )

        best = results[0]
        notes = []
        if unknown:
            notes.append(
                f"The knowledge base doesn't mention {_quote_list(unknown)}, so this answer "
                "may only cover part of your question."
            )
        confidence = "high" if best.score >= config.CONFIDENT_SCORE and not unknown else "low"
        if confidence == "low":
            notes.append("This is a weak match. Please check the source before relying on it.")

        # Cite other sections that score almost as well, rather than silently
        # picking one when the knowledge base is genuinely split.
        sources = [best] + [
            r for r in results[1:] if r.score >= best.score * config.RELATED_SCORE_RATIO
        ]
        if len(sources) > 1:
            notes.append("More than one section looks relevant, so all of them are listed as sources.")

        return Answer(
            question,
            Status.ANSWERED,
            self._extract(question, best.section),
            confidence=confidence,
            sources=[Source.from_result(r) for r in sources],
            notes=notes,
        )

    def _not_found(self, question: str, results: list[SearchResult], reason: str) -> Answer:
        text = (
            "I couldn't find an answer to this in the knowledge base. "
            f"{reason} Please contact {config.FALLBACK_CONTACT}."
        )
        return Answer(
            question,
            Status.NOT_FOUND,
            text,
            related=[Source.from_result(r) for r in results],
        )

    def _extract(self, question: str, section: Section) -> str:
        """Return the most relevant sentence(s) of a section, in their original order."""
        sentences = split_sentences(section.text)
        scores = self.retriever.similarity(question, sentences)
        ranked = sorted(range(len(sentences)), key=lambda i: scores[i], reverse=True)
        chosen = [i for i in ranked[: config.MAX_ANSWER_SENTENCES] if scores[i] > 0]
        if not chosen:  # the match came from the heading; the opening sentence summarises it
            chosen = [0]
        return " ".join(sentences[i] for i in sorted(chosen))


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]


def _quote_list(words: list[str]) -> str:
    quoted = [f"'{w}'" for w in words]
    return quoted[0] if len(quoted) == 1 else ", ".join(quoted[:-1]) + " or " + quoted[-1]
