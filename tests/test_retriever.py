"""Retrieval tests.

These pin down the behaviours the answer quality depends on: the brief's own
example questions find the right section, informal vocabulary still matches,
and out-of-scope words are detected rather than silently partially matched.
"""

import pytest

from knowledge_system.loader import Section, load_documents
from knowledge_system.retriever import TfidfRetriever
from knowledge_system.text import expand_query, tokenize


@pytest.fixture(scope="module")
def retriever(data_dir):
    return TfidfRetriever(load_documents(data_dir))


@pytest.mark.parametrize(
    "question, expected_id",
    [
        # The four example questions from the brief.
        ("How many days of annual leave do I get?", "holiday_policy.md#1"),
        ("Can I work from home on Friday?", "working_arrangements.md#2"),
        ("How do I report a laptop problem?", "it_support.md#1"),
        ("What expenses can I claim?", "expenses.md#1"),
    ],
)
def test_brief_examples_rank_expected_section_in_top_two(retriever, question, expected_id):
    # "What expenses can I claim?" is genuinely split between "What You Can
    # Claim" and "How to Submit a Claim", so top-2 is the honest bar here.
    top_ids = [r.section.id for r in retriever.search(question, top_k=2)]
    assert expected_id in top_ids


def test_informal_vocabulary_is_expanded(retriever):
    assert retriever.search("Can I WFH?")[0].section.id == "working_arrangements.md#2"


def test_word_forms_match_via_stemming():
    # "carry" in a question must match "Carrying Over Leave" in a document.
    assert tokenize("carry") == tokenize("carrying") == tokenize("carried")


def test_generic_words_do_not_drive_matches(retriever):
    # "policy" and "company" are in document titles but say nothing about the topic.
    assert retriever.search("What is the company's policy?") == []


def test_results_are_sorted_and_bounded(retriever):
    results = retriever.search("annual leave holiday", top_k=5)

    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0 < s <= 1 for s in scores)
    assert len(results) <= 5


def test_no_overlap_returns_no_results(retriever):
    assert retriever.search("Who is the CEO?") == []


def test_unknown_words_reports_original_words(retriever):
    assert retriever.unknown_words("How much paternity leave do I get?") == ["paternity"]
    assert retriever.unknown_words("How many days of annual leave?") == []


def test_conversational_filler_is_not_treated_as_a_topic(retriever):
    # Found by manual testing: "like" was reported as a word the knowledge base lacks.
    question = "and like if i don't take my annual leave will i get money?"
    assert "like" not in retriever.content_words(question)
    assert retriever.unknown_words(question) == ["money"]


def test_synonym_terms_count_as_known(retriever):
    # "WFH" never appears in the documents but we know how to translate it.
    assert retriever.unknown_words("Can I WFH?") == []


def test_expansion_keeps_original_words():
    assert expand_query("Can I WFH?").startswith("can i wfh?")


def test_empty_corpus_is_rejected():
    with pytest.raises(ValueError):
        TfidfRetriever([])


def test_headings_carry_weight():
    sections = [
        Section("a.md", "A", "1", "Parking", "General information about the site."),
        Section("b.md", "B", "1", "Visitors", "Visitors may use parking if booked."),
    ]
    assert TfidfRetriever(sections).search("parking")[0].section.doc_file == "a.md"
