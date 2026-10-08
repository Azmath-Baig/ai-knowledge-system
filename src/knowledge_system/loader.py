"""Load Markdown knowledge-base documents and split them into citable sections.

A *section* (one ``##`` heading and its body) is the unit we index and cite.
Splitting on the authors' own headings, rather than fixed-size chunks, means
every search result maps to a location a person can open and check.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# "## 2. Remote Working" -> number "2", title "Remote Working".
# The number is optional so un-numbered headings still load.
_SECTION_HEADING = re.compile(r"^##\s+(?:(\d+)[.)]\s*)?(.+?)\s*$")
_DOC_TITLE = re.compile(r"^#\s+(.+?)\s*$")

# Files in the data folder that describe the data rather than being part of it.
IGNORED_FILES = {"readme.md"}


@dataclass(frozen=True)
class Section:
    """One citable chunk of a knowledge-base document."""

    doc_file: str  # e.g. "working_arrangements.md"
    doc_title: str  # e.g. "Working Arrangements"
    number: str  # e.g. "2"
    title: str  # e.g. "Remote Working"
    text: str  # body text, without the heading

    @property
    def citation(self) -> str:
        """Human-readable source, e.g. 'Working Arrangements — Section 2: Remote Working'."""
        return f"{self.doc_title} — Section {self.number}: {self.title}"

    @property
    def id(self) -> str:
        """Stable identifier, e.g. 'working_arrangements.md#2'. Used by tests and evaluation."""
        return f"{self.doc_file}#{self.number}"


def parse_document(text: str, doc_file: str) -> list[Section]:
    """Split one Markdown document into sections.

    Text that appears before the first ``##`` heading (an introduction) is kept
    as section "0" so it is still searchable rather than silently dropped.
    """
    doc_title = Path(doc_file).stem.replace("_", " ").title()
    sections: list[Section] = []
    current_number, current_title = "0", "Introduction"
    body: list[str] = []

    def flush() -> None:
        content = "\n".join(body).strip()
        if content:
            sections.append(Section(doc_file, doc_title, current_number, current_title, content))

    for line in text.splitlines():
        if match := _DOC_TITLE.match(line):
            doc_title = match.group(1)
            continue
        if match := _SECTION_HEADING.match(line):
            flush()
            body = []
            current_number = match.group(1) or str(len(sections) + 1)
            current_title = match.group(2)
            continue
        body.append(line)
    flush()
    return sections


def load_documents(data_dir: str | Path) -> list[Section]:
    """Load every Markdown file in ``data_dir`` (sorted, for deterministic order)."""
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Knowledge-base folder not found: {data_dir}")

    sections: list[Section] = []
    for path in sorted(data_dir.glob("*.md")):
        if path.name.lower() in IGNORED_FILES:
            continue
        doc_sections = parse_document(path.read_text(encoding="utf-8"), path.name)
        if not doc_sections:
            logger.warning("No content found in %s; skipping", path.name)
        sections.extend(doc_sections)

    if not sections:
        raise ValueError(f"No knowledge-base content found in {data_dir}")

    logger.info("Loaded %d sections from %s", len(sections), data_dir)
    return sections
