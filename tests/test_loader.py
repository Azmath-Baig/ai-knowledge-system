"""Loader tests.

Citations are only as good as the parsing behind them: if a section boundary
or number is wrong, every answer from that section points to the wrong place.
"""

import pytest

from knowledge_system.loader import load_documents, parse_document

SAMPLE = """# Working Arrangements

## 1. Core Hours

Core hours are 10:00 to 16:00.

## 2. Remote Working

Employees may work remotely on Fridays.

Second paragraph of the same section.
"""


def test_splits_document_into_numbered_sections():
    sections = parse_document(SAMPLE, "working_arrangements.md")

    assert [(s.number, s.title) for s in sections] == [
        ("1", "Core Hours"),
        ("2", "Remote Working"),
    ]


def test_section_text_stays_with_its_own_heading():
    sections = parse_document(SAMPLE, "working_arrangements.md")
    remote = sections[1]

    assert "Fridays" in remote.text
    assert "Second paragraph" in remote.text
    assert "Core hours" not in remote.text  # no bleed from the previous section


def test_citation_identifies_document_and_section():
    remote = parse_document(SAMPLE, "working_arrangements.md")[1]

    assert remote.citation == "Working Arrangements — Section 2: Remote Working"
    assert remote.id == "working_arrangements.md#2"


def test_intro_text_before_first_heading_is_kept():
    text = "# Policy\n\nThis intro matters.\n\n## 1. Detail\n\nDetail text."
    sections = parse_document(text, "policy.md")

    assert sections[0].title == "Introduction"
    assert sections[0].doc_title == "Policy"
    assert "intro matters" in sections[0].text


def test_unnumbered_headings_get_sequential_numbers():
    text = "# Doc\n\n## First\n\nA.\n\n## Second\n\nB."
    assert [s.number for s in parse_document(text, "doc.md")] == ["1", "2"]


def test_load_documents_skips_readme_and_raises_on_empty(tmp_path):
    (tmp_path / "README.md").write_text("# About the data\n\n## 1. Info\n\nNot policy.")
    with pytest.raises(ValueError):
        load_documents(tmp_path)

    (tmp_path / "policy.md").write_text(SAMPLE)
    sections = load_documents(tmp_path)
    assert {s.doc_file for s in sections} == {"policy.md"}


def test_missing_folder_gives_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_documents(tmp_path / "does-not-exist")


def test_real_knowledge_base_loads(data_dir):
    sections = load_documents(data_dir)

    assert len({s.doc_file for s in sections}) == 7
    assert len({s.id for s in sections}) == len(sections), "section ids must be unique"
