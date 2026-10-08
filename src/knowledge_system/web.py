"""Minimal web interface and JSON API.

Deliberately server-rendered with a plain HTML form (no JavaScript framework):
the UI is a thin layer over ``KnowledgeBase.ask`` so all behaviour stays in the
tested core. Questions are sent as GET ``?q=`` so answers are linkable and the
browser back button works.

    python -m knowledge_system --web      # then open http://127.0.0.1:5000
"""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request
from markupsafe import Markup, escape

from .answerer import KnowledgeBase, split_sentences

MAX_QUESTION_LENGTH = 500

EXAMPLE_QUESTIONS = [
    "How many days of annual leave do I get?",
    "Can I work from home on Friday?",
    "How do I report a laptop problem?",
    "What expenses can I claim?",
    "What is the company's maternity policy?",
]


def highlight(section_text: str, answer_text: str) -> Markup:
    """Escape a source section and mark the sentences quoted in the answer.

    Showing the answer *in context* lets the reader check that it was not
    taken out of context, which matters more than the answer itself.
    """
    html = str(escape(section_text))
    for sentence in split_sentences(answer_text):
        quoted = str(escape(sentence))
        html = html.replace(quoted, f"<mark>{quoted}</mark>", 1)
    paragraphs = "".join(f"<p>{p}</p>" for p in html.split("\n\n"))
    return Markup(paragraphs)


def create_app(kb: KnowledgeBase | None = None) -> Flask:
    """Application factory: tests pass in their own KnowledgeBase."""
    app = Flask(__name__)
    kb = kb or KnowledgeBase.from_directory()
    app.jinja_env.globals["highlight"] = highlight

    @app.get("/")
    def index():
        question = request.args.get("q", "").strip()[:MAX_QUESTION_LENGTH]
        answer = kb.ask(question) if question else None
        return render_template(
            "index.html",
            question=question,
            answer=answer,
            examples=EXAMPLE_QUESTIONS,
            documents=kb.documents,
            section_count=len(kb.sections),
        )

    @app.route("/api/ask", methods=["GET", "POST"])
    def api_ask():
        payload = request.get_json(silent=True) or {}
        question = (payload.get("question") or request.values.get("q") or "").strip()
        if not question:
            return jsonify(error="Provide a question as JSON {'question': ...} or ?q=..."), 400
        if len(question) > MAX_QUESTION_LENGTH:
            return jsonify(error=f"Question must be at most {MAX_QUESTION_LENGTH} characters"), 400
        return jsonify(kb.ask(question).to_dict())

    @app.get("/health")
    def health():
        return jsonify(status="ok", sections=len(kb.sections))

    return app
