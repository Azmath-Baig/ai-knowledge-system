"""Measure search quality and refusal behaviour against a labelled question set.

Run with:  python -m knowledge_system.evaluate [--verbose]

Reports, separately, the things that can go wrong:
- retrieval:  is the right section ranked first / in the top 3?
- answering:  did we answer with the right section cited?
- refusing:   did we decline the questions the knowledge base can't answer,
              and how many answerable questions did we wrongly decline?

The score lists at the end are what the thresholds in ``config.py`` were chosen from.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from . import config
from .answerer import KnowledgeBase

DEFAULT_QUESTIONS = config.PROJECT_ROOT / "eval" / "questions.json"


@dataclass
class Report:
    answerable: int = 0
    unanswerable: int = 0
    hit_at_1: int = 0
    hit_at_3: int = 0
    correct_answers: int = 0  # answered, and the expected section is among the cited sources
    wrong_answers: int = 0  # answered, but citing the wrong section
    false_refusals: int = 0  # answerable but declined
    correct_refusals: int = 0  # unanswerable and declined
    hallucination_risks: int = 0  # unanswerable but answered anyway

    def lines(self) -> list[str]:
        a, u = self.answerable or 1, self.unanswerable or 1
        return [
            f"Answerable questions:   {self.answerable}",
            f"  Retrieval hit@1:      {self.hit_at_1 / a:.0%} ({self.hit_at_1})",
            f"  Retrieval hit@3:      {self.hit_at_3 / a:.0%} ({self.hit_at_3})",
            f"  Correct answers:      {self.correct_answers / a:.0%} ({self.correct_answers})",
            f"  Wrong section cited:  {self.wrong_answers}",
            f"  Wrongly declined:     {self.false_refusals}",
            f"Unanswerable questions: {self.unanswerable}",
            f"  Correctly declined:   {self.correct_refusals / u:.0%} ({self.correct_refusals})",
            f"  Answered anyway:      {self.hallucination_risks}",
        ]


def load_questions(path: Path = DEFAULT_QUESTIONS) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["questions"]


def evaluate(kb: KnowledgeBase, questions: list[dict], verbose: bool = False) -> Report:
    report = Report()
    right_scores: list[float] = []
    out_of_scope_scores: list[float] = []

    for item in questions:
        question, expected = item["question"], item["expected"]
        # A question may have several valid sections; normalise to a list.
        valid = [expected] if isinstance(expected, str) else expected
        results = kb.retriever.search(question, top_k=3)
        ranked_ids = [r.section.id for r in results]
        answer = kb.ask(question)
        cited = [f"{s.file}#{s.section}" for s in answer.sources]
        top_score = results[0].score if results else 0.0

        if expected is None:
            report.unanswerable += 1
            out_of_scope_scores.append(top_score)
            ok = not answer.answered
            report.correct_refusals += ok
            report.hallucination_risks += not ok
        else:
            report.answerable += 1
            report.hit_at_1 += bool(ranked_ids) and ranked_ids[0] in valid
            report.hit_at_3 += any(v in ranked_ids for v in valid)
            right_scores += [r.score for r in results if r.section.id in valid][:1]
            if not answer.answered:
                report.false_refusals += 1
                ok = False
            else:
                ok = any(v in cited for v in valid)
                report.correct_answers += ok
                report.wrong_answers += not ok

        if verbose or not ok:
            mark = "ok  " if ok else "FAIL"
            got = cited or answer.status.value
            print(f"[{mark}] {question!r}\n        expected={expected} got={got} top={top_score:.3f}")

    if verbose:
        print("\nScores of the correct section (answerable):", sorted(round(s, 3) for s in right_scores))
        print("Top scores for out-of-scope questions:  ", sorted(round(s, 3) for s in out_of_scope_scores))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--data", type=Path, default=config.DATA_DIR)
    parser.add_argument("--verbose", "-v", action="store_true", help="show every question")
    args = parser.parse_args()

    report = evaluate(KnowledgeBase.from_directory(args.data), load_questions(args.questions), args.verbose)
    print("\n" + "\n".join(report.lines()))


if __name__ == "__main__":
    main()
