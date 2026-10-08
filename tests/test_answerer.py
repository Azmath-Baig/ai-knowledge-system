"""Answer-level tests: the behaviours the brief cares most about.

1. Every answer cites where it came from.
2. Answers are taken from the source, never invented.
3. Questions the knowledge base cannot answer are declined, with a reason.
"""

import pytest

from knowledge_system.answerer import KnowledgeBase, Status
from knowledge_system.loader import Section


@pytest.fixture(scope="module")
def kb(data_dir):
    return KnowledgeBase.from_directory(data_dir)


def test_brief_example_answer_and_source(kb):
    answer = kb.ask("Can I work from home on Friday?")

    assert answer.status is Status.ANSWERED
    assert "work remotely on Fridays" in answer.text
    assert answer.sources[0].citation == "Working Arrangements — Section 2: Remote Working"
    assert answer.sources[0].file == "working_arrangements.md"


@pytest.mark.parametrize(
    "question",
    [
        "How many days of annual leave do I get?",
        "How do I report a laptop problem?",
        "What expenses can I claim?",
        "When are performance reviews held?",
    ],
)
def test_every_answer_has_a_source_and_comes_from_it(kb, question):
    answer = kb.ask(question)

    assert answer.answered
    assert answer.sources, "an answer without a source must never be returned"
    # Extractive: each sentence of the answer appears verbatim in the cited section.
    for sentence in answer.text.split(". "):
        assert sentence.rstrip(".") in answer.sources[0].text


@pytest.mark.parametrize(
    "question, reason_fragment",
    [
        ("What is the company's maternity policy?", "No section matched"),
        ("How much paternity leave do I get?", "doesn't mention 'paternity'"),
        ("When is salary paid?", "No section matched"),
        ("Who is the CEO?", "No section matched"),
    ],
)
def test_out_of_scope_questions_are_declined_with_a_reason(kb, question, reason_fragment):
    answer = kb.ask(question)

    assert answer.status is Status.NOT_FOUND
    assert answer.sources == []  # nothing is presented as the basis of an answer
    assert reason_fragment in answer.text
    assert "contact HR" in answer.text


def test_partial_match_on_generic_word_is_not_answered(kb):
    # The dangerous case: "leave" matches strongly, "paternity" not at all.
    answer = kb.ask("How much paternity leave do I get?")

    assert not answer.answered
    assert answer.related, "closest sections are offered so the user can browse"


def test_unknown_word_in_otherwise_answerable_question_adds_caveat(kb):
    answer = kb.ask("Can I work remotely from Spain on Fridays?")

    assert answer.answered
    assert answer.confidence == "low"
    assert any("'spain'" in note for note in answer.notes)


def test_strong_match_is_high_confidence_without_caveats(kb):
    answer = kb.ask("How many days of annual leave do I get?")

    assert answer.confidence == "high"
    assert answer.notes == []


def test_close_runner_up_is_cited_too(kb):
    # The knowledge base is genuinely split between two expenses sections.
    answer = kb.ask("What expenses can I claim?")

    assert len(answer.sources) == 2
    assert {s.file for s in answer.sources} == {"expenses.md"}


@pytest.mark.parametrize("question", ["", "   ", "what is it?", "how do I?"])
def test_empty_or_contentless_questions_are_invalid(kb, question):
    assert kb.ask(question).status is Status.INVALID


def test_extract_falls_back_to_first_sentence_when_only_heading_matched():
    sections = [
        Section("p.md", "Parking", "1", "Parking", "Spaces are limited. Book ahead."),
        Section("q.md", "Other", "1", "Other", "Unrelated text about something else."),
    ]
    answer = KnowledgeBase(sections).ask("parking")

    assert answer.text == "Spaces are limited."


def test_to_dict_is_json_ready(kb):
    data = kb.ask("Can I WFH?").to_dict()

    assert data["status"] == "answered"
    assert data["sources"][0]["citation"].startswith("Working Arrangements")
