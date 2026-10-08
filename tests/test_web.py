"""Web tests: the UI is thin, so these check it faithfully shows what the core
returns (answer, source, refusal), escapes user input, and validates the API."""

import pytest

from knowledge_system.answerer import KnowledgeBase
from knowledge_system.web import create_app, highlight


@pytest.fixture(scope="module")
def client(data_dir):
    app = create_app(KnowledgeBase.from_directory(data_dir))
    app.testing = True
    return app.test_client()


def test_home_page_shows_examples(client):
    page = client.get("/").get_data(as_text=True)
    assert "Try one of these" in page


def test_answer_page_shows_answer_and_source(client):
    page = client.get("/?q=Can I work from home on Friday?").get_data(as_text=True)

    assert "work remotely on Fridays" in page
    assert "working_arrangements.md" in page
    assert "high confidence" in page


def test_out_of_scope_page_says_no_answer(client):
    page = client.get("/?q=What is the company's maternity policy?").get_data(as_text=True)
    assert "No answer found" in page


def test_user_input_is_escaped(client):
    page = client.get("/?q=<script>alert(1)</script>").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_api_returns_answer_json(client):
    response = client.post("/api/ask", json={"question": "Can I WFH?"})

    assert response.status_code == 200
    assert response.get_json()["sources"][0]["file"] == "working_arrangements.md"


def test_api_rejects_missing_or_oversized_question(client):
    assert client.post("/api/ask", json={}).status_code == 400
    assert client.get("/api/ask?q=" + "a" * 501).status_code == 400


def test_highlight_marks_quoted_sentence_and_escapes_html():
    html = highlight("Keep <b>this</b>. Quote me here. Ignore this.", "Quote me here.")

    assert "<mark>Quote me here.</mark>" in html
    assert "&lt;b&gt;" in html
