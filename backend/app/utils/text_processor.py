"""
Digital FTE - Text Processing Utilities
Cleans, chunks, and preprocesses text for LLM and embedding consumption.
"""

import re
from typing import List


def clean_text(raw: str) -> str:
    """Normalize whitespace, fix encoding artifacts, clean raw CV text."""
    # Replace common encoding artifacts
    text = raw.replace("\x00", "").replace("\ufeff", "")
    # Normalize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines into double newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces (but preserve newlines)
    text = re.sub(r"[^\S\n]+", " ", text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks for embedding.
    Uses sentence boundaries where possible.
    """
    if len(text) <= chunk_size:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Overlap: keep last N characters
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + " " + sentence
            else:
                current_chunk = sentence
        else:
            current_chunk = current_chunk + " " + sentence if current_chunk else sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def extract_sections(text: str) -> dict:
    """
    Heuristic section detection from CV text.
    Returns a dict of section_name → section_text.
    """
    # Common CV section headers
    section_patterns = [
        r"(?i)(professional\s+summary|summary|profile|objective|about\s+me)",
        r"(?i)(work\s+experience|experience|employment\s+history|professional\s+experience)",
        r"(?i)(education|academic|qualifications)",
        r"(?i)(skills|technical\s+skills|core\s+competencies|competencies)",
        r"(?i)(projects|personal\s+projects|key\s+projects)",
        r"(?i)(certifications|certificates|licenses)",
        r"(?i)(languages|language\s+skills)",
        r"(?i)(awards|achievements|honors)",
        r"(?i)(publications|research)",
        r"(?i)(references)",
    ]

    combined_pattern = "|".join(f"({p})" for p in section_patterns)
    header_regex = re.compile(
        r"^[ \t]*(" + combined_pattern + r")[ \t]*:?[ \t]*$",
        re.MULTILINE | re.IGNORECASE,
    )

    matches = list(header_regex.finditer(text))
    sections = {}

    for i, match in enumerate(matches):
        header = match.group(1).strip().lower()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            # Normalize header name
            header_normalized = re.sub(r"\s+", "_", header)
            sections[header_normalized] = content

    return sections


def estimate_years_experience(text: str) -> int:
    """Rough estimate of years of experience from CV text."""
    year_pattern = re.compile(r"\b(20\d{2}|19\d{2})\b")
    years = [int(y) for y in year_pattern.findall(text)]
    if len(years) >= 2:
        return max(years) - min(years)
    return 0
