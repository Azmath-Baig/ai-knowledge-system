"""Experiment: would embeddings improve the knowledge system?

Compares TF-IDF (the default) with embedding models on the labelled
evaluation set, and answers three questions:

1. Ranking:  does mixing embedding similarity into the ranking put the right
             section first more often?
2. Refusals: can embedding scores tell answerable questions from out-of-scope
             ones? (If the score ranges overlap, they can't be used to decide
             *whether* to answer.)
3. End to end: with embeddings re-ranking TF-IDF's candidates, and TF-IDF still
             deciding whether to answer, do more questions get a correct answer?

Results and the decision they led to are in the README ("Would embeddings help?").

Run (downloads ~200 MB of models on first run; no PyTorch needed):
    pip install -r experiments/requirements.txt
    python experiments/compare_embeddings.py
"""

from __future__ import annotations

import contextlib
import io
import time
import warnings
from collections.abc import Callable

import numpy as np

from knowledge_system.answerer import KnowledgeBase
from knowledge_system.evaluate import evaluate, load_questions
from knowledge_system.loader import Section
from knowledge_system.retriever import SearchResult, TfidfRetriever

warnings.filterwarnings("ignore")  # model download / symlink noise on Windows

Encoder = Callable[[list[str], bool], np.ndarray]  # (texts, is_query) -> vectors
MIX_WEIGHTS = (0.0, 0.3, 0.5, 1.0)  # 0 = TF-IDF only, 1 = embeddings only


def model2vec_encoder(name: str) -> Encoder:
    from model2vec import StaticModel

    model = StaticModel.from_pretrained(name)
    return lambda texts, is_query=False: model.encode(texts)


def fastembed_encoder(name: str) -> Encoder:
    from fastembed import TextEmbedding

    model = TextEmbedding(name)
    return lambda texts, is_query=False: np.array(
        list(model.query_embed(texts) if is_query else model.embed(texts))
    )


MODELS: dict[str, Callable[[], Encoder]] = {
    "potion-base-8M (static)": lambda: model2vec_encoder("minishlab/potion-base-8M"),
    "potion-retrieval-32M (static)": lambda: model2vec_encoder("minishlab/potion-retrieval-32M"),
    "bge-small-en-v1.5 (transformer)": lambda: fastembed_encoder("BAAI/bge-small-en-v1.5"),
}


class SectionEmbeddings:
    """Unit-normalised embeddings for every section, plus query scoring."""

    def __init__(self, encode: Encoder, sections: list[Section]) -> None:
        self.encode = encode
        self.index = {s.id: i for i, s in enumerate(sections)}
        vectors = encode([f"{s.doc_title}. {s.title}. {s.text}" for s in sections], False)
        self.vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def scores(self, question: str) -> np.ndarray:
        q = self.encode([question], True)[0]
        return self.vectors @ (q / np.linalg.norm(q))


class HybridRerankRetriever(TfidfRetriever):
    """TF-IDF finds candidates and its scores still drive refusals;
    embeddings only change the order of the candidates."""

    def __init__(self, sections: list[Section], embeddings: SectionEmbeddings, weight: float) -> None:
        super().__init__(sections)
        self.embeddings, self.weight = embeddings, weight

    def search(self, question: str, top_k: int = 3) -> list[SearchResult]:
        results = super().search(question, top_k)
        emb = self.embeddings.scores(question)
        mixed = lambda r: (1 - self.weight) * r.score + self.weight * emb[self.embeddings.index[r.section.id]]  # noqa: E731
        return sorted(results, key=mixed, reverse=True)


def valid_ids(expected: str | list[str]) -> list[str]:
    return [expected] if isinstance(expected, str) else expected


def tfidf_scores(tfidf: TfidfRetriever, question: str, index: dict[str, int]) -> np.ndarray:
    """The default retriever's score for every section (0 where nothing matched)."""
    scores = np.zeros(len(index))
    for r in tfidf.search(question, top_k=len(index)):
        scores[index[r.section.id]] = r.score
    return scores


def ranking_report(kb: KnowledgeBase, embeddings: SectionEmbeddings, questions: list[dict]) -> None:
    sections, tfidf = kb.sections, kb.retriever
    answerable = [q for q in questions if q["expected"] is not None]
    hits = {w: [0, 0] for w in MIX_WEIGHTS}
    right_scores, out_of_scope_scores = [], []

    for item in questions:
        emb = embeddings.scores(item["question"])
        if item["expected"] is None:
            out_of_scope_scores.append(emb.max())
            continue
        valid = valid_ids(item["expected"])
        right_scores.append(emb[embeddings.index[valid[0]]])
        lexical = tfidf_scores(tfidf, item["question"], embeddings.index)
        for w in MIX_WEIGHTS:
            ranked = [sections[i].id for i in np.argsort(-((1 - w) * lexical + w * emb))[:3]]
            hits[w][0] += ranked[0] in valid
            hits[w][1] += any(v in ranked for v in valid)

    n = len(answerable)
    for w, (h1, h3) in hits.items():
        label = "TF-IDF only" if w == 0 else "embeddings only" if w == 1 else f"{w:.0%} embeddings"
        print(f"  {label:18} hit@1 {h1}/{n} ({h1 / n:.0%})   hit@3 {h3}/{n} ({h3 / n:.0%})")
    print(
        f"  Embedding score of the correct section: {min(right_scores):.2f}–{max(right_scores):.2f}"
        f"   |   best score for out-of-scope questions: {min(out_of_scope_scores):.2f}–{max(out_of_scope_scores):.2f}"
    )


def end_to_end_report(kb: KnowledgeBase, embeddings: SectionEmbeddings, questions: list[dict]) -> None:
    hybrid_kb = KnowledgeBase(kb.sections)
    hybrid_kb.retriever = HybridRerankRetriever(kb.sections, embeddings, weight=0.5)
    for label, system in (("TF-IDF only", kb), ("50% hybrid re-ranking", hybrid_kb)):
        with contextlib.redirect_stdout(io.StringIO()):  # hide per-question failures
            report = evaluate(system, questions)
        print(f"  {label}:")
        print("\n".join("    " + line for line in report.lines()))


def main() -> None:
    kb = KnowledgeBase.from_directory()
    questions = load_questions()

    last = None
    for name, make in MODELS.items():
        start = time.perf_counter()
        embeddings = SectionEmbeddings(make(), kb.sections)
        print(f"\n=== {name}  (load + index: {time.perf_counter() - start:.1f}s)")
        ranking_report(kb, embeddings, questions)
        last = embeddings

    print("\n=== End to end with the strongest model (bge-small), TF-IDF still deciding refusals")
    end_to_end_report(kb, last, questions)


if __name__ == "__main__":
    main()
