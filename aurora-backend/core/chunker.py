"""
Heading-based chunker — splits a note into sections by markdown headings.

Each chunk carries its heading path (e.g. ["Project Alpha", "Goals", "Q3"])
so search results and LLM context can point at the exact section.

Rules:
- Headings inside fenced code blocks are ignored.
- Text before the first heading becomes a section titled after the note.
- Heading-only sections (no body text) are dropped; short sections are kept
  so they keep their own heading.
- Sections larger than MAX_TOKENS are split on paragraph boundaries.
"""

import re
from typing import List, Tuple

from data.models import Note, NoteChunk

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

MAX_TOKENS = 400


def estimate_tokens(text: str) -> int:
    """Rough estimate (~4 chars per token)."""
    return max(1, len(text) // 4)


def _split_sections(body: str, note_title: str) -> List[Tuple[List[str], str]]:
    """Split markdown body into (heading_path, text) sections."""
    sections: List[Tuple[List[str], List[str]]] = []
    stack: List[Tuple[int, str]] = []  # (level, heading text)
    current_lines: List[str] = []
    current_path: List[str] = [note_title]
    in_fence = False

    for line in body.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            current_lines.append(line)
            continue

        m = None if in_fence else HEADING_RE.match(line)
        if m:
            # Close the current section
            sections.append((current_path, current_lines))
            level = len(m.group(1))
            heading = m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading))
            # Skip a heading that just repeats the note title (common H1 pattern)
            current_path = [note_title] + [
                h for _, h in stack if h.strip().lower() != note_title.strip().lower()
            ]
            current_lines = [line]
        else:
            current_lines.append(line)

    sections.append((current_path, current_lines))

    return [
        (path, "\n".join(lines).strip())
        for path, lines in sections
        if "\n".join(lines).strip()
    ]


def _split_large(text: str) -> List[str]:
    """Split an oversized section on blank-line paragraph boundaries."""
    paragraphs = re.split(r"\n\s*\n", text)
    parts: List[str] = []
    buf: List[str] = []
    buf_tokens = 0
    for para in paragraphs:
        t = estimate_tokens(para)
        if buf and buf_tokens + t > MAX_TOKENS:
            parts.append("\n\n".join(buf))
            buf, buf_tokens = [], 0
        buf.append(para)
        buf_tokens += t
    if buf:
        parts.append("\n\n".join(buf))
    return parts


def chunk_note(note: Note) -> List[NoteChunk]:
    """Split a note into heading-based chunks (frontmatter excluded)."""
    body = note.clean_content or ""
    if not body.strip():
        return []

    raw_sections = _split_sections(body, note.title)

    # Drop heading-only sections (e.g. "## Risks" immediately followed by
    # "### Mitigation") — their heading already lives in the child's path.
    # Short sections with real text are kept so they retain their own heading.
    merged: List[Tuple[List[str], str]] = []
    for path, text in raw_sections:
        lines = text.splitlines()
        has_heading = bool(lines) and HEADING_RE.match(lines[0]) is not None
        body_text = "\n".join(lines[1:] if has_heading else lines).strip()
        if body_text:
            merged.append((path, text))

    chunks: List[NoteChunk] = []
    for path, text in merged:
        pieces = _split_large(text) if estimate_tokens(text) > MAX_TOKENS else [text]
        for piece in pieces:
            chunks.append(
                NoteChunk(
                    note_id=note.id,
                    chunk_index=len(chunks),
                    content=piece,
                    heading_path=path,
                    token_count=estimate_tokens(piece),
                    metadata={
                        # ChromaDB metadata must be scalar values
                        "path": note.path,
                        "title": note.title,
                        "heading": " > ".join(path),
                    },
                )
            )
    return chunks
