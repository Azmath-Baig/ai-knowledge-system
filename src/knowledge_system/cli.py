"""Command-line interface.

    python -m knowledge_system                       # interactive mode
    python -m knowledge_system "Can I WFH on Friday?" # one question
    python -m knowledge_system --json "..."           # machine-readable output
    python -m knowledge_system --web                  # start the web UI
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import textwrap
from pathlib import Path

from . import config
from .answerer import Answer, KnowledgeBase

WIDTH = 78


def format_answer(answer: Answer, show_full_source: bool = False) -> str:
    """Render an answer in the layout the brief suggests: answer, then source."""
    wrap = lambda text, indent="": textwrap.fill(text, WIDTH, initial_indent=indent, subsequent_indent=indent)  # noqa: E731
    lines: list[str] = []

    if answer.answered:
        lines += ["Answer:", wrap(answer.text, "  "), "", f"Confidence: {answer.confidence}", ""]
        lines.append("Source:" if len(answer.sources) == 1 else "Sources:")
        for source in answer.sources:
            lines.append(f"  {source.file} — Section {source.section}")
            lines.append(f"  ({source.citation}, score {source.score:.2f})")
            if show_full_source:
                lines += ["", wrap(source.text, "    | "), ""]
        if answer.notes:
            lines.append("")
            lines += [wrap(f"Note: {note}") for note in answer.notes]
    else:
        lines.append(wrap(answer.text))
        if answer.related:
            lines += ["", "Closest sections (these may not answer your question):"]
            lines += [f"  - {s.citation} ({s.file})" for s in answer.related]
    return "\n".join(lines)


def interactive(kb: KnowledgeBase, show_full_source: bool) -> None:
    print(f"NALITS knowledge base — {len(kb.sections)} sections from {len(kb.documents)} documents.")
    print("Ask a question, or type 'quit' to exit.\n")
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if question.lower() in {"quit", "exit", "q"}:
            return
        if question:
            print(format_answer(kb.ask(question), show_full_source), end="\n\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="knowledge_system",
        description="Search the NALITS knowledge base and show where each answer comes from.",
    )
    parser.add_argument("question", nargs="*", help="question to ask (omit for interactive mode)")
    parser.add_argument("--data", type=Path, default=config.DATA_DIR, help="folder of Markdown documents")
    parser.add_argument("--json", action="store_true", help="print the answer as JSON")
    parser.add_argument("--full", action="store_true", help="also print the full source section")
    parser.add_argument("--web", action="store_true", help="start the web interface")
    parser.add_argument("--port", type=int, default=5000, help="port for --web (default 5000)")
    parser.add_argument("--verbose", "-v", action="store_true", help="log scores and decisions")
    args = parser.parse_args(argv)

    # Windows consoles default to a legacy code page that cannot print "—" or "£".
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        kb = KnowledgeBase.from_directory(args.data)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.web:
        from .web import create_app  # imported lazily: CLI use does not need Flask

        create_app(kb).run(port=args.port)
        return 0

    if not args.question:
        interactive(kb, args.full)
        return 0

    answer = kb.ask(" ".join(args.question))
    if args.json:
        print(json.dumps(answer.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_answer(answer, args.full))
    return 0


if __name__ == "__main__":
    sys.exit(main())
