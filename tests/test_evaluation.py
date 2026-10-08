"""Search-quality regression test.

Unit tests check individual behaviours; this checks the system as a whole on
the labelled question set, so a change to tokenisation, synonyms or thresholds
that quietly makes answers worse fails the build. The bars sit just below
current performance so that genuine regressions, not noise, trigger it.
"""

from knowledge_system.answerer import KnowledgeBase
from knowledge_system.evaluate import evaluate, load_questions


def test_search_quality_does_not_regress(data_dir):
    report = evaluate(KnowledgeBase.from_directory(data_dir), load_questions())

    # Safety first: never answer a question the knowledge base cannot answer.
    assert report.hallucination_risks == 0
    # The answer should be on the first page of results...
    assert report.hit_at_3 / report.answerable >= 0.95
    # ...and answered with the right citation most of the time.
    assert report.correct_answers / report.answerable >= 0.85
